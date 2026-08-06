import json
import urllib.error
import urllib.request
from datetime import datetime

from django.conf import settings
from django.db.models import F
from django.utils import timezone
from django_q.tasks import async_task

from enrollments.models import LessonProgress

from .models import QuizAttempt


def _quiz_webhook_payload(lesson, user, result, answers, *, timed_out=False, attempt=0) -> dict:
    """Monta o corpo do webhook a partir da correção. Roda no request (precisa do banco:
    curso, enunciados); o POST em si vai pra fila. `result` é um QuizResultOut."""
    by_key = {q['key']: q for q in (lesson.questions or [])}
    items = []
    for r in result.results:
        q = by_key.get(r.key, {})
        item = {'key': r.key, 'prompt': q.get('prompt', ''), 'type': r.type}
        if r.type == 'text':
            item['answer_text'] = r.answer_text
        else:
            item['chosen'] = r.chosen
            item['correct'] = r.correct
            item['is_correct'] = r.chosen == r.correct
        items.append(item)

    return {
        'event': 'quiz_timed_out' if timed_out else 'quiz_completed',
        'course_id': lesson.module.course_id,
        'course_name': lesson.module.course.name,
        'lesson_id': lesson.id,
        'lesson_name': lesson.name,
        'user': {'id': user.id, 'name': user.name, 'email': user.email, 'phone': user.phone},
        'score': result.score,
        'total': result.total,
        'timed_out': timed_out,
        'attempt': attempt,
        'submitted_at': timezone.now().isoformat(),
        'answers': items,
    }


def _apply_timeout(lesson, user, attempt, answers=None):
    """Finaliza uma tentativa vencida como FALHA (timeout). Atômico e idempotente: só a
    1ª via que "fechar" a tentativa (task ONCE, GET preguiçoso ou submit no limite)
    grava e dispara o webhook — as demais viram no-op pela guarda `submitted_at__isnull`.
    ponytail: corrida no exato limite é limitada pela GRACE do submit; empate resolve aqui."""
    from .api import _quiz_result  # lazy: evita ciclo tasks<->api

    now = timezone.now()
    answers = answers if answers is not None else (attempt.answers or {})
    graded = _quiz_result(lesson.questions or [], answers)
    graded.score = 0  # timeout = falha, ignora acertos parciais

    won = QuizAttempt.objects.filter(pk=attempt.pk, submitted_at__isnull=True).update(
        answers=answers,
        score=0,
        total=graded.total,
        timed_out=True,
        submitted_at=now,
        started_at=None,
        attempts=F('attempts') + 1,
    )
    if not won:
        return None  # outra via já finalizou esta tentativa

    attempt.refresh_from_db(fields=['attempts'])
    # "conclui mesmo com falha": timeout ainda marca a aula como concluída.
    LessonProgress.objects.update_or_create(user=user, lesson=lesson, defaults={'completed_at': now})

    if lesson.module.course.quiz_webhook_url:
        async_task(
            'courses.tasks.fire_quiz_webhook',
            lesson.module.course.quiz_webhook_url,
            _quiz_webhook_payload(lesson, user, graded, answers, timed_out=True, attempt=attempt.attempts),
            settings.QUIZ_WEBHOOK_SECRET,
        )
    return graded


def finalize_quiz_timeout(lesson_id, user_id, started_at_iso) -> None:
    """django-q ONCE agendada no vencimento. Marca falha por timeout se a tentativa
    ainda estiver aberta e for a mesma (mesmo `started_at`). Senão no-op — cobre o caso
    "aluno fechou a aba e não voltou". A agenda ONCE se auto-remove após rodar."""
    attempt = (
        QuizAttempt.objects.select_related('user', 'lesson__module__course')
        .filter(lesson_id=lesson_id, user_id=user_id)
        .first()
    )
    if not attempt or attempt.submitted_at or not attempt.started_at:
        return
    started = datetime.fromisoformat(started_at_iso)
    if abs((attempt.started_at - started).total_seconds()) > 1:
        return  # uma tentativa mais nova começou → esta agenda ficou obsoleta
    _apply_timeout(attempt.lesson, attempt.user, attempt)


def fire_quiz_webhook(url: str, payload: dict, secret: str = '') -> None:
    """Tarefa django-q: POST do payload. Levanta em erro → django-q loga/retenta."""
    body = json.dumps(payload).encode()
    headers = {'Content-Type': 'application/json'}
    if secret:
        headers['X-Webhook-Token'] = secret
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    urllib.request.urlopen(req, timeout=10)  # noqa: S310 (URL é config staff)
    # Check do builder: courses.tests.QuizWebhookPayloadTests (roda com o Django configurado).


def _sample_quiz_payload() -> dict:
    """Payload fictício com o MESMO formato de _quiz_webhook_payload, p/ o botão de teste.
    ponytail: dict estático — manter em sincronia manual com _quiz_webhook_payload se o
    shape mudar. Check em courses.tests garante que não diverge nas chaves de topo."""
    return {
        'event': 'quiz_completed',
        'test': True,
        'course_id': 0,
        'course_name': 'Curso de Teste',
        'lesson_id': 0,
        'lesson_name': 'Exercício de Teste',
        'user': {'id': 0, 'name': 'Aluno Teste', 'email': 'teste@exemplo.com', 'phone': '11999999999'},
        'score': 2,
        'total': 3,
        'timed_out': False,
        'attempt': 1,
        'submitted_at': timezone.now().isoformat(),
        'answers': [
            {'key': 'q1', 'prompt': 'Pergunta 1', 'type': 'choice', 'chosen': 0, 'correct': 0, 'is_correct': True},
            {'key': 'q2', 'prompt': 'Pergunta 2', 'type': 'text', 'answer_text': 'resposta livre'},
        ],
    }


def check_quiz_webhook(url: str) -> dict:
    """Dispara o payload de teste sincronamente e reporta. Reusa fire_quiz_webhook.
    ponytail: síncrono (bloqueia o worker até timeout=10s) — é um clique manual, ok."""
    try:
        fire_quiz_webhook(url, _sample_quiz_payload(), settings.QUIZ_WEBHOOK_SECRET)
    except urllib.error.HTTPError as e:
        return {'ok': False, 'status': e.code, 'detail': f'Servidor respondeu HTTP {e.code}'}
    except Exception as e:  # noqa: BLE001
        return {'ok': False, 'status': 0, 'detail': f'Não alcançável: {type(e).__name__}'}
    return {'ok': True, 'status': 200, 'detail': 'Webhook enviado com sucesso'}
