from ninja import Schema


class ExternalEnrollIn(Schema):
    email: str
    name: str = ''
    phone: str = ''
    course_ids: list[int] = []


class ExternalEnrollOut(Schema):
    detail: str
    user_created: bool
    enrolled_course_ids: list[int]
    skipped_course_ids: list[int]
