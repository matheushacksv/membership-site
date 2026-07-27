from types import SimpleNamespace

from django.test import TestCase

from .api import _quiz_result, attachment_library, link_attachment
from .models import Course, Lesson, LessonAttachment, Module
from .schemas import LinkAttachmentIn


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
