from datetime import datetime
from typing import Literal, Optional, Self

from ninja import Schema
from pydantic import EmailStr, Field, model_validator

CategoryLit = Literal['sales', 'marketing', 'strategy', 'tool', 'customer', 'lifestyle', 'development']


class CourseListOut(Schema):
    id: int
    name: str
    image: Optional[str] = None
    category: str
    is_active: bool
    sales_page: str | None = None
    checkout_link: str | None = None
    total_lessons: int | None = None
    completed_lessons: int | None = None
    resume_lesson_id: int | None = None


class LessonAttachmentOut(Schema):
    id: int
    title: str
    file_url: str
    size_bytes: int

    @staticmethod
    def resolve_file_url(obj) -> str:
        f = obj.file_url
        if not f:
            return ''
        try:
            return f.url
        except Exception:
            return str(f)


class LessonOut(Schema):
    id: int
    name: str
    kind: str = 'video'
    description: str | None
    video_provider: str | None
    video_id: str | None
    duration_seconds: int
    content: str | None
    allow_retake: bool = True
    time_limit_seconds: int = 0
    order: int
    is_published: bool = False
    attachments: list[LessonAttachmentOut] = []
    completed: bool = False

    @staticmethod
    def resolve_completed(obj) -> bool:
        return getattr(obj, '_completed_for_user', False)


class LessonIn(Schema):
    module_id: int
    name: str
    kind: Literal['video', 'quiz'] = 'video'
    description: str | None = None
    video_provider: Literal['', 'youtube', 'vimeo', 'panda'] = ''
    video_id: str | None = None
    duration_seconds: int | None = None
    content: str | None = None
    allow_retake: bool = True
    time_limit_seconds: int = 0
    order: int = 0
    is_published: bool = False

    @model_validator(mode='after')
    def at_least_one_content(self) -> Self:
        # Aula de exercício não tem vídeo nem conteúdo: o conteúdo dela são as perguntas.
        if not self.video_id and not self.content and self.kind != 'quiz':
            if self.is_published:
                raise ValueError('Lesson need a video, content or material')
        if bool(self.video_provider) != bool(self.video_id):
            raise ValueError('video_provider e video_id devem ser preenchidos juntos')
        return self


class LessonUpdateIn(Schema):
    name: str | None = None
    kind: Literal['video', 'quiz'] | None = None
    description: str | None = None
    video_provider: str | None = None
    video_id: str | None = None
    duration_seconds: int | None = None
    content: str | None = None
    allow_retake: bool | None = None
    time_limit_seconds: int | None = None
    order: int | None = None
    is_published: bool | None = None


class LessonAttachmentIn(Schema):
    lesson_id: int
    title: str
    file_url: str
    size_bytes: int = 0
    order: int = 0


class LessonAttachmentUpdateIn(Schema):
    title: str | None = None
    file_url: str | None = None
    size_bytes: int | None = None
    order: int | None = None


class AttachmentLibraryOut(LessonAttachmentOut):
    """Anexo já existente + de onde ele veio, pro picker do admin."""

    lesson_name: str
    course_name: str

    @staticmethod
    def resolve_lesson_name(obj) -> str:
        return obj.lesson.name

    @staticmethod
    def resolve_course_name(obj) -> str:
        return obj.lesson.module.course.name


class LinkAttachmentIn(Schema):
    attachment_id: int


class ModuleIn(Schema):
    course_id: int
    name: str
    order: int = 0
    is_published: bool = False


class ModuleUpdateIn(Schema):
    name: str | None = None
    order: int | None = None
    is_published: bool | None = None
    requires_previous: bool | None = None


class CopyModuleIn(Schema):
    course_id: int  # curso destino


class ModuleLibraryOut(Schema):
    """Módulo de qualquer curso + de onde veio, pro picker de importação do admin."""

    id: int
    name: str
    course_name: str
    lesson_count: int  # via annotate(Count('lessons')) — sem resolver

    @staticmethod
    def resolve_course_name(obj) -> str:
        return obj.course.name


class ModuleOut(Schema):
    id: int
    name: str
    order: int
    is_published: bool = False
    requires_previous: bool = False
    locked: bool = False
    lesson_count: int = 0
    lessons: list[LessonOut] = []

    @staticmethod
    def resolve_locked(obj) -> bool:
        return getattr(obj, '_locked', False)

    @staticmethod
    def resolve_lesson_count(obj) -> int:
        return len(obj.lessons.all())  # cache do prefetch, sem query extra

    @staticmethod
    def resolve_lessons(obj):
        # Módulo travado não vaza as aulas (nem vídeo nem conteúdo).
        return [] if getattr(obj, '_locked', False) else list(obj.lessons.all())


class CourseDetailOut(Schema):
    id: int
    name: str
    slug: str | None = None
    is_free: bool = False
    lp_template: str = ''
    image: str | None
    category: str
    modules: list[ModuleOut] = []
    is_active: bool
    sales_page: str | None
    checkout_link: str | None
    kiwify_product_id: str = ''
    access_days: int | None = None


class CourseIn(Schema):
    name: str
    slug: str | None = None
    is_free: bool = False
    lp_template: str = ''
    image: str | None = None
    category: CategoryLit
    sales_page: str | None = None
    checkout_link: str | None = None
    is_active: bool = False
    kiwify_product_id: str = ''
    access_days: int | None = None
    quiz_webhook_url: str = ''


class CourseOut(Schema):
    id: int
    name: str
    slug: str | None = None
    is_free: bool = False
    lp_template: str = ''
    image: str | None = None
    category: str
    is_active: bool = False
    sales_page: str | None = None
    checkout_link: str | None = None
    kiwify_product_id: str = ''
    access_days: int | None = None
    quiz_webhook_url: str = ''

    @staticmethod
    def resolve_image(obj) -> str | None:
        return obj.image.url if obj.image else None


