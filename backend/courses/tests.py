from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from enrollments.models import CourseEnrollment, LessonProgress

from .api import (
    QUIZ_TIMEOUT_GRACE,
    _assert_enrolled_or_403,
    _quiz_result,
    admin_lesson_comments,
    admin_read_lesson_comments,
    attachment_library,
    comments_tree,
    comments_unread_count,
    copy_module,
    delete_comment,
    free_course_lp,
    free_course_signup,
    get_lesson_quiz,
    link_attachment,
    module_library,
    reply_comment,
    start_lesson_quiz,
    submit_lesson_quiz,
)
from .helpers import _module_locked
from .models import Course, Lesson, LessonAttachment, LessonComment, Module, QuizAttempt
from .schemas import CommentUpdateIn, CopyModuleIn, FreeSignupIn, LinkAttachmentIn, QuizSubmitIn
from .tasks import _quiz_webhook_payload, finalize_quiz_timeout


class LinkAttachmentTests(TestCase):
    """Vincular anexo existente = nova linha na MESMA chave do storage, sem re-upload."""

    def setUp(self):
        self.request = SimpleNamespace(auth=SimpleNamespace(is_staff=True))
        course = Course.objects.create(name='Curso', category=Course.Category.SALES)
        module = Module.objects.create(course=course, name='Módulo', order=0)
        self.lesson_a = Lesson.objects.create(module=module, name='Aula A', order=0)
        self.lesson_b = Lesson.objects.create(module=module, name='Aula B', order=1)
        self.src = LessonAttachment.objects.create(
            lesson=self.lesson_a,
            title='Material.pdf',
            file_url='attachments/abc123.pdf',
            size_bytes=1234,
            order=0,
        )

    def _link(self, lesson):
        result = link_attachment(self.request, lesson.id, LinkAttachmentIn(attachment_id=self.src.id))
        self.assertEqual(result.status_code, 201)
        return result.value

    def test_link_reusa_mesmo_arquivo(self):
        LessonAttachment.objects.create(
            lesson=self.lesson_b, title='Outro', file_url='attachments/zzz.pdf', order=0
        )
        linked = self._link(self.lesson_b)

        self.assertNotEqual(linked.pk, self.src.pk)
        self.assertEqual(linked.file_url.name, self.src.file_url.name)
        self.assertEqual(linked.size_bytes, self.src.size_bytes)
        self.assertEqual(linked.order, 1)  # depois do que já existia na aula B

    def test_deletar_origem_nao_afeta_vinculado(self):
        linked = self._link(self.lesson_b)
        self.src.delete()

        linked.refresh_from_db()
        self.assertEqual(linked.file_url.name, 'attachments/abc123.pdf')

    def test_library_dedupe_por_arquivo(self):
        self._link(self.lesson_b)  # mesmo arquivo em 2 aulas
        LessonAttachment.objects.create(
            lesson=self.lesson_b, title='Outro.pdf', file_url='attachments/zzz.pdf', order=5
        )

        names = [a.file_url.name for a in attachment_library(self.request)]
        self.assertEqual(sorted(names), ['attachments/abc123.pdf', 'attachments/zzz.pdf'])

        self.assertEqual([a.title for a in attachment_library(self.request, q='Outro')], ['Outro.pdf'])


class QuizScoringTests(TestCase):
    """Correção do quiz: acerto casa chosen==correct; sem resposta conta erro."""

    questions = [
        {'key': 'q0', 'prompt': 'a', 'options': ['x', 'y'], 'correct': 0, 'explanation': 'porque x'},
        {'key': 'q1', 'prompt': 'b', 'options': ['x', 'y'], 'correct': 1, 'explanation': ''},
        {'key': 'q2', 'prompt': 'c', 'options': ['x', 'y'], 'correct': 0, 'explanation': ''},
    ]

    def test_score_conta_so_acertos(self):
        # q0 certo, q1 errado, q2 sem resposta (chosen=None).
        result = _quiz_result(self.questions, {'q0': 0, 'q1': 0})

        self.assertEqual(result.total, 3)
        self.assertEqual(result.score, 1)
        por_key = {r.key: r for r in result.results}
        self.assertEqual(por_key['q0'].chosen, 0)
        self.assertIsNone(por_key['q2'].chosen)  # sem resposta → erro, não crash
        self.assertEqual(por_key['q0'].explanation, 'porque x')

    def test_dissertativa_fora_da_nota(self):
        qs = [
            {'key': 'q0', 'prompt': 'a', 'type': 'choice', 'options': ['x', 'y'], 'correct': 0, 'explanation': ''},
            {'key': 'q1', 'prompt': 'disserte', 'type': 'text', 'options': [], 'correct': 0, 'explanation': ''},
        ]
        result = _quiz_result(qs, {'q0': 0, 'q1': 'minha resposta'})

        self.assertEqual(result.total, 1)  # só a de escolha entra no total
        self.assertEqual(result.score, 1)
        por_key = {r.key: r for r in result.results}
        self.assertEqual(por_key['q1'].type, 'text')
        self.assertEqual(por_key['q1'].answer_text, 'minha resposta')
        self.assertIsNone(por_key['q1'].chosen)


