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


class EvolutionConfigIn(Schema):
    base_url: str = ''
    instance: str = ''
    api_key: str = ''
    is_active: bool = False


class EvolutionConfigOut(Schema):
    base_url: str
    instance: str
    api_key: str
    is_active: bool


class PandaConfigIn(Schema):
    base_url: str = 'https://api-v2.pandavideo.com.br'
    api_key: str = ''
    is_active: bool = False


class PandaConfigOut(Schema):
    base_url: str
    api_key: str
    is_active: bool
