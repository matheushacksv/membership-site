from datetime import datetime

from ninja import Schema

from .models import Announcement


class AnnouncementOut(Schema):
    """Shape do aluno: só o que aparece no painel."""

    id: int
    title: str
    body: str
    image_url: str | None
    kind: str
    kind_label: str
    published_at: datetime | None

    @staticmethod
    def resolve_image_url(obj) -> str | None:
        return obj.image.url if obj.image else None

    @staticmethod
    def resolve_kind_label(obj) -> str:
        # str() força avaliar o proxy lazy de tradução (.label é _StrOrPromise no django-stubs)
        # e evita get_kind_display() (método dinâmico que o pyright não enxerga sem plugin).
        return str(Announcement.Kind(obj.kind).label)


class AnnouncementAdminOut(AnnouncementOut):
    is_published: bool
    email_sent_at: datetime | None
    created_at: datetime
