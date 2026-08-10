import re

from django.conf import settings
from django.core.mail import get_connection

from accounts.models import User
from core.utils.email import build_branded_email

from .models import Announcement

# Vídeo (iframe do YouTube) não roda em email → troca o embed por um link "Assistir vídeo".
_YT_BLOCK = re.compile(r'<div[^>]*data-youtube-video[^>]*>.*?</div>', re.DOTALL)
_IFRAME = re.compile(r'<iframe.*?</iframe>', re.DOTALL)
_SRC = re.compile(r'src="([^"]+)"')


def _video_to_link(html: str) -> str:
    def repl(m: re.Match) -> str:
        src = _SRC.search(m.group(0))
        url = src.group(1) if src else '#'
        return f'<p style="margin:16px 0;"><a href="{url}" style="color:#265F34;font-weight:bold;">▶ Assistir vídeo</a></p>'

    return _IFRAME.sub(repl, _YT_BLOCK.sub(repl, html))


def broadcast_email(announcement_id: int) -> None:
    """django-q: manda o informativo por email para todos os alunos ativos.

    ponytail: monta todas as mensagens em memória e envia numa passada (1 conexão).
    Teto: base de milhares → quebrar em chunks (N tasks) + respeitar rate-limit do
    provedor. Sem segmentação: vai para TODOS os ativos com email.
    """
    ann = Announcement.objects.filter(id=announcement_id).first()
    if not ann:
        return

    login_url = f'{settings.FRONTEND_URL.rstrip("/")}/login'
    body_html = _video_to_link(ann.body)  # corpo já é HTML rico do editor
    cover = ''
    if ann.image:
        cover = f'<img src="{ann.image.url}" alt="" style="max-width:100%;border-radius:8px;margin:0 0 16px;">'
    # texto puro (fallback): tira as tags do HTML rico
    body_text = re.sub(r'<[^>]+>', ' ', ann.body)
    body_text = re.sub(r'\s+', ' ', body_text).strip()

    conn = get_connection()
    msgs = []
    for email, name in User.objects.filter(is_active=True).exclude(email='').values_list('email', 'name'):
        greeting = f'Olá {name},' if name else 'Olá,'
        text = f'{greeting}\n\n{body_text}\n\nAcesse a plataforma: {login_url}'
        msgs.append(build_branded_email(
            ann.title, [email], text=text,
            content_html=f'<p>{greeting}</p>{cover}{body_html}',
            cta_label='Acessar a plataforma', cta_url=login_url, connection=conn,
        ))

    if msgs:
        conn.send_messages(msgs)
