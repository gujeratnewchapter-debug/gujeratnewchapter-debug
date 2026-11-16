from datetime import timedelta

import jwt
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from courses.models import Course
from enrollments.models import Enrollment
from meetings.livekit import create_livekit_access_token
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

    def test_host_can_invite_by_email_and_invitee_must_accept_before_joining(self):
        self.client.force_authenticate(self.host)
        invite_url = reverse('meeting-invite-users', args=[self.meeting.id])
        invite_response = self.client.post(invite_url, {'emails': [' INVITEE@example.com ']}, format='json')

        self.assertEqual(invite_response.status_code, 200, invite_response.data)
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

    def test_host_invite_reports_unknown_email_instead_of_silently_skipping(self):
        self.client.force_authenticate(self.host)

        response = self.client.post(
            reverse('meeting-invite-users', args=[self.meeting.id]),
            {'emails': ['missing@example.com']},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['unknown_emails'], ['missing@example.com'])
