import logging
import secrets
import uuid
from datetime import timedelta
from pathlib import Path
from typing import cast

from accounts.models import User, UserManager
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models import Count, Exists, F, OuterRef, Prefetch, Subquery
from django.db.models.query_utils import Q
from django.db.utils import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import async_task, schedule
from ninja import Form, Router, Status
from ninja.files import UploadedFile
from ninja_jwt.tokens import RefreshToken

from core.utils.errors import Error
from core.utils.permissions import staff_required
from enrollments.models import CourseEnrollment, LessonProgress
from enrollments.services import expiry_from_days

from .helpers import (
    _client_ip,
    _due_form,
    _has_course_access,
    _module_locked,
    compress_pdf,
    course_duration_sq,
)
from .models import (
    Banner,
    Course,
    CourseForm,
    DownloadLog,
    FormResponse,
    Lesson,
    LessonAttachment,
    LessonComment,
    Module,
    QuizAttempt,
)
from .schemas import (
    AdminCommentOut,
    AdminCommentTreeCourseOut,
    AttachmentLibraryOut,
    BannerOut,
    BannerUpdateIn,
    CommentIn,
    CommentOut,
    CommentUpdateIn,
    CopyModuleIn,
    CourseDetailOut,
    CourseFormIn,
    CourseFormOut,
    CourseIn,
    CourseListOut,
    CourseOut,
    CourseUpdateIn,
    DueFormOut,
    FormResponseAdminOut,
    FormResponseIn,
    FreeCourseLPOut,
    FreeSignupIn,
    FreeSignupOut,
    LessonAttachmentIn,
    LessonAttachmentOut,
    LessonAttachmentUpdateIn,
    LessonIn,
    LessonOut,
    LessonUpdateIn,
    LinkAttachmentIn,
    ModuleIn,
    ModuleLibraryOut,
    ModuleOut,
    ModuleUpdateIn,
    QuizQuestionIn,
    QuizResponseAdminOut,
    QuizResultOut,
    QuizSaveIn,
    QuizStateOut,
    QuizSubmitIn,
    QuizTimerOut,
    UnreadCountOut,
    WebhookTestIn,
)

logger = logging.getLogger(__name__)

catalog_router = Router(tags=['Catalog'])
admin_router = Router(tags=['Courses Admin'])

# Helpers


def _enqueue_panda_duration(lesson) -> None:
    """Best-effort: enfileira a busca da duração do vídeo no Panda pra preencher
    duration_seconds (carga horária automática). Só p/ vídeo Panda com id; falha de
    broker não pode derrubar o CRUD da aula."""
    if lesson.video_provider != 'panda' or not lesson.video_id:
        return
    try:
        async_task('integrations.tasks.fetch_lesson_duration', lesson.id)
    except Exception:  # noqa: BLE001
        logger.exception('Falha ao enfileirar duração do vídeo Panda')


def _assert_enrolled_or_403(request, lesson: Lesson):
    now = timezone.now()

    enrolled = (
        CourseEnrollment.objects.filter(user=request.auth, course_id=lesson.module.course_id, is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .exists()
    )
    if not enrolled:
        return Status(403, Error(detail='Not enrolled'))
    if _module_locked(request.auth, lesson.module):
        return Status(403, Error(detail='Módulo bloqueado'))
    return None


# * ----------------------------------------- * #
# ? ----------- Catalog Endpoints ----------- ? #
# * ----------------------------------------- * #


@catalog_router.get('/courses', response=list[CourseListOut])
def list_my_courses(request):
    user = request.auth
    now = timezone.now()

    resume_sq = (
        LessonProgress.objects.filter(
            user=user,
            lesson__module__course=OuterRef('pk'),
            lesson__is_published=True,
            completed_at__isnull=True,
        )
        .order_by('-last_watched_at')
        .values('lesson_id')[:1]
    )

    return (
        Course.objects.filter(
            is_active=True,
            enrollments__user=user,
            enrollments__is_active=True,
        )
        .filter(Q(enrollments__expires_at__isnull=True) | Q(enrollments__expires_at__gt=now))
        .annotate(
            total_lessons=Count(
                'modules__lessons',
                filter=Q(modules__lessons__is_published=True),
                distinct=True,
            ),
            completed_lessons=Count(
                'modules__lessons',
                filter=Q(
                    modules__lessons__is_published=True,
                    modules__lessons__progress__user=user,
                    modules__lessons__progress__completed_at__isnull=False,
                ),
                distinct=True,
            ),
            duration_seconds=course_duration_sq(),
            resume_lesson_id=Subquery(resume_sq),
        )
        .distinct()
        .order_by('name')
    )


@catalog_router.get('/courses/available', response=list[CourseListOut])
def list_available_courses(request, category: str | None = None):
    user = request.auth
    now = timezone.now()

    enrolled = CourseEnrollment.objects.filter(user=user, is_active=True, course=OuterRef('pk')).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )

    qs = Course.objects.filter(is_active=True).exclude(Exists(enrolled)).filter(Q(sales_page__isnull=False) | Q(checkout_link__isnull=False))
    if category:
        qs = qs.filter(category=category)
    return qs.annotate(duration_seconds=course_duration_sq()).order_by('name')


@catalog_router.get('/courses/{course_id}', response={200: CourseDetailOut, 403: Error, 404: Error})
def course_detail(request, course_id: int):
    user = request.auth

    has_access = Course.objects.filter(
        id=course_id,
        is_active=True,
        enrollments__user=user,
        enrollments__is_active=True,
    ).exists()

    if not has_access:
        return Status(403, Error(detail='Access denied'))

    course = get_object_or_404(
        Course.objects.annotate(duration_seconds=course_duration_sq()).prefetch_related(
            Prefetch(
                'modules',
                queryset=Module.objects.filter(is_published=True)
                .order_by('order')
                .prefetch_related(
                    Prefetch(
                        'lessons',
                        queryset=Lesson.objects.filter(is_published=True).order_by('order').prefetch_related('attachments'),
                    )
                ),
            )
        ),
        id=course_id,
    )

    completed_ids = set(
        LessonProgress.objects.filter(
            user=user,
            lesson__module__course=course,
            completed_at__isnull=False,
        ).values_list('lesson_id', flat=True)
    )

    # Lock por progressão: um módulo `requires_previous` trava até TODAS as aulas
    # publicadas dos módulos anteriores estarem concluídas. Módulos já vêm em ordem;
    # acumula os ids "até aqui" e checa subset, zero query extra.
    seen_lesson_ids: set[int] = set()
    for module in getattr(course, 'modules').all():
        module._locked = module.requires_previous and not seen_lesson_ids <= completed_ids
        for lesson in module.lessons.all():
            lesson._completed_for_user = lesson.id in completed_ids
            seen_lesson_ids.add(lesson.id)

    return Status(200, course)


