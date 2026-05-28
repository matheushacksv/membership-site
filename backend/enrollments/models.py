from django.conf import settings
from django.db import models


class CourseEnrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    source = models.CharField(max_length=32, blank=True, default='')
    external_order_id = models.CharField(max_length=64, blank=True, default='', db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"], name="uniq_enrollment_user_course"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]


class LessonProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        "courses.Lesson", on_delete=models.CASCADE, related_name="progress"
    )
    watch_seconds = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_watched_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "lesson"], name="uniq_progress_user_lesson"
            ),
        ]
        indexes = [models.Index(fields=["user", "completed_at"])]