class ModuleLockTests(TestCase):
    """`requires_previous` trava até concluir as aulas dos módulos anteriores."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(email='a@a.com', password='x', name='A')
        self.course = Course.objects.create(name='C', category=Course.Category.SALES)
        self.m1 = Module.objects.create(course=self.course, name='M1', order=0, is_published=True)
        self.m2 = Module.objects.create(
            course=self.course, name='M2', order=1, is_published=True, requires_previous=True
        )
        self.l1 = Lesson.objects.create(module=self.m1, name='L1', order=0, is_published=True)
        Lesson.objects.create(module=self.m2, name='L2', order=0, is_published=True)

    def test_travado_ate_concluir_anterior(self):
        self.assertTrue(_module_locked(self.user, self.m2))
        LessonProgress.objects.create(user=self.user, lesson=self.l1, completed_at=timezone.now())
        self.assertFalse(_module_locked(self.user, self.m2))

    def test_sem_flag_nunca_trava(self):
        self.assertFalse(_module_locked(self.user, self.m1))  # requires_previous=False


class QuizWebhookPayloadTests(TestCase):
    """Payload do webhook: nota só de escolha, texto coletado, enunciados juntos."""

    def test_payload_forma(self):
        course = Course.objects.create(name='Curso', category=Course.Category.SALES)
        module = Module.objects.create(course=course, name='M', order=0)
        lesson = Lesson.objects.create(
            module=module,
            name='Prova',
            kind=Lesson.Kind.QUIZ,
            order=0,
            questions=[
                {'key': 'q0', 'prompt': '2+2?', 'type': 'choice', 'options': ['3', '4'], 'correct': 1, 'explanation': ''},
                {'key': 'q1', 'prompt': 'Explique', 'type': 'text', 'options': [], 'correct': 0, 'explanation': ''},
            ],
        )
        user = get_user_model().objects.create_user(email='b@b.com', password='x', name='Bea')
        answers = {'q0': 1, 'q1': 'porque sim'}
        result = _quiz_result(lesson.questions, answers)

        payload = _quiz_webhook_payload(lesson, user, result, answers)
        self.assertEqual(payload['event'], 'quiz_completed')
        self.assertEqual((payload['score'], payload['total']), (1, 1))
        self.assertEqual(payload['user']['email'], 'b@b.com')
        self.assertEqual((payload['timed_out'], payload['attempt']), (False, 0))
        by_key = {a['key']: a for a in payload['answers']}
        self.assertTrue(by_key['q0']['is_correct'])
        self.assertEqual(by_key['q0']['prompt'], '2+2?')
        self.assertEqual(by_key['q1']['answer_text'], 'porque sim')

    def test_payload_timeout(self):
        course = Course.objects.create(name='C', category=Course.Category.SALES)
        module = Module.objects.create(course=course, name='M', order=0)
        lesson = Lesson.objects.create(
            module=module, name='P', kind=Lesson.Kind.QUIZ, order=0,
            questions=[{'key': 'q0', 'prompt': 'a', 'type': 'choice', 'options': ['x', 'y'], 'correct': 0, 'explanation': ''}],
        )
        user = get_user_model().objects.create_user(email='c@c.com', password='x', name='C')
        result = _quiz_result(lesson.questions, {})

        payload = _quiz_webhook_payload(lesson, user, result, {}, timed_out=True, attempt=1)
        self.assertEqual(payload['event'], 'quiz_timed_out')
        self.assertTrue(payload['timed_out'])
        self.assertEqual(payload['attempt'], 1)


class QuizTimerTests(TestCase):
    """Timer do exercício: submit no prazo é nota normal; estourado vira falha (score 0)."""

    questions = [{'key': 'q0', 'prompt': 'a', 'type': 'choice', 'options': ['x', 'y'], 'correct': 0, 'explanation': ''}]

    def setUp(self):
        self.user = get_user_model().objects.create_user(email='a@a.com', password='x', name='A')
        self.course = Course.objects.create(name='C', category=Course.Category.SALES)
        self.module = Module.objects.create(course=self.course, name='M', order=0, is_published=True)
        self.lesson = Lesson.objects.create(
            module=self.module, name='Prova', kind=Lesson.Kind.QUIZ, order=0,
            is_published=True, time_limit_seconds=60, questions=self.questions,
        )
        CourseEnrollment.objects.create(user=self.user, course=self.course, is_active=True)
        self.request = SimpleNamespace(auth=self.user)

    def _attempt(self, **kw):
        return QuizAttempt.objects.create(lesson=self.lesson, user=self.user, **kw)

    def test_submit_no_prazo_nota_normal(self):
        self._attempt(started_at=timezone.now())
        res = submit_lesson_quiz(self.request, self.lesson.id, QuizSubmitIn(answers={'q0': 0}))

        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.value.score, res.value.total), (1, 1))
        att = QuizAttempt.objects.get(lesson=self.lesson, user=self.user)
        self.assertFalse(att.timed_out)
        self.assertEqual(att.attempts, 1)
        self.assertIsNotNone(att.submitted_at)
        self.assertTrue(LessonProgress.objects.filter(user=self.user, lesson=self.lesson, completed_at__isnull=False).exists())

    def test_submit_apos_o_tempo_vira_falha(self):
        # tentativa aberta e já vencida (mesmo mandando gabarito certo)
        self._attempt(started_at=timezone.now() - timedelta(seconds=60 + QUIZ_TIMEOUT_GRACE + 5))
        res = submit_lesson_quiz(self.request, self.lesson.id, QuizSubmitIn(answers={'q0': 0}))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.value.score, 0)  # acerto ignorado: falha por timeout
        att = QuizAttempt.objects.get(lesson=self.lesson, user=self.user)
        self.assertTrue(att.timed_out)
        self.assertEqual(att.attempts, 1)
        self.assertTrue(LessonProgress.objects.filter(user=self.user, lesson=self.lesson, completed_at__isnull=False).exists())

    def test_client_sinaliza_timeout_no_zero(self):
        # auto-submit do front no zero (ainda dentro do GRACE server-side) → falha, não normal
        self._attempt(started_at=timezone.now())
        res = submit_lesson_quiz(self.request, self.lesson.id, QuizSubmitIn(answers={'q0': 0}, timed_out=True))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.value.score, 0)
        att = QuizAttempt.objects.get(lesson=self.lesson, user=self.user)
        self.assertTrue(att.timed_out)
        self.assertEqual(att.attempts, 1)

    def test_get_detecta_timeout_preguicoso(self):
        self._attempt(started_at=timezone.now() - timedelta(seconds=60 + QUIZ_TIMEOUT_GRACE + 5))
        res = get_lesson_quiz(self.request, self.lesson.id)

        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.value['timed_out'])
        self.assertIsNotNone(res.value['attempt'])  # já finalizada
        self.assertEqual(QuizAttempt.objects.get(lesson=self.lesson, user=self.user).attempts, 1)

    def test_start_idempotente_nao_estende(self):
        first = start_lesson_quiz(self.request, self.lesson.id)
        started = QuizAttempt.objects.get(lesson=self.lesson, user=self.user).started_at
        second = start_lesson_quiz(self.request, self.lesson.id)

        self.assertEqual(first.value.started_at, second.value.started_at)
        self.assertEqual(QuizAttempt.objects.get(lesson=self.lesson, user=self.user).started_at, started)


class QuizTimeoutTaskTests(TestCase):
    """finalize_quiz_timeout (django-q ONCE): fecha falha 1x mesmo sem o aluno voltar."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(email='a@a.com', password='x', name='A')
        self.course = Course.objects.create(name='C', category=Course.Category.SALES)
        self.module = Module.objects.create(course=self.course, name='M', order=0, is_published=True)
        self.lesson = Lesson.objects.create(
            module=self.module, name='Prova', kind=Lesson.Kind.QUIZ, order=0,
            is_published=True, time_limit_seconds=60,
            questions=[{'key': 'q0', 'prompt': 'a', 'type': 'choice', 'options': ['x', 'y'], 'correct': 0, 'explanation': ''}],
        )

    def test_task_fecha_falha_e_e_idempotente(self):
        started = timezone.now() - timedelta(seconds=120)
        att = QuizAttempt.objects.create(lesson=self.lesson, user=self.user, started_at=started)

        finalize_quiz_timeout(self.lesson.id, self.user.id, started.isoformat())
        att.refresh_from_db()
        self.assertTrue(att.timed_out)
        self.assertEqual(att.attempts, 1)
        self.assertEqual(att.score, 0)
        self.assertIsNotNone(att.submitted_at)

        # rodar de novo não conta outra falha (guarda por submitted_at)
        finalize_quiz_timeout(self.lesson.id, self.user.id, started.isoformat())
        att.refresh_from_db()
        self.assertEqual(att.attempts, 1)

    def test_task_no_op_se_started_at_mudou(self):
        att = QuizAttempt.objects.create(lesson=self.lesson, user=self.user, started_at=timezone.now())

        finalize_quiz_timeout(self.lesson.id, self.user.id, (timezone.now() - timedelta(hours=1)).isoformat())
        att.refresh_from_db()
        self.assertFalse(att.timed_out)  # agenda obsoleta → no-op
        self.assertEqual(att.attempts, 0)


