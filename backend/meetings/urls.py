from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MeetingInvitationViewSet, MeetingParticipantViewSet, MeetingTokenView, MeetingViewSet

router = DefaultRouter()
router.register(r'meetings', MeetingViewSet, basename='meeting')
router.register(r'meeting-invitations', MeetingInvitationViewSet, basename='meeting-invitation')
router.register(r'meeting-participants', MeetingParticipantViewSet, basename='meeting-participant')

urlpatterns = [
    path('meetings/<uuid:meeting_id>/token/', MeetingTokenView.as_view(), name='meeting-token'),
] + router.urls
