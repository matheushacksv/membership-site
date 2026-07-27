from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from enrollments.models import LessonProgress

from .api import _quiz_result, attachment_library, link_attachment
from .helpers import _module_locked
from .models import Course, Lesson, LessonAttachment, Module
from .schemas import LinkAttachmentIn
from .tasks import _quiz_webhook_payload


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
        by_key = {a['key']: a for a in payload['answers']}
        self.assertTrue(by_key['q0']['is_correct'])
        self.assertEqual(by_key['q0']['prompt'], '2+2?')
        self.assertEqual(by_key['q1']['answer_text'], 'porque sim')
