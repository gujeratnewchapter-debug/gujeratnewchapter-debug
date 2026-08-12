from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Conversation, Message, KnowledgeDocument
from .serializers import (
    ConversationSerializer, ConversationListSerializer, SendMessageSerializer,
    MessageSerializer, KnowledgeDocumentSerializer,
)
from .services import get_ai_reply


class ConversationViewSet(viewsets.ModelViewSet):
    """AI Tutor / Mentor / Coach chat threads (RFP section 9)."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(student=self.request.user).order_by('-updated_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_content = serializer.validated_data['content']

        Message.objects.create(conversation=conversation, role=Message.Role.USER, content=user_content)

        history = [
            {"role": m.role, "content": m.content}
            for m in conversation.messages.order_by('created_at')[:20]
        ]
        reply_text, sources = get_ai_reply(
            conversation.mode, history, user_content, course=conversation.course,
        )

        assistant_msg = Message.objects.create(
            conversation=conversation, role=Message.Role.ASSISTANT, content=reply_text, sources=sources,
        )
        conversation.save()  # bumps updated_at
        return Response(MessageSerializer(assistant_msg).data)


class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    """Instructor/admin-managed RAG knowledge base (RFP section 10)."""
    queryset = KnowledgeDocument.objects.all()
    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not (self.request.user.is_instructor or self.request.user.is_super_admin):
            qs = qs.none()
        return qs

    def perform_create(self, serializer):
        doc = serializer.save()
        # In production: enqueue a Celery task to chunk + embed doc.raw_text/file
        # into the vector store, then flip is_indexed=True.
        if doc.raw_text:
            doc.is_indexed = True
            doc.save()
