import io

from django.db.models import Count, Q
from django.db.utils import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Router, Status
from ninja.files import UploadedFile

from accounts.models import User
from core.utils.errors import Error
from core.utils.permissions import staff_required
from courses.helpers import _has_course_access
from courses.models import Course, Lesson

from .certificate_pdf import course_hours, render_certificate_pdf
from .models import Certificate, CertificateConfig, CourseEnrollment, LessonProgress
from .schemas import (
    BulkEnrollmentIn,
    BulkEnrollmentOut,
    CertificateConfigIn,
    CertificateConfigOut,
    CertificateOut,
    CertificateVerifyOut,
    CourseProgressOut,
    EnrollmentAdminPage,
    EnrollmentIn,
    EnrollmentOut,
    ProgressIn,
    ProgressOut,
    UpdateEnrollmentIn,
)
from .services import expiry_from_days

SIGNATURE_MAX_BYTES = 1 * 1024 * 1024  # 1MB

router = Router(tags=['Enrollment'])


# * ----------------------------------------- * #
# ? ----------- Enrollment Endpoints ----------- ? #
# * ----------------------------------------- * #


@router.post('/enrollments', response={201: EnrollmentOut, 403: Error, 404: Error, 409: Error})
def enroll_user(request, data: EnrollmentIn):
    staff_required(request)

    if not User.objects.filter(id=data.user_id).exists():
        return Status(404, Error(detail='User does not exist'))

    if not Course.objects.filter(id=data.course_id).exists():
        return Status(404, Error(detail='Course does not exist'))

    try:
        enrollment = CourseEnrollment.objects.create(
            user_id=data.user_id,
            course_id=data.course_id,
            expires_at=data.expires_at,
            is_active=data.is_active,
        )
    except IntegrityError:
        return Status(409, Error(detail='User already enrolled'))

    return Status(201, enrollment)


@router.delete('/enrollments/{enrollment_id}', response={204: None, 403: Error, 404: Error})
def delete_enroll(request, enrollment_id: int):
    staff_required(request)

    enrollment = get_object_or_404(CourseEnrollment, id=enrollment_id)
    enrollment.delete()
    return Status(204, None)


