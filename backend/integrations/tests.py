import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from integrations.models import EvolutionConfig
from integrations.tasks import _normalize_number, send_whatsapp_access

User = get_user_model()

URLOPEN = 'integrations.tasks.urllib.request.urlopen'


class NormalizeNumberTests(TestCase):
    def test_br_local_gets_ddi(self):
        self.assertEqual(_normalize_number('(11) 99999-8888'), '5511999998888')
        self.assertEqual(_normalize_number('1133334444'), '551133334444')  # fixo 10 díg

    def test_already_has_ddi_kept(self):
        self.assertEqual(_normalize_number('55 11 99999-8888'), '5511999998888')

    def test_empty(self):
        self.assertEqual(_normalize_number(''), '')
        self.assertEqual(_normalize_number('abc'), '')


class SendWhatsappAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='aluno@test.com', password='x', name='Aluno'
        )
        self.user.phone = '(11) 99999-8888'
        self.user.save()

    def _configure(self, **over):
        cfg = EvolutionConfig.load()
        cfg.base_url = over.get('base_url', 'https://evo.example.com/')
        cfg.instance = over.get('instance', 'minha-inst')
        cfg.api_key = over.get('api_key', 'sekret')
        cfg.is_active = over.get('is_active', True)
        cfg.save()
        return cfg

    def test_ready_sends_post_with_magic_link(self):
        self._configure()
        with mock.patch(URLOPEN) as urlopen:
            send_whatsapp_access(self.user.id)

        urlopen.assert_called_once()
        req = urlopen.call_args[0][0]
        # rstrip do trailing slash + monta a rota sendText/{instance}
        self.assertEqual(req.full_url, 'https://evo.example.com/message/sendText/minha-inst')
        self.assertEqual(req.get_header('Apikey'), 'sekret')
        payload = json.loads(req.data)
        self.assertEqual(payload['number'], '5511999998888')
        self.assertIn('/magic?token=', payload['text'])

    def test_inactive_config_no_send(self):
        self._configure(is_active=False)
        with mock.patch(URLOPEN) as urlopen:
            send_whatsapp_access(self.user.id)
        urlopen.assert_not_called()

    def test_incomplete_config_no_send(self):
        self._configure(api_key='')
        with mock.patch(URLOPEN) as urlopen:
            send_whatsapp_access(self.user.id)
        urlopen.assert_not_called()

    def test_user_without_phone_no_send(self):
        self._configure()
        self.user.phone = ''
        self.user.save()
        with mock.patch(URLOPEN) as urlopen:
            send_whatsapp_access(self.user.id)
        urlopen.assert_not_called()
