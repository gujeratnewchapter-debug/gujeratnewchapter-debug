from django.contrib.auth import get_user_model
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.exceptions import AuthenticationFailed

from .authentication import SupabaseJWTAuthentication

User = get_user_model()


class SupabaseJWTVerificationTests(SimpleTestCase):
    def test_authentication_challenge_uses_bearer_scheme(self):
        self.assertEqual(SupabaseJWTAuthentication().authenticate_header(None), 'Bearer')

    @override_settings(
        SUPABASE_JWT_SECRET='legacy-secret',
        SUPABASE_JWKS_URL='https://example.supabase.co/auth/v1/jwks',
    )
    @patch('accounts.authentication.jwt.PyJWKClient')
    @patch('accounts.authentication.jwt.get_unverified_header', return_value={'alg': 'ES256'})
    @patch('accounts.authentication.jwt.decode')
    def test_asymmetric_token_uses_jwks_even_if_legacy_secret_is_configured(
        self, decode, get_header, jwks_client,
    ):
        signing_key = jwks_client.return_value.get_signing_key_from_jwt.return_value
        signing_key.key = object()
        decode.return_value = {'sub': 'supabase-user', 'aud': 'authenticated'}

        payload = SupabaseJWTAuthentication()._decode_token('header.payload.signature')

        self.assertEqual(payload['sub'], 'supabase-user')
        jwks_client.assert_called_once_with(
            'https://example.supabase.co/auth/v1/.well-known/jwks.json'
        )
        decode.assert_called_once_with(
            'header.payload.signature',
            signing_key.key,
            algorithms=['ES256'],
            audience='authenticated',
            options={'verify_aud': True},
        )

    @override_settings(SUPABASE_JWT_SECRET='legacy-secret', SUPABASE_JWKS_URL='')
    @patch('accounts.authentication.jwt.get_unverified_header', return_value={'alg': 'HS256'})
    @patch('accounts.authentication.jwt.decode', return_value={'sub': 'supabase-user'})
    def test_legacy_hs256_token_uses_configured_secret(self, decode, get_header):
        payload = SupabaseJWTAuthentication()._decode_token('header.payload.signature')

        self.assertEqual(payload['sub'], 'supabase-user')
        decode.assert_called_once_with(
            'header.payload.signature',
            'legacy-secret',
            algorithms=['HS256'],
            audience='authenticated',
            options={'verify_aud': True},
        )

    @patch('accounts.authentication.jwt.get_unverified_header', return_value={'alg': 'none'})
    def test_rejects_unsupported_token_signing_algorithm(self, get_header):
        with self.assertRaisesMessage(AuthenticationFailed, 'unsupported signing algorithm'):
            SupabaseJWTAuthentication()._decode_token('header.payload.signature')


class LoginEmailRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='Password123!',
            first_name='Alice',
            last_name='Test',
            role=User.Role.STUDENT,
        )

    def test_login_accepts_email_and_returns_tokens(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'alice@example.com', 'password': 'Password123!'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertIn('access', payload)
        self.assertIn('refresh', payload)

    def test_session_sync_requires_bearer_authentication(self):
        response = self.client.get(reverse('session_sync'))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get('WWW-Authenticate'), 'Bearer')

    def test_register_accepts_full_name_and_splits_names(self):
        response = self.client.post(
            reverse('register'),
            {
                'email': 'new.user@example.com',
                'password': 'Password123!',
                'full_name': 'New User',
                'role': User.Role.STUDENT,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(email='new.user@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.username, 'new.user')

    def test_register_ignores_client_supplied_elevated_role(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'new.instructor',
                'email': 'new.instructor@example.com',
                'password': 'Password123!',
                'role': User.Role.INSTRUCTOR,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(username='new.instructor')
        self.assertEqual(user.role, User.Role.STUDENT)

    def test_student_cannot_change_role_to_instructor_or_admin(self):
        self.client.force_login(self.user)
        instructor_response = self.client.patch(
            reverse('me'), {'role': User.Role.INSTRUCTOR}, content_type='application/json',
        )
        admin_response = self.client.patch(
            reverse('me'), {'role': User.Role.SUPER_ADMIN}, content_type='application/json',
        )

        self.assertEqual(instructor_response.status_code, 200)
        self.assertEqual(admin_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.STUDENT)

    def test_instructor_cannot_change_role_to_admin(self):
        instructor = User.objects.create_user(
            username='instructor', email='instructor@example.com', password='Password123!', role=User.Role.INSTRUCTOR,
        )
        self.client.force_login(instructor)

        response = self.client.patch(
            reverse('me'), {'role': User.Role.SUPER_ADMIN}, content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        instructor.refresh_from_db()
        self.assertEqual(instructor.role, User.Role.INSTRUCTOR)

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_ignores_client_role(self, verify_token):
        verify_token.return_value = {
            'email': 'google-student@example.com',
            'given_name': 'Google',
            'family_name': 'Student',
        }

        response = self.client.post(
            reverse('login_google'),
            {'id_token': 'valid-token', 'role': User.Role.SUPER_ADMIN},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get(email='google-student@example.com').role, User.Role.STUDENT)
