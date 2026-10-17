from rest_framework import serializers
from .models import ServiceRequest, StartupMilestone, StartupProject, VisitorEvent, PlatformStat


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


class StartupMilestoneSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(queryset=StartupProject.objects.all())

    class Meta:
        model = StartupMilestone
        fields = ['id', 'project', 'title', 'details', 'due_date', 'status', 'order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_project(self, project):
        request = self.context.get('request')
        if request is None or project.owner_id != request.user.id:
            raise serializers.ValidationError('Choose one of your own startup projects.')
        if self.instance is not None and self.instance.project_id != project.id:
            raise serializers.ValidationError('A milestone cannot be moved to another project.')
        return project


class StartupProjectSerializer(serializers.ModelSerializer):
    owner = serializers.IntegerField(source='owner_id', read_only=True)
    milestones = StartupMilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = StartupProject
        fields = [
            'id', 'owner', 'title', 'description', 'industry', 'stage', 'status', 'problem',
            'solution', 'target_market', 'value_proposition', 'business_model', 'next_steps',
            'milestones', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'milestones', 'created_at', 'updated_at']