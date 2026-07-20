from types import SimpleNamespace

from django.test import TestCase

from .api import attachment_library, link_attachment
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
