from django.contrib import admin

from .models import Certificate, CertificateConfig


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('code', 'student_name', 'course', 'hours', 'issued_at')
    search_fields = ('code', 'student_name', 'student_cpf', 'user__email')
    list_filter = ('course', 'issued_at')
    readonly_fields = ('code', 'issued_at')


@admin.register(CertificateConfig)
class CertificateConfigAdmin(admin.ModelAdmin):
    list_display = ('signer_name', 'signer_role', 'updated_at')
    exclude = ('signature',)  # binário: editado pela UI do admin da plataforma
