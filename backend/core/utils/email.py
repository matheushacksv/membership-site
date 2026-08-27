from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

# Template de email compartilhado por todas as mensagens (accounts, announcements...).
# Layout table-based + estilos inline: é o que os clientes de email (Gmail, Outlook)
# renderizam de forma confiável, <style>/<head> e SVG são frequentemente removidos.
BRAND_COLOR = '#265F34'  # verde do logo

# Logo embutido via CID (anexo inline), NÃO por URL externa: URL depende de host público
# alcançável + não bloqueado pelo cliente (localhost em dev quebra). CID renderiza sempre.
_LOGO_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'email-logo.png'
LOGO_CID = 'brandlogo'


@lru_cache(maxsize=1)
def _logo_bytes() -> bytes:
    return _LOGO_PATH.read_bytes()


class _BrandedEmail(EmailMultiAlternatives):
    """Email da marca com o logo como recurso do HTML, não como anexo.

    Django 6 monta todo anexo em multipart/mixed, e nessa árvore o Gmail e o Outlook
    listam o logo.png como arquivo do email, mesmo com Content-Disposition inline. O
    container correto pra imagem referenciada por cid: é multipart/related, que a
    stdlib monta via add_related.
    """

    def _add_attachments(self, msg):
        super()._add_attachments(msg)
        # O logo entra dentro da parte HTML, que vira multipart/related. Fora dela, em
        # multipart/mixed (o que o Django 6 faz com qualquer anexo), o Gmail e o Outlook
        # listam o logo.png como arquivo do email mesmo com disposition inline.
        html = next((part for part in msg.walk() if part.get_content_type() == 'text/html'), None)
        if html is None:  # sem corpo HTML não há cid: pra resolver
            return
        html.add_related(
            _logo_bytes(),
            maintype='image',
            subtype='png',
            cid=f'<{LOGO_CID}>',
            disposition='inline',
            filename='logo.png',
        )


def render_email(content_html: str, cta_label: str | None = None, cta_url: str | None = None) -> str:
    """Envolve o conteúdo HTML no shell da marca (logo + card + botão + rodapé).

    content_html: parágrafos já formatados (<p>...</p>, <img>, etc).
    cta_label/cta_url: se ambos vierem, renderiza um botão destacado (ex.: "Acessar a plataforma").
    O logo é referenciado por cid:brandlogo, use build_branded_email() para anexá-lo.
    """
    site = getattr(settings, 'SITE_NAME', 'Grupo Enriquecedor')

    button = ''
    if cta_label and cta_url:
        button = (
            '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px 0 8px;">'
            f'<tr><td style="border-radius:8px;background:{BRAND_COLOR};">'
            f'<a href="{cta_url}" target="_blank" style="display:inline-block;padding:13px 30px;'
            'font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:bold;color:#ffffff;'
            f'text-decoration:none;border-radius:8px;">{cta_label}</a>'
            '</td></tr></table>'
        )

    return (
        '<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f4f4f5;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background:#f4f4f5;padding:32px 12px;"><tr><td align="center">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="max-width:600px;width:100%;background:#ffffff;border-radius:14px;'
        'overflow:hidden;border:1px solid #e5e5e5;">'
        '<tr><td style="background:#0a0a0a;padding:22px;text-align:center;">'
        f'<img src="cid:{LOGO_CID}" alt="{site}" width="46" height="46" style="display:inline-block;border:0;">'
        '</td></tr>'
        '<tr><td style="padding:32px;font-family:Arial,Helvetica,sans-serif;font-size:15px;'
        f'line-height:1.6;color:#27272a;">{content_html}{button}</td></tr>'
        '<tr><td style="padding:20px 32px;background:#fafafa;border-top:1px solid #eeeeee;'
        'font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#a1a1aa;text-align:center;">'
        f'{site} · Este é um email automático, não responda.</td></tr>'
        '</table></td></tr></table></body></html>'
    )


def build_branded_email(
    subject: str,
    recipients: list[str],
    *,
    text: str,
    content_html: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
    connection=None,
) -> EmailMultiAlternatives:
    """Monta o email já com o shell da marca + logo inline (CID). Chame .send() no retorno.

    Passe `connection` para reusar 1 conexão SMTP num lote (send_welcome_emails/broadcast).
    """
    msg = _BrandedEmail(subject, text, settings.DEFAULT_FROM_EMAIL, recipients, connection=connection)
    msg.attach_alternative(render_email(content_html, cta_label, cta_url), 'text/html')
    return msg
