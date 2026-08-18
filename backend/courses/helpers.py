import io
import subprocess
import tempfile
from datetime import timedelta

from django.db.models import OuterRef, Q, Subquery, Sum
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from courses.models import FormResponse, Lesson
from enrollments.models import CourseEnrollment, LessonProgress


def course_duration_sq():
    """Subquery: soma de duration_seconds das aulas de vídeo publicadas (segundos).
    Subquery, não annotate direto no queryset da listagem: os joins de matrícula/
    progresso ali fazem fan-out das linhas e um Sum sobre eles inflaria o total
    (mesmo bug do certificado). O Subquery isola o agregado por curso."""
    return Subquery(
        Lesson.objects.filter(module__course=OuterRef('pk'), is_published=True)
        .values('module__course')
        .annotate(s=Sum('duration_seconds'))
        .values('s')
    )


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


def compress_pdf(data: bytes, setting: str = '/printer') -> bytes:
    """Downsampla imagens do PDF via ghostscript. /printer = 300dpi: acima disso é desperdício (tela
    mostra ≤150dpi, impressão usa 300), então não há perda perceptível pro aluno. Encolhe apostila
    image-heavy ~8x. Devolve o ORIGINAL, sem tocar, se: não for PDF válido, o gs falhar, o resultado
    não encolher, ou o nº de páginas mudar — nunca troca por um arquivo corrompido/diferente.
    ponytail: shell-out pro gs (recomprimir imagem em Python seria reinventar). Knob `setting` se um
    dia quiserem qualidade diferente por curso."""
    try:
        n_before = len(PdfReader(io.BytesIO(data)).pages)
    except Exception:  # noqa: BLE001
        return data  # não é PDF válido: não mexe
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf') as fin, tempfile.NamedTemporaryFile(suffix='.pdf') as fout:
            fin.write(data)
            fin.flush()
            subprocess.run(
                ['gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.5', f'-dPDFSETTINGS={setting}',
                 '-dNOPAUSE', '-dQUIET', '-dBATCH', f'-sOutputFile={fout.name}', fin.name],
                check=True, timeout=180, capture_output=True,
            )
            with open(fout.name, 'rb') as f:
                out = f.read()
    except Exception:  # noqa: BLE001
        return data  # gs ausente/erro/timeout: mantém original
    if not out or len(out) >= len(data):
        return data  # não encolheu
    try:
        if len(PdfReader(io.BytesIO(out)).pages) != n_before:
            return data  # nº de páginas divergiu: descarta por segurança
    except Exception:  # noqa: BLE001
        return data
    return out


def _stamp_pdf(data: bytes, text: str) -> bytes:
    """Carimba a assinatura no rodapé da 1ª, do meio e da última página. reportlab gera o overlay,
    pypdf faz o merge.
    ponytail: carimbar TODA página faz merge_page por página e trava em apostila cheia de imagem
    (era o download que 'demorava bastante'). Escrever todas as páginas é barato; o custo é o merge.
    3 páginas = custo constante e a marca aparece no começo/meio/fim; DownloadLog guarda a trilha
    completa de quem baixou. Se exigirem marca em TODA página, isso é por-página e lento → job (django-q)."""
    try:
        reader = PdfReader(io.BytesIO(data))
        writer = PdfWriter()
        n = len(reader.pages)
        mark = {0, n // 2, n - 1}  # 1ª, meio, última (dedup p/ PDF de 1-2 páginas)
        for i, page in enumerate(reader.pages):
            if i in mark:
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
