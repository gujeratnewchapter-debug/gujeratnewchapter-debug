from django.urls import path

from .views import (
    SupportCallAdminActionView,
    SupportCallAdminDetailView,
    SupportCallAdminQueueView,
    SupportCallAdminSessionEndView,
    SupportCallAdminSessionTicketView,
    SupportCallAdminSessionTokenView,
    SupportCallAdminSessionView,
    SupportCallAdminTokenView,
    SupportCallRequestView,
    SupportCallStatusView,
    SupportCallTokenView,
)

urlpatterns = [
    path('requests/', SupportCallRequestView.as_view(), name='support-call-request'),
    path('status/', SupportCallStatusView.as_view(), name='support-call-status'),
    path('token/', SupportCallTokenView.as_view(), name='support-call-token'),
    path('admin/', SupportCallAdminQueueView.as_view(), name='support-call-admin-queue'),
    path('admin/<uuid:call_id>/', SupportCallAdminDetailView.as_view(), name='support-call-admin-detail'),
    path('admin/<uuid:call_id>/session-ticket/', SupportCallAdminSessionTicketView.as_view(), name='support-call-admin-session-ticket'),
    path('admin/<uuid:call_id>/token/', SupportCallAdminTokenView.as_view(), name='support-call-admin-token'),
    path('admin/<uuid:call_id>/<str:action>/', SupportCallAdminActionView.as_view(), name='support-call-admin-action'),
    path('admin-session/<uuid:call_id>/status/', SupportCallAdminSessionView.as_view(), name='support-call-admin-session-status'),
    path('admin-session/<uuid:call_id>/token/', SupportCallAdminSessionTokenView.as_view(), name='support-call-admin-session-token'),
    path('admin-session/<uuid:call_id>/end/', SupportCallAdminSessionEndView.as_view(), name='support-call-admin-session-end'),
]
