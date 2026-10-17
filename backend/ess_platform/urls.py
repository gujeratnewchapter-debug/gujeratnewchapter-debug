from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceRequestViewSet,
    StartupMilestoneViewSet,
    StartupProjectViewSet,
    analytics_summary,
    platform_stats,
    record_visitor,
)

router = DefaultRouter()
router.register('service-requests', ServiceRequestViewSet, basename='service-request')
router.register('startup-projects', StartupProjectViewSet, basename='startup-project')
router.register('startup-milestones', StartupMilestoneViewSet, basename='startup-milestone')
urlpatterns = router.urls + [path('visitor-events/', record_visitor), path('analytics/summary/', analytics_summary), path('stats/', platform_stats)]