from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, KnowledgeDocumentViewSet

router = DefaultRouter()
router.include_root_view = False
router.register('conversations', ConversationViewSet, basename='conversation')
router.register('knowledge-documents', KnowledgeDocumentViewSet, basename='knowledge-document')

urlpatterns = router.urls
