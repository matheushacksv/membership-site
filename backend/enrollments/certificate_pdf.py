"""Geração do PDF do certificado, on-demand a partir da linha Certificate.

reportlab desenha direto os bytes (mesmo idiom de courses.helpers._stamp_pdf). Sem storage:
o PDF nunca é gravado, regerar é mais barato que gerir arquivo + LGPD do bucket público.
"""

import io

from django.conf import settings
from django.db.models import Case, F, IntegerField, Sum, When
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from core.utils.email import _LOGO_PATH  # reusa o logo da marca (verde, fundo transparente)
from courses.models import Lesson

from .models import CertificateConfig

_GREEN = (0.149, 0.373, 0.204)  # #265F34, verde da marca
_DARK = (0.15, 0.15, 0.15)
_GRAY = (0.45, 0.45, 0.45)


def course_hours(course) -> int | None:
    """Carga horária do certificado: manual (Course.certificate_hours) se definida, senão
    soma da duração das aulas publicadas arredondada pra hora. 0 → None (omite a linha).

    Vídeo conta `duration_seconds`; exercício conta `time_limit_seconds` (a duração dele é o
    tempo da prova, exercício sem tempo contribui 0, sem inflar carga horária)."""
    if course.certificate_hours:
        return course.certificate_hours
    secs = (
        Lesson.objects.filter(module__course=course, is_published=True)
        .aggregate(
            s=Sum(
                Case(
                    When(kind='quiz', then=F('time_limit_seconds')),
                    default=F('duration_seconds'),
                    output_field=IntegerField(),
                )
            )
        )['s']
        or 0
    )
    return round(secs / 3600) or None


def _fmt_cpf(digits: str) -> str:
    return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}' if len(digits) == 11 else digits


def _wrap(c, text: str, font: str, size: float, max_w: float) -> list[str]:
    lines: list[str] = []
    cur = ''
    for word in text.split():
        trial = f'{cur} {word}'.strip()
        if c.stringWidth(trial, font, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _fit_size(c, text: str, font: str, max_w: float, size: float, min_size: float) -> float:
    """Reduz o corpo até o texto caber em max_w (nomes/curso longos não vazam a moldura)."""
    while size > min_size and c.stringWidth(text, font, size) > max_w:
        size -= 1
    return size


def _draw_qr(c, url: str, x: float, y: float, size: float) -> None:
    """QR nativo do reportlab (sem dependência nova) apontando pra página de verificação."""
    widget = qr.QrCodeWidget(url)
    b = widget.getBounds()
    d = Drawing(size, size, transform=[size / (b[2] - b[0]), 0, 0, size / (b[3] - b[1]), 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, x, y)


def render_certificate_pdf(cert) -> bytes:
    buf = io.BytesIO()
    w, h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(w, h))
    cx = w / 2
    site = getattr(settings, 'SITE_NAME', 'Grupo Enriquecedor')

    # moldura dupla verde
    c.setStrokeColorRGB(*_GREEN)
    c.setLineWidth(2.5)
    c.rect(11 * mm, 11 * mm, w - 22 * mm, h - 22 * mm)
    c.setLineWidth(0.7)
    c.rect(14 * mm, 14 * mm, w - 28 * mm, h - 28 * mm)

    # logo da marca no topo (fundo transparente → mask='auto')
    try:
        logo = ImageReader(str(_LOGO_PATH))
        size = 30 * mm
        c.drawImage(logo, cx - size / 2, h - 52 * mm, width=size, height=size,
                    preserveAspectRatio=True, mask='auto')
    except Exception:  # noqa: BLE001 (sem logo não pode quebrar a emissão)
        pass

    # título
    c.setFillColorRGB(*_GREEN)
    c.setFont('Helvetica-Bold', 32)
    c.drawCentredString(cx, h - 66 * mm, 'CERTIFICADO')
    c.setFillColorRGB(*_DARK)
    c.setFont('Helvetica', 12)
    c.drawCentredString(cx, h - 73 * mm, 'D E   C O N C L U S Ã O')
    c.setStrokeColorRGB(*_GREEN)
    c.setLineWidth(1)
    c.line(cx - 16 * mm, h - 77 * mm, cx + 16 * mm, h - 77 * mm)

    # aluno em destaque
    c.setFillColorRGB(*_DARK)
    c.setFont('Helvetica', 13)
    c.drawCentredString(cx, h - 92 * mm, 'Certificamos que')

    name = cert.student_name
    name_size = _fit_size(c, name, 'Helvetica-Bold', w - 80 * mm, 27, 16)
    c.setFillColorRGB(*_GREEN)
    c.setFont('Helvetica-Bold', name_size)
    c.drawCentredString(cx, h - 105 * mm, name)

    c.setFillColorRGB(*_GRAY)
    c.setFont('Helvetica', 11)
    c.drawCentredString(cx, h - 113 * mm, f'CPF {_fmt_cpf(cert.student_cpf)}')

    # frase de conclusão (quebra em linhas centralizadas)
    carga = f', com carga horária de {cert.hours} horas' if cert.hours else ''
    frase = (
        f'concluiu com êxito o curso "{cert.course.name}"{carga}, '
        f'em {cert.issued_at.strftime("%d/%m/%Y")}.'
    )
    c.setFillColorRGB(*_DARK)
    y = h - 128 * mm
    for line in _wrap(c, frase, 'Helvetica', 13, w - 70 * mm):
        c.drawCentredString(cx, y, line)
        y -= 7 * mm

    # bloco de assinatura (linha + responsável); assinatura escaneada do config, se houver
    cfg = CertificateConfig.load()
    sign_y = 42 * mm
    sig_bytes = bytes(cfg.signature) if cfg.signature else None
    if sig_bytes:
        try:
            sig = ImageReader(io.BytesIO(sig_bytes))
            c.drawImage(sig, cx - 22 * mm, sign_y + 1 * mm, width=44 * mm, height=16 * mm,
                        preserveAspectRatio=True, mask='auto')
        except Exception:  # noqa: BLE001 (assinatura inválida não pode quebrar a emissão)
            pass

    c.setStrokeColorRGB(*_DARK)
    c.setLineWidth(0.7)
    c.line(cx - 35 * mm, sign_y, cx + 35 * mm, sign_y)
    signer = cfg.signer_name.strip() or site
    role = cfg.signer_role.strip() or 'Coordenação'
    c.setFillColorRGB(*_DARK)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(cx, sign_y - 6 * mm, signer)
    c.setFillColorRGB(*_GRAY)
    c.setFont('Helvetica', 9)
    c.drawCentredString(cx, sign_y - 11 * mm, role)

    # QR de verificação no canto inferior direito (dentro da moldura)
    verify_url = f'{settings.FRONTEND_URL.rstrip("/")}/verificar/{cert.code}'
    try:
        _draw_qr(c, verify_url, w - 34 * mm, 16 * mm, 18 * mm)
    except Exception:  # noqa: BLE001 (QR não pode quebrar a emissão)
        pass

    # rodapé: emissor + código + link de verificação
    c.setFillColorRGB(*_GRAY)
    c.setFont('Helvetica', 9)
    c.drawCentredString(cx, 20 * mm, f'Emitido por {site}  ·  Código: {cert.code}')
    c.setFont('Helvetica', 8)
    c.drawCentredString(cx, 15 * mm, f'Verifique a autenticidade em {verify_url}')

    c.showPage()
    c.save()
    return buf.getvalue()
