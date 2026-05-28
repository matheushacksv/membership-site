from datetime import datetime
from typing import Literal, Optional, Self

from ninja import Schema
from pydantic import Field, model_validator

CategoryLit = Literal[
    'sales', 'marketing', 'strategy', 'tool', 'customer', 'lifestyle', 'development'
]


class CourseListOut(Schema):
    id: int
    name: str
    image: Optional[str] = None
    category: str
    is_active: bool
    sales_page: str | None = None
    checkout_link: str | None = None


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
    description: str | None
    video_provider: str | None
    video_id: str | None
    duration_seconds: int
    content: str | None
    order: int
    attachments: list[LessonAttachmentOut] = []
    completed: bool = False

    @staticmethod
    def resolve_completed(obj) -> bool:
        return getattr(obj, '_completed_for_user', False)


class LessonIn(Schema):
    module_id: int
    name: str
    description: str | None = None
    video_provider: Literal['', 'youtube', 'vimeo', 'panda'] = ''
    video_id: str | None = None
    duration_seconds: int | None = None
    content: str | None = None
    order: int = 0
    is_published: bool = False

    @model_validator(mode='after')
    def at_least_one_content(self) -> Self:
        if not self.video_id and not self.content:
            if self.is_published:
                raise ValueError('Lesson need a video, content or material')
        if bool(self.video_provider) != bool(self.video_id):
            raise ValueError('video_provider e video_id devem ser preenchidos juntos')
        return self


class LessonUpdateIn(Schema):
    name: str | None = None
    description: str | None = None
    video_provider: str | None = None
    video_id: str | None = None
    duration_seconds: int | None = None
    content: str | None = None
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


class ModuleIn(Schema):
    course_id: int
    name: str
    order: int = 0
    is_published: bool = False


class ModuleUpdateIn(Schema):
    name: str | None = None
    order: int | None = None
    is_published: bool | None = None


class ModuleOut(Schema):
    id: int
    name: str
    order: int
    is_published: bool = False
    lessons: list[LessonOut] = []

    @staticmethod
    def resolve_lessons(obj):
        return list(obj.lessons.all())


class CourseDetailOut(Schema):
    id: int
    name: str
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
    image: str | None = None
    category: CategoryLit
    sales_page: str | None = None
    checkout_link: str | None = None
    is_active: bool = False
    kiwify_product_id: str = ''
    access_days: int | None = None


class CourseOut(Schema):
    id: int
    name: str
    image: str | None = None
    category: str
    is_active: bool = False
    kiwify_product_id: str = ''
    access_days: int | None = None

    @staticmethod
    def resolve_image(obj) -> str | None:
        return obj.image.url if obj.image else None


class CourseUpdateIn(Schema):
    name: str | None = None
    image: str | None = None
    category: CategoryLit | None = None
    sales_page: str | None = None
    checkout_link: str | None = None
    is_active: bool | None = None
    kiwify_product_id: str | None = None
    access_days: int | None = None

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

