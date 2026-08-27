from unittest import mock
from urllib.parse import unquote

from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.test import TestCase
from ninja_jwt.tokens import AccessToken, RefreshToken

from accounts.api import MAGIC_LINK_SALT
from accounts.tasks import send_password_changed_email
from courses.models import Course
from enrollments.models import CourseEnrollment

User = get_user_model()

MAGIC_LOGIN = '/api/auth/magic/login'
RESET_PASSWORD = '/api/auth/reset-password'


class MagicLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='aluno@test.com', password='x', name='Aluno')
        self.staff = User.objects.create_user(email='staff@test.com', password='x', name='Staff')
        self.staff.is_staff = True
        self.staff.save()

    def _post(self, token):
        return self.client.post(MAGIC_LOGIN, data={'token': token}, content_type='application/json')

    def _staff_headers(self):
        access = RefreshToken.for_user(self.staff).access_token
        return {'HTTP_AUTHORIZATION': f'Bearer {access}'}

    def test_generate_and_consume_roundtrip(self):
        # staff gera → extrai token do url → consome → JWT do usuário certo
        res = self.client.post(
            f'/api/auth/admin/users/{self.user.id}/login-link', **self._staff_headers()
        )
        self.assertEqual(res.status_code, 200)
        url = res.json()['url']
        # token vai URL-encodado na URL; browser/Vue decodam antes do consume
        token = unquote(url.split('token=', 1)[1])

        res = self._post(token)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn('access', body)
        self.assertEqual(AccessToken(body['access'])['user_id'], self.user.id)

    def test_generate_requires_staff(self):
        access = RefreshToken.for_user(self.user).access_token  # não-staff
        res = self.client.post(
            f'/api/auth/admin/users/{self.user.id}/login-link',
            HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(res.status_code, 403)

    def test_tampered_token_rejected(self):
        token = signing.dumps(self.user.pk, salt=MAGIC_LINK_SALT)
        res = self._post(token + 'x')
        self.assertEqual(res.status_code, 401)

    def test_wrong_salt_rejected(self):
        token = signing.dumps(self.user.pk, salt='outro-salt')
        res = self._post(token)
        self.assertEqual(res.status_code, 401)

    def test_expired_token_rejected(self):
        token = signing.dumps(self.user.pk, salt=MAGIC_LINK_SALT)
        with mock.patch('accounts.api.MAGIC_LINK_MAX_AGE', -1):
            res = self._post(token)
        self.assertEqual(res.status_code, 401)

    def test_inactive_user_rejected(self):
        token = signing.dumps(self.user.pk, salt=MAGIC_LINK_SALT)
        self.user.is_active = False
        self.user.save()
        res = self._post(token)
        self.assertEqual(res.status_code, 401)

    @mock.patch('accounts.api.async_task')
    def test_reset_pair_sets_password_without_the_old_one(self, _async):
        """Fluxo do magic link: o par uid/token que vem no login troca a senha sem
        pedir a antiga, e vira sucata assim que a senha muda (não dá pra reusar)."""
        token = signing.dumps(self.user.pk, salt=MAGIC_LINK_SALT)
        data = self._post(token).json()

        body = {
            'uid': data['reset_uid'],
            'token': data['reset_token'],
            'password': 'senhanova123',
            'repeat_password': 'senhanova123',
        }
        res = self.client.post(RESET_PASSWORD, data=body, content_type='application/json')
        self.assertEqual(res.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('senhanova123'))
        # aviso de "sua senha foi alterada" enfileirado
        _async.assert_called_with('accounts.tasks.send_password_changed_email', self.user.pk)

        # mesmo par não serve de novo: o hash da senha entra no hash do token
        res = self.client.post(RESET_PASSWORD, data=body, content_type='application/json')
        self.assertEqual(res.status_code, 400)


class BrandedEmailTests(TestCase):
    """O logo é recurso do HTML (cid:), nunca um arquivo anexado ao email.

    Django 6 monta anexo em multipart/mixed, e ali o cliente lista o logo.png junto
    dos anexos do usuário. A árvore certa põe a imagem dentro da parte HTML.
    """

    def test_logo_vai_inline_e_nao_como_anexo(self):
        user = User.objects.create_user(email='aluno@test.com', password='x', name='Aluno')
        send_password_changed_email(user.pk)

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()

        images = [p for p in msg.walk() if p.get_content_type() == 'image/png']
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['Content-ID'], '<brandlogo>')
        self.assertNotIn('attachment', str(images[0]['Content-Disposition']))

        # a imagem mora dentro de um multipart/related, ao lado do HTML que a referencia
        related = [p for p in msg.walk() if p.get_content_type() == 'multipart/related']
        self.assertEqual(len(related), 1)
        subtipos = {p.get_content_type() for p in related[0].get_payload()}
        self.assertEqual(subtipos, {'text/html', 'image/png'})

        html = next(p for p in msg.walk() if p.get_content_type() == 'text/html')
        self.assertIn('cid:brandlogo', html.get_content())


class DeleteUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='aluno@test.com', password='x', name='Aluno')
        self.staff = User.objects.create_user(email='staff@test.com', password='x', name='Staff')
        self.staff.is_staff = True
        self.staff.save()
        self.course = Course.objects.create(name='Curso', category='sales')
        CourseEnrollment.objects.create(user=self.user, course=self.course)

    def _staff_headers(self):
        access = RefreshToken.for_user(self.staff).access_token
        return {'HTTP_AUTHORIZATION': f'Bearer {access}'}

    def _delete(self, user_id, headers):
        return self.client.delete(f'/api/auth/admin/users/{user_id}', **headers)

    def test_staff_delete_cascades_enrollments(self):
        res = self._delete(self.user.id, self._staff_headers())
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(id=self.user.id).exists())
        # cascade: matrícula some junto
        self.assertFalse(CourseEnrollment.objects.filter(user_id=self.user.id).exists())

    def test_non_staff_forbidden(self):
        access = RefreshToken.for_user(self.user).access_token
        res = self._delete(self.staff.id, {'HTTP_AUTHORIZATION': f'Bearer {access}'})
        self.assertEqual(res.status_code, 403)
        self.assertTrue(User.objects.filter(id=self.staff.id).exists())

    def test_cannot_delete_self(self):
        res = self._delete(self.staff.id, self._staff_headers())
        self.assertEqual(res.status_code, 400)
        self.assertTrue(User.objects.filter(id=self.staff.id).exists())

    def test_missing_user_404(self):
        res = self._delete(999999, self._staff_headers())
        self.assertEqual(res.status_code, 404)
