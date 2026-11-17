import uuid

from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html

from .models import (
    Meeting,
    MeetingAttendance,
    MeetingInvitation,
    MeetingParticipant,
    MeetingSession,
)


class MeetingParticipantInline(admin.TabularInline):
    model = MeetingParticipant
    extra = 0
    fields = ('user', 'role', 'is_host', 'joined_at', 'left_at', 'is_muted', 'is_camera_on')


class MeetingInvitationInline(admin.TabularInline):
    model = MeetingInvitation
    extra = 0
    fields = ('invited_user', 'status', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'status', 'host', 'scheduled_start', 'course')
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
        self._email_invitations(request, form.instance, invitations)

    def _email_invitations(self, request, meeting, invitations):
        recipients = list({invitation.invited_user_id: invitation.invited_user for invitation in invitations}.values())
        if not recipients:
            return

        from .emails import send_meeting_invitations

        result = send_meeting_invitations(meeting, recipients)
        sent = result['sent']
        failed = result['failed']
        if sent:
            self.message_user(
                request,
                f'Meeting invitation sent to {sent} recipient{"s" if sent != 1 else ""}.',
                level=messages.SUCCESS,
            )
        if failed or not result['configured']:
            self.message_user(
                request,
                f'Invitation email failed for {failed} recipient{"s" if failed != 1 else ""}. '
                'Check the SMTP configuration and Render application logs.',
                level=messages.ERROR,
            )

    @admin.action(description='Resend pending meeting invitations by email')
    def resend_pending_invitations(self, request, queryset):
        sent = 0
        failed = 0
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
        if sent:
            self.message_user(
                request,
                f'Meeting invitation sent to {sent} recipient{"s" if sent != 1 else ""}.',
                level=messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f'Invitation email failed for {failed} recipient{"s" if failed != 1 else ""}. '
                'Check the SMTP configuration and Render application logs.',
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
    readonly_fields = ('id', 'created_at', 'updated_at')


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