@router.put('/enrollments/{enrollment_id}', response={200: EnrollmentOut, 403: Error, 404: Error})
def update_enroll(request, enrollment_id: int, data: UpdateEnrollmentIn):
    staff_required(request)

    enrollment = get_object_or_404(CourseEnrollment, id=enrollment_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(enrollment, field, value)
    enrollment.save()
    return Status(200, enrollment)


@router.get('/enrollments', response=list[EnrollmentOut])
def list_enrollments(request, course_id: int | None = None, user_id: int | None = None):
    staff_required(request)
    qs = CourseEnrollment.objects.all().order_by('-enrolled_at')
    if course_id is not None:
        qs = qs.filter(course_id=course_id)
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    return qs


# * --------------- Admin: gestão em massa de matrículas --------------- * #


def _filter_admin_enrollments(course_id, status, search):
    qs = CourseEnrollment.objects.all()
    if course_id is not None:
        qs = qs.filter(course_id=course_id)
    if search:
        qs = qs.filter(Q(user__email__icontains=search) | Q(user__name__icontains=search))

    now = timezone.now()
    if status == 'active':
        qs = qs.filter(is_active=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    elif status == 'expired':
        qs = qs.filter(expires_at__isnull=False, expires_at__lte=now)
    elif status == 'lifetime':
        qs = qs.filter(expires_at__isnull=True)
    return qs


@router.get('/admin', response={200: EnrollmentAdminPage, 403: Error})
def list_enrollments_admin(
    request,
    course_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    staff_required(request)
    qs = _filter_admin_enrollments(course_id, status, search)
    total = qs.count()
    items = list(
        qs.select_related('user', 'course').order_by('-enrolled_at')[offset : offset + limit]
    )
    return Status(200, {'total': total, 'items': items})


@router.get('/admin/ids', response={200: list[int], 403: Error})
def list_enrollment_ids(
    request,
    course_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
):
    staff_required(request)
    qs = _filter_admin_enrollments(course_id, status, search)
    return Status(200, list(qs.values_list('id', flat=True)))


@router.post('/bulk', response={200: BulkEnrollmentOut, 403: Error})
def bulk_enrollments(request, data: BulkEnrollmentIn):
    staff_required(request)
    qs = CourseEnrollment.objects.filter(id__in=data.enrollment_ids)

    if data.action == 'delete':
        affected = qs.count()
        qs.delete()
    elif data.action == 'set_active':
        affected = qs.update(is_active=bool(data.is_active))
    elif data.action == 'set_expiry':
        # expires_at None = vitalícia
        affected = qs.update(expires_at=data.expires_at)
    else:  # apply_course_days: expira a partir do enrolled_at de cada matrícula
        rows = list(qs.select_related('course'))
        for e in rows:
            e.expires_at = expiry_from_days(e.course.access_days, e.enrolled_at)
        CourseEnrollment.objects.bulk_update(rows, ['expires_at'])
        affected = len(rows)

    return Status(200, BulkEnrollmentOut(affected=affected))


@router.get('/me/courses', response={200: list[EnrollmentOut]})
def my_courses(request):
    now = timezone.now()
    return CourseEnrollment.objects.filter(user_id=request.auth.id, is_active=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))


# * ----------------------------------------- * #
# ? ----------- Progress Endpoints ----------- ? #
# * ----------------------------------------- * #


def _completion(user, course_id: int) -> tuple[int, int]:
    """(total, concluídas) das aulas que o aluno realmente vê/conclui: publicadas E em
    módulo publicado (o course_detail só mostra módulos publicados). Fonte única do 100% —
    sem o filtro de módulo, uma aula publicada em módulo rascunho travava o certificado."""
    # distinct=True é obrigatório: o filtro do `completed` faz JOIN em progress (de TODOS os
    # usuários), duplicando linhas — sem distinct o `total` infla e nunca chega a 100%.
    agg = Lesson.objects.filter(
        module__course_id=course_id, module__is_published=True, is_published=True
    ).aggregate(
        total=Count('id', distinct=True),
        completed=Count(
            'id',
            filter=Q(progress__user=user, progress__completed_at__isnull=False),
            distinct=True,
        ),
    )
    return agg['total'], agg['completed']


def _issue_certificate(user, course) -> tuple[Certificate | None, str | None]:
    """Emite (ou retorna) o certificado se o aluno faz jus. Idempotente (get_or_create nos
    dois campos). Retorna (cert, None) em sucesso, ou (None, motivo) pra caller traduzir."""
    if not course.certificate_enabled:
        return None, 'disabled'
    if not user.cpf or not (user.name or '').strip():  # nome e CPF são impressos no certificado
        return None, 'profile'
    total, completed = _completion(user, course.id)
    if not total or completed < total:
        return None, 'incomplete'
    cert, _ = Certificate.objects.get_or_create(
        user=user,
        course=course,
        defaults={
            'student_name': user.name.strip(),
            'student_cpf': user.cpf,
            'hours': course_hours(course),
        },
    )
    return cert, None


@router.post('/me/lessons/{lesson_id}/progress', response={200: ProgressOut, 403: Error, 404: Error})
def upsert_progress(request, lesson_id: int, data: ProgressIn):
    lesson = get_object_or_404(Lesson.objects.select_related('module'), id=lesson_id, is_published=True)

    now = timezone.now()
    enrolled = (
        CourseEnrollment.objects.filter(
            user=request.auth,
            course_id=lesson.module.course_id,
            is_active=True,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .exists()
    )
    if not enrolled:
        return Status(403, Error(detail='Not enrolled'))

    progress, _ = LessonProgress.objects.get_or_create(user=request.auth, lesson=lesson)
    progress.watch_seconds = max(progress.watch_seconds, data.watch_seconds)
    progress.completed_at = now if data.completed else None
    progress.save()

    # Emissão automática ao fechar 100% (best-effort, idempotente). _issue_certificate
    # revalida conclusão + nome/CPF; aqui só o gatilho barato.
    if data.completed and request.auth.cpf and (request.auth.name or '').strip():
        course = lesson.module.course
        if course.certificate_enabled:
            _issue_certificate(request.auth, course)

    return Status(200, progress)


@router.get('/me/courses/{course_id}/progress', response={200: CourseProgressOut, 403: Error})
def course_progress(request, course_id: int):
    now = timezone.now()
    enrolled = (
        CourseEnrollment.objects.filter(user=request.auth, course_id=course_id, is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .exists()
    )

    if not enrolled:
        return Status(403, Error(detail='Not enrolled'))

    total, completed = _completion(request.auth, course_id)
    percent = (completed / total * 100) if total else 0
    return Status(
        200,
        CourseProgressOut(total_lessons=total, completed_count=completed, percent=percent),
    )


# * ----------------------------------------- * #
# ? ---------- Certificate Endpoints --------- ? #
# * ----------------------------------------- * #


@router.get('/me/certificates', response=list[CertificateOut])
def my_certificates(request):
    return (
        Certificate.objects.filter(user=request.auth)
        .select_related('course')
        .order_by('-issued_at')
    )


@router.get(
    '/me/courses/{course_id}/certificate',
    response={200: CertificateOut, 403: Error, 404: Error, 409: Error},
)
def get_or_issue_certificate(request, course_id: int):
    """Emite sob demanda (cobre alunos já 100% hoje) e devolve o certificado. O botão do
    curso usa os erros pra guiar o aluno (sem CPF → pedir CPF; incompleto → concluir)."""
    course = get_object_or_404(Course, id=course_id)
    if not _has_course_access(request.auth, course_id):
        return Status(403, Error(detail='Sem acesso ao curso'))

    cert, reason = _issue_certificate(request.auth, course)
    if reason == 'disabled':
        return Status(404, Error(detail='Este curso não emite certificado'))
    if reason == 'profile':
        return Status(409, Error(detail='Preencha seu nome e CPF no perfil para emitir o certificado'))
    if reason == 'incomplete':
        return Status(403, Error(detail='Conclua 100% das aulas para emitir o certificado'))
    return Status(200, cert)


@router.get('/verify/{code}', auth=None, response={200: CertificateVerifyOut, 404: Error})
def verify_certificate(request, code: str):
    """Verificação PÚBLICA (sem login). Empregador confere pelo código impresso/QR do PDF."""
    cert = (
        Certificate.objects.select_related('course')
        .filter(code=code.strip().upper())
        .first()
    )
    if not cert:
        return Status(404, Error(detail='Certificado não encontrado'))
    return Status(200, cert)


@router.get('/me/certificates/{code}/download', response={404: Error})
def download_certificate(request, code: str):
    cert = get_object_or_404(
        Certificate.objects.select_related('course', 'user'), code=code, user=request.auth
    )
    pdf = render_certificate_pdf(cert)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="certificado-{cert.code}.pdf"'
    return resp


# * ----------------------------------------- * #
# ? ------ Config do certificado (staff) ----- ? #
# * ----------------------------------------- * #


@router.get('/admin/certificate-config', response={200: CertificateConfigOut, 403: Error})
def get_certificate_config(request):
    staff_required(request)
    return Status(200, CertificateConfig.load())


@router.put('/admin/certificate-config', response={200: CertificateConfigOut, 403: Error})
def update_certificate_config(request, data: CertificateConfigIn):
    staff_required(request)
    cfg = CertificateConfig.load()
    cfg.signer_name = data.signer_name.strip()
    cfg.signer_role = data.signer_role.strip()
    cfg.save()
    return Status(200, cfg)


@router.post('/admin/certificate-config/signature', response={200: CertificateConfigOut, 400: Error, 403: Error})
def upload_certificate_signature(request, file: UploadedFile = File(...)):
    """Assinatura escaneada do certificado. PNG transparente só; guardada no banco (privada)."""
    staff_required(request)
    if file.content_type != 'image/png':
        return Status(400, Error(detail='Envie um PNG com fundo transparente'))
    if not file.size or file.size > SIGNATURE_MAX_BYTES:
        return Status(400, Error(detail='Arquivo muito grande (máx 1MB)'))

    data = file.read()
    from PIL import Image  # lazy: só quando alguém sobe assinatura

    try:
        img = Image.open(io.BytesIO(data))
        fmt, size = img.format, img.size
        img.verify()  # integridade real do arquivo
    except Exception:  # noqa: BLE001
        return Status(400, Error(detail='Arquivo não é um PNG válido'))
    if fmt != 'PNG':
        return Status(400, Error(detail='Envie um PNG com fundo transparente'))
    if size[0] > 3000 or size[1] > 3000:
        return Status(400, Error(detail='Imagem muito grande (máx 3000px)'))

    cfg = CertificateConfig.load()
    cfg.signature = data
    cfg.save()
    return Status(200, cfg)


@router.delete('/admin/certificate-config/signature', response={200: CertificateConfigOut, 403: Error})
def delete_certificate_signature(request):
    staff_required(request)
    cfg = CertificateConfig.load()
    cfg.signature = None
    cfg.save()
    return Status(200, cfg)


@router.get('/admin/certificate-config/signature', response={404: Error})
def certificate_signature_preview(request):
    # preview staff (o front busca como blob; <img src> não manda o JWT).
    staff_required(request)
    cfg = CertificateConfig.load()
    if not cfg.signature:
        return Status(404, Error(detail='Sem assinatura'))
    return HttpResponse(bytes(cfg.signature), content_type='image/png')
