import json
import urllib.error
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import Course, Lesson, Module
from integrations.api import backfill_panda
from integrations.models import EvolutionConfig, PandaConfig
from integrations.tasks import (
    _normalize_number,
    _panda_video_id,
    _parse_panda_duration,
    fetch_lesson_duration,
    send_whatsapp_access,
    sync_panda_durations,
)

User = get_user_model()

URLOPEN = 'integrations.tasks.urllib.request.urlopen'
SLEEP = 'integrations.tasks.time.sleep'


def _cm(payload: dict):
    """Mock do context manager retornado pelo urlopen (with ... as resp)."""
    m = mock.MagicMock()
    m.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return m


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


class PandaVideoIdTests(TestCase):
    UUID = '51f128dc-78b9-4716-b23c-e6b0940c563a'

    def test_extrai_v_da_url_de_embed(self):
        url = f'https://player-vz-x.tv.pandavideo.com.br/embed/?v={self.UUID}'
        self.assertEqual(_panda_video_id(url), self.UUID)

    def test_id_cru_passa_direto(self):
        self.assertEqual(_panda_video_id(self.UUID), self.UUID)

    def test_espacos_e_vazio(self):
        self.assertEqual(_panda_video_id(f'  {self.UUID} '), self.UUID)
        self.assertEqual(_panda_video_id(''), '')


class ParsePandaDurationTests(TestCase):
    def test_length_em_segundos(self):
        self.assertEqual(_parse_panda_duration({'length': 3600}), 3600)
        self.assertEqual(_parse_panda_duration({'length': 1800.0}), 1800)

    def test_ausente_ou_zero(self):
        self.assertIsNone(_parse_panda_duration({'length': 0}))
        self.assertIsNone(_parse_panda_duration({}))
        self.assertIsNone(_parse_panda_duration({'length': 'x'}))


EXT1 = '11111111-1111-1111-1111-111111111111'
EXT2 = '22222222-2222-2222-2222-222222222222'


def _embed(ext: str) -> str:
    return f'https://player-vz-x.tv.pandavideo.com.br/embed/?v={ext}'


def _page(videos: list[dict]):
    """Mock de uma página de GET /videos → {'videos': [...]}. Página vazia encerra o sweep."""
    return _cm({'videos': videos})


class FetchLessonDurationTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(name='C', category='sales', is_active=True)
        self.module = Module.objects.create(course=self.course, name='M', order=0, is_published=True)
        self.lesson = Lesson.objects.create(
            module=self.module, name='Aula', order=0, is_published=True,
            video_provider='panda', video_id=_embed(EXT1), duration_seconds=0,
        )
        cfg = PandaConfig.load()
        cfg.api_key = 'sekret'
        cfg.is_active = True
        cfg.save()

    def test_acha_na_listagem_e_grava(self):
        with mock.patch(SLEEP), mock.patch(URLOPEN) as urlopen:
            urlopen.side_effect = [_page([
                {'video_external_id': EXT2, 'length': 10},
                {'video_external_id': EXT1, 'length': 4200},
            ])]
            fetch_lesson_duration(self.lesson.id)
        req = urlopen.call_args[0][0]
        self.assertIn('/videos?page=1', req.full_url)
        self.assertEqual(req.get_header('Authorization'), 'sekret')
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.duration_seconds, 4200)

    def test_para_ao_encontrar_sem_pedir_proxima_pagina(self):
        with mock.patch(SLEEP), mock.patch(URLOPEN) as urlopen:
            urlopen.side_effect = [_page([{'video_external_id': EXT1, 'length': 60}])]
            fetch_lesson_duration(self.lesson.id)
        self.assertEqual(urlopen.call_count, 1)  # achou na pág 1, não pediu a 2

    def test_nao_encontrado_deixa_zero(self):
        with mock.patch(SLEEP), mock.patch(URLOPEN) as urlopen:
            urlopen.side_effect = [_page([{'video_external_id': EXT2, 'length': 99}]), _page([])]
            fetch_lesson_duration(self.lesson.id)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.duration_seconds, 0)

    def test_config_inativa_nao_busca(self):
        cfg = PandaConfig.load()
        cfg.is_active = False
        cfg.save()
        with mock.patch(URLOPEN) as urlopen:
            fetch_lesson_duration(self.lesson.id)
        urlopen.assert_not_called()

    def test_aula_nao_panda_nao_busca(self):
        self.lesson.video_provider = 'youtube'
        self.lesson.save()
        with mock.patch(URLOPEN) as urlopen:
            fetch_lesson_duration(self.lesson.id)
        urlopen.assert_not_called()


class SyncPandaDurationsTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(name='C', category='sales', is_active=True)
        self.module = Module.objects.create(course=self.course, name='M', order=0, is_published=True)
        self.l1 = Lesson.objects.create(module=self.module, name='A1', order=0, is_published=True, video_provider='panda', video_id=_embed(EXT1))
        self.l2 = Lesson.objects.create(module=self.module, name='A2', order=1, is_published=True, video_provider='panda', video_id=_embed(EXT2))
        self.l3 = Lesson.objects.create(module=self.module, name='A3', order=2, is_published=True, video_provider='youtube', video_id='yt')
        cfg = PandaConfig.load()
        cfg.api_key = 'sekret'
        cfg.is_active = True
        cfg.save()

    def test_sweep_mapeia_e_atualiza_so_panda(self):
        with mock.patch(SLEEP), mock.patch(URLOPEN) as urlopen:
            urlopen.side_effect = [
                _page([{'video_external_id': EXT1, 'length': 100}]),
                _page([{'video_external_id': EXT2, 'length': 200}]),
                _page([]),  # encerra o sweep
            ]
            sync_panda_durations()
        self.l1.refresh_from_db()
        self.l2.refresh_from_db()
        self.l3.refresh_from_db()
        self.assertEqual((self.l1.duration_seconds, self.l2.duration_seconds), (100, 200))
        self.assertEqual(self.l3.duration_seconds, 0)  # youtube fora

    def test_config_inativa_nao_busca(self):
        cfg = PandaConfig.load()
        cfg.is_active = False
        cfg.save()
        with mock.patch(URLOPEN) as urlopen:
            sync_panda_durations()
        urlopen.assert_not_called()

    def test_429_numa_pagina_respeita_retry(self):
        err = urllib.error.HTTPError('http://x', 429, 'rate', {'Retry-After': '0'}, None)
        with mock.patch(SLEEP) as sleep, mock.patch(URLOPEN) as urlopen:
            urlopen.side_effect = [err, _page([{'video_external_id': EXT1, 'length': 300}]), _page([])]
            sync_panda_durations()
        self.l1.refresh_from_db()
        self.assertEqual(self.l1.duration_seconds, 300)
        sleep.assert_any_call(0)  # dormiu o Retry-After


class BackfillEndpointTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(email='s@x.com', password='x', is_staff=True)
        self.course = Course.objects.create(name='C', category='sales', is_active=True)
        self.module = Module.objects.create(course=self.course, name='M', order=0, is_published=True)
        Lesson.objects.create(module=self.module, name='A1', order=0, is_published=True, video_provider='panda', video_id=_embed(EXT1))
        Lesson.objects.create(module=self.module, name='A2', order=1, is_published=True, video_provider='youtube', video_id='yt')  # ignorada

    def _req(self):
        return SimpleNamespace(auth=self.staff)

    def _ready(self):
        cfg = PandaConfig.load()
        cfg.api_key = 'sekret'
        cfg.is_active = True
        cfg.save()

    def test_nao_pronto_400(self):
        with mock.patch('integrations.api.async_task') as at:
            res = backfill_panda(self._req())
        self.assertEqual(res.status_code, 400)
        at.assert_not_called()

    def test_pronto_enfileira_sync(self):
        self._ready()
        with mock.patch('integrations.api.async_task') as at:
            res = backfill_panda(self._req())
        self.assertEqual(res.status_code, 200)
        at.assert_called_once_with('integrations.tasks.sync_panda_durations')
