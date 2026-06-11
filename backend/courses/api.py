import uuid
from pathlib import Path

from django.db import models, transaction
from django.db.models import Count, Exists, F, OuterRef, Prefetch, Subquery
from django.db.models.query_utils import Q
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Status
from ninja.files import UploadedFile

from core.utils.errors import Error
from core.utils.permissions import staff_required
from enrollments.models import CourseEnrollment, LessonProgress

from .models import Course, Lesson, LessonAttachment, LessonComment, Module
from .schemas import (
    CommentIn,
    CommentOut,
    CommentUpdateIn,
    CourseDetailOut,
    CourseIn,
    CourseListOut,
    CourseOut,
    CourseUpdateIn,
    LessonAttachmentIn,
    LessonAttachmentOut,
    LessonAttachmentUpdateIn,
    LessonIn,
    LessonOut,
    LessonUpdateIn,
    ModuleIn,
    ModuleOut,
    ModuleUpdateIn,
)

catalog_router = Router(tags=['Catalog'])
admin_router = Router(tags=['Courses Admin'])

# Helpers


def _assert_enrolled_or_403(request, lesson: Lesson):
    now = timezone.now()

    enrolled = (
        CourseEnrollment.objects.filter(user=request.auth, course_id=lesson.module.course_id, is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .exists()
    )
    if not enrolled:
        return Status(403, Error(detail='Not enrolled'))
    return None


# * ----------------------------------------- * #
# ? ----------- Catalog Endpoints ----------- ? #
# * ----------------------------------------- * #


@catalog_router.get('/courses', response=list[CourseListOut])
def list_my_courses(request):
    user = request.auth
    now = timezone.now()

    resume_sq = (
        LessonProgress.objects.filter(
            user=user,
            lesson__module__course=OuterRef('pk'),
            lesson__is_published=True,
            completed_at__isnull=True,
        )
        .order_by('-last_watched_at')
        .values('lesson_id')[:1]
    )

    return (
        Course.objects.filter(
            is_active=True,
            enrollments__user=user,
            enrollments__is_active=True,
        )
        .filter(Q(enrollments__expires_at__isnull=True) | Q(enrollments__expires_at__gt=now))
        .annotate(
            total_lessons=Count(
                'modules__lessons',
                filter=Q(modules__lessons__is_published=True),
                distinct=True,
            ),
            completed_lessons=Count(
                'modules__lessons',
                filter=Q(
                    modules__lessons__is_published=True,
                    modules__lessons__progress__user=user,
                    modules__lessons__progress__completed_at__isnull=False,
                ),
                distinct=True,
            ),
            resume_lesson_id=Subquery(resume_sq),
        )
        .distinct()
        .order_by('name')
    )


@catalog_router.get('/courses/available', response=list[CourseListOut])
def list_available_courses(request, category: str | None = None):
    user = request.auth
    now = timezone.now()

    enrolled = CourseEnrollment.objects.filter(user=user, is_active=True, course=OuterRef('pk')).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )

    qs = Course.objects.filter(is_active=True).exclude(Exists(enrolled)).filter(Q(sales_page__isnull=False) | Q(checkout_link__isnull=False))
    if category:
        qs = qs.filter(category=category)
    return qs.order_by('name')


@catalog_router.get('/courses/{course_id}', response={200: CourseDetailOut, 403: Error, 404: Error})
def course_detail(request, course_id: int):
    user = request.auth

    has_access = Course.objects.filter(
        id=course_id,
        is_active=True,
        enrollments__user=user,
        enrollments__is_active=True,
    ).exists()

    if not has_access:
        return Status(403, Error(detail='Access denied'))

    course = get_object_or_404(
        Course.objects.prefetch_related(
            Prefetch(
                'modules',
                queryset=Module.objects.filter(is_published=True)
                .order_by('order')
                .prefetch_related(
                    Prefetch(
                        'lessons',
                        queryset=Lesson.objects.filter(is_published=True).order_by('order').prefetch_related('attachments'),
                    )
                ),
            )
        ),
        id=course_id,
    )

    completed_ids = set(
        LessonProgress.objects.filter(
            user=user,
            lesson__module__course=course,
            completed_at__isnull=False,
        ).values_list('lesson_id', flat=True)
    )

    for module in getattr(course, 'modules').all():
        for lesson in module.lessons.all():
            lesson._completed_for_user = lesson.id in completed_ids

    return Status(200, course)


