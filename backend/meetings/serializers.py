from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Meeting, MeetingParticipant, MeetingInvitation, MeetingSession, MeetingAttendance

User = get_user_model()


class MeetingParticipantSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = MeetingParticipant
        fields = ['id', 'user', 'user_name', 'role', 'joined_at', 'left_at', 'is_host', 'is_muted', 'is_camera_on']

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username


class MeetingInvitationSerializer(serializers.ModelSerializer):
    invited_user = serializers.PrimaryKeyRelatedField(read_only=True)
    invited_user_name = serializers.SerializerMethodField()

    class Meta:
        model = MeetingInvitation
        fields = ['id', 'meeting', 'invited_user', 'invited_user_name', 'status', 'created_at', 'updated_at']

    def get_invited_user_name(self, obj):
        return f"{obj.invited_user.first_name} {obj.invited_user.last_name}".strip() or obj.invited_user.username


class MeetingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingSession
        fields = ['id', 'meeting', 'started_at', 'ended_at', 'host_identity', 'room_name', 'notes']


class MeetingAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingAttendance
        fields = ['id', 'meeting', 'user', 'joined_at', 'left_at', 'duration_seconds']


class MeetingSerializer(serializers.ModelSerializer):
    host = serializers.PrimaryKeyRelatedField(read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True, allow_null=True)
    participants = serializers.SerializerMethodField()
    invitations = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            'id', 'course', 'course_title', 'title', 'description', 'kind', 'status', 'host',
            'room_name', 'scheduled_start', 'scheduled_end', 'started_at', 'ended_at',
            'created_at', 'updated_at', 'participants', 'invitations'
        ]
        read_only_fields = ['id', 'host', 'created_at', 'updated_at', 'status']

    def validate_course(self, course):
        request = self.context.get('request')
        if (
            course is not None
            and request is not None
            and not request.user.is_super_admin
            and course.instructor_id != request.user.id
        ):
            raise serializers.ValidationError('You can only schedule meetings for your own courses.')
        return course

    def get_participants(self, obj):
        request = self.context.get('request')
        participants = obj.participants.all()
        if request and request.user != obj.host and not request.user.is_super_admin:
            is_participant = participants.filter(user=request.user).exists()
            if not is_participant:
                return []
        return MeetingParticipantSerializer(participants, many=True, context=self.context).data

    def get_invitations(self, obj):
        request = self.context.get('request')
        invitations = obj.invitations.all()
        if request and request.user != obj.host and not request.user.is_super_admin:
            invitations = invitations.filter(invited_user=request.user)
        return MeetingInvitationSerializer(invitations, many=True, context=self.context).data
