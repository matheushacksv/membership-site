from django.db import models


class EvolutionConfig(models.Model):
    """Config singleton (pk=1) da instância Evolution API pra WhatsApp. Editável no
    painel admin. api_key é segredo — só trafega por rota staff, nunca no front público."""

    base_url = models.URLField(blank=True)
    instance = models.CharField(max_length=120, blank=True)
    api_key = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls) -> 'EvolutionConfig':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def ready(self) -> bool:
        return self.is_active and bool(self.base_url and self.instance and self.api_key)

    def __str__(self) -> str:
        return f'EvolutionConfig(instance={self.instance!r}, active={self.is_active})'


class PandaConfig(models.Model):
    """Config singleton (pk=1) da API do Panda Video. Usada só pra buscar a duração dos
    vídeos e preencher Lesson.duration_seconds automático (carga horária do certificado).
    api_key é segredo — só trafega por rota staff."""

    base_url = models.URLField(blank=True, default='https://api-v2.pandavideo.com.br')
    api_key = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls) -> 'PandaConfig':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def ready(self) -> bool:
        return self.is_active and bool(self.base_url and self.api_key)

    def __str__(self) -> str:
        return f'PandaConfig(active={self.is_active})'
