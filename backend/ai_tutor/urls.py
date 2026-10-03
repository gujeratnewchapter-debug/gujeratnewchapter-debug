from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import business_advisor, ConversationViewSet, KnowledgeDocumentViewSet

router = DefaultRouter()
router.include_root_view = False
router.register('conversations', ConversationViewSet, basename='conversation')
router.register('knowledge-documents', KnowledgeDocumentViewSet, basename='knowledge-document')

urlpatterns = [
    path('advisor/', business_advisor, name='business-advisor'),
    *router.urls,
]
