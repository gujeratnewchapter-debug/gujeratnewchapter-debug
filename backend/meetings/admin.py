import logging
import smtplib
import uuid

from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, transaction
from django.utils.html import format_html

from .models import (
    Meeting,
    MeetingAttendance,
    MeetingInvitation,
    MeetingParticipant,
    MeetingSession,
)

logger = logging.getLogger(__name__)

EMAIL_FAILURE_ADVICE = {
    'authentication_failed': 'SMTP rejected the username or password; verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in the backend service settings.',
    'connection_failed': 'The backend could not connect to the SMTP server; verify EMAIL_HOST, EMAIL_PORT, TLS settings, and provider network restrictions.',
    'timeout': 'The SMTP server did not respond in time; verify the host and port and check the email provider status.',
    'recipient_rejected': 'The SMTP server rejected the recipient address; verify the student email and the provider’s recipient policies.',
    'message_rejected': 'The email provider rejected the message; verify DEFAULT_FROM_EMAIL and the sender domain authorization.',
    'missing_recipient_email': 'The invited student account does not have an email address.',
    'not_configured': 'The backend is using a non-SMTP or unconfigured email backend.',
    'configuration_error': 'The backend email service configuration is invalid; verify the email backend settings.',
    'api_connection_failed': 'The backend could not connect to the HTTPS email API; check outbound HTTPS access and the provider status.',
    'api_unavailable': 'The HTTPS email provider is unavailable; check the provider status and retry.',
    'rate_limited': 'The email provider rate limit was reached; wait before retrying invitations.',
    'api_authentication_failed': 'The email API rejected its key; verify RESEND_API_KEY in the backend service secrets.',
    'smtp_error': 'The SMTP server rejected the request; check the backend email logs and provider settings.',
    'unknown': 'Check the backend email logs for the delivery error.',
}


def _email_failure_advice(error_code):
    return EMAIL_FAILURE_ADVICE.get(error_code, EMAIL_FAILURE_ADVICE['unknown'])


class MeetingParticipantInline(admin.TabularInline):
    model = MeetingParticipant
    extra = 0
    raw_id_fields = ('user',)
    fields = ('user', 'role', 'is_host', 'joined_at', 'left_at', 'is_muted', 'is_camera_on')


