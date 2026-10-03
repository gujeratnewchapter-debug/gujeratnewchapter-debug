from rest_framework import serializers, viewsets, permissions
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from django.db import transaction
from .models import Conversation, Message, KnowledgeDocument
from .serializers import (
    ConversationSerializer, ConversationListSerializer, SendMessageSerializer,
    MessageSerializer, KnowledgeDocumentSerializer, BusinessAdvisorQuestionSerializer,
)
from .services import AIServiceUnavailable, get_ai_reply


class AIServiceUnavailableResponse(APIException):
    status_code = 503
    default_detail = 'The AI service is temporarily unavailable. Please try again shortly.'
    default_code = 'service_unavailable'


class BusinessAdvisorThrottle(SimpleRateThrottle):
    scope = 'business_advisor'
    rate = '10/min'

    def get_rate(self):
        return self.rate

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


@api_view(['POST'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([BusinessAdvisorThrottle])
def business_advisor(request):
    serializer = BusinessAdvisorQuestionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        reply_text, sources = get_ai_reply(
            Conversation.Mode.COACH,
            [],
            serializer.validated_data['question'],
        )
    except AIServiceUnavailable as error:
        raise AIServiceUnavailableResponse(str(error)) from error

    return Response({'content': reply_text, 'sources': sources})


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

        history = [
            {"role": m.role, "content": m.content}
            for m in conversation.messages.order_by('created_at')[:20]
        ]
        try:
            reply_text, sources = get_ai_reply(
                conversation.mode, history, user_content, course=conversation.course,
            )
        except AIServiceUnavailable as error:
            raise AIServiceUnavailableResponse(str(error)) from error

        with transaction.atomic():
            Message.objects.create(conversation=conversation, role=Message.Role.USER, content=user_content)
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
        if self.request.user.is_super_admin:
            return qs
        if self.request.user.is_instructor:
            return qs.filter(course__instructor=self.request.user)
        if not (self.request.user.is_instructor or self.request.user.is_super_admin):
            qs = qs.none()
        return qs

    def perform_create(self, serializer):
        if not (self.request.user.is_instructor or self.request.user.is_super_admin):
            raise PermissionDenied('Instructor or admin access required.')
        doc = serializer.save()
        # In production: enqueue a Celery task to chunk + embed doc.raw_text/file
        # into the vector store, then flip is_indexed=True.
        if doc.raw_text:
            doc.is_indexed = True
            doc.save()
