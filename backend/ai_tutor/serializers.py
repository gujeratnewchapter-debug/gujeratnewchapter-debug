from rest_framework import serializers
from .models import Conversation, Message, KnowledgeDocument


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'sources', 'created_at']
        read_only_fields = ['id', 'sources', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'course', 'mode', 'title', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_course(self, course):
        if course is None:
            return course
        request = self.context.get('request')
        user = request.user if request else None
        if not user or not user.is_authenticated:
            raise serializers.ValidationError('Authentication is required for course conversations.')
        if user.is_super_admin or (user.is_instructor and course.instructor_id == user.id):
            return course
        from enrollments.models import Enrollment
        if course.status != course.Status.PUBLISHED or not Enrollment.objects.filter(student=user, course=course).exists():
            raise serializers.ValidationError('Enroll in this published course before starting a conversation.')
        return course


class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'course', 'mode', 'title', 'last_message', 'updated_at']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        return msg.content[:120] if msg else ''


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField()


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeDocument
        fields = ['id', 'title', 'source_type', 'course', 'file', 'raw_text', 'version', 'is_indexed', 'uploaded_at']
        read_only_fields = ['id', 'is_indexed', 'uploaded_at']

    def validate_course(self, course):
        if course is None:
            return course
        request = self.context.get('request')
        user = request.user if request else None
        if user and (user.is_super_admin or course.instructor_id == user.id):
            return course
        raise serializers.ValidationError('You can only attach documents to your own courses.')
