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
