import hashlib
import jwt
from datetime import timedelta
import uuid

from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import SupportCallRequest


User = get_user_model()


class SupportCallAdminSiteTests(TestCase):
    def test_support_requests_are_visible_in_django_admin_with_portal_queue_link(self):
        admin = User.objects.create_superuser(
            username='support-admin-site',
            email='support-admin-site@example.com',
            password='Password123!',
        )
        call = SupportCallRequest.objects.create(
            display_name='Waiting Caller',
            email='waiting@example.com',
            mode=SupportCallRequest.Mode.VIDEO,
            capability_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            room_name=f'support-admin-{uuid.uuid4().hex}',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('admin:support_calls_supportcallrequest_changelist'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, call.display_name)
        self.assertContains(response, 'Open support queue')
        self.assertContains(response, '/static/support_calls/admin_support_calls.js')
        support_admin = django_admin.site._registry[SupportCallRequest]
        self.assertNotIn('display_name', support_admin.readonly_fields)
        self.assertNotIn('email', support_admin.readonly_fields)
        self.assertTrue(support_admin.has_delete_permission(response.wsgi_request, call))
        delete_response = self.client.post(
            reverse('admin:support_calls_supportcallrequest_delete', args=(call.id,)),
            {'post': 'yes'},
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(SupportCallRequest.objects.filter(pk=call.id).exists())

    @override_settings(
        LIVEKIT_URL='wss://live.example.com',
        LIVEKIT_API_KEY='test-livekit-key',
        LIVEKIT_API_SECRET='test-livekit-secret',
    )
    def test_django_admin_session_can_monitor_accept_and_create_a_private_join_ticket(self):
        admin = User.objects.create_superuser(
            username='support-admin-alerts',
            email='support-admin-alerts@example.com',
            password='Password123!',
        )
        call = SupportCallRequest.objects.create(
            display_name='Caller From Admin Session',
            email='caller@example.com',
            mode=SupportCallRequest.Mode.VIDEO,
            capability_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            room_name=f'support-admin-session-{uuid.uuid4().hex}',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.client.force_login(admin)

        queue = self.client.get(reverse('support-call-admin-queue'))
        accept = self.client.post(
            reverse('support-call-admin-action', args=(call.id, 'accept')),
            data='{}',
            content_type='application/json',
        )

        self.assertEqual(queue.status_code, 200)
        self.assertEqual(accept.status_code, 200)
        self.assertEqual(accept.data['status'], SupportCallRequest.Status.ACCEPTED)

        ticket = self.client.post(
            reverse('support-call-admin-session-ticket', args=(call.id,)),
            data='{}',
            content_type='application/json',
        )
        session_status = self.client.post(
            reverse('support-call-admin-session-status', args=(call.id,)),
            {'capability': ticket.data['capability']},
            content_type='application/json',
        )
        session_token = self.client.post(
            reverse('support-call-admin-session-token', args=(call.id,)),
            {'capability': ticket.data['capability']},
            content_type='application/json',
        )
        self.assertEqual(ticket.status_code, 200)
        call.refresh_from_db()
        self.assertEqual(call.admin_session_hash, hashlib.sha256(ticket.data['capability'].encode()).hexdigest())
        self.assertEqual(session_status.status_code, 200)
        self.assertEqual(session_status.data['status'], SupportCallRequest.Status.ACCEPTED)
        self.assertEqual(session_token.status_code, 200)


@override_settings(REST_FRAMEWORK={
    'DEFAULT_THROTTLE_RATES': {
        'support_call_create': '100/hour',
        'support_call_status': '100/hour',
        'support_call_token': '100/hour',
        'support_call_admin_token': '100/hour',
    },
})
class SupportCallApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(
            username='support-admin',
            email='support-admin@example.com',
            password='Password123!',
            role=User.Role.SUPER_ADMIN,
        )
        self.student = User.objects.create_user(
            username='support-student',
            email='student@example.com',
            first_name='Student',
            last_name='Caller',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.visitor_payload = {
            'display_name': 'Visitor Caller',
            'email': 'visitor@example.com',
            'question': 'I need help with enrollment.',
            'mode': 'video',
        }

    def create_request(self, **overrides):
        payload = {**self.visitor_payload, **overrides}
        response = self.client.post(reverse('support-call-request'), payload, format='json')
        return response

    def create_model_request(self, status=SupportCallRequest.Status.PENDING):
        return SupportCallRequest.objects.create(
            display_name='Caller',
            email='caller@example.com',
            mode=SupportCallRequest.Mode.AUDIO,
            status=status,
            capability_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            room_name=f'support-test-{uuid.uuid4().hex}',
            expires_at=timezone.now() + timedelta(minutes=10),
            accepted_at=timezone.now() if status == SupportCallRequest.Status.ACCEPTED else None,
        )

    def capability_payload(self, call_id, capability='known-test-capability'):
        return {'call_id': str(call_id), 'capability': capability}

    def test_public_request_only_returns_capability_to_caller_and_stores_hash(self):
        response = self.create_request(room_name='untrusted-room', identity='untrusted-identity')

        self.assertEqual(response.status_code, 201)
        call = SupportCallRequest.objects.get(pk=response.data['call_id'])
        self.assertEqual(call.capability_hash, hashlib.sha256(response.data['capability'].encode()).hexdigest())
        self.assertNotEqual(call.capability_hash, response.data['capability'])
        self.assertTrue(call.room_name.startswith('support-'))
        self.assertNotEqual(call.room_name, 'untrusted-room')
        self.assertNotIn('email', response.data)
        self.assertNotIn('room_name', response.data)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertNotIn('capability', str(call))

    def test_public_request_validates_fields_and_mode(self):
        response = self.create_request(mode='screen-share', email='not-an-email')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(SupportCallRequest.objects.count(), 0)

    def test_public_create_endpoint_is_rate_limited(self):
        cache.clear()

        responses = [self.create_request() for _ in range(11)]

        self.assertTrue(all(response.status_code == 201 for response in responses[:10]))
        self.assertEqual(responses[10].status_code, 429)

    def test_authenticated_student_email_comes_from_account(self):
        self.client.force_authenticate(self.student)

        response = self.create_request(email='someone-else@example.com')

        self.assertEqual(response.status_code, 201)
        call = SupportCallRequest.objects.get(pk=response.data['call_id'])
        self.assertEqual(call.email, self.student.email)
        self.assertEqual(call.display_name, 'Student Caller')
        self.assertEqual(call.requester, self.student)

    def test_non_student_cannot_use_public_request_endpoint_while_signed_in(self):
        instructor = User.objects.create_user(
            username='support-instructor',
            email='instructor@example.com',
            password='Password123!',
            role=User.Role.INSTRUCTOR,
        )
        self.client.force_authenticate(instructor)

        response = self.create_request()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(SupportCallRequest.objects.count(), 0)

    def test_super_admin_with_student_role_cannot_use_public_request_endpoint(self):
        admin = User.objects.create_user(
            username='support-role-admin',
            email='role-admin@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
            is_superuser=True,
        )
        self.client.force_authenticate(admin)

        response = self.create_request()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(SupportCallRequest.objects.count(), 0)

    def test_caller_status_requires_capability_and_does_not_expose_email(self):
        response = self.create_request()
        call = SupportCallRequest.objects.get(pk=response.data['call_id'])
        body = self.capability_payload(call.id, response.data['capability'])

        status_response = self.client.post(reverse('support-call-status'), body, format='json')
        denied_response = self.client.post(
            reverse('support-call-status'),
            self.capability_payload(call.id, 'x' * 40),
            format='json',
        )

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data['status'], SupportCallRequest.Status.PENDING)
        self.assertNotIn('email', status_response.data)
        self.assertEqual(denied_response.status_code, 404)

    def test_public_status_endpoint_is_rate_limited(self):
        response = self.create_request()
        payload = self.capability_payload(response.data['call_id'], response.data['capability'])

        statuses = [
            self.client.post(reverse('support-call-status'), payload, format='json').status_code
            for _ in range(13)
        ]

        self.assertTrue(all(result == 200 for result in statuses[:12]))
        self.assertEqual(statuses[12], 429)

    def test_caller_cannot_get_token_before_acceptance(self):
        response = self.create_request()

        token_response = self.client.post(
            reverse('support-call-token'),
            self.capability_payload(response.data['call_id'], response.data['capability']),
            format='json',
        )

        self.assertEqual(token_response.status_code, 409)
        self.assertNotIn('token', token_response.data)

    @override_settings(
        LIVEKIT_URL='wss://live.example.com',
        LIVEKIT_API_KEY='test-livekit-key',
        LIVEKIT_API_SECRET='test-livekit-secret',
    )
    def test_public_token_endpoint_is_rate_limited(self):
        response = self.create_request()
        call = SupportCallRequest.objects.get(pk=response.data['call_id'])
        call.status = SupportCallRequest.Status.ACCEPTED
        call.accepted_at = timezone.now()
        call.save(update_fields=('status', 'accepted_at'))
        payload = self.capability_payload(call.id, response.data['capability'])

        statuses = [
            self.client.post(reverse('support-call-token'), payload, format='json').status_code
            for _ in range(6)
        ]

        self.assertTrue(all(result == 200 for result in statuses[:5]))
        self.assertEqual(statuses[5], 429)

    def test_only_super_admin_can_list_or_accept_requests(self):
        call = self.create_model_request()
        queue_url = reverse('support-call-admin-queue')
        action_url = reverse('support-call-admin-action', args=(call.id, 'accept'))
        self.client.force_authenticate(self.student)

        list_response = self.client.get(queue_url)
        accept_response = self.client.post(action_url, {}, format='json')

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(accept_response.status_code, 403)
        call.refresh_from_db()
        self.assertEqual(call.status, SupportCallRequest.Status.PENDING)

    @override_settings(
        LIVEKIT_URL='wss://live.example.com',
        LIVEKIT_API_KEY='test-livekit-key',
        LIVEKIT_API_SECRET='test-livekit-secret',
    )
    def test_admin_accepts_and_gets_a_short_lived_token_without_exposing_email_in_queue(self):
        call = self.create_model_request()
        self.client.force_authenticate(self.admin)

        queue_response = self.client.get(reverse('support-call-admin-queue'))
        accept_response = self.client.post(
            reverse('support-call-admin-action', args=(call.id, 'accept')),
            {},
            format='json',
        )
        token_response = self.client.post(reverse('support-call-admin-token', args=(call.id,)), {}, format='json')

        self.assertEqual(queue_response.status_code, 200)
        self.assertEqual(queue_response.data[0]['email'], call.email)
        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(token_response.status_code, 200)
        token_claims = jwt.decode(
            token_response.data['token'],
            'test-livekit-secret',
            algorithms=['HS256'],
            options={'verify_iat': False, 'verify_exp': False},
        )
        self.assertEqual(token_claims['sub'], f'support-admin-{self.admin.pk}')
        self.assertEqual(token_claims['video']['room'], call.room_name)
        self.assertTrue(token_claims['video']['roomAdmin'])
        self.assertEqual(token_claims['video']['canPublishSources'], ['microphone'])
        self.assertFalse(token_claims['video']['canPublishData'])
        self.assertNotIn('canUpdateOwnMetadata', token_claims['video'])
        self.assertLessEqual(token_claims['exp'] - token_claims['iat'], 30 * 60)

    @override_settings(
        LIVEKIT_URL='wss://live.example.com',
        LIVEKIT_API_KEY='test-livekit-key',
        LIVEKIT_API_SECRET='test-livekit-secret',
    )
    def test_admin_can_call_a_student_and_only_that_student_can_answer(self):
        self.client.force_authenticate(self.admin)
        create_response = self.client.post(
            reverse('support-call-admin-outbound'),
            {'student_id': self.student.pk, 'mode': 'video'},
            format='json',
        )

        self.assertEqual(create_response.status_code, 201)
        call = SupportCallRequest.objects.get(pk=create_response.data['call_id'])
        self.assertEqual(call.direction, SupportCallRequest.Direction.ADMIN_TO_STUDENT)
        self.assertEqual(call.recipient, self.student)
        self.assertEqual(create_response.data['status'], SupportCallRequest.Status.PENDING)

        admin_ticket = self.client.post(
            reverse('support-call-admin-session-ticket', args=(call.id,)),
            data='{}',
            content_type='application/json',
        )
        self.assertEqual(admin_ticket.status_code, 200)

        self.client.force_authenticate(self.student)
        student_queue = self.client.get(reverse('support-call-student-queue'))
        self.assertEqual(student_queue.status_code, 200)
        self.assertEqual(student_queue.data[0]['call_id'], str(call.id))
        self.assertEqual(student_queue.data[0]['display_name'], 'support-admin')

        accepted = self.client.post(reverse('support-call-student-action', args=(call.id, 'accept')))
        student_token = self.client.post(reverse('support-call-student-token', args=(call.id,)))
        admin_token = self.client.post(
            reverse('support-call-admin-session-token', args=(call.id,)),
            {'capability': admin_ticket.data['capability']},
            format='json',
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data['status'], SupportCallRequest.Status.ACCEPTED)
        self.assertEqual(student_token.status_code, 200)
        self.assertEqual(admin_token.status_code, 200)
        claims = jwt.decode(
            student_token.data['token'],
            'test-livekit-secret',
            algorithms=['HS256'],
            options={'verify_iat': False, 'verify_exp': False},
        )
        self.assertEqual(claims['sub'], f'support-student-{self.student.pk}')
        self.assertEqual(claims['video']['room'], call.room_name)
        admin_claims = jwt.decode(
            admin_token.data['token'],
            'test-livekit-secret',
            algorithms=['HS256'],
            options={'verify_iat': False, 'verify_exp': False},
        )
        self.assertIn('camera', admin_claims['video']['canPublishSources'])

        other_student = User.objects.create_user(
            username='other-support-student',
            email='other-student@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(other_student)
        forbidden = self.client.post(reverse('support-call-student-action', args=(call.id, 'accept')))
        self.assertEqual(forbidden.status_code, 404)

    def test_admin_outbound_call_validates_student_and_mode(self):
        self.client.force_authenticate(self.admin)

        invalid_student = self.client.post(
            reverse('support-call-admin-outbound'),
            {'student_id': 'not-an-id', 'mode': 'video'},
            format='json',
        )
        invalid_mode = self.client.post(
            reverse('support-call-admin-outbound'),
            {'student_id': self.student.pk, 'mode': 'screen-share'},
            format='json',
        )

        self.assertEqual(invalid_student.status_code, 400)
        self.assertEqual(invalid_mode.status_code, 400)
        self.assertEqual(SupportCallRequest.objects.count(), 0)

    def test_only_the_target_student_can_view_or_answer_an_admin_call(self):
        call = self.create_model_request()
        call.direction = SupportCallRequest.Direction.ADMIN_TO_STUDENT
        call.recipient = self.student
        call.handled_by = self.admin
        call.save(update_fields=('direction', 'recipient', 'handled_by'))
        self.client.force_authenticate(self.admin)

        admin_cannot_answer_as_student = self.client.post(
            reverse('support-call-student-action', args=(call.id, 'accept')),
        )

        self.assertEqual(admin_cannot_answer_as_student.status_code, 403)
        call.refresh_from_db()
        self.assertEqual(call.status, SupportCallRequest.Status.PENDING)

    @override_settings(
        LIVEKIT_URL='wss://live.example.com',
        LIVEKIT_API_KEY='test-livekit-key',
        LIVEKIT_API_SECRET='test-livekit-secret',
    )
    def test_caller_token_is_issued_only_after_acceptance_with_server_generated_identity(self):
        response = self.create_request()
        call = SupportCallRequest.objects.get(pk=response.data['call_id'])
        call.status = SupportCallRequest.Status.ACCEPTED
        call.accepted_at = timezone.now()
        call.save(update_fields=('status', 'accepted_at'))

        token_response = self.client.post(
            reverse('support-call-token'),
            self.capability_payload(call.id, response.data['capability']),
            format='json',
        )

        self.assertEqual(token_response.status_code, 200)
        token_claims = jwt.decode(
            token_response.data['token'],
            'test-livekit-secret',
            algorithms=['HS256'],
            options={'verify_iat': False, 'verify_exp': False},
        )
        self.assertEqual(token_claims['sub'], f'support-caller-{call.pk.hex}')
        self.assertEqual(token_claims['video']['room'], call.room_name)
        self.assertNotIn('roomAdmin', token_claims['video'])
        self.assertEqual(token_claims['video']['canPublishSources'], ['microphone', 'camera'])
        self.assertFalse(token_claims['video']['canPublishData'])
        self.assertEqual(token_claims['name'], token_claims['sub'])
        self.assertNotIn('email', token_response.data)

    @override_settings(
        LIVEKIT_URL='wss://live.example.com',
        LIVEKIT_API_KEY='test-livekit-key',
        LIVEKIT_API_SECRET='test-livekit-secret',
    )
    def test_audio_caller_token_cannot_publish_video(self):
        response = self.create_request(mode='audio')
        call = SupportCallRequest.objects.get(pk=response.data['call_id'])
        call.status = SupportCallRequest.Status.ACCEPTED
        call.accepted_at = timezone.now()
        call.save(update_fields=('status', 'accepted_at'))

        token_response = self.client.post(
            reverse('support-call-token'),
            self.capability_payload(call.id, response.data['capability']),
            format='json',
        )

        self.assertEqual(token_response.status_code, 200)
        token_claims = jwt.decode(
            token_response.data['token'],
            'test-livekit-secret',
            algorithms=['HS256'],
            options={'verify_iat': False, 'verify_exp': False},
        )
        self.assertEqual(token_claims['video']['canPublishSources'], ['microphone'])

    @override_settings(LIVEKIT_URL='', LIVEKIT_API_KEY='', LIVEKIT_API_SECRET='')
    def test_admin_cannot_accept_when_livekit_is_not_configured(self):
        call = self.create_model_request()
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse('support-call-admin-action', args=(call.id, 'accept')),
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 503)
        call.refresh_from_db()
        self.assertEqual(call.status, SupportCallRequest.Status.PENDING)

    def test_reject_and_admin_end_change_call_status(self):
        pending = self.create_model_request()
        active = self.create_model_request(status=SupportCallRequest.Status.ACCEPTED)
        self.client.force_authenticate(self.admin)

        reject_response = self.client.post(
            reverse('support-call-admin-action', args=(pending.id, 'reject')),
            {},
            format='json',
        )
        end_response = self.client.post(
            reverse('support-call-admin-action', args=(active.id, 'end')),
            {},
            format='json',
        )
        self.client.force_authenticate(self.student)
        caller_end_response = self.client.post(
            reverse('support-call-admin-action', args=(active.id, 'end')),
            {},
            format='json',
        )

        self.assertEqual(reject_response.data['status'], SupportCallRequest.Status.REJECTED)
        self.assertEqual(end_response.data['status'], SupportCallRequest.Status.ENDED)
        self.assertEqual(caller_end_response.status_code, 403)

    def test_expired_pending_request_is_not_accepted(self):
        call = self.create_model_request()
        call.expires_at = timezone.now() - timedelta(seconds=1)
        call.save(update_fields=('expires_at',))
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            reverse('support-call-admin-action', args=(call.id, 'accept')),
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        call.refresh_from_db()
        self.assertEqual(call.status, SupportCallRequest.Status.EXPIRED)
