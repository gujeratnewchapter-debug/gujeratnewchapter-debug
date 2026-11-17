import json
import smtplib
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

import jwt
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core import mail
from django.db import DatabaseError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from courses.models import Course
from enrollments.models import Enrollment
from meetings.livekit import create_livekit_access_token
from meetings.admin import MeetingAdmin
from meetings.models import Meeting, MeetingInvitation, MeetingParticipant

User = get_user_model()


class LiveKitAccessTokenTests(TestCase):
    @override_settings(LIVEKIT_API_KEY='test-api-key', LIVEKIT_API_SECRET='test-api-secret')
    def test_generates_token_with_livekit_video_grants(self):
        token = create_livekit_access_token(
            'demo-room', 'user-123', 'mentor', is_host=True, display_name='Mentor Name'
        )

        payload = jwt.decode(
            token,
            'test-api-secret',
            algorithms=['HS256'],
            options={'verify_iat': False, 'verify_exp': False},
        )

        self.assertEqual(payload['iss'], 'test-api-key')
        self.assertEqual(payload['sub'], 'user-123')
        self.assertEqual(payload['name'], 'Mentor Name')
        self.assertEqual(payload['video'], {
            'room': 'demo-room',
            'roomJoin': True,
            'canPublish': True,
            'canSubscribe': True,
            'canPublishData': True,
            'canUpdateOwnMetadata': True,
            'roomAdmin': True,
        })
        self.assertNotIn('audio', payload)
        self.assertNotIn('role', payload)

    @override_settings(LIVEKIT_API_KEY='', LIVEKIT_API_SECRET='')
    def test_requires_livekit_credentials(self):
        with self.assertRaisesMessage(ValueError, 'LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be configured.'):
            create_livekit_access_token('demo-room', 'user-123', 'student')


class MeetingServiceStatusTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='meeting-service-admin',
            email='service-admin@example.com',
            password='Password123!',
            role=User.Role.SUPER_ADMIN,
        )
        self.student = User.objects.create_user(
            username='meeting-service-student',
            email='service-student@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.url = reverse('meeting-service-status')

    @override_settings(
        LIVEKIT_URL='wss://live.example.com',
        LIVEKIT_API_KEY='test-livekit-key',
        LIVEKIT_API_SECRET='test-livekit-secret',
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.example.com',
        EMAIL_HOST_USER='mail-user',
        EMAIL_HOST_PASSWORD='mail-password',
        DEFAULT_FROM_EMAIL='meetings@example.com',
    )
    @patch('meetings.views.get_connection')
    def test_admin_can_check_service_connectivity_without_exposing_secrets(self, get_connection_mock):
        connection = get_connection_mock.return_value
        connection.open.return_value = True
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['livekit'], {'configured': True, 'missing': []})
        self.assertEqual(response.data['email'], {
            'configured': True,
            'missing': [],
            'provider': 'smtp',
            'connection': 'connected',
            'error': None,
        })
        self.assertNotIn('test-livekit-secret', str(response.data))
        self.assertNotIn('mail-password', str(response.data))
        connection.close.assert_called_once()

    @override_settings(
        LIVEKIT_URL='',
        LIVEKIT_API_KEY='',
        LIVEKIT_API_SECRET='',
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        EMAIL_HOST='',
        EMAIL_HOST_USER='',
        EMAIL_HOST_PASSWORD='',
        DEFAULT_FROM_EMAIL='webmaster@localhost',
    )
    @patch('meetings.views.get_connection')
    def test_unconfigured_services_are_reported_without_opening_mail_connection(self, get_connection_mock):
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['livekit'], {
            'configured': False,
            'missing': ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET'],
        })
        self.assertEqual(response.data['email'], {
            'configured': False,
            'missing': ['EMAIL_BACKEND'],
            'provider': 'smtp',
            'connection': 'not_configured',
            'error': None,
        })
        get_connection_mock.assert_not_called()

    @override_settings(
        LIVEKIT_URL='wss://live.example.com',
        LIVEKIT_API_KEY='test-livekit-key',
        LIVEKIT_API_SECRET='test-livekit-secret',
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='',
        EMAIL_HOST_USER='',
        EMAIL_HOST_PASSWORD='',
        DEFAULT_FROM_EMAIL='webmaster@localhost',
        RESEND_API_KEY='re_test-api-key',
    )
    @patch('meetings.views.get_connection')
    def test_resend_api_configuration_bypasses_smtp_connectivity_check(self, get_connection_mock):
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], {
            'configured': True,
            'missing': [],
            'provider': 'resend_api',
            'connection': 'api_configured',
            'error': None,
        })
        self.assertNotIn('re_test-api-key', str(response.data))
        get_connection_mock.assert_not_called()

    @override_settings(
        LIVEKIT_URL='wss://live.example.com',
        LIVEKIT_API_KEY='test-livekit-key',
        LIVEKIT_API_SECRET='test-livekit-secret',
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.example.com',
        EMAIL_HOST_USER='mail-user',
        EMAIL_HOST_PASSWORD='mail-password',
        DEFAULT_FROM_EMAIL='meetings@example.com',
    )
    @patch('meetings.views.get_connection')
    def test_smtp_authentication_failure_has_a_safe_diagnostic(self, get_connection_mock):
        get_connection_mock.return_value.open.side_effect = smtplib.SMTPAuthenticationError(535, b'auth failed')
        self.client.force_authenticate(self.admin)

        with self.assertLogs('meetings.views', level='ERROR'):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email']['connection'], 'failed')
        self.assertEqual(response.data['email']['error'], 'authentication_failed')
        self.assertEqual(response.data['email']['provider'], 'smtp')
        self.assertNotIn('mail-password', str(response.data))

    def test_students_cannot_check_service_configuration(self):
        self.client.force_authenticate(self.student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class MeetingAuthorizationTests(APITestCase):
    def setUp(self):
        self.host = User.objects.create_user(
            username='meeting-host', email='host@example.com', password='Password123!', role=User.Role.INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username='enrolled-student', email='student@example.com', password='Password123!', role=User.Role.STUDENT
        )
        self.other_student = User.objects.create_user(
            username='other-student', email='invitee@example.com', password='Password123!', role=User.Role.STUDENT
        )
        self.course = Course.objects.create(
            title='Startup Basics',
            slug='startup-basics',
            description='Course description',
            instructor=self.host,
            status=Course.Status.PUBLISHED,
        )
        self.enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        self.meeting = Meeting.objects.create(
            course=self.course,
            title='Live classroom',
            kind=Meeting.Kind.CLASSROOM,
            host=self.host,
            room_name='startup-classroom',
            scheduled_start=timezone.now() + timedelta(minutes=10),
        )
        self.list_url = reverse('meeting-list')
        self.detail_url = reverse('meeting-detail', args=[self.meeting.id])
        self.join_url = reverse('meeting-join-meeting', args=[self.meeting.id])

    def test_enrolled_student_can_see_and_join_course_classroom(self):
        self.client.force_authenticate(self.student)

        list_response = self.client.get(self.list_url)
        join_response = self.client.post(self.join_url)

        self.assertEqual(list_response.status_code, 200)
        meetings = list_response.data
        self.assertEqual(len(meetings), 1)
        self.assertEqual(join_response.status_code, 200)
        self.assertTrue(MeetingParticipant.objects.filter(
            meeting=self.meeting, user=self.student, joined_at__isnull=False
        ).exists())

    def test_unenrolled_student_cannot_discover_or_join_course_classroom(self):
        self.client.force_authenticate(self.other_student)

        list_response = self.client.get(self.list_url)
        join_response = self.client.post(self.join_url)

        self.assertEqual(list_response.status_code, 200)
        meetings = list_response.data
        self.assertEqual(len(meetings), 0)
        self.assertIn(join_response.status_code, (403, 404))

    def test_non_host_cannot_edit_or_delete_accessible_meeting(self):
        self.client.force_authenticate(self.student)
        payload = {
            'title': 'Changed title',
            'kind': Meeting.Kind.CLASSROOM,
            'scheduled_start': (timezone.now() + timedelta(hours=1)).isoformat(),
        }

        update_response = self.client.patch(self.detail_url, payload)
        delete_response = self.client.delete(self.detail_url)

        self.assertEqual(update_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertEqual(self.meeting.title, 'Live classroom')

    def test_consultation_request_can_be_accepted_or_rejected_by_host(self):
        consultation = Meeting.objects.create(
            course=self.course,
            title='Mentor office hours',
            kind=Meeting.Kind.CONSULTATION,
            host=self.host,
            room_name='mentor-office-hours',
            scheduled_start=timezone.now() + timedelta(hours=2),
        )
        request_url = reverse('meeting-request-consultation', args=[consultation.id])
        review_url = reverse('meeting-review-consultation', args=[consultation.id])

        self.client.force_authenticate(self.student)
        request_response = self.client.post(request_url)
        self.assertEqual(request_response.status_code, 201)
        invitation = MeetingInvitation.objects.get(meeting=consultation, invited_user=self.student)
        self.assertEqual(invitation.status, MeetingInvitation.Status.PENDING)

        self.client.force_authenticate(self.host)
        accept_response = self.client.post(review_url, {
            'invitation_id': str(invitation.id),
            'decision': 'accept',
        }, format='json')
        self.assertEqual(accept_response.status_code, 200)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, MeetingInvitation.Status.ACCEPTED)
        self.assertTrue(MeetingParticipant.objects.filter(meeting=consultation, user=self.student).exists())

        self.client.force_authenticate(self.student)
        second_request = self.client.post(reverse('meeting-request-consultation', args=[consultation.id]))
        self.assertEqual(second_request.status_code, 200)

        rejectable = Meeting.objects.create(
            course=self.course,
            title='Second office hours',
            kind=Meeting.Kind.CONSULTATION,
            host=self.host,
            room_name='second-office-hours',
            scheduled_start=timezone.now() + timedelta(hours=3),
        )
        self.client.post(reverse('meeting-request-consultation', args=[rejectable.id]))
        pending = MeetingInvitation.objects.get(meeting=rejectable, invited_user=self.student)
        self.client.force_authenticate(self.host)
        reject_response = self.client.post(
            reverse('meeting-review-consultation', args=[rejectable.id]),
            {'invitation_id': str(pending.id), 'decision': 'reject'},
            format='json',
        )
        self.assertEqual(reject_response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, MeetingInvitation.Status.DECLINED)

    def test_non_enrolled_student_cannot_request_consultation(self):
        consultation = Meeting.objects.create(
            course=self.course,
            title='Mentor office hours',
            kind=Meeting.Kind.CONSULTATION,
            host=self.host,
            room_name='another-office-hours',
            scheduled_start=timezone.now() + timedelta(hours=2),
        )
        self.client.force_authenticate(self.other_student)

        response = self.client.post(reverse('meeting-request-consultation', args=[consultation.id]))

        self.assertIn(response.status_code, (403, 404))
        self.assertFalse(MeetingInvitation.objects.filter(meeting=consultation, invited_user=self.other_student).exists())

    @override_settings(LIVEKIT_API_KEY='key', LIVEKIT_API_SECRET='secret', LIVEKIT_URL='wss://live.example.com')
    def test_enrolled_student_receives_token_only_after_host_starts_meeting(self):
        self.client.force_authenticate(self.student)
        token_url = reverse('meeting-token', args=[self.meeting.id])
        before_start = self.client.get(token_url)
        self.assertEqual(before_start.status_code, 409)

        self.client.force_authenticate(self.host)
        start_response = self.client.post(reverse('meeting-start-meeting', args=[self.meeting.id]))
        self.assertEqual(start_response.status_code, 200)

        self.client.force_authenticate(self.student)
        token_response = self.client.get(token_url)
        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(token_response['Cache-Control'], 'no-store')
        self.assertIn('token', token_response.data)
        self.assertEqual(token_response.data['room_name'], self.meeting.room_name)
        self.assertEqual(
            set(token_response.data),
            {'token', 'room_name', 'identity', 'url'},
        )
        self.assertNotIn('secret', str(token_response.data))
        token_payload = jwt.decode(
            token_response.data['token'],
            'secret',
            algorithms=['HS256'],
            options={'verify_iat': False, 'verify_exp': False},
        )
        self.assertEqual(token_payload['iss'], 'key')
        self.assertEqual(token_payload['sub'], str(self.student.id))
        self.assertEqual(token_payload['video']['room'], self.meeting.room_name)

    @override_settings(LIVEKIT_API_KEY='key', LIVEKIT_API_SECRET='secret', LIVEKIT_URL='')
    def test_livekit_token_endpoint_reports_missing_server_url(self):
        self.client.force_authenticate(self.host)
        self.client.post(reverse('meeting-start-meeting', args=[self.meeting.id]))

        response = self.client.get(reverse('meeting-token', args=[self.meeting.id]))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['detail'], 'LiveKit is not configured for this environment.')

    def test_host_can_create_a_meeting_and_is_assigned_as_host(self):
        self.client.force_authenticate(self.host)
        response = self.client.post(self.list_url, {
            'course': self.course.id,
            'title': 'New classroom',
            'kind': Meeting.Kind.CLASSROOM,
        }, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        created = Meeting.objects.get(id=response.data['id'])
        self.assertEqual(created.host, self.host)
        self.assertTrue(created.room_name)
        self.assertTrue(MeetingParticipant.objects.filter(meeting=created, user=self.host, is_host=True).exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_admin_can_schedule_individual_group_and_course_meetings(self):
        admin = User.objects.create_user(
            username='meeting-audience-admin', email='audience-admin@example.com',
            password='Password123!', role=User.Role.SUPER_ADMIN,
        )
        group_student = User.objects.create_user(
            username='meeting-group-student', email='group-student@example.com',
            password='Password123!', role=User.Role.STUDENT,
        )
        self.client.force_authenticate(admin)

        individual_response = self.client.post(self.list_url, {
            'title': 'Individual student session',
            'kind': Meeting.Kind.CONSULTATION,
            'scheduled_start': (timezone.now() + timedelta(hours=2)).isoformat(),
        }, format='json')
        self.assertEqual(individual_response.status_code, 201, individual_response.data)
        individual = Meeting.objects.get(id=individual_response.data['id'])
        individual_invites = self.client.post(
            reverse('meeting-invite-users', args=[individual.id]),
            {'emails': [self.student.email], 'student_only': True},
            format='json',
        )
        self.assertEqual(individual_invites.status_code, 200, individual_invites.data)
        self.assertEqual(
            list(individual.invitations.values_list('invited_user__email', flat=True)),
            [self.student.email],
        )

        group_response = self.client.post(self.list_url, {
            'title': 'Selected student group session',
            'kind': Meeting.Kind.DISCUSSION,
            'scheduled_start': (timezone.now() + timedelta(hours=3)).isoformat(),
        }, format='json')
        self.assertEqual(group_response.status_code, 201, group_response.data)
        group = Meeting.objects.get(id=group_response.data['id'])
        group_invites = self.client.post(
            reverse('meeting-invite-users', args=[group.id]),
            {'emails': [self.student.email, group_student.email], 'student_only': True},
            format='json',
        )
        self.assertEqual(group_invites.status_code, 200, group_invites.data)
        self.assertEqual(group.invitations.count(), 2)
        invalid_group_invites = self.client.post(
            reverse('meeting-invite-users', args=[group.id]),
            {'emails': [self.host.email], 'student_only': True},
            format='json',
        )
        self.assertEqual(invalid_group_invites.status_code, 400)
        self.assertEqual(group.invitations.count(), 2)

        course_response = self.client.post(self.list_url, {
            'course': self.course.id,
            'title': 'Course student classroom',
            'kind': Meeting.Kind.CLASSROOM,
            'scheduled_start': (timezone.now() + timedelta(hours=4)).isoformat(),
        }, format='json')
        self.assertEqual(course_response.status_code, 201, course_response.data)
        course_meeting = Meeting.objects.get(id=course_response.data['id'])
        course_invites = self.client.post(
            reverse('meeting-invite-users', args=[course_meeting.id]),
            {'course_students': True},
            format='json',
        )
        self.assertEqual(course_invites.status_code, 200, course_invites.data)
        self.assertEqual(course_invites.data['invited_count'], 1)
        self.assertEqual(course_invites.data['email_delivery'], {
            'sent': 1,
            'failed': 0,
            'configured': True,
            'error': None,
        })
        self.assertIn(f'/meetings/{course_meeting.id}', mail.outbox[-1].body)

        self.client.force_authenticate(self.student)
        self.assertIn(
            str(course_meeting.id),
            {item['id'] for item in self.client.get(self.list_url).data},
        )
        self.assertEqual(
            self.client.post(reverse('meeting-join-meeting', args=[course_meeting.id])).status_code,
            200,
        )
        self.client.force_authenticate(group_student)
        self.assertIn(
            str(group.id),
            {item['id'] for item in self.client.get(self.list_url).data},
        )

    def test_student_can_book_private_meeting_for_admin_schedule(self):
        admin = User.objects.create_user(
            username='meeting-admin', email='admin@example.com', password='Password123!',
            role=User.Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(self.student)
        response = self.client.post(self.list_url, {
            'title': 'Talk with an ESS administrator',
            'kind': Meeting.Kind.CONSULTATION,
            'scheduled_start': (timezone.now() + timedelta(hours=2)).isoformat(),
        }, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data['admin_notification_sent'])
        self.assertEqual(len(mail.outbox), 1)
        notification = mail.outbox[0]
        self.assertIn('New student meeting request', notification.subject)
        self.assertIn(self.student.email, notification.body)
        self.assertIn('Talk with an ESS administrator', notification.body)
        self.assertIn('/meetings', notification.body)
        self.assertEqual(len(notification.alternatives), 1)
        self.assertIn('Open meetings schedule', notification.alternatives[0][0])
        self.assertIn('Ethiopian Startup School', notification.from_email)
        meeting = Meeting.objects.get(id=response.data['id'])
        self.assertEqual(meeting.host, self.student)
        self.assertIsNone(meeting.course_id)
        self.assertTrue(MeetingParticipant.objects.filter(meeting=meeting, user=self.student, is_host=True).exists())

        self.client.force_authenticate(admin)
        admin_schedule = self.client.get(self.list_url)
        self.assertEqual(admin_schedule.status_code, 200)
        self.assertIn(str(meeting.id), {item['id'] for item in admin_schedule.data})

        start_response = self.client.post(reverse('meeting-start-meeting', args=[meeting.id]))
        self.assertEqual(start_response.status_code, 200)
        admin_join_response = self.client.post(reverse('meeting-join-meeting', args=[meeting.id]))
        self.assertEqual(admin_join_response.status_code, 200)

        self.client.force_authenticate(self.student)
        join_response = self.client.post(reverse('meeting-join-meeting', args=[meeting.id]))
        self.assertEqual(join_response.status_code, 200)

    def test_student_cannot_create_non_consultation_or_course_meeting(self):
        self.client.force_authenticate(self.student)
        classroom_response = self.client.post(self.list_url, {
            'title': 'Unauthorized classroom',
            'kind': Meeting.Kind.CLASSROOM,
        }, format='json')
        course_consultation_response = self.client.post(self.list_url, {
            'title': 'Course-linked private meeting',
            'kind': Meeting.Kind.CONSULTATION,
            'course': self.course.id,
        }, format='json')

        self.assertEqual(classroom_response.status_code, 403)
        self.assertEqual(course_consultation_response.status_code, 400)
        self.assertFalse(Meeting.objects.filter(title__in=[
            'Unauthorized classroom', 'Course-linked private meeting',
        ]).exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('meetings.emails.EmailMultiAlternatives.send', side_effect=OSError('SMTP unavailable'))
    def test_student_booking_succeeds_when_admin_email_delivery_fails(self, _send_email):
        User.objects.create_user(
            username='meeting-admin-smtp-error', password='Password123!',
            role=User.Role.SUPER_ADMIN, email='admin@example.com',
        )
        self.client.force_authenticate(self.student)

        with self.assertLogs('meetings.emails', level='ERROR'):
            response = self.client.post(self.list_url, {
                'title': 'Admin email unavailable',
                'kind': Meeting.Kind.CONSULTATION,
                'scheduled_start': (timezone.now() + timedelta(hours=2)).isoformat(),
            }, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(response.data['admin_notification_sent'])
        self.assertTrue(Meeting.objects.filter(title='Admin email unavailable').exists())

    def test_meeting_detail_includes_course_title_or_null(self):
        self.client.force_authenticate(self.host)

        linked_response = self.client.get(self.detail_url)
        unlinked_meeting = Meeting.objects.create(
            title='Open discussion',
            kind=Meeting.Kind.DISCUSSION,
            host=self.host,
            room_name='open-discussion',
            scheduled_start=timezone.now() + timedelta(hours=1),
        )
        unlinked_response = self.client.get(reverse('meeting-detail', args=[unlinked_meeting.id]))

        self.assertEqual(linked_response.status_code, 200)
        self.assertEqual(linked_response.data['course_title'], self.course.title)
        self.assertEqual(unlinked_response.status_code, 200)
        self.assertIsNone(unlinked_response.data['course'])
        self.assertIsNone(unlinked_response.data['course_title'])

    def test_instructor_cannot_schedule_a_meeting_for_another_instructors_course(self):
        other_instructor = User.objects.create_user(
            username='other-host', password='Password123!', role=User.Role.INSTRUCTOR
        )
        other_course = Course.objects.create(
            title='Other course',
            slug='other-course',
            description='Another course',
            instructor=other_instructor,
            status=Course.Status.PUBLISHED,
        )
        self.client.force_authenticate(self.host)

        response = self.client.post(self.list_url, {
            'course': other_course.id,
            'title': 'Unauthorized classroom',
            'kind': Meeting.Kind.CLASSROOM,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('course', response.data)
        self.assertFalse(Meeting.objects.filter(title='Unauthorized classroom').exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_host_can_invite_by_email_and_invitee_must_accept_before_joining(self):
        self.client.force_authenticate(self.host)
        invite_url = reverse('meeting-invite-users', args=[self.meeting.id])
        invite_response = self.client.post(invite_url, {'emails': [' INVITEE@example.com ']}, format='json')

        self.assertEqual(invite_response.status_code, 200, invite_response.data)
        self.assertEqual(invite_response.data['email_delivery'], {
            'sent': 1,
            'failed': 0,
            'configured': True,
            'error': None,
        })
        self.assertIn(f'/meetings/{self.meeting.id}', mail.outbox[0].body)
        invitation = MeetingInvitation.objects.get(meeting=self.meeting, invited_user=self.other_student)
        self.assertEqual(invitation.status, MeetingInvitation.Status.PENDING)

        self.client.force_authenticate(self.other_student)
        join_response = self.client.post(self.join_url)
        self.assertIn(join_response.status_code, (403, 404))
        accept_response = self.client.post(
            reverse('meeting-accept-invitation', args=[self.meeting.id]), format='json',
        )
        self.assertEqual(accept_response.status_code, 200, accept_response.data)
        join_response = self.client.post(self.join_url)
        self.assertEqual(join_response.status_code, 200, join_response.data)

    @override_settings(
        RESEND_API_KEY='re_test-api-key',
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        FRONTEND_BASE_URL='https://school.example',
    )
    @patch('meetings.emails.urlopen')
    def test_invitation_uses_resend_https_api_when_configured(self, urlopen_mock):
        self.client.force_authenticate(self.host)

        response = self.client.post(
            reverse('meeting-invite-users', args=[self.meeting.id]),
            {'emails': [self.other_student.email]},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['email_delivery'], {
            'sent': 1,
            'failed': 0,
            'configured': True,
            'error': None,
        })
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.resend.com/emails')
        self.assertEqual(request.get_header('Authorization'), 'Bearer re_test-api-key')
        payload = json.loads(request.data)
        self.assertEqual(payload['to'], [self.other_student.email])
        self.assertIn(f'https://school.example/meetings/{self.meeting.id}', payload['text'])
        self.assertIn('Open meeting', payload['html'])

    @override_settings(
        RESEND_API_KEY='re_test-api-key',
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
    )
    @patch(
        'meetings.emails.urlopen',
        side_effect=HTTPError('https://api.resend.com/emails', 401, 'unauthorized', {}, None),
    )
    def test_resend_authentication_failure_has_a_safe_delivery_code(self, _urlopen_mock):
        self.client.force_authenticate(self.host)

        with self.assertLogs('meetings.emails', level='ERROR'):
            response = self.client.post(
                reverse('meeting-invite-users', args=[self.meeting.id]),
                {'emails': [self.other_student.email]},
                format='json',
            )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['email_delivery'], {
            'sent': 0,
            'failed': 1,
            'configured': True,
            'error': 'api_authentication_failed',
        })

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('meetings.emails.EmailMultiAlternatives.send', side_effect=OSError('SMTP unavailable'))
    def test_invitation_email_failure_is_reported_without_losing_invitation(self, _send_email):
        self.client.force_authenticate(self.host)

        response = self.client.post(
            reverse('meeting-invite-users', args=[self.meeting.id]),
            {'emails': [self.other_student.email]},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['email_delivery'], {
            'sent': 0,
            'failed': 1,
            'configured': True,
            'error': 'connection_failed',
        })
        self.assertTrue(MeetingInvitation.objects.filter(
            meeting=self.meeting,
            invited_user=self.other_student,
            status=MeetingInvitation.Status.PENDING,
        ).exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_console_email_backend_does_not_claim_invitation_was_sent(self):
        self.client.force_authenticate(self.host)

        response = self.client.post(
            reverse('meeting-invite-users', args=[self.meeting.id]),
            {'emails': [self.other_student.email]},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['email_delivery'], {
            'sent': 0,
            'failed': 1,
            'configured': False,
            'error': 'not_configured',
        })

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    @patch('meetings.emails.get_connection')
    def test_invitation_reports_smtp_authentication_failure_without_exposing_credentials(
        self, get_connection_mock,
    ):
        get_connection_mock.return_value.open.side_effect = smtplib.SMTPAuthenticationError(
            535, b'authentication failed'
        )
        self.client.force_authenticate(self.host)

        with self.assertLogs('meetings.emails', level='ERROR'):
            response = self.client.post(
                reverse('meeting-invite-users', args=[self.meeting.id]),
                {'emails': [self.other_student.email]},
                format='json',
            )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['email_delivery'], {
            'sent': 0,
            'failed': 1,
            'configured': True,
            'error': 'authentication_failed',
        })
        self.assertNotIn('authentication failed', str(response.data))

    def test_host_invite_reports_unknown_email_instead_of_silently_skipping(self):
        self.client.force_authenticate(self.host)

        response = self.client.post(
            reverse('meeting-invite-users', args=[self.meeting.id]),
            {'emails': ['missing@example.com']},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['unknown_emails'], ['missing@example.com'])


class MeetingAdminTests(TestCase):
    def test_staff_can_open_standalone_invitation_add_page(self):
        admin_user = User.objects.create_superuser(
            username='meeting-add-page-admin',
            email='meeting-add-page-admin@example.com',
            password='Password123!',
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('admin:meetings_meetinginvitation_add'))

        self.assertEqual(response.status_code, 200, response.content[:1000])
        invitation_form = response.context['adminform'].form
        self.assertIsInstance(invitation_form.fields['meeting'].widget, ForeignKeyRawIdWidget)
        self.assertIsInstance(invitation_form.fields['invited_user'].widget, ForeignKeyRawIdWidget)

    def test_meeting_models_are_registered_in_django_admin(self):
        self.assertTrue(admin.site.is_registered(Meeting))
        self.assertTrue(admin.site.is_registered(MeetingParticipant))
        self.assertTrue(admin.site.is_registered(MeetingInvitation))

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        FRONTEND_BASE_URL='https://school.example',
    )
    def test_admin_creates_room_and_emails_new_pending_invitation_with_direct_link(self):
        admin_user = User.objects.create_superuser(
            username='meeting-admin', email='admin@example.com', password='Password123!',
        )
        student = User.objects.create_user(
            username='meeting-student', email='student@example.com', password='Password123!',
            role=User.Role.STUDENT,
        )
        meeting = Meeting(
            title='Admin scheduled session',
            host=admin_user,
            room_name='',
            scheduled_start=timezone.now() + timedelta(hours=1),
        )
        request = RequestFactory().post('/admin/meetings/meeting/add/')
        request.user = admin_user
        request.session = {}
        request._messages = FallbackStorage(request)
        meeting_admin = MeetingAdmin(Meeting, admin.site)

        meeting_admin.save_model(request, meeting, form=None, change=False)
        invitation = MeetingInvitation.objects.create(
            meeting=meeting,
            invited_user=student,
            status=MeetingInvitation.Status.PENDING,
        )
        invitation_formset = SimpleNamespace(
            model=MeetingInvitation,
            new_objects=[invitation],
            changed_objects=[],
        )

        with self.captureOnCommitCallbacks(execute=True), patch.object(MeetingAdmin, 'save_formset'):
            meeting_admin.save_related(
                request,
                form=SimpleNamespace(instance=meeting, save_m2m=lambda: None),
                formsets=[invitation_formset],
                change=False,
            )

        self.assertTrue(meeting.room_name.startswith('room-'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            f'https://school.example/meetings/{meeting.pk}',
            mail.outbox[0].body,
        )
        self.assertIn('Open meeting', mail.outbox[0].alternatives[0][0])
        messages = list(request._messages)
        self.assertTrue(any('SMTP handoff' in str(message) for message in messages))

    @override_settings(FRONTEND_BASE_URL='https://school.example')
    def test_admin_exposes_shareable_link_for_existing_meeting(self):
        admin_user = User.objects.create_superuser(
            username='meeting-link-admin', email='admin-link@example.com', password='Password123!',
        )
        meeting = Meeting.objects.create(
            title='Shareable session',
            host=admin_user,
            room_name='shareable-session',
            scheduled_start=timezone.now() + timedelta(hours=1),
        )

        link = MeetingAdmin(Meeting, admin.site).meeting_link(meeting)
        call_link = MeetingAdmin(Meeting, admin.site).open_meeting(meeting)

        self.assertIn(f'href="https://school.example/meetings/{meeting.pk}"', str(link))
        self.assertIn('Open / start call', str(call_link))

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        FRONTEND_BASE_URL='https://school.example',
    )
    def test_admin_can_resend_pending_invitations_for_existing_meetings(self):
        admin_user = User.objects.create_superuser(
            username='meeting-resend-admin', email='resend-admin@example.com', password='Password123!',
        )
        student = User.objects.create_user(
            username='meeting-resend-student', email='resend-student@example.com',
            password='Password123!', role=User.Role.STUDENT,
        )
        meeting = Meeting.objects.create(
            title='Previously unsent invitation',
            host=admin_user,
            room_name='previously-unsent',
            scheduled_start=timezone.now() + timedelta(hours=1),
        )
        MeetingInvitation.objects.create(
            meeting=meeting,
            invited_user=student,
            status=MeetingInvitation.Status.PENDING,
        )
        request = RequestFactory().post('/admin/meetings/meeting/')
        request.user = admin_user
        request.session = {}
        request._messages = FallbackStorage(request)

        MeetingAdmin(Meeting, admin.site).resend_pending_invitations(
            request,
            Meeting.objects.filter(pk=meeting.pk),
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f'https://school.example/meetings/{meeting.pk}', mail.outbox[0].body)
        self.assertTrue(any('SMTP handoff' in str(message) for message in request._messages))

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        FRONTEND_BASE_URL='https://school.example',
    )
    def test_saving_existing_pending_invitation_resends_email_with_meeting_link(self):
        admin_user = User.objects.create_superuser(
            username='meeting-invitation-admin', email='invitation-admin@example.com',
            password='Password123!',
        )
        student = User.objects.create_user(
            username='meeting-invitation-student', email='invitation-student@example.com',
            password='Password123!', role=User.Role.STUDENT,
        )
        meeting = Meeting.objects.create(
            title='Standalone invitation',
            host=admin_user,
            room_name='standalone-invitation',
            scheduled_start=timezone.now() + timedelta(hours=1),
        )
        request = RequestFactory().post('/admin/meetings/meetinginvitation/add/')
        request.user = admin_user
        request.session = {}
        request._messages = FallbackStorage(request)
        invitation_admin = admin.site._registry[MeetingInvitation]
        invitation = MeetingInvitation(
            meeting=meeting,
            invited_user=student,
            status=MeetingInvitation.Status.PENDING,
        )

        with self.captureOnCommitCallbacks(execute=True):
            invitation_admin.save_model(request, invitation, form=None, change=False)
            invitation_admin.save_model(request, invitation, form=None, change=True)

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn(f'https://school.example/meetings/{meeting.pk}', mail.outbox[-1].body)
        self.assertIn(
            f'href="https://school.example/meetings/{meeting.pk}"',
            str(invitation_admin.meeting_link(invitation)),
        )

    def test_invitation_is_saved_when_email_settings_lookup_fails(self):
        admin_user = User.objects.create_superuser(
            username='meeting-save-error-admin',
            email='meeting-save-error-admin@example.com',
            password='Password123!',
        )
        student = User.objects.create_user(
            username='meeting-save-error-student',
            email='meeting-save-error-student@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        meeting = Meeting.objects.create(
            title='Email settings failure session',
            host=admin_user,
            room_name='email-settings-failure',
            scheduled_start=timezone.now() + timedelta(hours=1),
        )
        self.client.force_login(admin_user)

        with self.captureOnCommitCallbacks(execute=True), patch(
            'meetings.emails.send_meeting_invitations',
            side_effect=DatabaseError('temporary email settings database failure'),
        ):
            response = self.client.post(
                reverse('admin:meetings_meetinginvitation_add'),
                {
                    'meeting': str(meeting.pk),
                    'invited_user': str(student.pk),
                    'status': MeetingInvitation.Status.PENDING,
                },
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        invitation = MeetingInvitation.objects.get(meeting=meeting, invited_user=student)
        request = RequestFactory().post('/admin/meetings/meetinginvitation/add/')
        request.user = admin_user
        request.session = {}
        request._messages = FallbackStorage(request)
        meeting_admin = MeetingAdmin(Meeting, admin.site)
        with self.assertLogs('meetings.admin', level='ERROR'), patch(
            'meetings.emails.send_meeting_invitations',
            side_effect=DatabaseError('temporary email settings database failure'),
        ):
            meeting_admin._email_invitations(request, meeting, [invitation])
        self.assertTrue(any(
            'invitation was saved, but its email could not be sent' in str(message).lower()
            for message in request._messages
        ))
