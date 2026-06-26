from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_q.tasks import async_task
from email_validator import EmailNotValidError, validate_email

from .models import User


def _password_setup_url(user: User) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'


def send_welcome_email(user_id: int):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    setup_url = _password_setup_url(user)
    login_url = f'{settings.FRONTEND_URL}/login'
    name = user.name or ''

    text = (
        f'Olá {name},\n\n'
        'Sua conta na plataforma está pronta.\n\n'
        f'Defina sua senha de acesso neste link (expira em 24h):\n{setup_url}\n\n'
        f'Depois é só entrar em {login_url}.'
    )
    html = (
        f'<p>Olá {name},</p>'
        '<p>Sua conta na plataforma está pronta.</p>'
        f'<p><a href="{setup_url}">Defina sua senha de acesso</a> (o link expira em 24h).</p>'
        f'<p>Depois é só acessar <a href="{login_url}">{login_url}</a>.</p>'
    )

    send_mail(
        subject='Seu acesso à plataforma',
        message=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html,
        fail_silently=False,
    )


def send_new_course_email(user_id: int, course_name: str = ''):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    login_url = f'{settings.FRONTEND_URL}/login'
    name = user.name or ''
    course = course_name or 'um novo curso'

    text = (
        f'Olá {name},\n\n'
        f'Seu acesso ao curso "{course}" foi liberado.\n\n'
        f'Entre com sua senha de sempre em {login_url} para começar.'
    )
    html = (
        f'<p>Olá {name},</p>'
        f'<p>Seu acesso ao curso <strong>{course}</strong> foi liberado.</p>'
        f'<p>Entre com sua senha de sempre em <a href="{login_url}">{login_url}</a> para começar.</p>'
    )

    send_mail(
        subject='Novo curso liberado',
        message=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html,
        fail_silently=True,
    )


def send_reset_email(user_id: int, reset_url: str):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    text = (
        f'Olá {user.name or ""}, \n\n'
        f'Acesse o link para redefinir sua senha: {reset_url}\n\n'
        'O link expira em 24 horas.\n\n'
        'Se você não solicitou, ignore este email.'
    )

    html = (
        f'<p>Olá {user.name or ""},</p>'
        f'<p>Clique no link para redefinir sua senha:</p>'
        f'<p><a href="{reset_url}">{reset_url}</a></p>'
        '<p>O link expira em 24 horas.</p>'
        '<p>Se você não solicitou, ignore este email</p>'
    )

    send_mail(
        subject='Redefinição de senha - Grupo Enriquecedor',
        message=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html,
        fail_silently=True,
    )

def send_welcome_email_with_reset(user_id: int, reset_url: str | None = None):
    send_welcome_email(user_id)


def bulk_import_task(users: list[dict], course_ids: list[int], send_welcome: bool = True) -> dict:
    """Processa UM lote da importação em massa, no worker.

    O endpoint quebra a lista em lotes e enfileira uma task destas por lote (mesmo
    `group`), cada uma bem abaixo do timeout de 60s do worker. `users` é lista de
    {'email': str, 'name': str|None}. Email inválido vai pra `errors` e não derruba
    o resto. Retorna o resumo do lote; o status agrega os lotes pelo group.
    """
    from django.utils import timezone

    from courses.models import Course
    from enrollments.models import CourseEnrollment
    from enrollments.services import expiry_from_days

    created = existing = enrolled = 0
    errors: list[str] = []

    # {course_id: access_days} — precisa do access_days pra computar a expiração;
    # sem isso a matrícula entra vitalícia ignorando a janela de acesso do curso.
    courses_map = dict(
        Course.objects.filter(id__in=course_ids).values_list('id', 'access_days')
    )
    now = timezone.now()

    for item in users:
        raw = item.get('email')
        try:
            email = validate_email(raw, check_deliverability=False).normalized
        except EmailNotValidError:
            errors.append(f'{raw or "(vazio)"}: email inválido')
            continue
        try:
            with transaction.atomic():
                user, was_created = User.objects.get_or_create(
                    email=email, defaults={'name': item.get('name') or ''}
                )
                if was_created:
                    # Senha inutilizável (sem pbkdf2): o aluno define a senha real
                    # pelo link do email. set_password aqui faria hashing caro por
                    # aluno e estourava o timeout de 60s do worker em lotes grandes.
                    user.set_unusable_password()
                    user.save()
                    created += 1
                    if send_welcome:
                        async_task(
                            'accounts.tasks.send_welcome_email_with_reset', user.pk
                        )
                else:
                    existing += 1

                for c_id, access_days in courses_map.items():
                    _, was_enrolled = CourseEnrollment.objects.get_or_create(
                        user=user,
                        course_id=c_id,
                        defaults={'expires_at': expiry_from_days(access_days, now)},
                    )
                    if was_enrolled:
                        enrolled += 1
        except Exception as e:
            errors.append(f'{email}: {e}')

    return {
        'created': created,
        'existing': existing,
        'enrolled': enrolled,
        'errors': errors,
    }