@catalog_router.get('/lessons/{lesson_id}/comments', response={200: list[CommentOut], 403: Error, 404: Error})
def list_comments(request, lesson_id: int):
    lesson = get_object_or_404(Lesson.objects.select_related('module'), id=lesson_id)
    if denied := _assert_enrolled_or_403(request, lesson):
        return denied
    return Status(
        200,
        LessonComment.objects.filter(lesson_id=lesson_id, parent__isnull=True)
        .select_related('author')
        .prefetch_related('replies__author')
        .order_by('created_at'),
    )


@catalog_router.post('/lessons/{lesson_id}/comments', response={201: CommentOut, 400: Error, 403: Error, 404: Error})
def create_comment(request, lesson_id: int, data: CommentIn):
    lesson = get_object_or_404(Lesson.objects.select_related('module'), id=lesson_id)
    if denied := _assert_enrolled_or_403(request, lesson):
        return denied

    parent = None
    if data.parent_id:
        parent = get_object_or_404(LessonComment, id=data.parent_id)
        if getattr(parent, 'lesson_id') != lesson.pk:
            return Status(400, Error(detail='Parent from different lesson'))
        if getattr(parent, 'parent_id', None) is not None:
            return Status(400, Error(detail='Cannot reply to a reply'))
    comment = LessonComment.objects.create(lesson=lesson, author=request.auth, parent=parent, body=data.body)
    return Status(201, comment)


@catalog_router.patch('/comments/{comment_id}', response={200: CommentOut, 403: Error, 404: Error})
def update_comment(request, comment_id: int, data: CommentUpdateIn):
    comment = get_object_or_404(LessonComment, id=comment_id)
    if getattr(comment, 'author_id') != request.auth.id:
        return Status(403, Error(detail='Not the author'))
    comment.body = data.body
    comment.updated_at = timezone.now()
    comment.save(update_fields=['body', 'updated_at'])
    return Status(200, comment)


@catalog_router.delete('/comments/{comment_id}', response={204: None, 403: Error, 404: Error})
def delete_comment(request, comment_id: int):
    comment = get_object_or_404(LessonComment, id=comment_id)
    if getattr(comment, 'author_id') != request.auth.id and not request.auth.is_staff:
        return Status(403, Error(detail='Forbidden'))
    comment.delete()
    return Status(204, None)


# * ----------------------------------------- * #
# ? ----------- Admin Endpoints ----------- ? #
# * ----------------------------------------- * #


@admin_router.get('/courses', response=list[CourseOut])
def list_all_courses(request):
    staff_required(request)

    return Course.objects.all().order_by('-created_at')


@admin_router.post('/courses', response={201: CourseOut, 403: Error})
def create_course(request, data: CourseIn):
    staff_required(request)

    course = Course.objects.create(
        name=data.name,
        image=data.image,
        category=data.category,
        sales_page=data.sales_page,
        checkout_link=data.checkout_link,
        is_active=data.is_active,
        kiwify_product_id=data.kiwify_product_id,
        access_days=data.access_days,
    )

    return Status(201, course)


