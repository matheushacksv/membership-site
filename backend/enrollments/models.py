import uuid

from django.conf import settings
from django.db import models


def _gen_certificate_code() -> str:
    return uuid.uuid4().hex[:12].upper()


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


class Certificate(models.Model):
    """Certificado de conclusão (100% do curso). Só metadado: o PDF é regerado on-demand
    a partir desta linha (ver enrollments/certificate_pdf.py) — nada é gravado no storage.
    Os campos de aluno/carga são snapshots do momento da emissão, pro certificado ficar
    estável se o aluno depois renomear ou o curso mudar."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates"
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="certificates"
    )
    code = models.CharField(max_length=12, unique=True, default=_gen_certificate_code, editable=False)
    student_name = models.CharField(max_length=155)
    student_cpf = models.CharField(max_length=11)
    hours = models.PositiveIntegerField(null=True, blank=True)  # null = sem carga horária impressa
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"], name="uniq_certificate_user_course"
            ),
        ]

    def __str__(self) -> str:
        return f'{self.code} · {self.student_name}'


class CertificateConfig(models.Model):
    """Config singleton (pk=1) do certificado: assinatura + responsável, editável no admin.

    A assinatura fica no BANCO (BinaryField), não no bucket público do MinIO: um PNG isolado
    da assinatura é forjável, então não pode ser servido por URL pública. É lida no render do
    PDF e só sai por endpoint staff."""

    signer_name = models.CharField(max_length=120, blank=True, default='')
    signer_role = models.CharField(max_length=120, blank=True, default='')
    signature = models.BinaryField(null=True, blank=True)  # PNG transparente (bytes)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls) -> 'CertificateConfig':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        return f'CertificateConfig(signer={self.signer_name!r}, has_signature={bool(self.signature)})'
