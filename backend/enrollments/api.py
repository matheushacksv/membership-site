from django.db.models import Count, Q
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Status

from accounts.models import User
from core.utils.errors import Error
from core.utils.permissions import staff_required
from courses.models import Course, Lesson

from .models import CourseEnrollment, LessonProgress
from .schemas import (
    CourseProgressOut,
    EnrollmentIn,
    EnrollmentOut,
    ProgressIn,
    ProgressOut,
    UpdateEnrollmentIn,
)

router = Router(tags=['Enrollment'])


# * ----------------------------------------- * #
# ? ----------- Enrollment Endpoints ----------- ? #
# * ----------------------------------------- * #


@router.post(
    '/enrollments', response={201: EnrollmentOut, 403: Error, 404: Error, 409: Error}
)
def enroll_user(request, data: EnrollmentIn):
    staff_required(request)

    if not User.objects.filter(id=data.user_id).exists():
        return Status(404, Error(detail='User does not exist'))

    if not Course.objects.filter(id=data.course_id).exists():
        return Status(404, Error(detail='Course does not exist'))

    try:
        enrollment = CourseEnrollment.objects.create(
            user_id=data.user_id,
            course_id=data.course_id,
            expires_at=data.expires_at,
            is_active=data.is_active,
        )
    except IntegrityError:
        return Status(409, Error(detail='User already enrolled'))

    return Status(201, enrollment)


@router.delete(
    '/enrollments/{enrollment_id}', response={204: None, 403: Error, 404: Error}
)
def delete_enroll(request, enrollment_id: int):
    staff_required(request)

    enrollment = get_object_or_404(CourseEnrollment, id=enrollment_id)
    enrollment.delete()
    return Status(204, None)


@router.put(
    '/enrollments/{enrollment_id}',
    response={200: EnrollmentOut, 403: Error, 404: Error},
)
def update_enroll(request, enrollment_id: int, data: UpdateEnrollmentIn):
    staff_required(request)

    enrollment = get_object_or_404(CourseEnrollment, id=enrollment_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(enrollment, field, value)
    enrollment.save()
    return Status(200, enrollment)


@router.get('/enrollments', response=list[EnrollmentOut])
def list_enrollments(request, course_id: int | None = None, user_id: int | None = None):
    staff_required(request)
    qs = CourseEnrollment.objects.all().order_by('-enrolled_at')
    if course_id is not None:
        qs = qs.filter(course_id=course_id)
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    return qs


@router.get('/me/courses', response={200: list[EnrollmentOut]})
def my_courses(request):
    now = timezone.now()
    return CourseEnrollment.objects.filter(
        user_id=request.auth.id, is_active=True
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))


# * ----------------------------------------- * #
# ? ----------- Progress Endpoints ----------- ? #
# * ----------------------------------------- * #


@router.post(
    '/me/lessons/{lesson_id}/progress',
    response={200: ProgressOut, 403: Error, 404: Error},
)
def upsert_progress(request, lesson_id: int, data: ProgressIn):
    lesson = get_object_or_404(
        Lesson.objects.select_related('module'), id=lesson_id, is_published=True
    )

    now = timezone.now()
    enrolled = (
        CourseEnrollment.objects.filter(
            user=request.auth,
            course_id=lesson.module.course_id,
            is_active=True,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .exists()
    )
    if not enrolled:
        return Status(403, Error(detail='Not enrolled'))

    progress, _ = LessonProgress.objects.get_or_create(user=request.auth, lesson=lesson)
    progress.watch_seconds = max(progress.watch_seconds, data.watch_seconds)
    progress.completed_at = now if data.completed else None
    progress.save()
    return Status(200, progress)


@router.get(
    '/me/courses/{course_id}/progress', response={200: CourseProgressOut, 403: Error}
)
def course_progress(request, course_id: int):
    now = timezone.now()
    enrolled = (
        CourseEnrollment.objects.filter(
            user=request.auth, course_id=course_id, is_active=True
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .exists()
    )

    if not enrolled:
        return Status(403, Error(detail='Not enrolled'))

    agg = Lesson.objects.filter(
        module__course_id=course_id, is_published=True
    ).aggregate(
        total=Count('id'),
        completed=Count(
            'id',
            filter=Q(progress__user=request.auth, progress__completed_at__isnull=False),
        ),
    )
    total = agg['total']
    completed = agg['completed']
    percent = (completed / total * 100) if total else 0
    return Status(
        200,
        CourseProgressOut(
            total_lessons=total, completed_count=completed, percent=percent
        ),
    )
