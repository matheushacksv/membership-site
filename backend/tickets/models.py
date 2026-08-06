from django.conf import settings
from django.db import models


class Ticket(models.Model):
    class Category(models.TextChoices):
        TECHNICAL = 'technical', 'Erro técnico'
        BUG = 'bug', 'Reportar Bug'
        ACCESS = 'access', 'Sem Acesso'
        PERFORMANCE = 'performance', 'Lentidão/Performance'
        OUT = 'out', 'Sistema fora do ar'
        SUGGESTION = 'suggestion', 'Sugestão de melhoria'
        DOUBT = 'doubt', 'Dúvidas'

    class Status(models.TextChoices):
        OPEN = 'open', 'Aberto'
        IN_PROGRESS = 'in_progress', 'Em andamento'
        RESOLVED = 'resolved', 'Resolvido'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    user_id: int  # anotação bare: ensina o pyright o atributo <fk>_id (Django cria em runtime); não vira campo
    category = models.CharField(max_length=20, choices=Category.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # bump em nova mensagem/status → ordena a fila

    class Meta:
        ordering = ['-updated_at']
        indexes = [models.Index(fields=['status', 'updated_at'])]

    def __str__(self):
        return f'#{self.pk} · {self.category} · user {self.user_id}'


class TicketMessage(models.Model):
    """Cada mensagem da thread — incl. a 1ª (descrição do aluno). Sem caso especial pro root."""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    ticket_id: int  # anotação bare p/ o pyright (ver Ticket.user_id)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ticket_messages')
    body = models.TextField()
    attachment = models.FileField(upload_to='tickets/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'msg {self.pk} · ticket {self.ticket_id}'
