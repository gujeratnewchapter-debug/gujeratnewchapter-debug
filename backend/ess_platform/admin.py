from django.contrib import admin
from .models import ServiceRequest, VisitorEvent, PlatformStat


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('service', 'requester', 'status', 'assigned_to', 'created_at')
    list_filter = ('status', 'service')
    search_fields = ('name', 'email', 'service', 'notes')


@admin.register(VisitorEvent)
class VisitorEventAdmin(admin.ModelAdmin):
    list_display = ('path', 'session_key', 'created_at')
    list_filter = ('path', 'created_at')


@admin.register(PlatformStat)
class PlatformStatAdmin(admin.ModelAdmin):
    list_display = ('label', 'metric', 'manual_value', 'is_enabled', 'order')
    list_filter = ('is_enabled', 'metric')
    ordering = ('order',)