class CourseUpdateIn(Schema):
    name: str | None = None
    slug: str | None = None
    is_free: bool | None = None
    lp_template: str | None = None
    image: str | None = None
    category: CategoryLit | None = None
    sales_page: str | None = None
    checkout_link: str | None = None
    is_active: bool | None = None
    kiwify_product_id: str | None = None
    access_days: int | None = None
    quiz_webhook_url: str | None = None


# --- LP de curso gratuito (endpoints públicos /catalog/free/*) ---
class FreeCourseLPOut(Schema):
    id: int
    name: str
    lp_template: str = ''
    image: str | None = None

    @staticmethod
    def resolve_image(obj) -> str | None:
        return obj.image.url if obj.image else None


class FreeSignupIn(Schema):
    name: str
    email: EmailStr
    phone: str = ''


class FreeSignupOut(Schema):
    created: bool
    course_id: int
    access: str | None = None
    refresh: str | None = None


class BannerOut(Schema):
    id: int
    title: str
    image: str | None = None
    url: str
    is_active: bool

    @staticmethod
    def resolve_image(obj) -> str | None:
        return obj.image.url if obj.image else None


class BannerUpdateIn(Schema):
    title: str | None = None
    url: str | None = None
    is_active: bool | None = None


class CommentAuthorOut(Schema):
    id: int
    name: str | None
    avatar: str | None = None
    is_staff: bool

    @staticmethod
    def resolve_avatar(obj) -> str | None:
        return obj.avatar.url if obj.avatar else None


class CommentOut(Schema):
    id: int
    body: str
    created_at: datetime
    updated_at: datetime | None
    author: CommentAuthorOut
    replies: list['CommentOut'] = []


class CommentIn(Schema):
    body: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = None


class CommentUpdateIn(Schema):
    body: str = Field(min_length=1, max_length=2000)


# Forms

FieldType = Literal['text', 'textarea', 'rating', 'choice']


class FormFieldSchema(Schema):
    key: str = ''
    label: str
    type: FieldType
    required: bool = False
    options: list[str] = []


class CourseFormIn(Schema):
    title: str = ''
    description: str = ''
    fields: list[FormFieldSchema] = []
    every_days: int = 30
    required: bool = False
    is_active: bool = True

    @model_validator(mode='after')
    def check_fields(self) -> Self:
        for f in self.fields:
            if f.type == 'choice' and not [o for o in f.options if o.strip()]:
                raise ValueError(f'Campo  "{f.label}" (escolha) precisa de opções')
        return self


class CourseFormOut(Schema):
    id: int
    title: str
    description: str
    fields: list[FormFieldSchema] = []
    every_days: int
    required: bool
    is_active: bool


class FormResponseIn(Schema):
    answers: dict = {}
    skipped: bool = False


class FormResponseAdminOut(Schema):
    id: int
    user_name: str | None
    user_email: str
    answers: dict
    created_at: datetime

    @staticmethod
    def resolve_user_name(obj):
        return obj.user.name

    @staticmethod
    def resolve_user_email(obj):
        return obj.user.email

class DueFormOut(Schema):
    form: CourseFormOut | None = None


# Quiz (aula de exercício)


class QuizQuestionOut(Schema):
    """O que o aluno recebe ANTES de responder. Sem `correct`/`explanation` de propósito:
    o que sai daqui está no devtools dele."""

    key: str
    prompt: str
    type: str = 'choice'  # 'choice' | 'text' (dissertativa)
    options: list[str] = []


class QuizQuestionIn(Schema):
    """Pergunta completa — só trafega em rota staff."""

    key: str = ''
    prompt: str
    type: Literal['choice', 'text'] = 'choice'
    options: list[str] = []
    correct: int = 0
    explanation: str = ''

    @model_validator(mode='after')
    def check_options(self) -> Self:
        if self.type == 'text':  # dissertativa não tem opções/gabarito
            return self
        opts = [o for o in self.options if o.strip()]
        if len(opts) < 2:
            raise ValueError(f'"{self.prompt}" precisa de ao menos 2 opções')
        if not 0 <= self.correct < len(opts):
            raise ValueError(f'"{self.prompt}": gabarito fora das opções')
        return self


class QuizSaveIn(Schema):
    questions: list[QuizQuestionIn] = []


class QuizSubmitIn(Schema):
    # int = índice da opção (escolha); str = texto (dissertativa).
    answers: dict[str, int | str] = {}
    timed_out: bool = False  # só sinal de UX; o servidor revalida o tempo


class QuizTimerOut(Schema):
    started_at: datetime
    expires_at: datetime
    server_now: datetime


class QuizResultItem(Schema):
    key: str
    type: str = 'choice'
    correct: int
    chosen: int | None = None
    answer_text: str | None = None  # dissertativa: o que o aluno escreveu
    explanation: str = ''


class QuizResultOut(Schema):
    score: int
    total: int
    results: list[QuizResultItem] = []


class QuizStateOut(Schema):
    questions: list[QuizQuestionOut] = []
    attempt: QuizResultOut | None = None
    allow_retake: bool = True
    time_limit_seconds: int = 0
    timer: QuizTimerOut | None = None  # tentativa em curso (retoma o tempo restante)
    attempts: int = 0
    timed_out: bool = False


class QuizResponseAdminOut(Schema):
    user_name: str | None
    user_email: str
    score: int
    total: int
    attempts: int = 0
    timed_out: bool = False
    answers: dict
    updated_at: datetime

    @staticmethod
    def resolve_user_name(obj):
        return obj.user.name

    @staticmethod
    def resolve_user_email(obj):
        return obj.user.email