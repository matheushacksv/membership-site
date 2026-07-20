import secrets
import uuid
from pathlib import Path
from typing import cast

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django_q.tasks import async_task, count_group, result_group
from ninja import Router, Status
from ninja.files import UploadedFile
from ninja_jwt.tokens import RefreshToken

from core.utils.errors import Error
from core.utils.permissions import staff_required
from courses.models import Course
from enrollments.models import CourseEnrollment

from .models import User, UserManager
from .schemas import (
    BulkImportIn,
    BulkImportOut,
    BulkImportQueuedOut,
    BulkImportStatusOut,
    ForgotPasswordIn,
    LoginIn,
    MessageOut,
    NewUserFromWebhook,
    RefreshIn,
    ResendLinkIn,
    ResetPasswordIn,
    StaffCreateUserIn,
    StaffUpdateUser,
    TokenOut,
    UpdateMeIn,
    UserOut,
    UserSignup,
)

ALLOWED = {'image/jpeg', 'image/png', 'image/webp'}
MAX_BYTES = 2 * 1024 * 1024  # 2MB

router = Router(tags=['Users'])


@router.post('/register', response={201: TokenOut, 400: Error}, auth=None)
def signup(request, data: UserSignup):
    if User.objects.filter(email=data.email).exists():
        return Status(400, Error(detail='User already exists'))

    user = cast(UserManager, User.objects).create_user(email=data.email, password=data.password, name=data.name or '')

    if not user:
        return Status(400, Error(detail='Creation user error'))

    async_task('accounts.tasks.send_welcome_email', user.id)
    refresh = RefreshToken.for_user(user)
    return Status(201, TokenOut(access=str(refresh.access_token), refresh=str(refresh)))  # type: ignore


@router.post('/forgot-password', response={200: MessageOut}, auth=None)
def forgot_password(request, data: ForgotPasswordIn, auth=None):
    user = User.objects.filter(email=data.email).first()
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'
        async_task('accounts.tasks.send_reset_email', user.pk, reset_url)
    return Status(200, MessageOut(detail='If the email exists, you will receive a link soon'))


@router.post('/reset-password', response={200: MessageOut, 400: Error}, auth=None)
def reset_password(request, data: ResetPasswordIn):
    if len(data.password) < 8:
        return Status(400, Error(detail='Password must be 8 characters or more'))

    try:
        uid = force_str(urlsafe_base64_decode(data.uid))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Status(400, Error(detail='Invalid link'))

    if not default_token_generator.check_token(user, data.token):
        return Status(400, Error(detail='Invalid or expired link'))

    user.set_password(data.password)
    user.save()
    return Status(200, MessageOut(detail='Password reset successfully'))


