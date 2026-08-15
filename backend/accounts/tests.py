from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


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
