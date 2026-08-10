from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from .api import (
    admin_create,
    admin_send_email,
    list_announcements,
    mark_read,
    unread_count,
)
from .models import Announcement
from .tasks import broadcast_email

# Uploads em memória — nunca toca o MinIO nos testes.
MEM_STORAGE = {
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(STORAGES=MEM_STORAGE)
class AnnouncementFlowTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.aluno = U.objects.create_user(email='aluno@x.com', password='x', name='Aluno')
        self.staff = U.objects.create_user(email='staff@x.com', password='x', name='Staff', is_staff=True)

    def _req(self, user):
        return SimpleNamespace(auth=user)

    def _new(self, published=True, file=None):
        res = admin_create(self._req(self.staff), title='Manutenção', body='Vamos ficar fora das 2h às 3h', kind='downtime', is_published=published, file=file)
        self.assertEqual(res.status_code, 201)
        return Announcement.objects.get()

    def test_rascunho_nao_aparece_pro_aluno(self):
        self._new(published=False)
        self.assertEqual(list(list_announcements(self._req(self.aluno))), [])

    def test_publicar_carimba_published_at_e_aparece(self):
        ann = self._new(published=True)
        self.assertIsNotNone(ann.published_at)
        self.assertEqual([a.id for a in list_announcements(self._req(self.aluno))], [ann.id])

    def test_create_body_vazio_e_kind_invalido_400(self):
        self.assertEqual(admin_create(self._req(self.staff), title='x', body='   ').status_code, 400)
        self.assertEqual(admin_create(self._req(self.staff), title='x', body='y', kind='zzz').status_code, 400)

    def test_create_com_imagem(self):
        img = SimpleUploadedFile('capa.png', b'\x89PNG\r\n', content_type='image/png')
        ann = self._new(published=True, file=img)
        self.assertTrue(ann.image.name.endswith('.png'))

    def test_create_imagem_tipo_invalido_400(self):
        bad = SimpleUploadedFile('x.gif', b'GIF89a', content_type='image/gif')
        self.assertEqual(admin_create(self._req(self.staff), title='t', body='b', file=bad).status_code, 400)

    def test_unread_respeita_seen_e_mark_read_zera(self):
        self._new(published=True)
        self.assertEqual(unread_count(self._req(self.aluno))['count'], 1)
        mark_read(self._req(self.aluno))
        self.aluno.refresh_from_db()
        self.assertIsNotNone(self.aluno.notifications_seen_at)
        self.assertEqual(unread_count(self._req(self.aluno))['count'], 0)

    def test_seen_anterior_ainda_conta_novo(self):
        # aluno já leu tudo; um informativo publicado DEPOIS volta a contar
        self.aluno.notifications_seen_at = timezone.now()
        self.aluno.save(update_fields=['notifications_seen_at'])
        self._new(published=True)
        self.assertEqual(unread_count(self._req(self.aluno))['count'], 1)

    @patch('announcements.api.async_task')
    def test_send_email_carimba_e_bloqueia_reenvio(self, mock_task):
        ann = self._new(published=True)
        res = admin_send_email(self._req(self.staff), ann.id)
        self.assertEqual(res.status_code, 200)
        ann.refresh_from_db()
        self.assertIsNotNone(ann.email_sent_at)
        mock_task.assert_called_once_with('announcements.tasks.broadcast_email', ann.id)
        # 2º disparo é bloqueado
        self.assertEqual(admin_send_email(self._req(self.staff), ann.id).status_code, 400)

    @patch('announcements.api.async_task')
    def test_send_email_rascunho_400(self, mock_task):
        ann = self._new(published=False)
        self.assertEqual(admin_send_email(self._req(self.staff), ann.id).status_code, 400)
        mock_task.assert_not_called()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_broadcast_envia_so_ativos(self):
        U = get_user_model()
        U.objects.create_user(email='inativo@x.com', password='x', name='Inativo', is_active=False)
        ann = self._new(published=True)
        broadcast_email(ann.id)
        recipients = {m.to[0] for m in mail.outbox}
        self.assertEqual(recipients, {'aluno@x.com', 'staff@x.com'})  # inativo fora
        self.assertTrue(mail.outbox[0].alternatives)  # tem versão html
