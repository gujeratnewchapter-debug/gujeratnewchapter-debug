import logging
import smtplib
import socket
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.mail import get_connection
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Meeting, MeetingInvitation, MeetingParticipant, MeetingSession

logger = logging.getLogger(__name__)


class IsHostOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return request.user.is_super_admin or request.user == obj.host or getattr(obj, 'host_id', None) == request.user.id


class IsMeetingParticipant(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, 'is_super_admin', False):
            return True
        if hasattr(obj, 'host_id') and obj.host_id == request.user.id:
            return True
        return MeetingParticipant.objects.filter(meeting=obj, user=request.user).exists()


class MeetingViewSet(viewsets.ModelViewSet):
    queryset = Meeting.objects.select_related('host', 'course').prefetch_related('participants__user', 'invitations__invited_user')
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in {'update', 'partial_update', 'destroy'}:
            return [IsHostOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        if user.is_super_admin:
            return qs
        if user.is_instructor or user.is_mentor:
            return qs.filter(
                Q(host=user)
                | Q(kind__in=['classroom', 'discussion'], course__instructor=user)
                | Q(kind='consultation', course__instructor=user, status=Meeting.Status.SCHEDULED)
            ).distinct()
        return qs.filter(
            Q(host=user) |
            Q(participants__user=user) |
            Q(invitations__invited_user=user, invitations__status__in=['pending', 'accepted']) |
            Q(kind__in=['classroom', 'discussion'], course__enrollments__student=user) |
            Q(kind='consultation', status=Meeting.Status.SCHEDULED, course__enrollments__student=user)
        ).distinct()

    def get_serializer_class(self):
        from .serializers import MeetingSerializer
        return MeetingSerializer

    @action(detail=False, methods=['get'], url_path='service-status')
    def service_status(self, request):
        if not request.user.is_super_admin:
            return Response({'detail': 'Only administrators can check meeting services.'}, status=403)

        livekit_missing = [
            name for name, value in (
                ('LIVEKIT_URL', settings.LIVEKIT_URL),
                ('LIVEKIT_API_KEY', settings.LIVEKIT_API_KEY),
                ('LIVEKIT_API_SECRET', settings.LIVEKIT_API_SECRET),
            )
            if not value
        ]
        email_missing = [
            name for name, value in (
                ('EMAIL_HOST', settings.EMAIL_HOST),
                ('EMAIL_HOST_USER', settings.EMAIL_HOST_USER),
                ('EMAIL_HOST_PASSWORD', settings.EMAIL_HOST_PASSWORD),
                (
                    'DEFAULT_FROM_EMAIL',
                    '' if settings.DEFAULT_FROM_EMAIL.endswith('@localhost') else settings.DEFAULT_FROM_EMAIL,
                ),
            )
            if not value
        ]
        console_backend = settings.EMAIL_BACKEND.endswith('.console.EmailBackend')
        email_configured = not console_backend and not email_missing
        email_connection = 'not_configured'
        email_error = None

        if email_configured:
            connection = get_connection(fail_silently=False)
            try:
                opened = connection.open()
                if opened:
                    email_connection = 'connected'
                else:
                    email_connection = 'failed'
                    email_error = 'connection_failed'
            except smtplib.SMTPAuthenticationError:
                email_connection = 'failed'
                email_error = 'authentication_failed'
                logger.exception('Meeting service check could not authenticate to the configured email service.')
            except (smtplib.SMTPException, OSError, socket.timeout):
                email_connection = 'failed'
                email_error = 'connection_failed'
                logger.exception('Meeting service check could not connect to the configured email service.')
            finally:
                try:
                    connection.close()
                except (smtplib.SMTPException, OSError, socket.timeout):
                    logger.exception('Meeting service check could not close the email connection.')

        return Response({
            'livekit': {
                'configured': not livekit_missing,
                'missing': livekit_missing,
            },
            'email': {
                'configured': email_configured,
                'missing': ['EMAIL_BACKEND'] if console_backend else email_missing,
                'connection': email_connection,
                'error': email_error,
            },
        })

    def create(self, request, *args, **kwargs):
        user = request.user
        permitted_roles = {user.Role.INSTRUCTOR, user.Role.MENTOR, user.Role.SUPER_ADMIN}
        is_student_consultation = (
            user.role == user.Role.STUDENT
            and request.data.get('kind') == Meeting.Kind.CONSULTATION
        )
        if is_student_consultation and request.data.get('course'):
            return Response({'detail': 'Private admin meetings cannot be linked to a course.'}, status=400)
        if user.role not in permitted_roles and not is_student_consultation:
            return Response({'detail': 'Only instructors, mentors, or admins may create meetings.'}, status=403)
        data = request.data.copy()
        data['host'] = user.id
        data['room_name'] = data.get('room_name') or f"room-{uuid.uuid4().hex[:12]}"
        data['scheduled_start'] = data.get('scheduled_start') or timezone.now() + timedelta(minutes=30)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        meeting = serializer.save(host=user)
        MeetingParticipant.objects.get_or_create(meeting=meeting, user=user, defaults={'role': 'host', 'is_host': True})
        if is_student_consultation:
            from .emails import notify_admins_of_student_booking

            admin_notification_sent = notify_admins_of_student_booking(meeting)
            response_data = serializer.data
            response_data['admin_notification_sent'] = bool(admin_notification_sent)
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _can_join(self, meeting, user):
        if user == meeting.host or user.is_super_admin:
            return True
        if MeetingParticipant.objects.filter(meeting=meeting, user=user).exists():
            return True
        if MeetingInvitation.objects.filter(
            meeting=meeting, invited_user=user, status=MeetingInvitation.Status.ACCEPTED
        ).exists():
            return True
        if meeting.kind in {Meeting.Kind.CLASSROOM, Meeting.Kind.DISCUSSION} and meeting.course_id:
            from enrollments.models import Enrollment
            return Enrollment.objects.filter(student=user, course_id=meeting.course_id).exists()
        return False

    @action(detail=True, methods=['post'], url_path='join')
    def join_meeting(self, request, pk=None):
        meeting = self.get_object()
        if meeting.status in {Meeting.Status.CANCELLED, Meeting.Status.ENDED}:
            return Response({'detail': 'Meeting is unavailable.'}, status=404)
        if not self._can_join(meeting, request.user):
            return Response({'detail': 'You are not authorized to join this meeting.'}, status=403)
        participant, _ = MeetingParticipant.objects.get_or_create(meeting=meeting, user=request.user, defaults={'role': request.user.role})
        participant.joined_at = timezone.now()
        participant.left_at = None
        participant.is_host = request.user == meeting.host
        participant.save(update_fields=['joined_at', 'left_at', 'is_host'])
        return Response({'detail': 'Joined meeting successfully.', 'room_name': meeting.room_name})

    @action(detail=True, methods=['post'], url_path='leave')
    def leave_meeting(self, request, pk=None):
        meeting = self.get_object()
        participant = MeetingParticipant.objects.filter(meeting=meeting, user=request.user).first()
        if participant:
            participant.left_at = timezone.now()
            participant.save(update_fields=['left_at'])
        return Response({'detail': 'Left meeting.'})

    @action(detail=True, methods=['post'], url_path='start')
    def start_meeting(self, request, pk=None):
        meeting = self.get_object()
        if request.user != meeting.host and not request.user.is_super_admin:
            return Response({'detail': 'Only the host can start the meeting.'}, status=403)
        if meeting.status in {Meeting.Status.ENDED, Meeting.Status.CANCELLED}:
            return Response({'detail': 'This meeting can no longer be started.'}, status=400)
        if meeting.status != Meeting.Status.LIVE:
            meeting.status = Meeting.Status.LIVE
            meeting.started_at = timezone.now()
            meeting.save(update_fields=['status', 'started_at', 'updated_at'])
            MeetingSession.objects.create(meeting=meeting, room_name=meeting.room_name, host_identity=str(request.user.id))
        return Response({'detail': 'Meeting started.'})

    @action(detail=True, methods=['post'], url_path='end')
    def end_meeting(self, request, pk=None):
        meeting = self.get_object()
        if request.user != meeting.host and not request.user.is_super_admin:
            return Response({'detail': 'Only the host can end the meeting.'}, status=403)
        meeting.status = Meeting.Status.ENDED
        meeting.ended_at = timezone.now()
        meeting.save(update_fields=['status', 'ended_at', 'updated_at'])
        MeetingSession.objects.filter(meeting=meeting, ended_at__isnull=True).update(ended_at=meeting.ended_at)
        return Response({'detail': 'Meeting ended.'})

    @action(detail=True, methods=['post'], url_path='invite')
    def invite_users(self, request, pk=None):
        meeting = self.get_object()
        if request.user != meeting.host and not request.user.is_super_admin:
            return Response({'detail': 'Only the host can invite users.'}, status=403)
        invited_user_ids = request.data.get('user_ids', [])
        if hasattr(request.data, 'getlist'):
            invited_user_ids = request.data.getlist('user_ids')
        elif isinstance(invited_user_ids, str):
            invited_user_ids = [invited_user_ids]
        invited_emails = request.data.get('emails', [])
        if isinstance(invited_emails, str):
            invited_emails = invited_emails.split(',')
        student_only = request.data.get('student_only') is True
        course_students = request.data.get('course_students') is True
        if student_only and not request.user.is_super_admin:
            return Response({'detail': 'Only administrators can create student-only invitations.'}, status=403)
        if course_students:
            if not request.user.is_super_admin:
                return Response({'detail': 'Only administrators can email an entire course roster.'}, status=403)
            if meeting.kind != Meeting.Kind.CLASSROOM or not meeting.course_id:
                return Response({'detail': 'Choose a course classroom before inviting its students.'}, status=400)
            if invited_user_ids or invited_emails:
                return Response({'detail': 'Send course invitations separately from individual invitees.'}, status=400)
        if not isinstance(invited_user_ids, (list, tuple)) or not isinstance(invited_emails, (list, tuple)):
            return Response({'detail': 'Provide user_ids and emails as lists.'}, status=400)
        if any(not isinstance(email, str) for email in invited_emails):
            return Response({'detail': 'Each invitee email must be a string.'}, status=400)
        if not course_students and len(invited_user_ids) + len(invited_emails) > 50:
            return Response({'detail': 'You can invite up to 50 users at a time.'}, status=400)

        User = request.user.__class__
        invitees = {}
        missing_ids = []
        if course_students:
            invitees = {
                student.pk: student
                for student in User.objects.filter(
                    enrollments__course_id=meeting.course_id,
                    is_active=True,
                    role=User.Role.STUDENT,
                ).distinct()
            }
            if not invitees:
                return Response({'detail': 'There are no active student accounts enrolled in this course.'}, status=400)

        for user_id in invited_user_ids:
            invitee = User.objects.filter(id=user_id, is_active=True).first()
            if student_only and invitee and invitee.role != User.Role.STUDENT:
                invitee = None
            if not invitee:
                missing_ids.append(str(user_id))
            else:
                invitees[invitee.pk] = invitee

        normalized_emails = {
            email.strip().lower()
            for email in invited_emails
            if isinstance(email, str) and email.strip()
        }
        missing_emails = []
        for email in normalized_emails:
            invitee = User.objects.filter(email__iexact=email, is_active=True).first()
            if student_only and invitee and invitee.role != User.Role.STUDENT:
                invitee = None
            if not invitee:
                missing_emails.append(email)
            else:
                invitees[invitee.pk] = invitee
        if missing_ids or missing_emails:
            return Response({
                'detail': 'Some invitees could not be found.',
                'unknown_user_ids': missing_ids,
                'unknown_emails': missing_emails,
            }, status=400)
        if not invitees:
            return Response({'detail': 'Provide at least one valid invitee.'}, status=400)

        created = []
        if not course_students:
            for user in invitees.values():
                obj, _ = MeetingInvitation.objects.get_or_create(
                    meeting=meeting,
                    invited_user=user,
                    defaults={'status': MeetingInvitation.Status.PENDING},
                )
                if obj.status in {MeetingInvitation.Status.DECLINED, MeetingInvitation.Status.CANCELLED}:
                    obj.status = MeetingInvitation.Status.PENDING
                    obj.save(update_fields=['status', 'updated_at'])
                created.append({'user_id': str(user.id), 'email': user.email, 'status': obj.status})
        from .emails import send_meeting_invitations

        email_delivery = send_meeting_invitations(
            meeting,
            list(invitees.values()),
            require_acceptance=not course_students,
        )
        return Response({
            'detail': 'Invitations processed.',
            'invitations': created,
            'invited_count': len(invitees),
            'email_delivery': email_delivery,
        })

    @action(detail=True, methods=['post'], url_path='accept-invitation')
    def accept_invitation(self, request, pk=None):
        meeting = self.get_object()
        invite = MeetingInvitation.objects.filter(meeting=meeting, invited_user=request.user).first()
        if not invite:
            return Response({'detail': 'No invitation found.'}, status=404)
        if invite.status != MeetingInvitation.Status.PENDING:
            return Response({'detail': 'This invitation is no longer pending.'}, status=400)
        invite.status = MeetingInvitation.Status.ACCEPTED
        invite.save(update_fields=['status', 'updated_at'])
        MeetingParticipant.objects.get_or_create(meeting=meeting, user=request.user, defaults={'role': request.user.role})
        return Response({'detail': 'Invitation accepted.'})

    @action(detail=True, methods=['post'], url_path='request-consultation')
    def request_consultation(self, request, pk=None):
        meeting = self.get_object()
        if meeting.kind != Meeting.Kind.CONSULTATION or meeting.status != Meeting.Status.SCHEDULED:
            return Response({'detail': 'This consultation is not accepting requests.'}, status=400)
        if request.user == meeting.host or request.user.is_super_admin:
            return Response({'detail': 'Meeting hosts do not need to request access.'}, status=400)
        if not meeting.course_id:
            return Response({'detail': 'This consultation is not open for course requests.'}, status=403)
        from enrollments.models import Enrollment
        if not Enrollment.objects.filter(student=request.user, course_id=meeting.course_id).exists():
            return Response({'detail': 'Enroll in this course before requesting a consultation.'}, status=403)

        invitation, created = MeetingInvitation.objects.get_or_create(
            meeting=meeting,
            invited_user=request.user,
            defaults={'status': MeetingInvitation.Status.PENDING},
        )
        if not created and invitation.status == MeetingInvitation.Status.DECLINED:
            invitation.status = MeetingInvitation.Status.PENDING
            invitation.save(update_fields=['status', 'updated_at'])
        elif not created and invitation.status == MeetingInvitation.Status.ACCEPTED:
            return Response({'detail': 'You already have access to this consultation.'}, status=200)
        return Response(
            {'detail': 'Consultation request sent.', 'invitation_id': str(invitation.id), 'status': invitation.status},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='review-consultation')
    def review_consultation(self, request, pk=None):
        meeting = self.get_object()
        if meeting.kind != Meeting.Kind.CONSULTATION:
            return Response({'detail': 'Only consultation requests can be reviewed here.'}, status=400)
        if request.user != meeting.host and not request.user.is_super_admin:
            return Response({'detail': 'Only the consultation host can review requests.'}, status=403)
        invitation_id = request.data.get('invitation_id')
        decision = request.data.get('decision')
        if decision not in {'accept', 'reject'}:
            return Response({'detail': 'Decision must be accept or reject.'}, status=400)
        invitation = MeetingInvitation.objects.filter(
            id=invitation_id, meeting=meeting, status=MeetingInvitation.Status.PENDING
        ).first()
        if not invitation:
            return Response({'detail': 'Pending consultation request not found.'}, status=404)
        invitation.status = (
            MeetingInvitation.Status.ACCEPTED
            if decision == 'accept'
            else MeetingInvitation.Status.DECLINED
        )
        invitation.save(update_fields=['status', 'updated_at'])
        if decision == 'accept':
            MeetingParticipant.objects.get_or_create(
                meeting=meeting, user=invitation.invited_user, defaults={'role': invitation.invited_user.role}
            )
        return Response({'detail': f'Consultation request {decision}ed.', 'status': invitation.status})

    @action(detail=True, methods=['get'], url_path='token')
    def livekit_token(self, request, pk=None):
        meeting = self.get_object()
        if meeting.status != Meeting.Status.LIVE:
            return Response({'detail': 'This meeting is not live.'}, status=409)
        if not self._can_join(meeting, request.user):
            return Response({'detail': 'Unauthorized.'}, status=403)

        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET or not settings.LIVEKIT_URL:
            return Response({'detail': 'LiveKit is not configured for this environment.'}, status=503)

        from .livekit import create_livekit_access_token
        display_name = f'{request.user.first_name} {request.user.last_name}'.strip() or request.user.username
        token = create_livekit_access_token(
            meeting.room_name, str(request.user.id), display_name=display_name,
            is_host=request.user == meeting.host or request.user.is_super_admin,
        )
        return Response(
            {'token': token, 'room_name': meeting.room_name, 'identity': str(request.user.id), 'url': settings.LIVEKIT_URL},
            headers={'Cache-Control': 'no-store'},
        )


class MeetingInvitationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MeetingInvitation.objects.select_related('meeting', 'invited_user')
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return self.queryset
        return self.queryset.filter(Q(invited_user=user) | Q(meeting__host=user)).distinct()


class MeetingParticipantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MeetingParticipant.objects.select_related('meeting', 'user')
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return self.queryset
        return self.queryset.filter(Q(user=user) | Q(meeting__host=user)).distinct()


class MeetingTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = Meeting.objects.filter(id=meeting_id).first()
        if not meeting:
            return Response({'detail': 'Meeting not found.'}, status=404)
        if meeting.status != Meeting.Status.LIVE:
            return Response({'detail': 'This meeting is not live.'}, status=409)
        view = MeetingViewSet()
        if not view._can_join(meeting, request.user):
            return Response({'detail': 'Unauthorized.'}, status=403)
        if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET or not settings.LIVEKIT_URL:
            return Response({'detail': 'LiveKit is not configured for this environment.'}, status=503)

        from .livekit import create_livekit_access_token
        display_name = f'{request.user.first_name} {request.user.last_name}'.strip() or request.user.username
        token = create_livekit_access_token(
            meeting.room_name, str(request.user.id), display_name=display_name,
            is_host=request.user == meeting.host or request.user.is_super_admin,
        )
        return Response(
            {'token': token, 'room_name': meeting.room_name, 'identity': str(request.user.id), 'url': settings.LIVEKIT_URL},
            headers={'Cache-Control': 'no-store'},
        )
