import io
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from courses.models import FormResponse, Lesson
from enrollments.models import CourseEnrollment, LessonProgress


def _due_form(user, course):
    form = course.forms.filter(is_active=True).order_by('-updated_at').first()

    if not form or not form.fields:
        return None

    engaged = LessonProgress.objects.filter(user=user, lesson__module__course=course, completed_at__isnull=False).exists()

    if not engaged:
        return None

    last = FormResponse.objects.filter(form=form, user=user).order_by('-created_at').first()
    if last:
        now = timezone.now()
        if last.skipped:
            # "Depois": tenta de novo em 24h
            if last.created_at > now - timedelta(hours=24):
                return None
        elif not form.every_days or last.created_at > now - timedelta(days=form.every_days):
            # Respondeu: respeita a cadência (every_days=0 = nunca mais)
            return None
    return form


def _module_locked(user, module) -> bool:
    """Módulo com `requires_previous` trava até TODAS as aulas publicadas dos módulos
    de ordem menor (mesmo curso) estarem concluídas pelo aluno."""
    if not module.requires_previous:
        return False

    prev_lesson_ids = set(
        Lesson.objects.filter(
            module__course_id=module.course_id,
            module__order__lt=module.order,
            is_published=True,
        ).values_list('id', flat=True)
    )
    if not prev_lesson_ids:  # nada antes → destravado
        return False

    done = set(
        LessonProgress.objects.filter(
            user=user, lesson_id__in=prev_lesson_ids, completed_at__isnull=False
        ).values_list('lesson_id', flat=True)
    )
    return not prev_lesson_ids <= done


def _has_course_access(user, course_id: int) -> bool:
    now = timezone.now()

    return (
        CourseEnrollment.objects.filter(user=user, course_id=course_id, is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .exists()
    )


def _client_ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    # ponytail: confia no 1º XFF (só nosso Caddy na frente). Mais proxies → pegar o trusted da direita.
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


def _signature_text(user, ip: str) -> str:
    who = user.name or user.email
    when = timezone.localtime().strftime('%d/%m/%Y %H:%M')
    return f'Baixado por {who} · {user.email} · IP {ip} · {when}'


def _stamp_pdf(data: bytes, text: str) -> bytes:
    """Carimba o texto no rodapé de cada página. reportlab gera o overlay, pypdf faz o merge."""
    try:
        reader = PdfReader(io.BytesIO(data))
        writer = PdfWriter()
        for page in reader.pages:
            w, h = float(page.mediabox.width), float(page.mediabox.height)
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(w, h))
            c.setFont('Helvetica', 7)
            c.setFillColorRGB(0.45, 0.45, 0.45)
            c.drawString(18, 10, text)
            c.save()
            buf.seek(0)
            page.merge_page(PdfReader(buf).pages[0])
            writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:  # noqa: BLE001
        # encrypted/malformado: devolve original. DownloadLog já registrou quem baixou.
        return data


def _stamp_image(data: bytes, text: str) -> tuple[bytes, str]:
    """Faixa preta no rodapé com a assinatura. Fonte escala com a largura. Re-encoda JPEG."""
    img = Image.open(io.BytesIO(data)).convert('RGB')
    w, h = img.size
    pad = max(6, w // 100)
    fs = max(14, w // 55)  # escala c/ largura → visível tanto em thumb quanto em foto 6000px
    font = ImageFont.load_default(size=fs)
    while fs > 10 and font.getlength(text) > w - 2 * pad:  # garante que a assinatura cabe
        fs -= 2
        font = ImageFont.load_default(size=fs)
    asc, desc = font.getmetrics()
    band = asc + desc + pad * 2
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, h - band, w, h), fill=(0, 0, 0))
    draw.text((pad, h - band + pad), text, fill=(255, 255, 255), font=font)
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=90)
    return out.getvalue(), 'image/jpeg'
