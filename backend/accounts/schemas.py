from datetime import datetime
from typing import Annotated, Optional, Self

from ninja import Schema
from pydantic import EmailStr, Field, model_validator


class UserSignup(Schema):
    name: Optional[str] = None
    email: EmailStr
    password: str
    repeat_password: str

    @model_validator(mode='after')
    def check_password_length(self) -> Self:
        if len(self.password) <= 8 or len(self.repeat_password) <= 8:
            raise ValueError('Password need to be 8 characters long or more')
        return self

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        if self.password != self.repeat_password:
            raise ValueError('Passwords do not match')
        return self


class NewUserFromWebhook(Schema):
    name: Optional[str] = None
    email: EmailStr
    password: str


class UserOut(Schema):
    id: int
    name: str | None
    email: EmailStr
    phone: str | None = None
    avatar: str | None = None
    is_staff: bool = False

    @staticmethod
    def resolve_avatar(obj) -> str | None:
        return obj.avatar.url if obj.avatar else None


class StaffCreateUserIn(Schema):
    email: EmailStr
    name: str | None = None
    course_ids: list[int] = []


class BulkUserItem(Schema):
    # str (não EmailStr): validação por-item no handler. EmailStr aqui barraria
    # o body inteiro (422) num único email ruim, abortando toda a importação.
    email: str
    name: str | None = None


class BulkImportIn(Schema):
    users: list[BulkUserItem]
    course_ids: list[int] = []
    send_welcome: bool = True


class BulkImportOut(Schema):
    created: int
    existing: int
    enrolled: int
    errors: list[str]


class BulkImportQueuedOut(Schema):
    task_id: str  # group_id na verdade
    total: int
    chunks: int


class BulkImportStatusOut(Schema):
    status: str  # 'pending' | 'done' | 'failed'
    result: BulkImportOut | None = None


class TokenOut(Schema):
    access: str
    refresh: str


class RefreshIn(Schema):
    refresh: str


class MagicLoginIn(Schema):
    token: str


class MagicLinkOut(Schema):
    url: str
    expires_at: datetime


class LoginIn(Schema):
    email: EmailStr
    password: str


class ForgotPasswordIn(Schema):
    email: EmailStr


class ResendLinkIn(Schema):
    uid: str


class ResetPasswordIn(Schema):
    uid: str
    token: str
    password: Annotated[str, Field(min_length=8)]
    repeat_password: str

    def check_passwords_match(self) -> Self:
        if self.password != self.repeat_password:
            raise ValueError('Passwords do not match')
        return self


class MessageOut(Schema):
    detail: str


class UpdateMeIn(Schema):
    name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    phone: str | None = None

    @model_validator(mode='after')
    def check_password_fields(self) -> Self:
        if self.new_password and not self.current_password:
            raise ValueError('To change your password, inform your actual password')
        return self


class StaffUpdateUser(Schema):
    name: str | None = None
    email: EmailStr | None = None
