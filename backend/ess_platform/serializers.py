from rest_framework import serializers
from .models import ServiceRequest, VisitorEvent, PlatformStat


class ServiceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = ['id', 'name', 'email', 'service', 'notes', 'status', 'assigned_to', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'assigned_to', 'created_at', 'updated_at']


class VisitorEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorEvent
        fields = ['path', 'session_key']


class PlatformStatSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(read_only=True)
    label = serializers.CharField(read_only=True)

    class Meta:
        model = PlatformStat
        fields = ['metric', 'label', 'translations', 'manual_value', 'is_enabled', 'order', 'value']