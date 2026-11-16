from django.contrib import admin

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
    readonly_fields = ('id', 'room_name', 'started_at', 'ended_at', 'created_at', 'updated_at')
    inlines = (MeetingParticipantInline, MeetingInvitationInline)
    date_hierarchy = 'scheduled_start'


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