@router.post('/reset-password/resend', response={200: MessageOut}, auth=None)
def resend_reset(request, data: ResendLinkIn):
    try:
        user_id = force_str(urlsafe_base64_decode(data.uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user:
        token = default_token_generator.make_token(user)
        reset_url = f'{settings.FRONTEND_URL}/reset-password?uid={data.uid}&token={token}'
        async_task('accounts.tasks.send_reset_email', user.pk, reset_url)

    return Status(200, MessageOut(detail='If the account exists, a new link was sent'))


@router.get('/reset-password/validate', response={200: MessageOut, 400: Error}, auth=None)
def validate_reset(request, uid: str, token: str):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Status(400, Error(detail='Invalid link'))

    if not default_token_generator.check_token(user, token):
        return Status(400, Error(detail='Invalid or expired link'))
    return Status(200, MessageOut(detail='ok'))


@router.post('/register-webhook', response={201: UserOut, 400: Error}, auth=None)
def new_user_webhook(request, data: NewUserFromWebhook):
    if User.objects.filter(email=data.email).exists():
        return Status(400, Error(detail='User already exists'))

    user = cast(UserManager, User.objects).create_user(email=data.email, password=data.password, name=data.name or '')

    if not user:
        return Status(400, Error(detail='Creation user error'))

    async_task('accounts.tasks.send_welcome_email', user.pk)
    return Status(201, user)


@router.post('/login', response={200: TokenOut, 404: Error, 401: Error}, auth=None)
def signin(request, data: LoginIn):
    if not User.objects.filter(email=data.email).exists():
        return Status(404, Error(detail='User doesnt exist'))

    user = authenticate(request, username=data.email, password=data.password)

    if not user:
        return Status(401, Error(detail='Invalid email or password'))

    refresh = RefreshToken.for_user(user)

    return Status(200, TokenOut(access=str(refresh.access_token), refresh=str(refresh)))  # type: ignore


@router.post('/refresh', response={200: TokenOut, 401: Error}, auth=None)
def refresh_token(request, data: RefreshIn):
    try:
        refresh = RefreshToken(data.refresh)
        return Status(
            200,
            TokenOut(access=str(refresh.access_token), refresh=str(refresh)),  # type: ignore
        )
    except Exception:
        return Status(401, Error(detail='Invalid or expired token'))


@router.get('/me', response=UserOut)
def me(request):
    return request.auth


@router.put('/me', response=UserOut)
def update_me(request, data: UpdateMeIn):

    user = request.auth

    if data.new_password:
        if len(data.new_password) < 8:
            return Status(400, Error(detail='Password need to be 8 character long or more'))
        if not user.check_password(data.current_password):
            return Status(400, Error(detail='Incorrect password'))
        user.set_password(data.new_password)

    if data.name is not None:
        user.name = data.name

    if data.phone is not None:
        user.phone = data.phone.strip() or None

    user.save()
    return Status(200, user)


@router.post('/me/avatar', response={200: UserOut, 400: Error})
def upload_avatar(request, file: UploadedFile):
    user = request.auth

    if file.size is None or file.size > MAX_BYTES:
        return Status(400, Error(detail='File too large (max 2MB)'))
    if file.content_type not in ALLOWED:
        return Status(400, Error(detail='Invalid file type'))
    if not file.name:
        return Status(400, Error(detail='Missing filename'))

    ext = Path(file.name).suffix.lower()
    new_name = f'{uuid.uuid4().hex}{ext}'

    if user.avatar:
        user.avatar.delete(save=False)

    user.avatar.save(new_name, file, save=True)
    return Status(200, user)


@router.get('/admin/users', response=list[UserOut])
def list_users(request, search: str | None = None):
    staff_required(request)

    qs = User.objects.all().order_by('-created_at')
    if search:
        qs = qs.filter(Q(email__icontains=search) | Q(name__icontains=search))
    return qs[:100]


@router.post('/admin/users', response={201: UserOut, 400: Error, 409: Error})
def staff_create_user(request, data: StaffCreateUserIn):
    staff_required(request)
    if User.objects.filter(email=data.email.strip().lower()).exists():
        return Status(409, Error(detail='User already exists'))

    user = cast(UserManager, User.objects).create_user(email=data.email.strip().lower(), password=secrets.token_urlsafe(32), name=data.name or '')

    for course_id in data.course_ids:
        if Course.objects.filter(id=course_id).exists():
            CourseEnrollment.objects.get_or_create(user=user, course_id=course_id)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'
    async_task('accounts.tasks.send_welcome_email_with_reset', user.pk, reset_url)

    return Status(201, user)


@router.post('/admin/users/{user_id}/resend-welcome', response={200: MessageOut, 404: Error})
def resend_welcome(request, user_id: int):
    staff_required(request)

    user = get_object_or_404(User, id=user_id)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'
    async_task('accounts.tasks.send_welcome_email_with_reset', user.pk, reset_url)
    return Status(200, MessageOut(detail='Email enviado'))


BULK_CHUNK_SIZE = 300


@router.post('/admin/users/bulk-import', response={202: BulkImportQueuedOut})
def bulk_import_users(request, data: BulkImportIn):
    staff_required(request)

    # Lista sem limite: quebra em lotes e enfileira uma task por lote (mesmo group),
    # cada uma abaixo do timeout de 60s do worker. O front consulta o group em
    # /bulk-import/{group_id}?chunks=N e o status agrega os lotes. Síncrono estourava
    # o timeout HTTP; task única estourava o timeout do worker em 1700+ linhas.
    payload = [{'email': u.email, 'name': u.name} for u in data.users]
    course_ids = list(data.course_ids)
    group_id = uuid.uuid4().hex

    chunks = [payload[i : i + BULK_CHUNK_SIZE] for i in range(0, len(payload), BULK_CHUNK_SIZE)]
    for chunk in chunks:
        async_task(
            'accounts.tasks.bulk_import_task',
            chunk,
            course_ids,
            data.send_welcome,
            group=group_id,
        )

    return Status(
        202,
        BulkImportQueuedOut(task_id=group_id, total=len(payload), chunks=len(chunks)),
    )


@router.get('/admin/users/bulk-import/{group_id}', response={200: BulkImportStatusOut})
def bulk_import_status(request, group_id: str, chunks: int):
    staff_required(request)

    # count_group(failures=False) usa Task.objects (base) = TODAS as linhas do
    # group, sucesso + falha. É o total finalizado; não somar failures (dobraria).
    done = count_group(group_id)
    if done < chunks:
        return Status(200, BulkImportStatusOut(status='pending', result=None))

    created = existing = enrolled = 0
    errors: list[str] = []
    for r in result_group(group_id, failures=True) or []:
        if isinstance(r, dict):
            created += r.get('created', 0)
            existing += r.get('existing', 0)
            enrolled += r.get('enrolled', 0)
            errors += r.get('errors', [])
        else:
            # lote que falhou inteiro: surfaceia o traceback (resumido)
            errors.append(str(r)[:300])

    return Status(
        200,
        BulkImportStatusOut(
            status='done',
            result=BulkImportOut(
                created=created,
                existing=existing,
                enrolled=enrolled,
                errors=errors,
            ),
        ),
    )


@router.put('/admin/users/{user_id}', response={200: UserOut, 403: Error, 404: Error})
def staff_edit_user(request, user_id: int, data: StaffUpdateUser):
    staff_required(request)

    user = get_object_or_404(User, id=user_id)

    if data.email:
        user.email = data.email
    if data.name:
        user.name = data.name

    user.save()
    return Status(200, user)
