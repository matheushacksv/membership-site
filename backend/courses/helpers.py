from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from courses.models import FormResponse
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


def _has_course_access(user, course_id: int) -> bool:
    now = timezone.now()

    return (
        CourseEnrollment.objects.filter(user=user, course_id=course_id, is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .exists()
    )
