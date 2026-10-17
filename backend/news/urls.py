from rest_framework.routers import DefaultRouter

from .views import ArticleViewSet, NoticeViewSet


router = DefaultRouter()
router.include_root_view = False
router.register('news', ArticleViewSet, basename='news-article')
router.register('notices', NoticeViewSet, basename='news-notice')

urlpatterns = router.urls
