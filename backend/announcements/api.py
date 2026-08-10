import uuid
from pathlib import Path

from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_q.tasks import async_task
from ninja import File, Form, Router, Status
from ninja.files import UploadedFile

from core.utils.errors import Error
from core.utils.permissions import staff_required

from .models import Announcement
from .schemas import AnnouncementAdminOut, AnnouncementOut

router = Router(tags=['Announcements'])

_ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def _clean_image(file: UploadedFile) -> str:
    """Valida a imagem do informativo e devolve um nome uuid. Levanta ValueError com msg pronta."""
    if file.size is None or file.size > 5 * 1024 * 1024:
        raise ValueError('Imagem muito grande (máx 5MB)')
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise ValueError('Tipo inválido: jpg, png ou webp')
    if not file.name:
        raise ValueError('Arquivo sem nome')
    return f'{uuid.uuid4().hex}{Path(file.name).suffix.lower()}'


# * -------------------------------------------- * #
# ? ------------------ Aluno ------------------- ? #
# * -------------------------------------------- * #


@router.get('', response=list[AnnouncementOut])
def list_announcements(request):
    return Announcement.objects.filter(is_published=True)[:20]


@router.get('/unread-count', response=dict)
def unread_count(request):
    seen = request.auth.notifications_seen_at
    qs = Announcement.objects.filter(is_published=True)
    if seen:
        qs = qs.filter(published_at__gt=seen)
    return {'count': qs.count()}


@router.post('/mark-read', response=dict)
def mark_read(request):
    request.auth.notifications_seen_at = timezone.now()
    request.auth.save(update_fields=['notifications_seen_at'])
    return {'ok': True}


# * -------------------------------------------- * #
# ? ------------------ Staff ------------------- ? #
# * -------------------------------------------- * #


@router.get('/admin/all', response=list[AnnouncementAdminOut])
def admin_list(request):
    staff_required(request)
    return Announcement.objects.all()


@router.post('/admin/upload-image', response={200: dict, 400: Error})
def admin_upload_image(request, file: UploadedFile = File(...)):
    """Upload de imagem inline do editor rico → devolve {url} pública pra embutir no corpo."""
    staff_required(request)
    try:
        name = _clean_image(file)
    except ValueError as e:
        return Status(400, Error(detail=str(e)))
    path = default_storage.save(f'announcements/{name}', file)
    return {'url': default_storage.url(path)}


@router.post('/admin', response={201: AnnouncementAdminOut, 400: Error})
def admin_create(
    request,
    title: str = Form(...),
    body: str = Form(...),
    kind: str = Form(Announcement.Kind.INFO),
    is_published: bool = Form(False),
    file: UploadedFile | None = File(None),
):
    staff_required(request)
    title, body = title.strip(), body.strip()
    if not title or not body:
        return Status(400, Error(detail='Título e texto são obrigatórios'))
    if kind not in Announcement.Kind.values:
        return Status(400, Error(detail='Tipo inválido'))
    new_name = None
    if file:
        try:
            new_name = _clean_image(file)
        except ValueError as e:
            return Status(400, Error(detail=str(e)))
    ann = Announcement(title=title, body=body, kind=kind, is_published=is_published)
    if is_published:
        ann.published_at = timezone.now()
    ann.save()
    if file:
        ann.image.save(new_name, file, save=True)
    return Status(201, ann)


# POST (não PATCH): multipart/FILES só é populado nativamente em POST no Django; PATCH exigiria
# o fix_request_files_middleware global do ninja. POST /admin/{id} evita esse acoplamento.
@router.post('/admin/{ann_id}', response={200: AnnouncementAdminOut, 400: Error, 404: Error})
def admin_update(
    request,
    ann_id: int,
    title: str = Form(...),
    body: str = Form(...),
    kind: str = Form(Announcement.Kind.INFO),
    is_published: bool = Form(False),
    remove_image: bool = Form(False),
    file: UploadedFile | None = File(None),
):
    staff_required(request)
    title, body = title.strip(), body.strip()
    if not title or not body:
        return Status(400, Error(detail='Título e texto são obrigatórios'))
    if kind not in Announcement.Kind.values:
        return Status(400, Error(detail='Tipo inválido'))
    new_name = None
    if file:
        try:
            new_name = _clean_image(file)
        except ValueError as e:
            return Status(400, Error(detail=str(e)))

    ann = get_object_or_404(Announcement, id=ann_id)
    ann.title, ann.body, ann.kind = title, body, kind
    # Publicar pela 1ª vez carimba published_at (base dos não-lidos). Despublicar mantém o carimbo.
    if is_published and ann.published_at is None:
        ann.published_at = timezone.now()
    ann.is_published = is_published
    if file:
        ann.image.save(new_name, file, save=False)
    elif remove_image and ann.image:
        ann.image.delete(save=False)
    ann.save()
    return Status(200, ann)


@router.delete('/admin/{ann_id}', response={204: None, 404: Error})
def admin_delete(request, ann_id: int):
    staff_required(request)
    get_object_or_404(Announcement, id=ann_id).delete()
    return 204, None


@router.post('/admin/{ann_id}/send-email', response={200: AnnouncementAdminOut, 400: Error, 404: Error})
def admin_send_email(request, ann_id: int):
    staff_required(request)
    ann = get_object_or_404(Announcement, id=ann_id)
    if not ann.is_published:
        return Status(400, Error(detail='Publique o informativo antes de enviar por email'))
    if ann.email_sent_at:
        return Status(400, Error(detail='Email já enviado para este informativo'))
    # Carimba antes de enfileirar: trava o botão na hora e evita duplo-disparo por corrida de clique.
    ann.email_sent_at = timezone.now()
    ann.save(update_fields=['email_sent_at'])
    async_task('announcements.tasks.broadcast_email', ann.id)
    return Status(200, ann)
