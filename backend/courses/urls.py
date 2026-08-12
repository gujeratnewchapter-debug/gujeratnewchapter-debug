from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import CategoryViewSet, CourseViewSet, SectionViewSet, LessonViewSet, GlobalSearchView

router = DefaultRouter()
router.include_root_view = False
router.register('categories', CategoryViewSet, basename='category')
router.register('courses', CourseViewSet, basename='course')
router.register('sections', SectionViewSet, basename='section')
router.register('lessons', LessonViewSet, basename='lesson')

urlpatterns = [
    path('search/', GlobalSearchView.as_view(), name='global-search'),
] + router.urls