@catalog_router.get('/lessons/{lesson_id}/comments', response={200: list[CommentOut], 403: Error, 404: Error})
def list_comments(request, lesson_id: int):
    lesson = get_object_or_404(Lesson.objects.select_related('module'), id=lesson_id)
    if denied := _assert_enrolled_or_403(request, lesson):
        return denied
    return Status(
        200,
        LessonComment.objects.filter(lesson_id=lesson_id, parent__isnull=True)
        .select_related('author')
        .prefetch_related('replies__author')
        .order_by('created_at'),
    )


@catalog_router.post('/lessons/{lesson_id}/comments', response={201: CommentOut, 400: Error, 403: Error, 404: Error})
def create_comment(request, lesson_id: int, data: CommentIn):
    lesson = get_object_or_404(Lesson.objects.select_related('module__course'), id=lesson_id)
    if denied := _assert_enrolled_or_403(request, lesson):
        return denied
    if lesson.kind == Lesson.Kind.QUIZ:
        return Status(403, Error(detail='Comentários desativados em exercícios'))
    if not lesson.module.course.comments_enabled and not request.auth.is_staff:
        return Status(403, Error(detail='Comentários desativados neste curso'))

    parent = None
    if data.parent_id:
        parent = get_object_or_404(LessonComment, id=data.parent_id)
        if getattr(parent, 'lesson_id') != lesson.pk:
            return Status(400, Error(detail='Parent from different lesson'))
        if getattr(parent, 'parent_id', None) is not None:
            return Status(400, Error(detail='Cannot reply to a reply'))
    comment = LessonComment.objects.create(lesson=lesson, author=request.auth, parent=parent, body=data.body)
    return Status(201, comment)


@catalog_router.patch('/comments/{comment_id}', response={200: CommentOut, 403: Error, 404: Error})
def update_comment(request, comment_id: int, data: CommentUpdateIn):
    comment = get_object_or_404(LessonComment, id=comment_id)
    if getattr(comment, 'author_id') != request.auth.id:
        return Status(403, Error(detail='Not the author'))
    comment.body = data.body
    comment.updated_at = timezone.now()
    comment.save(update_fields=['body', 'updated_at'])
    return Status(200, comment)


@catalog_router.delete('/comments/{comment_id}', response={204: None, 403: Error, 404: Error})
def delete_comment(request, comment_id: int):
    comment = get_object_or_404(LessonComment, id=comment_id)
    if getattr(comment, 'author_id') != request.auth.id and not request.auth.is_staff:
        return Status(403, Error(detail='Forbidden'))
    comment.delete()
    return Status(204, None)


# * ----------------------------------------- * #
# ? ----------- Course Form (aluno) ----------- ? #
# * ----------------------------------------- * #


@catalog_router.get('/courses/{course_id}/form', response={200: DueFormOut})
def get_due_form(request, course_id: int):
    if not _has_course_access(request.auth, course_id):
        return Status(200, {'form': None})
    course = Course.objects.filter(id=course_id).first()
    form = _due_form(request.auth, course) if course else None
    return Status(200, {'form': form})


@catalog_router.post('/forms/{form_id}/responses', response={200: dict, 400: Error, 403: Error, 404: Error})
def submit_form_response(request, form_id: int, data: FormResponseIn):
    form = get_object_or_404(CourseForm, id=form_id)
    if not _has_course_access(request.auth, form.course_id):
        return Status(403, Error(detail='Not enrolled'))

    if not data.skipped:
        missing = [
            f.get('label')
            for f in form.fields
            if f.get('required') and not str(data.answers.get(f.get('key'), '')).strip()
        ]
        if missing:
            return Status(400, Error(detail=f'Campos obrigatórios: {", ".join(missing)}'))

    FormResponse.objects.create(
        form=form,
        user=request.auth,
        answers={} if data.skipped else data.answers,
        skipped=data.skipped,
    )
    return Status(200, {'ok': True})


# * ----------------------------------------- * #
# ? ------------- Quiz (aluno) --------------- ? #
# * ----------------------------------------- * #


def _quiz_result(questions: list[dict], answers: dict) -> QuizResultOut:
    """Corrige. Só roda no servidor, é aqui que o gabarito aparece pela primeira vez.
    Dissertativa (type='text') não entra na nota: coletada só. total/score contam só escolha."""
    results = []
    for q in questions:
        raw = answers.get(q['key'])
        if q.get('type', 'choice') == 'text':
            results.append({
                'key': q['key'],
                'type': 'text',
                'correct': -1,
                'chosen': None,
                'answer_text': str(raw) if raw is not None else None,
                'explanation': q.get('explanation', ''),
            })
        else:
            results.append({
                'key': q['key'],
                'type': 'choice',
                'correct': q['correct'],
                'chosen': raw if isinstance(raw, int) else None,
                'explanation': q.get('explanation', ''),
            })
    choice = [r for r in results if r['type'] == 'choice']
    score = sum(1 for r in choice if r['chosen'] == r['correct'])
    return QuizResultOut(score=score, total=len(choice), results=results)


QUIZ_TIMEOUT_GRACE = 3  # segundos de folga p/ latência de rede (submit no limite não vira falha)


def _attempt_result(questions: list[dict], attempt) -> QuizResultOut:
    """Resultado de uma tentativa já finalizada. Respeita a nota guardada, timeout ficou
    com score=0 mesmo que a correção das respostas parciais desse mais."""
    r = _quiz_result(questions, attempt.answers)
    r.score = attempt.score
    r.total = attempt.total
    return r


