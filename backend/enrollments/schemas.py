from ninja import Schema
from datetime import datetime
from typing import Literal

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


class EnrollmentAdminOut(Schema):
    id: int
    user_id: int
    user_name: str | None
    user_email: str
    course_id: int
    course_name: str
    expires_at: datetime | None
    is_active: bool
    enrolled_at: datetime

    @staticmethod
    def resolve_user_name(obj):
        return obj.user.name

    @staticmethod
    def resolve_user_email(obj):
        return obj.user.email

    @staticmethod
    def resolve_course_name(obj):
        return obj.course.name


class EnrollmentAdminPage(Schema):
    total: int
    items: list[EnrollmentAdminOut]


class BulkEnrollmentIn(Schema):
    enrollment_ids: list[int]
    action: Literal['set_expiry', 'apply_course_days', 'delete', 'set_active']
    expires_at: datetime | None = None  # set_expiry: data, ou None = vitalícia
    is_active: bool | None = None       # set_active


class BulkEnrollmentOut(Schema):
    affected: int

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


class CertificateOut(Schema):
    code: str
    course_id: int
    course_name: str
    hours: int | None = None
    issued_at: datetime

    @staticmethod
    def resolve_course_name(obj) -> str:
        return obj.course.name


def _mask_cpf(digits: str) -> str:
    # 529.982.247-25 → 529.***.***-25 (confere sem expor o número inteiro; LGPD)
    return f'{digits[:3]}.***.***-{digits[9:]}' if len(digits) == 11 else '***'


class CertificateVerifyOut(Schema):
    """Payload PÚBLICO da verificação, sem CPF completo (LGPD)."""

    code: str
    student_name: str
    student_cpf: str  # mascarado
    course_name: str
    hours: int | None = None
    issued_at: datetime

    @staticmethod
    def resolve_course_name(obj) -> str:
        return obj.course.name

    @staticmethod
    def resolve_student_cpf(obj) -> str:
        return _mask_cpf(obj.student_cpf)


class CertificateConfigOut(Schema):
    signer_name: str
    signer_role: str
    has_signature: bool

    @staticmethod
    def resolve_has_signature(obj) -> bool:
        return bool(obj.signature)


class CertificateConfigIn(Schema):
    signer_name: str = ''
    signer_role: str = ''
