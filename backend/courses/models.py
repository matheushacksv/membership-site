from django.db import models
from django.core.exceptions import ValidationError


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
    image = models.ImageField(upload_to='thumbs/', blank=True, null=True)
    category = models.CharField(max_length=155, choices=Category.choices)
    sales_page = models.URLField(max_length=155, null=True, blank=True)
    checkout_link = models.URLField(max_length=155, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    kiwify_product_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    access_days = models.PositiveIntegerField(null=True, blank=True, help_text='Dias de acesso após matrícula. Vazio = vitalício')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [models.Index(fields=['course', 'order'])]
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'order'], name='uniq_module_order_per_course'
            )
        ]

    def __str__(self) -> str:
        return self.name


class Lesson(models.Model):
    class VideoProvider(models.TextChoices):
        YOUTUBE = 'youtube', 'YouTube'
        VIMEO = 'vimeo', 'Vimeo'
        PANDA = 'panda', 'Panda'

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    video_provider = models.CharField(
        choices=VideoProvider.choices, max_length=255, blank=True, default=''
    )
    video_id = models.CharField(max_length=255, blank=True, default='')
    content = models.TextField(blank=True, default='')
    duration_seconds = models.PositiveIntegerField(default=0)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [models.Index(fields=['module', 'order'])]
        constraints = [
            models.UniqueConstraint(
                fields=['module', 'order'], name='uniq_lesson_order_per_module'
            ),
            models.CheckConstraint(
                name='lesson_video_provider_and_id_together',
                condition=(
                    (models.Q(video_provider='') & models.Q(video_id=''))
                    | (~models.Q(video_provider='') & ~models.Q(video_id=''))
                ),
            ),
        ]


class LessonAttachment(models.Model):
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name='attachments'
    )
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

        