def _quiz_timer_out(lesson, attempt) -> QuizTimerOut | None:
    """Timer da tentativa em curso (started_at setado, submitted_at nulo). Deixa o front
    retomar o tempo restante após reload sem confiar no relógio do cliente."""
    if not lesson.time_limit_seconds or not attempt or attempt.submitted_at or not attempt.started_at:
        return None
    return QuizTimerOut(
        started_at=attempt.started_at,
        expires_at=attempt.started_at + timedelta(seconds=lesson.time_limit_seconds),
        server_now=timezone.now(),
    )


def _quiz_expired(lesson, attempt, now) -> bool:
    """Tentativa aberta cujo tempo (+GRACE) já estourou no relógio do servidor."""
    return bool(
        lesson.time_limit_seconds
        and attempt
        and attempt.started_at
        and not attempt.submitted_at
        and now > attempt.started_at + timedelta(seconds=lesson.time_limit_seconds + QUIZ_TIMEOUT_GRACE)
    )


@catalog_router.get('/lessons/{lesson_id}/quiz', response={200: QuizStateOut, 403: Error, 404: Error})
def get_lesson_quiz(request, lesson_id: int):
    lesson = get_object_or_404(Lesson.objects.select_related('module__course'), id=lesson_id)
    if denied := _assert_enrolled_or_403(request, lesson):  # acesso + lock de módulo
        return denied

    questions = lesson.questions or []
    attempt = QuizAttempt.objects.filter(lesson=lesson, user=request.auth).first()

    # Detecção preguiçosa: tentativa aberta que já venceu vira falha por timeout aqui
    # mesmo, defesa extra à task ONCE. A guarda atômica evita webhook duplicado.
    if _quiz_expired(lesson, attempt, timezone.now()):
        from .tasks import _apply_timeout

        _apply_timeout(lesson, request.auth, attempt)
        attempt.refresh_from_db()

    # Só é "resultado" quando a tentativa foi finalizada (submitted_at != None).
    submitted = attempt and attempt.submitted_at
    return Status(200, {
        'questions': questions,
        'attempt': _attempt_result(questions, attempt) if submitted else None,
        'allow_retake': lesson.allow_retake,
        'time_limit_seconds': lesson.time_limit_seconds,
        'timer': _quiz_timer_out(lesson, attempt),
        'attempts': attempt.attempts if attempt else 0,
        'timed_out': bool(attempt.timed_out) if attempt else False,
    })


@catalog_router.post('/lessons/{lesson_id}/quiz/start', response={200: QuizTimerOut, 400: Error, 403: Error, 404: Error, 409: Error})
def start_lesson_quiz(request, lesson_id: int):
    """Marca o início da tentativa cronometrada (fonte da verdade do tempo é o servidor) e
    agenda o vencimento. Reload não estende o tempo, devolve o mesmo timer."""
    lesson = get_object_or_404(Lesson.objects.select_related('module__course'), id=lesson_id)
    if denied := _assert_enrolled_or_403(request, lesson):
        return denied
    if not lesson.time_limit_seconds:
        return Status(400, Error(detail='Exercício sem tempo'))

    now = timezone.now()
    attempt = QuizAttempt.objects.filter(lesson=lesson, user=request.auth).first()

    # Tentativa aberta ainda no prazo → mesmo timer (anti-trapaça: reload não reseta).
    if attempt and attempt.started_at and not attempt.submitted_at and not _quiz_expired(lesson, attempt, now):
        return Status(200, _quiz_timer_out(lesson, attempt))

    # Aberta mas vencida → fecha como falha antes de decidir recomeçar.
    if _quiz_expired(lesson, attempt, now):
        from .tasks import _apply_timeout

        _apply_timeout(lesson, request.auth, attempt)
        attempt.refresh_from_db()

    # 1 tentativa: já finalizou e refazer desligado → travado.
    if not lesson.allow_retake and attempt and attempt.submitted_at:
        return Status(409, Error(detail='Exercício já respondido'))

    if attempt:
        QuizAttempt.objects.filter(pk=attempt.pk).update(started_at=now, submitted_at=None)
        attempt.started_at, attempt.submitted_at = now, None
    else:
        attempt = QuizAttempt.objects.create(lesson=lesson, user=request.auth, started_at=now)

    # ONCE no vencimento: fecha a falha mesmo se o aluno fechar a aba. Guarda por started_at
    # torna a task idempotente; a ONCE se auto-remove após rodar (sem cancelamento).
    schedule(
        'courses.tasks.finalize_quiz_timeout',
        lesson.id,
        request.auth.id,
        now.isoformat(),
        schedule_type=Schedule.ONCE,
        next_run=now + timedelta(seconds=lesson.time_limit_seconds + QUIZ_TIMEOUT_GRACE),
    )
    return Status(200, _quiz_timer_out(lesson, attempt))


