from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Course(models.Model):
    class Category(models.TextChoices):
        SALES = 'sales', 'Vendas e Negociação'
        MARKETING = 'marketing', 'Marketing'
        STRATEGY = 'strategy', 'Estratégia Digital'
        TOOL = 'tool', 'Ferramenta(s)'
        CUSTOMER = 'customer', 'Customer Success'
        LIFESTYLE = 'lifestyle', 'Estilo de Vida'
        DEVELOPMENT = 'development', 'Desenvolvimento'

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=160, unique=True, null=True, blank=True, help_text='URL da LP pública (/lp/<slug>). Só usado se is_free')
    is_free = models.BooleanField(default=False, help_text='Curso gratuito: libera cadastro pela LP pública /lp/<slug>')
    lp_template = models.CharField(max_length=32, blank=True, default='', help_text="Layout da LP: '' = padrão, 'closer' = pré-qualificação Closer")
    image = models.ImageField(upload_to='thumbs/', blank=True, null=True)
    category = models.CharField(max_length=155, choices=Category.choices)
    sales_page = models.URLField(max_length=155, null=True, blank=True)
    checkout_link = models.URLField(max_length=155, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    kiwify_product_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    access_days = models.PositiveIntegerField(null=True, blank=True, help_text='Dias de acesso após matrícula. Vazio = vitalício')
    quiz_webhook_url = models.URLField(max_length=500, blank=True, default='', help_text='POST disparado ao aluno concluir um exercício deste curso. Vazio = desligado')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=False)
    requires_previous = models.BooleanField(default=False, help_text='Trava até todas as aulas dos módulos anteriores estarem concluídas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [models.Index(fields=['course', 'order'])]
        constraints = [models.UniqueConstraint(fields=['course', 'order'], name='uniq_module_order_per_course')]

    def __str__(self) -> str:
        return self.name


class Lesson(models.Model):
    class VideoProvider(models.TextChoices):
        YOUTUBE = 'youtube', 'YouTube'
        VIMEO = 'vimeo', 'Vimeo'
        PANDA = 'panda', 'Panda'

    class Kind(models.TextChoices):
        VIDEO = 'video', 'Vídeo'
        QUIZ = 'quiz', 'Exercício'

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.VIDEO)
    questions = models.JSONField(default=list, blank=True)  # [{key, prompt, options, correct, explanation}]
    description = models.TextField(blank=True)
    video_provider = models.CharField(choices=VideoProvider.choices, max_length=255, blank=True, default='')
    video_id = models.CharField(max_length=255, blank=True, default='')
    content = models.TextField(blank=True, default='')
    duration_seconds = models.PositiveIntegerField(default=0)
    allow_retake = models.BooleanField(default=True, help_text='Exercício: permitir refazer. Desligado = 1 tentativa')
    time_limit_seconds = models.PositiveIntegerField(default=0, help_text='Exercício: tempo em segundos. 0 = sem tempo')
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [models.Index(fields=['module', 'order'])]
        constraints = [
            models.UniqueConstraint(fields=['module', 'order'], name='uniq_lesson_order_per_module'),
            models.CheckConstraint(
                name='lesson_video_provider_and_id_together',
                condition=((models.Q(video_provider='') & models.Q(video_id='')) | (~models.Q(video_provider='') & ~models.Q(video_id=''))),
            ),
        ]


class LessonAttachment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attachments')
    title = models.CharField(max_length=255)
    file_url = models.FileField(upload_to='attachments/')
    size_bytes = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']


class LessonComment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['lesson', 'parent', 'created_at'])]

    def clean(self):
        if self.parent and self.parent.parent_id is not None:
            raise ValidationError('Replies just can be replyed by root comments')


class CourseForm(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='forms')
    title = models.CharField(max_length=255, default='')
    description = models.CharField(max_length=500, blank=True, default='')
    fields = models.JSONField(default=list)
    every_days = models.PositiveIntegerField(default=30)
    required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class FormResponse(models.Model):
    form = models.ForeignKey(CourseForm, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='form_responses')
    answers = models.JSONField(default=dict)
    skipped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['form', 'user', 'created_at'])]


class QuizAttempt(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quiz_attempts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    answers = models.JSONField(default=dict)  # {key: índice escolhido}
    score = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    attempts = models.PositiveIntegerField(default=0)  # nº de finalizações (submit ou timeout)
    timed_out = models.BooleanField(default=False)  # a última tentativa venceu no tempo
    started_at = models.DateTimeField(null=True, blank=True)  # início da tentativa em curso
    submitted_at = models.DateTimeField(null=True, blank=True)  # finalização; nulo = tentativa aberta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # ponytail: 1 linha por aluno/aula, sempre a última tentativa (update_or_create).
        # Histórico some. Se um dia quiserem ver evolução: derruba a constraint e a tela
        # de respostas passa a usar DISTINCT ON (lesson, user).
        constraints = [models.UniqueConstraint(fields=['lesson', 'user'], name='uniq_quiz_attempt_per_user')]

    def __str__(self) -> str:
        return f'{self.user_id} · {self.lesson_id} · {self.score}/{self.total}'


class Banner(models.Model):
    title = models.CharField(max_length=255)  # alt/título interno
    image = models.ImageField(upload_to='banners/')
    url = models.URLField(max_length=500)  # destino ao clicar
    is_active = models.BooleanField(default=False)  # só aparece p/ aluno quando ativado
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # mais novo no topo

    def __str__(self) -> str:
        return self.title


class DownloadLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='downloads')
    attachment = models.ForeignKey(LessonAttachment, on_delete=models.SET_NULL, null=True, related_name='downloads')
    email = models.EmailField()  # snapshot: trilha sobrevive à edição/exclusão do user
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['attachment', 'created_at'])]

    def __str__(self) -> str:
        return f'{self.email} · {self.created_at:%d/%m/%Y %H:%M}'
