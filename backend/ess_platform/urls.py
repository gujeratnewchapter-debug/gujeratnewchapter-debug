from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ServiceRequestViewSet, analytics_summary, platform_stats, record_visitor

router = DefaultRouter()
router.register('service-requests', ServiceRequestViewSet, basename='service-request')
urlpatterns = router.urls + [path('visitor-events/', record_visitor), path('analytics/summary/', analytics_summary), path('stats/', platform_stats)]