@catalog_router.post('/lessons/{lesson_id}/quiz', response={200: QuizResultOut, 400: Error, 403: Error, 404: Error, 409: Error})
def submit_lesson_quiz(request, lesson_id: int, data: QuizSubmitIn):
    lesson = get_object_or_404(Lesson.objects.select_related('module__course'), id=lesson_id)
    if denied := _assert_enrolled_or_403(request, lesson):  # acesso + lock de módulo
        return denied

    questions = lesson.questions or []
    if not questions:
        return Status(400, Error(detail='Aula sem perguntas'))

    attempt = QuizAttempt.objects.filter(lesson=lesson, user=request.auth).first()

    # 1 tentativa: já finalizou e o admin desligou o refazer → bloqueia sobrescrita.
    if not lesson.allow_retake and attempt and attempt.submitted_at:
        return Status(409, Error(detail='Exercício já respondido'))

    now = timezone.now()
    # Timeout se: (a) o cliente sinalizou (auto-submit no zero), confiamos porque só
    # PIORA p/ o aluno, sem incentivo a trapaça; ou (b) o servidor vê o tempo estourado
    # (limite+GRACE), pega quem manda timed_out=false e submete atrasado.
    is_timeout = bool(lesson.time_limit_seconds) and (
        data.timed_out or not attempt or not attempt.started_at or _quiz_expired(lesson, attempt, now)
    )

    if is_timeout:
        from .tasks import _apply_timeout

        if attempt is None or attempt.submitted_at:
            # submeteu sem start (ou tentativa já fechada) → abre uma p/ registrar a falha.
            attempt = QuizAttempt.objects.create(lesson=lesson, user=request.auth, started_at=now)
        result = _apply_timeout(lesson, request.auth, attempt, answers=data.answers)
        if result is None:  # a task ONCE já fechou este ciclo
            attempt.refresh_from_db()
            result = _attempt_result(questions, attempt)
        return Status(200, result)

    result = _quiz_result(questions, data.answers)
    defaults = {
        'answers': data.answers,
        'score': result.score,
        'total': result.total,
        'timed_out': False,
        'submitted_at': now,
        'started_at': None,
    }
    if attempt:
        QuizAttempt.objects.filter(pk=attempt.pk).update(attempts=F('attempts') + 1, **defaults)
        attempt.refresh_from_db(fields=['attempts'])
    else:
        attempt = QuizAttempt.objects.create(lesson=lesson, user=request.auth, attempts=1, **defaults)

    # Responder conclui a aula. `last_watched_at` é auto_now, não precisa passar.
    LessonProgress.objects.update_or_create(
        user=request.auth,
        lesson=lesson,
        defaults={'completed_at': now},
    )

    if lesson.module.course.quiz_webhook_url:
        from .tasks import _quiz_webhook_payload  # evita import de rede no boot

        async_task(
            'courses.tasks.fire_quiz_webhook',
            lesson.module.course.quiz_webhook_url,
            _quiz_webhook_payload(lesson, request.auth, result, data.answers, attempt=attempt.attempts),
            settings.QUIZ_WEBHOOK_SECRET,
        )
    return Status(200, result)


@catalog_router.get('/attachments/{attachment_id}/download', response={403: Error, 404: Error})
def download_attachment(request, attachment_id: int):
    att = get_object_or_404(LessonAttachment.objects.select_related('lesson__module'), id=attachment_id)
    if denied := _assert_enrolled_or_403(request, att.lesson):  # acesso + lock de módulo
        return denied

    # Trilha forense: quem clicou baixar, quando, IP. Snapshot do email sobrevive à edição do user.
    DownloadLog.objects.create(user=request.auth, attachment=att, email=request.auth.email, ip=_client_ip(request) or None)

    # ponytail: carimbo por-usuário DESLIGADO. Proxiar (ler o arquivo pelo backend e reenviar) sobre o
    # MinIO lento (~0.5 MB/s) dava TTFB enorme + prendia worker → download de 1min. Redirect = 1 hop,
    # stream nativo do MinIO, worker liberado na hora. Bucket é public-read (a marca já vazava pela URL
    # direta). DownloadLog acima mantém a trilha. Religar carimbo real = CDN/bucket privado + LAN; aí
    # voltar a ler att.file_url e carimbar com _stamp_pdf/_stamp_image (ainda em courses/helpers.py).
    return HttpResponseRedirect(att.file_url.url)


@catalog_router.get('/banners', response=list[BannerOut])
def list_active_banners(request):
    return Banner.objects.filter(is_active=True)


# * ----------------------------------------- * #
# ? --------- LP de curso gratuito ---------- ? #
# * ----------------------------------------- * #
# Públicos (auth=None): a LP fica no subdomínio de cursos, sem login. Só operam em
# curso is_free=True, nunca matriculam num curso pago (gate de segurança).


@catalog_router.get('/free/{slug}', response={200: FreeCourseLPOut, 404: Error}, auth=None)
def free_course_lp(request, slug: str):
    course = Course.objects.filter(slug=slug, is_free=True).first()
    if not course:
        return Status(404, Error(detail='Curso não encontrado'))
    return Status(200, course)


@catalog_router.post('/free/{slug}/signup', response={200: FreeSignupOut, 404: Error}, auth=None)
def free_course_signup(request, slug: str, data: FreeSignupIn):
    course = Course.objects.filter(slug=slug, is_free=True).first()
    if not course:
        return Status(404, Error(detail='Curso não encontrado'))

    email = data.email.strip().lower()
    phone = (data.phone or '').strip()

    user = User.objects.filter(email=email).first()
    created = user is None
    if created:
        user = cast(UserManager, User.objects).create_user(
            email=email, password=secrets.token_urlsafe(32), name=(data.name or '').strip()
        )
        if phone:
            user.phone = phone
            user.save(update_fields=['phone'])
    elif phone and not user.phone:
        user.phone = phone
        user.save(update_fields=['phone'])

    CourseEnrollment.objects.get_or_create(
        user=user,
        course=course,
        defaults={'source': 'lp', 'expires_at': expiry_from_days(course.access_days), 'is_active': True},
    )

    # Envio do acesso. Novo = email "definir senha"; existente = aviso de matrícula
    # (login com a senha dele). WhatsApp (best-effort) só sai se EvolutionConfig ativo.
    if created:
        async_task('accounts.tasks.send_welcome_email_with_reset', user.pk)
    else:
        async_task('accounts.tasks.send_external_access_email', user.pk, [course.name])
    if user.phone:
        try:
            async_task('integrations.tasks.send_whatsapp_access', user.pk)
        except Exception:
            logger.exception('Falha ao enfileirar whatsapp de acesso (LP)')

    # Segurança: só auto-loga (emite JWT) conta RECÉM-criada nesta request. Email já
    # existente jamais é logado por um POST público, evita account takeover. O dono
    # da conta existente entra pelos canais que provam posse (email/WhatsApp).
    access = refresh = None
    if created:
        token = RefreshToken.for_user(user)
        access, refresh = str(token.access_token), str(token)

    return Status(200, FreeSignupOut(created=created, course_id=course.id, access=access, refresh=refresh))


# * ----------------------------------------- * #
# ? ----------- Admin Endpoints ----------- ? #
# * ----------------------------------------- * #


@admin_router.get('/courses', response=list[CourseOut])
def list_all_courses(request):
    staff_required(request)

    return Course.objects.all().order_by('-created_at')


