import json
import urllib.request

from django.utils import timezone


def _quiz_webhook_payload(lesson, user, result, answers) -> dict:
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
        'event': 'quiz_completed',
        'course_id': lesson.module.course_id,
        'course_name': lesson.module.course.name,
        'lesson_id': lesson.id,
        'lesson_name': lesson.name,
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
        'score': result.score,
        'total': result.total,
        'submitted_at': timezone.now().isoformat(),
        'answers': items,
    }


def fire_quiz_webhook(url: str, payload: dict, secret: str = '') -> None:
    """Tarefa django-q: POST do payload. Levanta em erro → django-q loga/retenta."""
    body = json.dumps(payload).encode()
    headers = {'Content-Type': 'application/json'}
    if secret:
        headers['X-Webhook-Token'] = secret
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    urllib.request.urlopen(req, timeout=10)  # noqa: S310 (URL é config staff)
    # Check do builder: courses.tests.QuizWebhookPayloadTests (roda com o Django configurado).
