import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_q.tasks import async_task
from ninja import Router, Status

from accounts.models import User
from core.utils.errors import Error
from core.utils.permissions import staff_required
from courses.models import Course
from enrollments.models import CourseEnrollment

router = Router(tags=['Integrations'])


@router.get('/kiwify/config', response={200: dict, 403: Error})
def kiwify_config(request):
    staff_required(request)
    return Status(200, {'token': settings.KIWIFY_WEBHOOK_TOKEN or ''})


APPROVED = {'order_approved'}
REVOKE = {'order_refunded', 'chargeback'}

# Helpers


def _handle_approved(email: str, name: str, phone: str, course: Course, order_id: str):
    if not email:
        return Status(200, {'detail': 'ignored: no email'})

    with transaction.atomic():
        user, created = User.objects.get_or_create(
            email=email, defaults={'name': name or '', 'phone': phone or ''}
        )
        if created:
            user.set_password(secrets.token_urlsafe(32))
            user.save()
        expires_at = None
        if course.access_days:
            expires_at = timezone.now() + timedelta(days=course.access_days)

        enrollment, e_created = CourseEnrollment.objects.get_or_create(
            user=user,
            course=course,
            defaults={
                'is_active': True,
                'expires_at': expires_at,
                'source': 'kiwify',
                'external_order_id': order_id,
            },
        )
        if not e_created:
            enrollment.is_active = True
            if expires_at:
                enrollment.expires_at = expires_at
            enrollment.source = enrollment.source or 'kiwify'
            enrollment.external_order_id = order_id or enrollment.external_order_id
            enrollment.save()
    if created:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'
        async_task('accounts.tasks.send_welcome_email_with_reset', user.pk, reset_url)
    else:
        async_task('accounts.tasks.send_welcome_email_with_reset', user.pk)

    return Status(200, {'detail': 'enrolled'})


def _handle_revoke(email: str, course: Course, order_id: str):
    qs = CourseEnrollment.objects.filter(course=course)
    if order_id:
        qs = qs.filter(external_order_id=order_id)
    elif email:
        qs = qs.filter(user__email=email)
    else:
        return Status(200, {'detail': 'ignored: no identifier'})

    updated = qs.update(is_active=False)
    return Status(200, {'detail': f'revoked: {updated}'})


# * ----------------------------------------- * #
# ? ----------- Integrations Endpoints ----------- ? #
# * ----------------------------------------- * #


@router.post('/kiwify/webhook', response={200: dict, 401: Error, 400: Error}, auth=None)
def kiwify_webhook(request, signature: str = ''):
    expected = settings.KIWIFY_WEBHOOK_TOKEN
    if not expected or signature != expected:
        return Status(401, Error(detail='Invalid signature'))

    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return Status(400, Error(detail='Invalid JSON'))

    event = (payload.get('webhook_event_type') or '').lower()
    product = payload.get('Product') or {}
    customer = payload.get('Customer') or {}
    product_id = str(product.get('product_id') or '')
    email = (customer.get('email') or '').strip().lower()
    name = customer.get('full_name') or ''
    phone = customer.get('mobile') or ''
    order_id = str(payload.get('order_id') or '')

    if not product_id:
        return Status(200, {'detail': 'ignored: no product_id'})

    course = Course.objects.filter(kiwify_product_id=product_id).first()
    if not course:
        return Status(200, {'detail': f'ignored: unmapped product {product_id}'})

    if event in APPROVED:
        return _handle_approved(email, name, phone, course, order_id)
    if event in REVOKE:
        return _handle_revoke(email, course, order_id)
    return Status(200, {'detail': f'ignored event: {event}'})
