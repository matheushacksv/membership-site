from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from enrollments.models import CourseEnrollment, LessonProgress

from .api import (
    QUIZ_TIMEOUT_GRACE,
    _quiz_result,
    attachment_library,
    get_lesson_quiz,
    link_attachment,
    start_lesson_quiz,
    submit_lesson_quiz,
)
from .helpers import _module_locked
from .models import Course, Lesson, LessonAttachment, Module, QuizAttempt
from .schemas import LinkAttachmentIn, QuizSubmitIn
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
