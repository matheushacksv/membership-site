import uuid
from pathlib import Path

from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Status
from ninja.files import UploadedFile

from core.utils.errors import Error
from core.utils.permissions import staff_required
from courses.models import Lesson
from enrollments.models import CourseEnrollment, LessonProgress

from .models import Ticket, TicketMessage
from .schemas import MessageIn, RequesterOut, StatusIn, TicketDetailOut, TicketMessageOut, TicketOut  # noqa: F401 (MessageIn: doc do shape do body)

router = Router(tags=['Tickets'])

# Anexo de suporte (print do bug, comprovante). Público no MinIO, ok, sem valor forense.
_ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'application/pdf'}


def _clean_upload(file: UploadedFile) -> str:
    """Valida o anexo e devolve um nome uuid. Levanta ValueError com msg pronta pro Error."""
    if file.size is None or file.size > 5 * 1024 * 1024:
        raise ValueError('Arquivo muito grande (máx 5MB)')
    if file.content_type not in _ALLOWED_TYPES:
        raise ValueError('Tipo inválido: jpg, png, webp ou pdf')
    if not file.name:
        raise ValueError('Arquivo sem nome')
    return f'{uuid.uuid4().hex}{Path(file.name).suffix.lower()}'


# * -------------------------------------------- * #
# ? --------------- Aluno (dono) --------------- ? #
# * -------------------------------------------- * #


@router.post('', response={201: TicketDetailOut, 400: Error})
def create_ticket(request, category: Form[str], body: Form[str], file: UploadedFile | None = File(None)):
    """Abre um chamado. Multipart: categoria + descrição (vira a 1ª mensagem) + anexo opcional."""
    category = (category or '').strip()
    body = (body or '').strip()
    if category not in Ticket.Category.values:
        return Status(400, Error(detail='Categoria inválida'))
    if not body:
        return Status(400, Error(detail='Descreva o problema'))
    new_name = None
    if file:
        try:
            new_name = _clean_upload(file)
        except ValueError as e:
            return Status(400, Error(detail=str(e)))

    ticket = Ticket.objects.create(user=request.auth, category=category)
    msg = TicketMessage.objects.create(ticket=ticket, author=request.auth, body=body)
    if file:
        msg.attachment.save(new_name, file, save=True)
    return Status(201, ticket)


@router.get('', response=list[TicketOut])
def list_my_tickets(request):
    return Ticket.objects.filter(user=request.auth)


@router.get('/{ticket_id}', response={200: TicketDetailOut, 403: Error, 404: Error})
def get_ticket(request, ticket_id: int):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if ticket.user_id != request.auth.id and not request.auth.is_staff:
        return Status(403, Error(detail='Sem acesso a este chamado'))
    return Status(200, ticket)


@router.post('/{ticket_id}/messages', response={201: TicketMessageOut, 400: Error, 403: Error, 404: Error})
def add_message(request, ticket_id: int, body: Form[str], file: UploadedFile | None = File(None)):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    is_staff = request.auth.is_staff
    if ticket.user_id != request.auth.id and not is_staff:
        return Status(403, Error(detail='Sem acesso a este chamado'))
    # RESOLVED é terminal: não reabre por resposta: abre-se um novo chamado.
    if ticket.status == Ticket.Status.RESOLVED:
        return Status(400, Error(detail='Chamado finalizado. Abra um novo chamado.'))
    body = (body or '').strip()
    if not body:
        return Status(400, Error(detail='Mensagem vazia'))
    new_name = None
    if file:
        try:
            new_name = _clean_upload(file)
        except ValueError as e:
            return Status(400, Error(detail=str(e)))

    msg = TicketMessage.objects.create(ticket=ticket, author=request.auth, body=body)
    if file:
        msg.attachment.save(new_name, file, save=True)

    # Staff responde chamado aberto → em andamento.
    if is_staff and ticket.status == Ticket.Status.OPEN:
        ticket.status = Ticket.Status.IN_PROGRESS
    ticket.save(update_fields=['status', 'updated_at'])  # bump updated_at → sobe na fila
    return Status(201, msg)


# * -------------------------------------------- * #
# ? ------------------ Staff ------------------- ? #
# * -------------------------------------------- * #


@router.get('/admin/all', response=list[TicketOut])
def admin_list_tickets(request, status: str | None = None, category: str | None = None):
    staff_required(request)
    qs = Ticket.objects.select_related('user').prefetch_related('messages')
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category=category)
    out = []
    for t in qs:
        t.user_name = t.user.name
        t.user_email = t.user.email
        msgs = list(t.messages.all())
        t.last_message = msgs[-1].body[:120] if msgs else ''
        out.append(t)
    return out


@router.get('/admin/open-count', response=dict)
def admin_open_count(request):
    staff_required(request)
    # ponytail: conta status=OPEN (novos, sem triagem). "Última msg do aluno" = upgrade futuro.
    return {'count': Ticket.objects.filter(status=Ticket.Status.OPEN).count()}


@router.get('/admin/{ticket_id}/requester', response={200: RequesterOut, 404: Error})
def admin_ticket_requester(request, ticket_id: int):
    """Ficha completa do aluno do chamado: perfil, matrículas com progresso e outros chamados."""
    staff_required(request)
    ticket = get_object_or_404(Ticket.objects.select_related('user'), id=ticket_id)
    user = ticket.user

    # ponytail: 2 counts por matrícula; ok com poucos cursos por aluno.
    enrollments = []
    for e in CourseEnrollment.objects.filter(user=user).select_related('course').order_by('-enrolled_at'):
        enrollments.append({
            'course_name': e.course.name,
            'is_active': e.is_active,
            'enrolled_at': e.enrolled_at,
            'expires_at': e.expires_at,
            'source': e.source,
            'total': Lesson.objects.filter(module__course=e.course_id, is_published=True).count(),
            'completed': LessonProgress.objects.filter(
                user=user,
                lesson__module__course=e.course_id,
                lesson__is_published=True,
                completed_at__isnull=False,
            ).count(),
        })

    last = LessonProgress.objects.filter(user=user).order_by('-last_watched_at').first()
    return Status(200, {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'phone': user.phone,
        'cpf': user.cpf,
        'avatar_url': user.avatar.url if user.avatar else None,
        'is_active': user.is_active,
        'created_at': user.created_at,
        'last_activity_at': last.last_watched_at if last else None,
        'enrollments': enrollments,
        'other_tickets': Ticket.objects.filter(user=user).exclude(id=ticket.id).order_by('-created_at'),
    })


@router.patch('/admin/{ticket_id}/status', response={200: TicketOut, 400: Error, 404: Error})
def admin_set_status(request, ticket_id: int, data: StatusIn):
    staff_required(request)
    if data.status not in Ticket.Status.values:
        return Status(400, Error(detail='Status inválido'))
    ticket = get_object_or_404(Ticket, id=ticket_id)
    # Staff pode reabrir um RESOLVED (vira o status pedido). Aluno segue sem reabrir: add_message barra.
    ticket.status = data.status
    ticket.save(update_fields=['status', 'updated_at'])
    return Status(200, ticket)
