from urllib.parse import parse_qs, urlparse
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

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

    def test_login_with_duplicate_emails_authenticates_the_matching_password(self):
        matching_user = User.objects.create_user(
            username='alice-duplicate',
            email='alice@example.com',
            password='AnotherPassword123!',
            role=User.Role.STUDENT,
        )

        response = self.client.post(
            reverse('login'),
            {'username': 'alice@example.com', 'password': 'AnotherPassword123!'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        token = RefreshToken(response.json()['refresh'])
        self.assertEqual(str(token['user_id']), str(matching_user.pk))

    def test_login_with_duplicate_emails_and_ambiguous_password_fails_cleanly(self):
        User.objects.create_user(
            username='alice-duplicate',
            email='alice@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )

        response = self.client.post(
            reverse('login'),
            {'username': 'alice@example.com', 'password': 'Password123!'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401, response.content)
        self.assertEqual(response.json(), {'detail': 'No active account found with the given credentials'})

    @override_settings(FRONTEND_BASE_URL='https://school.example')
    def test_password_reset_request_emails_a_single_use_frontend_link(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': self.user.email},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(mail.outbox), 1)
        reset_url = next(
            part for part in mail.outbox[0].body.split()
            if part.startswith('https://school.example/reset-password?')
        )
        query = parse_qs(urlparse(reset_url).query)
        self.assertEqual(query['provider'], ['django'])
        self.assertEqual(query['uid'], [urlsafe_base64_encode(force_bytes(self.user.pk))])
        self.assertTrue(default_token_generator.check_token(self.user, query['token'][0]))

    def test_password_reset_request_does_not_disclose_unknown_or_unusable_accounts(self):
        unknown = self.client.post(
            reverse('password_reset'),
            {'email': 'unknown@example.com'},
            content_type='application/json',
        )
        self.user.set_unusable_password()
        self.user.save(update_fields=['password'])
        unusable = self.client.post(
            reverse('password_reset'),
            {'email': self.user.email},
            content_type='application/json',
        )

        expected = {'detail': 'If an eligible account exists for that email, a password reset email will be sent.'}
        self.assertEqual(unknown.status_code, 200, unknown.content)
        self.assertEqual(unusable.status_code, 200, unusable.content)
        self.assertEqual(unknown.json(), expected)
        self.assertEqual(unusable.json(), expected)
        self.assertEqual(mail.outbox, [])

    def test_password_reset_confirm_updates_password_and_invalidates_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        response = self.client.post(
            reverse('password_reset_confirm'),
            {'uid': uid, 'token': token, 'new_password': 'A-new-unique-password-482!'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('A-new-unique-password-482!'))
        self.assertFalse(default_token_generator.check_token(self.user, token))

    def test_password_reset_confirm_rejects_invalid_tokens_and_weak_passwords(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        invalid_token = self.client.post(
            reverse('password_reset_confirm'),
            {'uid': uid, 'token': 'invalid-token', 'new_password': 'A-new-unique-password-482!'},
            content_type='application/json',
        )
        weak_password = self.client.post(
            reverse('password_reset_confirm'),
            {
                'uid': uid,
                'token': default_token_generator.make_token(self.user),
                'new_password': 'password',
            },
            content_type='application/json',
        )

        self.assertEqual(invalid_token.status_code, 400, invalid_token.content)
        self.assertEqual(weak_password.status_code, 400, weak_password.content)
        self.assertTrue(self.user.check_password('Password123!'))

    @patch('accounts.views.send_mail', return_value=0)
    def test_password_reset_email_delivery_failure_is_reported(self, send_mail):
        response = self.client.post(
            reverse('password_reset'),
            {'email': self.user.email},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 503, response.content)
        send_mail.assert_called_once()

    def test_login_refresh_token_renews_access_for_same_user(self):
        login_response = self.client.post(
            reverse('login'),
            {'username': 'alice@example.com', 'password': 'Password123!'},
            content_type='application/json',
        )
        refresh_response = self.client.post(
            reverse('login_refresh'),
            {'refresh': login_response.json()['refresh']},
            content_type='application/json',
        )

        self.assertEqual(refresh_response.status_code, 200, refresh_response.content)
        profile_response = self.client.get(
            reverse('me'),
            HTTP_AUTHORIZATION=f"Bearer {refresh_response.json()['access']}",
        )

        self.assertEqual(profile_response.status_code, 200, profile_response.content)
        self.assertEqual(profile_response.json()['id'], self.user.id)
        self.assertEqual(profile_response.json()['role'], User.Role.STUDENT)
        self.assertFalse(profile_response.json()['is_super_admin'])

    def test_superuser_profile_exposes_administrator_access_flag(self):
        admin = User.objects.create_superuser(
            username='root-support-admin',
            email='root-support-admin@example.com',
            password='Password123!',
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('me'))

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['role'], User.Role.STUDENT)
        self.assertTrue(response.json()['is_super_admin'])

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
            reverse('me'),
            {'role': User.Role.SUPER_ADMIN, 'is_super_admin': True},
            content_type='application/json',
        )

        self.assertEqual(instructor_response.status_code, 200)
        self.assertEqual(admin_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.STUDENT)
        self.assertFalse(self.user.is_super_admin)

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
