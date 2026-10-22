from datetime import datetime

from ninja import Schema

from .models import Ticket


class TicketMessageOut(Schema):
    id: int
    body: str
    attachment_url: str | None
    author_name: str | None
    is_staff: bool
    created_at: datetime

    @staticmethod
    def resolve_attachment_url(obj) -> str | None:
        return obj.attachment.url if obj.attachment else None

    @staticmethod
    def resolve_author_name(obj) -> str | None:
        return obj.author.name

    @staticmethod
    def resolve_is_staff(obj) -> bool:
        return obj.author.is_staff


class TicketOut(Schema):
    """Item de lista. user_* e last_message só preenchem na listagem admin."""

    id: int
    category: str
    category_label: str
    status: str
    status_label: str
    created_at: datetime
    updated_at: datetime
    user_name: str | None = None
    user_email: str | None = None
    last_message: str | None = None

    @staticmethod
    def resolve_category_label(obj) -> str:
        # str() força avaliar o proxy lazy de tradução (.label é _StrOrPromise no django-stubs)
        # e evita get_category_display() (método dinâmico que o pyright não enxerga sem plugin).
        return str(Ticket.Category(obj.category).label)

    @staticmethod
    def resolve_status_label(obj) -> str:
        return str(Ticket.Status(obj.status).label)


class TicketDetailOut(TicketOut):
    messages: list[TicketMessageOut]


class RequesterEnrollmentOut(Schema):
    course_name: str
    is_active: bool
    enrolled_at: datetime
    expires_at: datetime | None
    source: str
    completed: int
    total: int


class RequesterTicketOut(Schema):
    id: int
    category_label: str
    status: str
    status_label: str
    created_at: datetime

    @staticmethod
    def resolve_category_label(obj) -> str:
        return str(Ticket.Category(obj.category).label)

    @staticmethod
    def resolve_status_label(obj) -> str:
        return str(Ticket.Status(obj.status).label)


class RequesterOut(Schema):
    """Ficha do aluno que abriu o chamado (só staff)."""

    id: int
    name: str | None
    email: str
    phone: str | None
    cpf: str
    avatar_url: str | None
    is_active: bool
    created_at: datetime
    last_activity_at: datetime | None  # última aula assistida (JWT não grava last_login)
    enrollments: list[RequesterEnrollmentOut]
    other_tickets: list[RequesterTicketOut]


class MessageIn(Schema):
    body: str


class StatusIn(Schema):
    status: str
