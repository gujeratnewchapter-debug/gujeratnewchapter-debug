from django.urls import path

from .views import FeatureFlagListView


urlpatterns = [
    path('feature-flags/', FeatureFlagListView.as_view(), name='feature-flag-list'),
]