class FreeCourseSignupTests(TestCase):
    """LP pública: cadastro só libera curso is_free. Conta nova auto-loga; existente não."""

    def setUp(self):
        self.request = SimpleNamespace(auth=None)  # endpoint é auth=None, não usa request
        self.course = Course.objects.create(
            name='Curso Grátis', category=Course.Category.SALES, slug='curso-gratis', is_free=True
        )

    def _signup(self, slug, **kw):
        return free_course_signup(self.request, slug, FreeSignupIn(**kw))

    def test_novo_matricula_source_lp_e_loga(self):
        res = self._signup('curso-gratis', name='João', email='J@Example.com', phone='11999998888')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.value.created)
        self.assertTrue(res.value.access and res.value.refresh)  # auto-login conta nova
        self.assertEqual(res.value.course_id, self.course.id)

        user = get_user_model().objects.get(email='j@example.com')  # normalizado
        self.assertEqual(user.phone, '11999998888')
        enr = CourseEnrollment.objects.get(user=user, course=self.course)
        self.assertEqual(enr.source, 'lp')
        self.assertTrue(enr.is_active)

    def test_existente_nao_loga_e_matricula_uma_vez(self):
        get_user_model().objects.create_user(email='ana@example.com', password='x' * 12, name='Ana')

        res = self._signup('curso-gratis', name='Ana', email='ana@example.com')
        self.assertTrue(res.status_code == 200 and res.value.created is False)
        self.assertIsNone(res.value.access)  # existente NUNCA auto-loga (anti-takeover)
        self.assertIsNone(res.value.refresh)

        self._signup('curso-gratis', name='Ana', email='ana@example.com')  # idempotente
        self.assertEqual(CourseEnrollment.objects.filter(course=self.course).count(), 1)

    def test_curso_nao_free_404(self):
        Course.objects.create(name='Pago', category=Course.Category.SALES, slug='pago', is_free=False)
        res = self._signup('pago', name='X', email='x@example.com')
        self.assertEqual(res.status_code, 404)
        self.assertEqual(CourseEnrollment.objects.count(), 0)

    def test_lp_get_so_expõe_free(self):
        Course.objects.create(name='Pago', category=Course.Category.SALES, slug='pago', is_free=False)
        self.assertEqual(free_course_lp(self.request, 'curso-gratis').status_code, 200)
        self.assertEqual(free_course_lp(self.request, 'pago').status_code, 404)

    def test_register_normal_nao_matricula(self):
        from accounts.api import signup as account_signup
        from accounts.schemas import UserSignup

        account_signup(
            self.request,
            UserSignup(name='Zé', email='ze@example.com', password='senha12345', repeat_password='senha12345'),
        )
        self.assertEqual(CourseEnrollment.objects.count(), 0)  # /register nunca dá curso


