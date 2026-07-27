from unittest import mock

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase
from ninja_jwt.tokens import AccessToken, RefreshToken

from accounts.api import MAGIC_LINK_SALT

User = get_user_model()

MAGIC_LOGIN = '/api/auth/magic/login'


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
        token = url.split('token=', 1)[1]

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