class MeetingInvitationInline(admin.TabularInline):
    model = MeetingInvitation
    extra = 0
    raw_id_fields = ('invited_user',)
    fields = ('invited_user', 'status', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'status', 'host', 'scheduled_start', 'course', 'open_meeting')
    list_filter = ('kind', 'status', 'scheduled_start')
    search_fields = ('title', 'description', 'host__username', 'host__email', 'participants__user__email')
    readonly_fields = ('id', 'room_name', 'meeting_link', 'started_at', 'ended_at', 'created_at', 'updated_at')
    inlines = (MeetingParticipantInline, MeetingInvitationInline)
    date_hierarchy = 'scheduled_start'
    actions = ('resend_pending_invitations',)

    @admin.display(description='Shareable meeting link')
    def meeting_link(self, obj):
        if not obj or not obj.pk:
            return 'Save the meeting to create its link.'
        url = f'{settings.FRONTEND_BASE_URL.rstrip("/")}/meetings/{obj.pk}'
        return format_html('<a href="{0}" target="_blank" rel="noopener noreferrer">{0}</a>', url)

    @admin.display(description='Live meeting')
    def open_meeting(self, obj):
        if obj.status not in {Meeting.Status.SCHEDULED, Meeting.Status.LIVE}:
            return '—'
        url = f'{settings.FRONTEND_BASE_URL.rstrip("/")}/meetings/{obj.pk}'
        label = 'Join call' if obj.status == Meeting.Status.LIVE else 'Open / start call'
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener noreferrer">{1}</a>',
            url,
            label,
        )

    def save_model(self, request, obj, form, change):
        if not obj.room_name:
            obj.room_name = f'room-{uuid.uuid4().hex[:12]}'
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        invitations = []
        for formset in formsets:
            if formset.model != MeetingInvitation:
                continue
            invitations.extend(
                invitation
                for invitation in formset.new_objects
                if invitation.status == MeetingInvitation.Status.PENDING
            )
            invitations.extend(
                invitation
                for invitation, changed_fields in formset.changed_objects
                if 'status' in changed_fields and invitation.status == MeetingInvitation.Status.PENDING
            )
        if invitations:
            transaction.on_commit(
                lambda: self._email_invitations(request, form.instance, invitations),
                robust=True,
            )

    def _email_invitations(self, request, meeting, invitations):
        recipients = list({invitation.invited_user_id: invitation.invited_user for invitation in invitations}.values())
        if not recipients:
            return

        from .emails import send_meeting_invitations

        try:
            result = send_meeting_invitations(meeting, recipients)
        except (DatabaseError, ImproperlyConfigured, OSError, smtplib.SMTPException, ValueError):
            logger.exception('Could not prepare or send invitations for meeting %s.', meeting.pk)
            self.message_user(
                request,
                'The invitation was saved, but its email could not be sent. Check the backend email settings and logs.',
                level=messages.ERROR,
            )
            return
        sent = result['sent']
        failed = result['failed']
        if sent:
            self.message_user(
                request,
                f'Email server accepted the meeting invitation for {sent} recipient{"s" if sent != 1 else ""}. '
                'This confirms SMTP handoff, not inbox delivery; ask the recipient to check Spam/Junk if it is missing.',
                level=messages.SUCCESS,
            )
        if failed or not result['configured']:
            self.message_user(
                request,
                f'Invitation email failed for {failed} recipient{"s" if failed != 1 else ""}. '
                f'{_email_failure_advice(result.get("error"))} '
                'Retry from the pending invitation action after correcting the issue.',
                level=messages.ERROR,
            )

    @admin.action(description='Resend pending meeting invitations by email')
    def resend_pending_invitations(self, request, queryset):
        sent = 0
        failed = 0
        error_codes = set()
        for meeting in queryset:
            invitations = list(
                meeting.invitations
                .filter(status=MeetingInvitation.Status.PENDING)
                .select_related('invited_user')
            )
            if not invitations:
                continue
            from .emails import send_meeting_invitations

            result = send_meeting_invitations(
                meeting,
                [invitation.invited_user for invitation in invitations],
            )
            sent += result['sent']
            failed += result['failed']
            if result.get('error'):
                error_codes.add(result['error'])
        if sent:
            self.message_user(
                request,
                f'Email server accepted the meeting invitation for {sent} recipient{"s" if sent != 1 else ""}. '
                'This confirms SMTP handoff, not inbox delivery; ask the recipient to check Spam/Junk if it is missing.',
                level=messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f'Invitation email failed for {failed} recipient{"s" if failed != 1 else ""}. '
                f'{_email_failure_advice(next(iter(error_codes), None))} '
                'Retry from the pending invitation action after correcting the issue.',
                level=messages.ERROR,
            )


@admin.register(MeetingParticipant)
class MeetingParticipantAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'user', 'role', 'is_host', 'joined_at', 'left_at')
    list_filter = ('role', 'is_host', 'joined_at')
    search_fields = ('meeting__title', 'user__username', 'user__email')


@admin.register(MeetingInvitation)
class MeetingInvitationAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'invited_user', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('meeting__title', 'invited_user__username', 'invited_user__email')
    raw_id_fields = ('meeting', 'invited_user')
    readonly_fields = ('id', 'meeting_link', 'created_at', 'updated_at')
    actions = ('resend_selected_pending_invitations',)

    @admin.display(description='Shareable meeting link')
    def meeting_link(self, obj):
        return MeetingAdmin(Meeting, admin.site).meeting_link(obj.meeting)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status == MeetingInvitation.Status.PENDING:
            transaction.on_commit(
                lambda: MeetingAdmin(Meeting, admin.site)._email_invitations(
                    request,
                    obj.meeting,
                    [obj],
                ),
                robust=True,
            )

    @admin.action(description='Resend selected pending meeting invitations')
    def resend_selected_pending_invitations(self, request, queryset):
        pending = queryset.filter(
            status=MeetingInvitation.Status.PENDING,
        ).select_related('meeting', 'invited_user')
        invitations_by_meeting = {}
        for invitation in pending:
            invitations_by_meeting.setdefault(invitation.meeting, []).append(invitation)
        meeting_admin = MeetingAdmin(Meeting, admin.site)
        for meeting, invitations in invitations_by_meeting.items():
            meeting_admin._email_invitations(request, meeting, invitations)


@admin.register(MeetingSession)
class MeetingSessionAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'started_at', 'ended_at', 'host_identity')
    search_fields = ('meeting__title', 'host_identity', 'room_name')
    readonly_fields = ('id', 'started_at')


@admin.register(MeetingAttendance)
class MeetingAttendanceAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'user', 'joined_at', 'left_at', 'duration_seconds')
    list_filter = ('joined_at',)
    search_fields = ('meeting__title', 'user__username', 'user__email')
    readonly_fields = ('id', 'joined_at')