class CopyModuleTests(TestCase):
    """Importar módulo entre cursos = deep-clone (snapshot). Independente do original;
    anexos apontam pra mesma chave no MinIO; access_days sai do curso destino."""

    def setUp(self):
        self.request = SimpleNamespace(auth=SimpleNamespace(is_staff=True))
        # Curso X (origem) com 1 módulo, 2 aulas, 1 anexo.
        self.x = Course.objects.create(name='Curso X', category=Course.Category.SALES)
        self.src_module = Module.objects.create(course=self.x, name='Prospecção', order=0, is_published=True)
        self.src_l1 = Lesson.objects.create(module=self.src_module, name='Aula 1', order=0, is_published=True)
        self.src_l2 = Lesson.objects.create(module=self.src_module, name='Aula 2', order=1, is_published=True)
        LessonAttachment.objects.create(
            lesson=self.src_l1, title='Material.pdf', file_url='attachments/abc123.pdf', size_bytes=999, order=0
        )
        # Curso Y (destino), grátis, com 30 dias de acesso e um módulo já em order=0.
        self.y = Course.objects.create(name='Curso Y', category=Course.Category.SALES, is_free=True, access_days=30)
        Module.objects.create(course=self.y, name='Intro', order=0)

    def _copy(self, target):
        result = copy_module(self.request, self.src_module.id, CopyModuleIn(course_id=target.id))
        self.assertEqual(result.status_code, 201)
        return Module.objects.get(id=result.value.id)

    def test_clona_conteudo_e_fica_independente(self):
        new_mod = self._copy(self.y)

        # Módulo novo no curso destino, ids diferentes, entra despublicado.
        self.assertEqual(new_mod.course_id, self.y.id)
        self.assertNotEqual(new_mod.id, self.src_module.id)
        self.assertFalse(new_mod.is_published)
        self.assertEqual(new_mod.order, 1)  # próximo livre (destino já tinha order=0)

        # Aulas clonadas com ids novos, mesmos dados.
        new_lessons = list(new_mod.lessons.order_by('order'))
        self.assertEqual([l.name for l in new_lessons], ['Aula 1', 'Aula 2'])
        self.assertNotIn(self.src_l1.id, [l.id for l in new_lessons])

        # Anexo aponta pra MESMA chave no storage (sem re-upload).
        att = new_lessons[0].attachments.get()
        self.assertNotEqual(att.lesson_id, self.src_l1.id)
        self.assertEqual(att.file_url.name, 'attachments/abc123.pdf')

        # Snapshot: editar o original depois NÃO muda a cópia.
        self.src_l1.name = 'Aula 1 editada'
        self.src_l1.save(update_fields=['name'])
        new_lessons[0].refresh_from_db()
        self.assertEqual(new_lessons[0].name, 'Aula 1')

    def test_acesso_vem_do_curso_destino(self):
        new_mod = self._copy(self.y)
        copied = Lesson.objects.select_related('module').get(module=new_mod, name='Aula 1')
        user = get_user_model().objects.create_user(email='aluno@x.com', password='x', name='Aluno')
        req = SimpleNamespace(auth=user)

        # Só matrícula em X (origem) NÃO dá acesso à cópia (que vive em Y).
        CourseEnrollment.objects.create(user=user, course=self.x, is_active=True)
        denied = _assert_enrolled_or_403(req, copied)
        self.assertIsNotNone(denied)
        self.assertEqual(denied.status_code, 403)

        # Matrícula no destino Y libera — access_days é o de Y.
        CourseEnrollment.objects.create(
            user=user, course=self.y, is_active=True, expires_at=timezone.now() + timedelta(days=30)
        )
        self.assertIsNone(_assert_enrolled_or_403(req, copied))

    def test_library_lista_filtra_e_exclui(self):
        rows = {m.id: m for m in module_library(self.request)}
        self.assertIn(self.src_module.id, rows)
        self.assertEqual(rows[self.src_module.id].course.name, 'Curso X')  # resolver do schema usa isso
        self.assertEqual(rows[self.src_module.id].lesson_count, 2)  # annotate, existe no obj cru

        # q casa nome do módulo ou do curso.
        self.assertEqual([m.id for m in module_library(self.request, q='Prospec')], [self.src_module.id])

        # exclude_course_id tira os módulos do próprio curso.
        ids = [m.id for m in module_library(self.request, exclude_course_id=self.x.id)]
        self.assertNotIn(self.src_module.id, ids)


