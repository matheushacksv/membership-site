import logging
import time

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import get_connection
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_q.tasks import async_task
from email_validator import EmailNotValidError, validate_email

from core.utils.email import build_branded_email

from .models import User

logger = logging.getLogger(__name__)


def _password_setup_url(user: User) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'


def _build_welcome_email(user: User) -> tuple[str, str, str, str, str]:
    """(subject, text, content_html, cta_label, cta_url) do email de boas-vindas.
    Compartilhado pelo envio single (send_welcome_email) e em lote (send_welcome_emails)."""
    setup_url = _password_setup_url(user)
    login_url = f'{settings.FRONTEND_URL}/login'
    name = user.name or ''

    text = (
        f'Olá {name},\n\n'
        'Sua conta na plataforma está pronta.\n\n'
        f'Defina sua senha de acesso neste link (expira em 24h):\n{setup_url}\n\n'
        f'Depois é só entrar em {login_url}.'
    )
    content = (
        f'<p>Olá {name},</p>'
        '<p>Sua conta na plataforma está pronta. Defina sua senha de acesso no botão abaixo '
        '(o link expira em 24 horas). Depois é só entrar normalmente.</p>'
    )
    return 'Seu acesso à plataforma', text, content, 'Definir minha senha', setup_url


def send_welcome_email(user_id: int):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    subject, text, content, cta_label, cta_url = _build_welcome_email(user)
    build_branded_email(subject, [user.email], text=text, content_html=content, cta_label=cta_label, cta_url=cta_url).send(fail_silently=False)


def send_welcome_emails(user_ids: list[int]):
    """Envia boas-vindas pra um LOTE reusando UMA conexão SMTP, com pacing.

    Bulk grande dispara muitos emails: 1 task/login por aluno saturava o provedor
    (rajada de logins + volume → bloqueio temporário). Aqui abrimos 1 conexão por
    lote e espaçamos os envios (EMAIL_PACE_SECONDS) pra ficar dentro do rate do
    provedor. Falha de um endereço só loga e segue; falha de conexão derruba a task
    (sem retry infinito por causa de ack_failures/max_attempts no Q_CLUSTER).
    """
    if not user_ids:
        return

    pace = settings.EMAIL_PACE_SECONDS
    users = list(User.objects.filter(id__in=user_ids))
    connection = get_connection(fail_silently=False)
    connection.open()
    try:
        for i, user in enumerate(users):
            subject, text, content, cta_label, cta_url = _build_welcome_email(user)
            msg = build_branded_email(
                subject, [user.email], text=text, content_html=content,
                cta_label=cta_label, cta_url=cta_url, connection=connection,
            )
            try:
                msg.send()
            except Exception as e:  # noqa: BLE001
                logger.warning('welcome email falhou p/ %s: %s', user.email, e)
            if pace and i < len(users) - 1:
                time.sleep(pace)
    finally:
        connection.close()


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
    content = (
        f'<p>Olá {name},</p>'
        f'<p>Seu acesso ao curso <strong>{course}</strong> foi liberado. '
        'Entre com sua senha de sempre para começar.</p>'
    )
    build_branded_email(
        'Novo curso liberado', [user.email], text=text, content_html=content,
        cta_label='Acessar a plataforma', cta_url=login_url,
    ).send(fail_silently=True)


def send_external_access_email(user_id: int, course_names: list[str] | None = None):
    """Notifica um usuário JÁ EXISTENTE que foi matriculado via external_enroll (CRM).

    Um único email cobrindo todos os cursos da chamada (não 1 por curso). Usuário novo
    NÃO usa isto, recebe o email padrão de definir senha. fail_silently: best-effort.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    login_url = f'{settings.FRONTEND_URL}/login'
    forgot_url = f'{settings.FRONTEND_URL}/forgot-password'
    name = user.name or ''
    nomes = course_names or []
    alvo = f'nos cursos: {", ".join(nomes)}' if nomes else 'na plataforma'

    text = (
        f'Olá {name},\n\n'
        f'Você foi matriculado {alvo}.\n\n'
        f'Entre com sua senha em {login_url}.\n'
        f'Se precisar, redefina a senha em {forgot_url}.'
    )
    content = (
        f'<p>Olá {name},</p>'
        f'<p>Você foi matriculado {alvo}. Entre com sua senha de sempre no botão abaixo. '
        f'Se precisar, <a href="{forgot_url}" style="color:#265F34;">redefina a senha</a>.</p>'
    )
    build_branded_email(
        'Você foi matriculado', [user.email], text=text, content_html=content,
        cta_label='Entrar na plataforma', cta_url=login_url,
    ).send(fail_silently=True)


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
    content = (
        f'<p>Olá {user.name or ""},</p>'
        '<p>Recebemos um pedido para redefinir sua senha. Clique no botão abaixo para criar uma nova '
        '(o link expira em 24 horas).</p>'
        '<p style="color:#71717a;font-size:13px;">Se você não solicitou, ignore este email.</p>'
    )
    build_branded_email(
        'Redefinição de senha - Grupo Enriquecedor', [user.email], text=text, content_html=content,
        cta_label='Redefinir senha', cta_url=reset_url,
    ).send(fail_silently=True)

def send_password_changed_email(user_id: int):
    """Avisa o dono da conta que a senha mudou, com link pra retomar se não foi ele.

    É a rede de segurança do login por magic link: quem recebe o link define senha sem
    saber a antiga, então uma troca indevida (link reencaminhado, número de WhatsApp
    errado/reciclado) precisa chegar ao email, que o usuário NÃO consegue alterar
    sozinho, logo continua sendo o canal do dono. O link do botão é gerado depois da
    troca, com o hash novo, e derruba a senha do invasor quando usado."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    when = timezone.localtime().strftime('%d/%m/%Y às %H:%M')
    recover_url = _password_setup_url(user)
    name = user.name or ''

    text = (
        f'Olá {name},\n\n'
        f'A senha da sua conta foi alterada em {when}.\n\n'
        'Se foi você, ignore este email.\n\n'
        f'Se NÃO foi você, redefina a senha agora por este link:\n{recover_url}\n\n'
        'Isso invalida a senha que acabou de ser criada.'
    )
    content = (
        f'<p>Olá {name},</p>'
        f'<p>A senha da sua conta foi alterada em <strong>{when}</strong>.</p>'
        '<p>Se foi você, não precisa fazer nada.</p>'
        '<p><strong>Se não foi você</strong>, clique no botão abaixo para definir uma nova senha. '
        'Isso invalida a senha que acabou de ser criada.</p>'
    )
    build_branded_email(
        'Sua senha foi alterada - Grupo Enriquecedor', [user.email], text=text, content_html=content,
        cta_label='Não fui eu, redefinir senha', cta_url=recover_url,
    ).send(fail_silently=True)


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
    new_user_ids: list[int] = []

    # {course_id: access_days}: precisa do access_days pra computar a expiração;
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
                        new_user_ids.append(user.pk)
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
        except Exception as e:  # noqa: BLE001
            errors.append(f'{email}: {e}')

    # Boas-vindas em LOTES (1 conexão SMTP + pacing por lote), em vez de 1 task/login
    # por aluno, evita a rajada de logins/volume que bloqueia o provedor de email.
    batch_size = settings.EMAIL_BATCH_SIZE
    for i in range(0, len(new_user_ids), batch_size):
        async_task(
            'accounts.tasks.send_welcome_emails', new_user_ids[i : i + batch_size]
        )

    return {
        'created': created,
        'existing': existing,
        'enrolled': enrolled,
        'errors': errors,
    }
