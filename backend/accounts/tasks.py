from django.conf import settings
from django.core.mail import send_mail

from .models import User


def send_welcome_email(user_id: int):
    user = User.objects.get(id=user_id)

    send_mail(
        subject='Seu acesso ao curso chegou!',
        message=f'Olá {user.name}, sua conta foi criada. Faça o acesso clicando aqui: {settings.FRONTEND_URL}/login',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
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

def send_welcome_email_with_reset(user_id: int, reset_url: str):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 

    send_mail(
        subject='Seu acesso à plataforma',
        message=(
            f'Olá {user.name or ""},\n\n'
            f'Sua conta foi criada. Defina sua senha clicando no link:\n{reset_url}\n\n'
            'O link expira em 24h.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False
    )