class AdminCommentModerationTests(TestCase):
    """Fila de moderação: pendente aparece; responder/resolver/excluir tira da fila."""

    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            email='staff@x.com', password='x', name='Staff', is_staff=True
        )
        self.aluno = get_user_model().objects.create_user(email='aluno@x.com', password='x', name='Aluno')
        self.req = SimpleNamespace(auth=self.staff)  # staff NÃO matriculado — prova bypass no reply

        self.course = Course.objects.create(name='Curso Z', category=Course.Category.SALES)
        self.module = Module.objects.create(course=self.course, name='Módulo 1', order=0)
        self.lesson = Lesson.objects.create(module=self.module, name='Aula 1', order=0)
        self.vazia = Lesson.objects.create(module=self.module, name='Aula sem coment', order=1)
        self.root = LessonComment.objects.create(lesson=self.lesson, author=self.aluno, body='Dúvida')

    def _fresh(self, obj):
        return LessonComment.objects.get(id=obj.id)

    def test_reply_anexa_na_raiz_ignora_matricula_e_resolve_thread(self):
        reply_ch = LessonComment.objects.create(lesson=self.lesson, author=self.aluno, parent=self.root, body='eu tb')
        res = reply_comment(self.req, self.root.id, CommentUpdateIn(body='Resposta'))
        self.assertEqual(res.status_code, 201)
        reply = res.value
        self.assertEqual(reply.parent_id, self.root.id)
        self.assertEqual(reply.author_id, self.staff.id)
        self.assertEqual(reply.lesson_id, self.lesson.id)

        # responder resolve a thread inteira (raiz + resposta do aluno) → sai da fila.
        self.assertIsNotNone(self._fresh(self.root).resolved_at)
        self.assertIsNotNone(self._fresh(reply_ch).resolved_at)
        self.assertEqual(comments_unread_count(self.req)['count'], 0)

        # reply de um reply → normaliza pra raiz (regra 1 nível).
        res2 = reply_comment(self.req, reply.id, CommentUpdateIn(body='Mais uma'))
        self.assertEqual(res2.value.parent_id, self.root.id)

    def test_abrir_aula_resolve_pendentes_da_aula(self):
        LessonComment.objects.create(lesson=self.lesson, author=self.aluno, parent=self.root, body='reply')
        admin_read_lesson_comments(self.req, self.lesson.id)  # abrir = moderar
        self.assertIsNotNone(self._fresh(self.root).resolved_at)
        self.assertEqual(comments_tree(self.req), [])  # aula sai da fila
        self.assertEqual(comments_unread_count(self.req)['count'], 0)

    def test_tree_so_pendentes_agrupa_e_conta(self):
        LessonComment.objects.create(lesson=self.lesson, author=self.aluno, parent=self.root, body='reply')
        tree = comments_tree(self.req)

        self.assertEqual(len(tree), 1)
        lessons = tree[0]['modules'][0]['lessons']
        self.assertEqual([l['lesson_id'] for l in lessons], [self.lesson.id])  # aula vazia ausente
        self.assertEqual(lessons[0]['pending_count'], 2)  # root + reply do aluno

        # abrir a aula zera; aula fica de fora.
        admin_read_lesson_comments(self.req, self.lesson.id)
        self.assertEqual(comments_tree(self.req), [])

    def test_unread_exclui_staff_e_resolvidos(self):
        LessonComment.objects.create(lesson=self.lesson, author=self.staff, parent=self.root, body='staff')  # não conta
        outra = Lesson.objects.create(module=self.module, name='Aula 2', order=2)
        LessonComment.objects.create(lesson=outra, author=self.aluno, body='outra pendente')
        self.assertEqual(comments_unread_count(self.req)['count'], 2)  # 2 do aluno pendentes

        admin_read_lesson_comments(self.req, self.lesson.id)  # resolve só a aula aberta
        self.assertEqual(comments_unread_count(self.req)['count'], 1)  # sobra a da outra aula

    def test_admin_lista_thread_sem_resolver(self):
        LessonComment.objects.create(lesson=self.lesson, author=self.aluno, parent=self.root, body='reply')
        roots = list(admin_lesson_comments(self.req, self.lesson.id))  # GET não resolve
        self.assertEqual([c.id for c in roots], [self.root.id])  # só raízes
        self.assertIsNone(self._fresh(self.root).resolved_at)  # GET é read-only

    def test_staff_deleta_comentario_de_outro(self):
        res = delete_comment(SimpleNamespace(auth=self.staff), self.root.id)
        self.assertEqual(res.status_code, 204)
        self.assertFalse(LessonComment.objects.filter(id=self.root.id).exists())
