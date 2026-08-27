from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .api import (
    _clean_upload,
    add_message,
    admin_list_tickets,
    admin_open_count,
    admin_set_status,
    create_ticket,
    get_ticket,
)
from .models import Ticket
from .schemas import StatusIn, TicketMessageOut

# Uploads em memória: nunca toca o MinIO nos testes.
MEM_STORAGE = {
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(STORAGES=MEM_STORAGE)
class TicketFlowTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.aluno = U.objects.create_user(email='aluno@x.com', password='x', name='Aluno')
        self.outro = U.objects.create_user(email='outro@x.com', password='x', name='Outro')
        self.staff = U.objects.create_user(email='staff@x.com', password='x', name='Staff', is_staff=True)

    def _req(self, user):
        return SimpleNamespace(auth=user)

    def test_create_amarra_user_e_primeira_mensagem(self):
        res = create_ticket(self._req(self.aluno), category='bug', body='Não abre o vídeo', file=None)
        self.assertEqual(res.status_code, 201)
        t = Ticket.objects.get()
        self.assertEqual(t.user_id, self.aluno.id)
        self.assertEqual(t.status, Ticket.Status.OPEN)
        msgs = list(t.messages.all())
        self.assertEqual(len(msgs), 1)
        self.assertEqual((msgs[0].body, msgs[0].author_id), ('Não abre o vídeo', self.aluno.id))

    def test_create_categoria_invalida_400(self):
        self.assertEqual(create_ticket(self._req(self.aluno), category='xpto', body='oi', file=None).status_code, 400)

    def test_create_body_vazio_400(self):
        self.assertEqual(create_ticket(self._req(self.aluno), category='bug', body='   ', file=None).status_code, 400)

    def test_create_com_anexo(self):
        f = SimpleUploadedFile('bug.png', b'\x89PNG\r\n', content_type='image/png')
        res = create_ticket(self._req(self.aluno), category='bug', body='print', file=f)
        self.assertEqual(res.status_code, 201)
        msg = Ticket.objects.get().messages.get()
        self.assertTrue(msg.attachment.name.endswith('.png'))

    def test_get_bloqueia_outro_libera_dono_e_staff(self):
        create_ticket(self._req(self.aluno), category='doubt', body='dúvida', file=None)
        t = Ticket.objects.get()
        self.assertEqual(get_ticket(self._req(self.outro), t.id).status_code, 403)
        self.assertEqual(get_ticket(self._req(self.aluno), t.id).status_code, 200)
        self.assertEqual(get_ticket(self._req(self.staff), t.id).status_code, 200)

    def test_staff_responde_vira_em_andamento(self):
        create_ticket(self._req(self.aluno), category='bug', body='b', file=None)
        t = Ticket.objects.get()
        add_message(self._req(self.staff), t.id, body='estamos vendo', file=None)
        t.refresh_from_db()
        self.assertEqual(t.status, Ticket.Status.IN_PROGRESS)

    def test_resolvido_e_terminal_nao_aceita_mensagem(self):
        create_ticket(self._req(self.aluno), category='bug', body='b', file=None)
        t = Ticket.objects.get()
        admin_set_status(self._req(self.staff), t.id, StatusIn(status='resolved'))
        res = add_message(self._req(self.aluno), t.id, body='ainda com problema', file=None)
        self.assertEqual(res.status_code, 400)
        t.refresh_from_db()
        self.assertEqual(t.status, Ticket.Status.RESOLVED)  # não reabriu

    def test_admin_nao_reabre_resolvido(self):
        create_ticket(self._req(self.aluno), category='bug', body='b', file=None)
        t = Ticket.objects.get()
        admin_set_status(self._req(self.staff), t.id, StatusIn(status='resolved'))
        res = admin_set_status(self._req(self.staff), t.id, StatusIn(status='in_progress'))
        self.assertEqual(res.status_code, 400)
        t.refresh_from_db()
        self.assertEqual(t.status, Ticket.Status.RESOLVED)

    def test_open_count_conta_so_abertos(self):
        create_ticket(self._req(self.aluno), category='bug', body='1', file=None)
        create_ticket(self._req(self.aluno), category='bug', body='2', file=None)
        alvo = Ticket.objects.order_by('id').last()
        admin_set_status(self._req(self.staff), alvo.id, StatusIn(status='in_progress'))
        self.assertEqual(admin_open_count(self._req(self.staff))['count'], 1)

    def test_admin_list_preenche_user_e_last_message(self):
        create_ticket(self._req(self.aluno), category='bug', body='primeiro', file=None)
        t = Ticket.objects.get()
        add_message(self._req(self.staff), t.id, body='resposta staff', file=None)
        rows = admin_list_tickets(self._req(self.staff))
        self.assertEqual(rows[0].user_email, self.aluno.email)
        self.assertEqual(rows[0].last_message, 'resposta staff')

    def test_set_status_invalido_400(self):
        create_ticket(self._req(self.aluno), category='bug', body='b', file=None)
        t = Ticket.objects.get()
        self.assertEqual(admin_set_status(self._req(self.staff), t.id, StatusIn(status='xxx')).status_code, 400)

    def test_attachment_url_resolver(self):
        # bug do scaffold: resolver acessava obj.attachemnts (typo). Sem anexo → None; com anexo → .url.
        self.assertIsNone(TicketMessageOut.resolve_attachment_url(SimpleNamespace(attachment=None)))
        fake = SimpleNamespace(attachment=SimpleNamespace(url='http://m/f.png'))
        self.assertEqual(TicketMessageOut.resolve_attachment_url(fake), 'http://m/f.png')

    def test_clean_upload_rejeita_tamanho_e_tipo(self):
        big = SimpleUploadedFile('a.png', b'x', content_type='image/png')
        big.size = 6 * 1024 * 1024
        with self.assertRaises(ValueError):
            _clean_upload(big)
        with self.assertRaises(ValueError):
            _clean_upload(SimpleUploadedFile('a.exe', b'x', content_type='application/x-msdownload'))
