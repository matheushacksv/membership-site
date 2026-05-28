from ninja import Schema
from datetime import datetime

class EnrollmentIn(Schema):
    user_id: int
    course_id: int
    expires_at: datetime | None = None
    is_active: bool = True

class EnrollmentOut(Schema):
    id: int
    user_id: int
    course_id: int
    expires_at: datetime | None
    is_active: bool

class UpdateEnrollmentIn(Schema):
    expires_at: datetime | None = None
    is_active: bool | None = None

class ProgressIn(Schema):
    watch_seconds: int = 0
    completed: bool = False

class ProgressOut(Schema):
    id: int
    lesson_id: int
    watch_seconds: int
    completed_at: datetime | None
    last_watched_at: datetime

class CourseProgressOut(Schema):
    total_lessons: int
    completed_count: int
    percent: float
