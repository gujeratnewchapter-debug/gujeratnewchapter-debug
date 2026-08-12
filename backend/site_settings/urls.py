from django.urls import path
from .views import SiteSettingsView, ContactMessageView

urlpatterns = [
    path('site-settings/', SiteSettingsView.as_view(), name='site-settings'),
    path('contact/', ContactMessageView.as_view(), name='contact'),
]