@admin_router.put('/courses/{course_id}', response={200: CourseOut, 403: Error, 404: Error})
def update_course(request, course_id: int, data: CourseUpdateIn):
    staff_required(request)

    course = get_object_or_404(Course, id=course_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(course, field, value)

    course.save()

    return Status(200, course)


@admin_router.delete('/courses/{course_id}', response={204: None, 403: Error, 404: Error})
def delete_course(request, course_id: int):
    staff_required(request)

    course = get_object_or_404(Course, id=course_id)

    course.delete()

    return Status(204, None)


@admin_router.post('/courses/{course_id}/image', response={200: CourseOut, 400: Error, 404: Error})
def upload_course_image(request, course_id: int, file: UploadedFile):
    staff_required(request)
    course = get_object_or_404(Course, id=course_id)

    if file.size is None or file.size > 5 * 1024 * 1024:
        return Status(400, Error(detail='Image too large (max 5MB)'))
    if file.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        return Status(400, Error(detail='Invalid image type: jpg, png or webp'))
    if not file.name:
        return Status(400, Error(detail='Name is required'))

    ext = Path(file.name).suffix.lower()
    new_name = f'{uuid.uuid4().hex}{ext}'
    if course.image:
        course.image.delete(save=False)
    course.image.save(new_name, file, save=True)
    return Status(200, course)


@admin_router.post('/modules', response={201: ModuleOut, 403: Error, 404: Error, 409: Error})
def create_module(request, data: ModuleIn):
    staff_required(request)

    if not Course.objects.filter(id=data.course_id).exists():
        return Status(404, Error(detail='Course not found'))

    current_max = Module.objects.filter(course_id=data.course_id).aggregate(models.Max('order'))['order__max']
    next_order = 0 if current_max is None else current_max + 1

    try:
        module = Module.objects.create(
            course_id=data.course_id,
            name=data.name,
            order=data.order if data.order > 0 else next_order,
            is_published=data.is_published,
        )
    except IntegrityError:
        return Status(409, Error(detail='Order conflict'))
    return Status(201, module)


@admin_router.get('/modules/{module_id}', response={200: ModuleOut, 404: Error})
def get_module(request, module_id: int):
    staff_required(request)
    return get_object_or_404(Module, id=module_id)


@admin_router.get('/modules', response=list[ModuleOut])
def list_modules(request, course_id: int):
    staff_required(request)
    return Module.objects.filter(course_id=course_id).order_by('order')


@admin_router.put('/modules/{module_id}', response={200: ModuleOut, 403: Error, 404: Error, 409: Error})
def update_module(request, module_id: int, data: ModuleUpdateIn):
    staff_required(request)

    module = get_object_or_404(Module, id=module_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(module, field, value)

    try:
        module.save()
    except IntegrityError:
        return Status(409, Error(detail='Order conflict'))
    return Status(200, module)


@admin_router.delete('/modules/{module_id}', response={204: None, 403: Error, 404: Error})
def delete_module(request, module_id: int):
    staff_required(request)
    module = get_object_or_404(Module, id=module_id)
    module.delete()
    return Status(204, None)


@admin_router.patch('/courses/{course_id}/modules/reorder', response={204: None, 403: Error, 404: Error})
def reorder_modules(request, course_id: int, order: list[int]):
    staff_required(request)

    if not Course.objects.filter(id=course_id).exists():
        return Status(404, Error(detail='Course does not exist'))

    with transaction.atomic():
        Module.objects.filter(course_id=course_id).update(order=-1 * (F('order') + 1))
        for new_order, module_id in enumerate(order):
            Module.objects.filter(id=module_id, course_id=course_id).update(order=new_order)

    return Status(204, None)


@admin_router.post('/lessons', response={201: LessonOut, 403: Error, 404: Error, 409: Error})
def create_lesson(request, data: LessonIn):
    staff_required(request)

    if not Module.objects.filter(id=data.module_id).exists():
        return Status(404, Error(detail='Module does not exist'))

    current_max = Lesson.objects.filter(module_id=data.module_id).aggregate(models.Max('order'))['order__max']
    next_order = 0 if current_max is None else current_max + 1

    try:
        lesson = Lesson.objects.create(
            module_id=data.module_id,
            name=data.name,
            description=data.description or '',
            video_provider=data.video_provider or '',
            video_id=data.video_id or '',
            content=data.content or '',
            duration_seconds=data.duration_seconds or 0,
            order=data.order if data.order > 0 else next_order,
            is_published=data.is_published,
        )
    except IntegrityError:
        return Status(409, Error(detail='Order conflict or invalid video fields'))
    return Status(201, lesson)


@admin_router.get('/lessons/{lesson_id}', response={200: LessonOut, 404: Error})
def get_lesson(request, lesson_id: int):
    staff_required(request)
    return get_object_or_404(Lesson, id=lesson_id)


@admin_router.get('/lessons', response=list[LessonOut])
def list_lessons(request, module_id: int):
    staff_required(request)
    return Lesson.objects.filter(module_id=module_id).order_by('order')


@admin_router.put('/lessons/{lesson_id}', response={200: LessonOut, 403: Error, 404: Error, 409: Error})
def update_lesson(request, lesson_id: int, data: LessonUpdateIn):
    staff_required(request)

    lesson = get_object_or_404(Lesson, id=lesson_id)

    text_fields = {'description', 'video_provider', 'video_id', 'content'}
    for field, value in data.model_dump(exclude_unset=True).items():
        if field in text_fields and value is None:
            value = ''
        setattr(lesson, field, value)

    try:
        lesson.save()
    except IntegrityError:
        return Status(409, Error(detail='Invalid video fields or order conflict'))
    return Status(200, lesson)


@admin_router.delete('/lessons/{lesson_id}', response={204: None, 403: Error, 404: Error})
def delete_lesson(request, lesson_id: int):
    staff_required(request)

    lesson = get_object_or_404(Lesson, id=lesson_id)
    lesson.delete()
    return Status(204, None)


@admin_router.patch('/modules/{module_id}/lessons/reorder', response={204: None, 403: Error, 404: Error})
def reorder_lessons(request, module_id: int, order: list[int]):
    staff_required(request)

    if not Module.objects.filter(id=module_id).exists():
        return Status(404, Error(detail='Module does not exist'))

    with transaction.atomic():
        Lesson.objects.filter(module_id=module_id).update(order=-1 * (F('order') + 1))
        for new_order, lesson_id in enumerate(order):
            Lesson.objects.filter(id=lesson_id, module_id=module_id).update(order=new_order)
    return Status(204, None)


@admin_router.post('/attachments', response={201: LessonAttachmentOut, 403: Error, 404: Error})
def create_attachment(request, data: LessonAttachmentIn):
    staff_required(request)

    if not Lesson.objects.filter(id=data.lesson_id).exists():
        return Status(404, Error(detail='Lesson not found'))

    attachment = LessonAttachment.objects.create(
        lesson_id=data.lesson_id,
        title=data.title,
        file_url=data.file_url,
        size_bytes=data.size_bytes,
        order=data.order,
    )
    return Status(201, attachment)


@admin_router.get('/lessons/{lesson_id}/attachments', response=list[LessonAttachmentOut])
def list_attachments(request, lesson_id: int):
    staff_required(request)
    return LessonAttachment.objects.filter(lesson_id=lesson_id).order_by('order', 'id')


@admin_router.post('/lessons/{lesson_id}/attachments/upload', response={201: LessonAttachmentOut, 400: Error, 404: Error})
def upload_attachment(request, lesson_id: int, file: UploadedFile, title: str | None = None):
    staff_required(request)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if file.size is None or file.size > 50 * 1024 * 1024:
        return Status(400, Error(detail='Arquivo muito grande (max 50MB)'))
    if not file.name:
        return Status(400, Error(detail='Nome ausente'))

    ext = Path(file.name).suffix.lower()
    new_name = f'{uuid.uuid4().hex}{ext}'

    current_max = LessonAttachment.objects.filter(lesson=lesson).aggregate(models.Max('order'))['order__max']
    next_order = 0 if current_max is None else current_max + 1

    attachment = LessonAttachment(
        lesson=lesson,
        title=title or file.name,
        size_bytes=file.size,
        order=next_order,
    )
    attachment.file_url.save(new_name, file, save=False)
    attachment.save()
    return Status(201, attachment)


@admin_router.put('/attachments/{attachment_id}', response={200: LessonAttachmentOut, 403: Error, 404: Error})
def update_attachment(request, attachment_id: int, data: LessonAttachmentUpdateIn):
    staff_required(request)

    attachment = get_object_or_404(LessonAttachment, id=attachment_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(attachment, field, value)
    attachment.save()
    return Status(200, attachment)


@admin_router.delete('/attachments/{attachment_id}', response={204: None, 403: Error, 404: Error})
def delete_attachment(request, attachment_id: int):
    staff_required(request)

    attachment = get_object_or_404(LessonAttachment, id=attachment_id)
    attachment.delete()
    return Status(204, None)
