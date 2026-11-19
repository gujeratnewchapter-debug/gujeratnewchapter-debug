from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html

from .models import SupportCallRequest


@admin.register(SupportCallRequest)
class SupportCallRequestAdmin(admin.ModelAdmin):
    list_display = (
        'display_name',
        'direction',
        'recipient',
        'mode',
        'status',
        'created_at',
        'expires_at',
        'open_support_queue',
    )
    list_filter = ('status', 'mode', 'created_at')
    search_fields = ('display_name', 'email', 'question')
    ordering = ('-created_at',)
    readonly_fields = (
        'requester',
        'recipient',
        'direction',
        'mode',
        'status',
        'room_name',
        'handled_by',
        'created_at',
        'accepted_at',
        'ended_at',
        'expires_at',
        'updated_at',
    )
    fields = (
        'requester',
        'recipient',
        'direction',
        'display_name',
        'email',
        'question',
        'mode',
        'status',
        'room_name',
        'handled_by',
        'created_at',
        'accepted_at',
        'ended_at',
        'expires_at',
        'updated_at',
    )

    @admin.display(description='Live response')
    def open_support_queue(self, _call):
        url = f'{settings.FRONTEND_BASE_URL.rstrip("/")}/admin/support-calls'
        return format_html('<a href="{}" target="_blank" rel="noopener">Open support queue</a>', url)

    def has_add_permission(self, request):
        return False
