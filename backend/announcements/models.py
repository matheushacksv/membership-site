from django.db import models


class Announcement(models.Model):
    """Informativo broadcast: downtime, mudança na plataforma, nova feature."""

    class Kind(models.TextChoices):
        DOWNTIME = 'downtime', 'Fora do ar'
        CHANGE = 'change', 'Mudança na plataforma'
        FEATURE = 'feature', 'Nova funcionalidade'
        INFO = 'info', 'Informativo'

    title = models.CharField(max_length=200)
    body = models.TextField()
    image = models.ImageField(upload_to='announcements/', null=True, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.INFO)
    is_published = models.BooleanField(default=False)  # espelha Banner.is_active: só aparece pro aluno quando publicado
    published_at = models.DateTimeField(null=True, blank=True)  # setado na 1ª publicação; base do cálculo de não-lidos
    email_sent_at = models.DateTimeField(null=True, blank=True)  # null = nunca enviado; trava reenvio
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self) -> str:
        return f'#{self.pk} · {self.kind} · {self.title}'
