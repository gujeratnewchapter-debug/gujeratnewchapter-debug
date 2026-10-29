from django.urls import path
from .views import (
    AdvertisementEventView,
    AdvertisementListView,
    SiteSettingsView,
    ContactMessageView,
    PageContentView,
)

urlpatterns = [
    path('advertisements/', AdvertisementListView.as_view(), name='advertisements'),
    path('advertisement-events/', AdvertisementEventView.as_view(), name='advertisement-events'),
    path('site-settings/', SiteSettingsView.as_view(), name='site-settings'),
    path('contact/', ContactMessageView.as_view(), name='contact'),
    path('page-content/<slug:slug>/', PageContentView.as_view(), name='page-content'),
]
