from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

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
