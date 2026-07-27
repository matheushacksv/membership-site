import json
import re
import urllib.request

from accounts.api import build_magic_login_url
from accounts.models import User
from integrations.models import EvolutionConfig


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
