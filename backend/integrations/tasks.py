import json
import re
import time
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlparse

from accounts.api import build_magic_login_url
from accounts.models import User
from integrations.models import EvolutionConfig, PandaConfig

# Panda: a duração vem da LISTAGEM (GET /videos devolve `length` + `video_external_id` por
# item), então varremos a biblioteca em páginas em vez de 1 GET por vídeo. THROTTLE espaça
# as páginas (rate limit). PAGE_LIMIT alto = menos páginas = menos chamadas.
THROTTLE_SECONDS = 1.0
PANDA_PAGE_LIMIT = 100


def _normalize_number(phone: str) -> str:
    """Telefone livre → só dígitos com DDI, formato que a Evolution espera.

    ponytail: assume Brasil. DDD+número (10-11 dígitos) sem DDI → prefixa 55.
    Já com DDI (12-13 díg) mantém. Trocar/parametrizar se for atender internacional.
    """
    digits = re.sub(r'\D', '', phone or '')
    if 10 <= len(digits) <= 11:
        digits = '55' + digits
    return digits


def send_whatsapp_access(user_id: int) -> None:
    """Tarefa django-q: manda WhatsApp reforçando acesso, com magic-login link (24h).

    Best-effort: se a config não estiver pronta ou o usuário não tiver telefone,
    retorna sem enviar. Erro de rede levanta → django-q loga/retenta (limitado por
    max_attempts no Q_CLUSTER). Nunca é chamada de forma que derrube o request.
    """
    cfg = EvolutionConfig.load()
    if not cfg.ready:
        return

    user = User.objects.filter(id=user_id).first()
    if not user or not user.phone:
        return

    number = _normalize_number(user.phone)
    if not number:
        return

    link = build_magic_login_url(user)
    text = (
        f'Olá {user.name or ""}! Seu acesso à plataforma está pronto. '
        f'Entre direto por aqui (link válido 24h):\n{link}'
    )
    body = json.dumps({'number': number, 'text': text}).encode()
    req = urllib.request.Request(
        f'{cfg.base_url.rstrip("/")}/message/sendText/{cfg.instance}',
        data=body,
        headers={'Content-Type': 'application/json', 'apikey': cfg.api_key},
        method='POST',
    )
    urllib.request.urlopen(req, timeout=10)  # noqa: S310 (URL é config staff)


def _panda_video_id(raw: str) -> str:
    """O campo video_id costuma guardar a URL de embed inteira
    (…/embed/?v=<uuid>), não o id cru. A API do Panda quer só o <uuid> do `v=`.
    Extrai o `v`; se não houver, assume que já é o id."""
    raw = (raw or '').strip()
    if 'v=' in raw:
        v = parse_qs(urlparse(raw).query).get('v', [''])[0]
        if v:
            return v
    return raw


def _parse_panda_duration(video: dict) -> int | None:
    """Duração em segundos de um objeto de vídeo do Panda (`length`)."""
    v = video.get('length')
    return int(v) if isinstance(v, (int, float)) and v > 0 else None


def _list_panda_page(cfg, page: int) -> list[dict]:
    """Uma página de GET /videos. Trata 429 (Retry-After) com 1 retry; outros erros sobem."""
    url = f'{cfg.base_url.rstrip("/")}/videos?page={page}&limit={PANDA_PAGE_LIMIT}'
    req = urllib.request.Request(
        url,
        headers={'Authorization': cfg.api_key, 'Accept': 'application/json'},
        method='GET',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (URL é config staff)
            data = json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as e:
        if e.code != 429:
            raise
        time.sleep(int(e.headers.get('Retry-After') or 5))
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            data = json.loads(resp.read() or b'{}')
    return data.get('videos') or []


def _iter_panda_videos(cfg):
    """Varre a biblioteca inteira, página a página (com throttle), yieldando cada vídeo.

    ponytail: sweep sequencial. Teto: biblioteca gigante (muitas páginas × throttle) pode
    passar do timeout de 60s do worker. Se acontecer, subir PANDA_PAGE_LIMIT ou tirar o
    throttle entre páginas (a listagem raramente bate no rate limit).
    """
    page = 1
    while True:
        videos = _list_panda_page(cfg, page)
        if not videos:
            return
        yield from videos
        page += 1
        time.sleep(THROTTLE_SECONDS)


def fetch_lesson_duration(lesson_id: int) -> None:
    """Tarefa django-q (1 aula, no save): acha o vídeo na listagem do Panda pelo
    video_external_id (o `?v=` do embed) e grava Lesson.duration_seconds. Para assim que
    encontra. Best-effort: sem config/sem vídeo Panda → retorna.
    """
    from courses.models import Lesson  # lazy: evita import circular no boot

    cfg = PandaConfig.load()
    if not cfg.ready:
        return

    lesson = (
        Lesson.objects.filter(id=lesson_id, video_provider='panda').exclude(video_id='').first()
    )
    if not lesson:
        return

    ext = _panda_video_id(lesson.video_id)
    for video in _iter_panda_videos(cfg):
        if video.get('video_external_id') == ext:
            secs = _parse_panda_duration(video)
            if secs:
                Lesson.objects.filter(id=lesson.id).update(duration_seconds=secs)
            return


def sync_panda_durations() -> None:
    """Tarefa django-q (backfill): varre a biblioteca UMA vez, mapeia
    video_external_id → length e grava a duração de todas as aulas Panda que casarem.
    Best-effort: uma página que falha (não-429) sobe e o django-q loga; o admin re-roda.
    """
    from courses.models import Lesson  # lazy: evita import circular no boot

    cfg = PandaConfig.load()
    if not cfg.ready:
        return

    ext_to_len: dict[str, int] = {}
    for video in _iter_panda_videos(cfg):
        ext = video.get('video_external_id')
        secs = _parse_panda_duration(video)
        if ext and secs:
            ext_to_len[ext] = secs

    for lesson in Lesson.objects.filter(video_provider='panda').exclude(video_id=''):
        secs = ext_to_len.get(_panda_video_id(lesson.video_id))
        if secs:
            Lesson.objects.filter(id=lesson.id).update(duration_seconds=secs)
