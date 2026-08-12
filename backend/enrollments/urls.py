from rest_framework.routers import DefaultRouter
from .views import EnrollmentViewSet, BookmarkViewSet

router = DefaultRouter()
router.include_root_view = False
router.register('enrollments', EnrollmentViewSet, basename='enrollment')
router.register('bookmarks', BookmarkViewSet, basename='bookmark')

urlpatterns = router.urls