@admin_router.post('/courses', response={201: CourseOut, 403: Error})
def create_course(request, data: CourseIn):
    staff_required(request)

    course = Course.objects.create(
        name=data.name,
        slug=data.slug or None,
        is_free=data.is_free,
        lp_template=data.lp_template or '',
        image=data.image,
        category=data.category,
        sales_page=data.sales_page,
        checkout_link=data.checkout_link,
        is_active=data.is_active,
        kiwify_product_id=data.kiwify_product_id,
        access_days=data.access_days,
        quiz_webhook_url=data.quiz_webhook_url,
        comments_enabled=data.comments_enabled,
        certificate_enabled=data.certificate_enabled,
        certificate_hours=data.certificate_hours,
    )

    return Status(201, course)


@admin_router.post('/courses/quiz-webhook/test', response={200: dict, 400: Error, 403: Error})
def test_quiz_webhook(request, data: WebhookTestIn):
    staff_required(request)

    url = (data.url or '').strip()
    if not url:
        return Status(400, Error(detail='Informe a URL do webhook'))
    from .tasks import check_quiz_webhook  # lazy: evita import de rede no boot

    return Status(200, check_quiz_webhook(url))


@admin_router.put('/courses/{course_id}', response={200: CourseOut, 403: Error, 404: Error})
def update_course(request, course_id: int, data: CourseUpdateIn):
    staff_required(request)

    course = get_object_or_404(Course, id=course_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        if field == 'slug' and not value:
            value = None  # slug vazio → NULL (unique não aceita vários '')
        setattr(course, field, value)

    course.save()

    return Status(200, course)


@admin_router.delete('/courses/{course_id}', response={204: None, 403: Error, 404: Error})
def delete_course(request, course_id: int):
    staff_required(request)

    course = get_object_or_404(Course, id=course_id)

    course.delete()

    return Status(204, None)


@admin_router.post('/courses/{course_id}/image', response={200: CourseOut, 400: Error, 404: Error})
def upload_course_image(request, course_id: int, file: UploadedFile):
    staff_required(request)
    course = get_object_or_404(Course, id=course_id)

    if file.size is None or file.size > 5 * 1024 * 1024:
        return Status(400, Error(detail='Image too large (max 5MB)'))
    if file.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        return Status(400, Error(detail='Invalid image type: jpg, png or webp'))
    if not file.name:
        return Status(400, Error(detail='Name is required'))

    ext = Path(file.name).suffix.lower()
    new_name = f'{uuid.uuid4().hex}{ext}'
    if course.image:
        course.image.delete(save=False)
    course.image.save(new_name, file, save=True)
    return Status(200, course)


@admin_router.post('/modules', response={201: ModuleOut, 403: Error, 404: Error, 409: Error})
def create_module(request, data: ModuleIn):
    staff_required(request)

    if not Course.objects.filter(id=data.course_id).exists():
        return Status(404, Error(detail='Course not found'))

    current_max = Module.objects.filter(course_id=data.course_id).aggregate(models.Max('order'))['order__max']
    next_order = 0 if current_max is None else current_max + 1

    try:
        module = Module.objects.create(
            course_id=data.course_id,
            name=data.name,
            order=data.order if data.order > 0 else next_order,
            is_published=data.is_published,
        )
    except IntegrityError:
        return Status(409, Error(detail='Order conflict'))
    return Status(201, module)


@admin_router.get('/modules/{module_id}', response={200: ModuleOut, 404: Error})
def get_module(request, module_id: int):
    staff_required(request)
    return get_object_or_404(Module, id=module_id)


@admin_router.get('/modules', response=list[ModuleOut])
def list_modules(request, course_id: int):
    staff_required(request)
    return Module.objects.filter(course_id=course_id).order_by('order')


@admin_router.put('/modules/{module_id}', response={200: ModuleOut, 403: Error, 404: Error, 409: Error})
def update_module(request, module_id: int, data: ModuleUpdateIn):
    staff_required(request)

    module = get_object_or_404(Module, id=module_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(module, field, value)

    try:
        module.save()
    except IntegrityError:
        return Status(409, Error(detail='Order conflict'))
    return Status(200, module)


@admin_router.delete('/modules/{module_id}', response={204: None, 403: Error, 404: Error})
def delete_module(request, module_id: int):
    staff_required(request)
    module = get_object_or_404(Module, id=module_id)
    module.delete()
    return Status(204, None)


@admin_router.patch('/courses/{course_id}/modules/reorder', response={204: None, 403: Error, 404: Error})
def reorder_modules(request, course_id: int, order: list[int]):
    staff_required(request)

    if not Course.objects.filter(id=course_id).exists():
        return Status(404, Error(detail='Course does not exist'))

    with transaction.atomic():
        Module.objects.filter(course_id=course_id).update(order=-1 * (F('order') + 1))
        for new_order, module_id in enumerate(order):
            Module.objects.filter(id=module_id, course_id=course_id).update(order=new_order)

    return Status(204, None)


@admin_router.get('/module-library', response=list[ModuleLibraryOut])
def module_library(request, q: str = '', exclude_course_id: int | None = None, limit: int = 200):
    """Módulos de qualquer curso, pro admin importar (copiar) noutro curso.
    Path com hífen p/ não colidir com /modules/{module_id} (int)."""
    staff_required(request)

    qs = Module.objects.select_related('course').annotate(lesson_count=Count('lessons'))
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(course__name__icontains=q))
    if exclude_course_id:
        qs = qs.exclude(course_id=exclude_course_id)
    return qs.order_by('course__name', 'order')[:limit]


@admin_router.post('/modules/{module_id}/copy', response={201: ModuleOut, 403: Error, 404: Error})
def copy_module(request, module_id: int, data: CopyModuleIn):
    """Deep-clone de um módulo (aulas + anexos) noutro curso. Snapshot independente:
    editar o original depois não reflete na cópia. Anexos apontam pra mesma chave no
    MinIO (sem re-upload, igual link_attachment). Progresso/quiz ficam separados porque
    as aulas têm ids novos. access_days sai do curso destino (acesso é por matrícula)."""
    staff_required(request)

    src = get_object_or_404(Module.objects.prefetch_related('lessons__attachments'), id=module_id)
    if not Course.objects.filter(id=data.course_id).exists():
        return Status(404, Error(detail='Course not found'))

    with transaction.atomic():
        cur = Module.objects.filter(course_id=data.course_id).aggregate(models.Max('order'))['order__max']
        new_module = Module.objects.create(
            course_id=data.course_id,
            name=src.name,
            order=0 if cur is None else cur + 1,
            is_published=False,  # entra despublicado; admin revisa e libera
            requires_previous=src.requires_previous,
        )
        for lesson in src.lessons.all():  # order original já é único no módulo novo (fresco)
            new_lesson = Lesson.objects.create(
                module=new_module,
                name=lesson.name,
                kind=lesson.kind,
                questions=lesson.questions,
                description=lesson.description,
                video_provider=lesson.video_provider,
                video_id=lesson.video_id,
                content=lesson.content,
                duration_seconds=lesson.duration_seconds,
                allow_retake=lesson.allow_retake,
                time_limit_seconds=lesson.time_limit_seconds,
                order=lesson.order,
                is_published=lesson.is_published,
            )
            LessonAttachment.objects.bulk_create([
                LessonAttachment(
                    lesson=new_lesson,
                    title=a.title,
                    file_url=a.file_url.name,  # mesma chave MinIO, sem re-upload
                    size_bytes=a.size_bytes,
                    order=a.order,
                )
                for a in lesson.attachments.all()
            ])
    return Status(201, new_module)


@admin_router.post('/lessons', response={201: LessonOut, 403: Error, 404: Error, 409: Error})
def create_lesson(request, data: LessonIn):
    staff_required(request)

    if not Module.objects.filter(id=data.module_id).exists():
        return Status(404, Error(detail='Module does not exist'))

    current_max = Lesson.objects.filter(module_id=data.module_id).aggregate(models.Max('order'))['order__max']
    next_order = 0 if current_max is None else current_max + 1

    try:
        lesson = Lesson.objects.create(
            module_id=data.module_id,
            name=data.name,
            kind=data.kind,
            description=data.description or '',
            video_provider=data.video_provider or '',
            video_id=data.video_id or '',
            content=data.content or '',
            duration_seconds=data.duration_seconds or 0,
            allow_retake=data.allow_retake,
            time_limit_seconds=data.time_limit_seconds or 0,
            order=data.order if data.order > 0 else next_order,
            is_published=data.is_published,
        )
    except IntegrityError:
        return Status(409, Error(detail='Order conflict or invalid video fields'))
    _enqueue_panda_duration(lesson)
    return Status(201, lesson)


@admin_router.get('/lessons/{lesson_id}', response={200: LessonOut, 404: Error})
def get_lesson(request, lesson_id: int):
    staff_required(request)
    return get_object_or_404(Lesson, id=lesson_id)


@admin_router.get('/lessons', response=list[LessonOut])
def list_lessons(request, module_id: int):
    staff_required(request)
    return Lesson.objects.filter(module_id=module_id).order_by('order')


@admin_router.put('/lessons/{lesson_id}', response={200: LessonOut, 403: Error, 404: Error, 409: Error})
def update_lesson(request, lesson_id: int, data: LessonUpdateIn):
    staff_required(request)

    lesson = get_object_or_404(Lesson, id=lesson_id)
    old_video = (lesson.video_provider, lesson.video_id)

    dumped = data.model_dump(exclude_unset=True)
    text_fields = {'description', 'video_provider', 'video_id', 'content'}
    for field, value in dumped.items():
        if field in text_fields and value is None:
            value = ''
        setattr(lesson, field, value)

    try:
        lesson.save()
    except IntegrityError:
        return Status(409, Error(detail='Invalid video fields or order conflict'))
    # Só rebusca no Panda se o vídeo REALMENTE mudou: não sobrescreve a duração digitada
    # à mão a cada save (publicar/renomear) nem re-varre a biblioteca à toa.
    if (lesson.video_provider, lesson.video_id) != old_video:
        _enqueue_panda_duration(lesson)
    return Status(200, lesson)


@admin_router.delete('/lessons/{lesson_id}', response={204: None, 403: Error, 404: Error})
def delete_lesson(request, lesson_id: int):
    staff_required(request)

    lesson = get_object_or_404(Lesson, id=lesson_id)
    lesson.delete()
    return Status(204, None)


@admin_router.patch('/modules/{module_id}/lessons/reorder', response={204: None, 403: Error, 404: Error})
def reorder_lessons(request, module_id: int, order: list[int]):
    staff_required(request)

    if not Module.objects.filter(id=module_id).exists():
        return Status(404, Error(detail='Module does not exist'))

    with transaction.atomic():
        Lesson.objects.filter(module_id=module_id).update(order=-1 * (F('order') + 1))
        for new_order, lesson_id in enumerate(order):
            Lesson.objects.filter(id=lesson_id, module_id=module_id).update(order=new_order)
    return Status(204, None)


@admin_router.post('/attachments', response={201: LessonAttachmentOut, 403: Error, 404: Error})
def create_attachment(request, data: LessonAttachmentIn):
    staff_required(request)

    if not Lesson.objects.filter(id=data.lesson_id).exists():
        return Status(404, Error(detail='Lesson not found'))

    attachment = LessonAttachment.objects.create(
        lesson_id=data.lesson_id,
        title=data.title,
        file_url=data.file_url,
        size_bytes=data.size_bytes,
        order=data.order,
    )
    return Status(201, attachment)


@admin_router.get('/attachments', response=list[AttachmentLibraryOut])
def attachment_library(request, q: str = '', limit: int = 100):
    """Biblioteca de anexos já enviados, pro admin reaproveitar em outra aula."""
    staff_required(request)

    qs = LessonAttachment.objects.exclude(file_url='')
    if q:
        qs = qs.filter(title__icontains=q)

    # DISTINCT ON (Postgres): 1 linha por arquivo, a mais recente. Sem isso um PDF
    # reusado em N aulas polui a lista com N entradas idênticas.
    ids = list(qs.order_by('file_url', '-id').distinct('file_url').values_list('id', flat=True))
    return (
        LessonAttachment.objects.filter(id__in=ids)
        .select_related('lesson__module__course')
        .order_by('-id')[:limit]
    )


@admin_router.post('/lessons/{lesson_id}/attachments/link', response={201: LessonAttachmentOut, 403: Error, 404: Error})
def link_attachment(request, lesson_id: int, data: LinkAttachmentIn):
    staff_required(request)
    lesson = get_object_or_404(Lesson, id=lesson_id)
    src = get_object_or_404(LessonAttachment, id=data.attachment_id)

    current_max = LessonAttachment.objects.filter(lesson=lesson).aggregate(models.Max('order'))['order__max']

    # ponytail: aponta pra MESMA chave no MinIO (file_url.name), sem re-upload.
    # Seguro porque delete_attachment só apaga a linha, nunca o objeto do bucket.
    attachment = LessonAttachment.objects.create(
        lesson=lesson,
        title=src.title,
        file_url=src.file_url.name,
        size_bytes=src.size_bytes,
        order=0 if current_max is None else current_max + 1,
    )
    return Status(201, attachment)


@admin_router.get('/lessons/{lesson_id}/attachments', response=list[LessonAttachmentOut])
def list_attachments(request, lesson_id: int):
    staff_required(request)
    return LessonAttachment.objects.filter(lesson_id=lesson_id).order_by('order', 'id')


@admin_router.post('/lessons/{lesson_id}/attachments/upload', response={201: LessonAttachmentOut, 400: Error, 404: Error})
def upload_attachment(request, lesson_id: int, file: UploadedFile, title: str | None = None):
    staff_required(request)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if file.size is None or file.size > 50 * 1024 * 1024:
        return Status(400, Error(detail='Arquivo muito grande (max 50MB)'))
    if not file.name:
        return Status(400, Error(detail='Nome ausente'))

    ext = Path(file.name).suffix.lower()
    new_name = f'{uuid.uuid4().hex}{ext}'

    current_max = LessonAttachment.objects.filter(lesson=lesson).aggregate(models.Max('order'))['order__max']
    next_order = 0 if current_max is None else current_max + 1

    attachment = LessonAttachment(lesson=lesson, title=title or file.name, order=next_order)
    if ext == '.pdf':
        # Comprime na entrada (gs /printer): apostila image-heavy encolhe ~8x sem perda perceptível.
        # compress_pdf devolve o original se o gs falhar/não encolher, então nunca piora.
        blob = compress_pdf(file.read())
        attachment.size_bytes = len(blob)
        attachment.file_url.save(new_name, ContentFile(blob), save=False)
    else:
        attachment.size_bytes = file.size
        attachment.file_url.save(new_name, file, save=False)
    attachment.save()
    return Status(201, attachment)


@admin_router.put('/attachments/{attachment_id}', response={200: LessonAttachmentOut, 403: Error, 404: Error})
def update_attachment(request, attachment_id: int, data: LessonAttachmentUpdateIn):
    staff_required(request)

    attachment = get_object_or_404(LessonAttachment, id=attachment_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(attachment, field, value)
    attachment.save()
    return Status(200, attachment)


@admin_router.delete('/attachments/{attachment_id}', response={204: None, 403: Error, 404: Error})
def delete_attachment(request, attachment_id: int):
    staff_required(request)

    attachment = get_object_or_404(LessonAttachment, id=attachment_id)
    attachment.delete()
    return Status(204, None)

# * ----------------------------------------- * #
# ? ----------- Forms Endpoints ----------- ? #
# * ----------------------------------------- * #


@admin_router.get('/courses/{course_id}/form', response={200: DueFormOut, 403: Error})
def get_course_form(request, course_id: int):
    staff_required(request)
    form = (
        CourseForm.objects.filter(course_id=course_id, is_active=True)
        .order_by('-updated_at')
        .first()
    )
    return Status(200, {'form': form})


@admin_router.put('/courses/{course_id}/form', response={200: CourseFormOut, 403: Error, 404: Error})
def upsert_course_form(request, course_id: int, data: CourseFormIn):
    staff_required(request)
    course = get_object_or_404(Course, id=course_id)

    fields = []
    for i, f in enumerate(data.fields):
        d = f.dict()
        d['key'] = d['key'] or f'campo_{i}'  # chave estável p/ casar resposta↔campo
        if d['type'] != 'choice':
            d['options'] = []
        fields.append(d)

    form = course.forms.filter(is_active=True).order_by('-updated_at').first() or CourseForm(course=course)
    form.title = data.title
    form.description = data.description
    form.fields = fields
    form.every_days = data.every_days
    form.required = data.required
    form.is_active = data.is_active
    form.save()
    return Status(200, form)


@admin_router.get('/courses/{course_id}/form/responses', response={200: list[FormResponseAdminOut], 403: Error})
def list_form_responses(request, course_id: int):
    staff_required(request)
    qs = (
        FormResponse.objects.filter(form__course_id=course_id, skipped=False)
        .select_related('user')
        .order_by('-created_at')
    )
    return Status(200, list(qs))


# * ----------------------------------------- * #
# ? ----------- Quiz Endpoints (admin) ------ ? #
# * ----------------------------------------- * #


@admin_router.get('/lessons/{lesson_id}/quiz', response={200: list[QuizQuestionIn], 403: Error, 404: Error})
def get_lesson_quiz_admin(request, lesson_id: int):
    staff_required(request)
    lesson = get_object_or_404(Lesson, id=lesson_id)
    return Status(200, lesson.questions or [])


@admin_router.put('/lessons/{lesson_id}/quiz', response={200: list[QuizQuestionIn], 403: Error, 404: Error})
def save_lesson_quiz(request, lesson_id: int, data: QuizSaveIn):
    staff_required(request)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    questions = []
    for i, q in enumerate(data.questions):
        d = q.dict()
        d['key'] = d['key'] or f'q_{i}'  # chave estável p/ casar resposta↔pergunta
        d['options'] = [o for o in d['options'] if o.strip()]
        questions.append(d)

    lesson.questions = questions
    lesson.save(update_fields=['questions', 'updated_at'])
    return Status(200, questions)


@admin_router.get('/lessons/{lesson_id}/quiz/responses', response={200: list[QuizResponseAdminOut], 403: Error})
def list_quiz_responses(request, lesson_id: int):
    staff_required(request)
    # Só tentativas finalizadas (ignora as em curso, ainda sem submit).
    qs = (
        QuizAttempt.objects.filter(lesson_id=lesson_id, submitted_at__isnull=False)
        .select_related('user')
        .order_by('-updated_at')
    )
    return Status(200, list(qs))


# * ----------------------------------------- * #
# ? ------- Comment Moderation (admin) ------- ? #
# * ----------------------------------------- * #


def _pending_q():
    """Comentário que ainda precisa de moderação: de aluno e não resolvido."""
    return Q(comments__resolved_at__isnull=True) & Q(comments__author__is_staff=False)


def _resolve_thread(root_id: int):
    """Marca a thread inteira (raiz + respostas) como moderada, sai da fila."""
    LessonComment.objects.filter(Q(id=root_id) | Q(parent_id=root_id)).update(resolved_at=timezone.now())


@admin_router.get('/comments/tree', response=list[AdminCommentTreeCourseOut])
def comments_tree(request):
    """Fila de moderação: Curso > Módulo > Aula, só aulas com comentário PENDENTE."""
    staff_required(request)
    qs = (
        Lesson.objects.select_related('module__course')
        .annotate(pending_count=Count('comments', distinct=True, filter=_pending_q()))
        .filter(pending_count__gt=0)
        .order_by('module__course__name', 'module__order', 'order')
    )

    courses: dict = {}
    for lesson in qs:
        course, module = lesson.module.course, lesson.module
        cnode = courses.setdefault(course.id, {'course_id': course.id, 'course_name': course.name, 'modules': {}})
        mnode = cnode['modules'].setdefault(
            module.id, {'module_id': module.id, 'module_name': module.name, 'lessons': []}
        )
        mnode['lessons'].append(
            {'lesson_id': lesson.id, 'lesson_name': lesson.name, 'pending_count': lesson.pending_count}
        )
    return [
        {'course_id': c['course_id'], 'course_name': c['course_name'], 'modules': list(c['modules'].values())}
        for c in courses.values()
    ]


@admin_router.get('/comments/unread-count', response=UnreadCountOut)
def comments_unread_count(request):
    """Badge = total de comentários pendentes (de aluno, não resolvidos)."""
    staff_required(request)
    count = LessonComment.objects.filter(author__is_staff=False, resolved_at__isnull=True).count()
    return {'count': count}


def _lesson_thread(lesson_id: int):
    return (
        LessonComment.objects.filter(lesson_id=lesson_id, parent__isnull=True)
        .select_related('author')
        .prefetch_related('replies__author')
        .order_by('created_at')
    )


@admin_router.get('/lessons/{lesson_id}/comments', response=list[AdminCommentOut])
def admin_lesson_comments(request, lesson_id: int):
    """Thread da aula pro admin (só leitura), sem gate de matrícula (mirror de list_comments)."""
    staff_required(request)
    return _lesson_thread(lesson_id)


@admin_router.post('/lessons/{lesson_id}/comments/read', response=list[AdminCommentOut])
def admin_read_lesson_comments(request, lesson_id: int):
    """Abrir a aula = moderar: marca todos os pendentes da aula como vistos → saem da fila."""
    staff_required(request)
    LessonComment.objects.filter(
        lesson_id=lesson_id, resolved_at__isnull=True, author__is_staff=False
    ).update(resolved_at=timezone.now())
    return _lesson_thread(lesson_id)


@admin_router.post('/comments/{comment_id}/reply', response={201: AdminCommentOut, 404: Error})
def reply_comment(request, comment_id: int, data: CommentUpdateIn):
    staff_required(request)
    target = get_object_or_404(LessonComment, id=comment_id)
    root_id = target.parent_id or target.id  # 1 nível: anexa na raiz da thread
    reply = LessonComment.objects.create(
        lesson_id=target.lesson_id, author=request.auth, parent_id=root_id, body=data.body
    )
    _resolve_thread(root_id)  # responder = moderar → tira a thread da fila
    return Status(201, reply)


# * ----------------------------------------- * #
# ? ----------- Banners Endpoints ----------- ? #
# * ----------------------------------------- * #


@admin_router.get('/banners', response=list[BannerOut])
def list_banners(request):
    staff_required(request)
    return Banner.objects.all()


@admin_router.post('/banners', response={201: BannerOut, 400: Error, 403: Error})
def create_banner(request, file: UploadedFile, title: str = Form(...), url: str = Form(...), is_active: bool = Form(False)):
    staff_required(request)

    if not url.startswith(('http://', 'https://')):
        return Status(400, Error(detail='URL deve começar com http:// ou https://'))
    if file.size is None or file.size > 5 * 1024 * 1024:
        return Status(400, Error(detail='Imagem muito grande (max 5MB)'))
    if file.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        return Status(400, Error(detail='Tipo inválido: jpg, png ou webp'))
    if not file.name:
        return Status(400, Error(detail='Nome ausente'))

    ext = Path(file.name).suffix.lower()
    new_name = f'{uuid.uuid4().hex}{ext}'
    banner = Banner(title=title, url=url, is_active=is_active)
    banner.image.save(new_name, file, save=True)
    return Status(201, banner)


@admin_router.put('/banners/{banner_id}', response={200: BannerOut, 400: Error, 403: Error, 404: Error})
def update_banner(request, banner_id: int, data: BannerUpdateIn):
    staff_required(request)

    banner = get_object_or_404(Banner, id=banner_id)
    payload = data.model_dump(exclude_unset=True)
    if 'url' in payload and not payload['url'].startswith(('http://', 'https://')):
        return Status(400, Error(detail='URL deve começar com http:// ou https://'))

    for field, value in payload.items():
        setattr(banner, field, value)
    banner.save()
    return Status(200, banner)


@admin_router.delete('/banners/{banner_id}', response={204: None, 403: Error, 404: Error})
def delete_banner(request, banner_id: int):
    staff_required(request)

    banner = get_object_or_404(Banner, id=banner_id)
    if banner.image:
        banner.image.delete(save=False)  # não deixar órfão no MinIO
    banner.delete()
    return Status(204, None)
