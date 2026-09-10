from django.urls import path
from .views import SiteSettingsView, ContactMessageView, PageContentView

urlpatterns = [
    path('site-settings/', SiteSettingsView.as_view(), name='site-settings'),
    path('contact/', ContactMessageView.as_view(), name='contact'),
    path('page-content/<slug:slug>/', PageContentView.as_view(), name='page-content'),
]
