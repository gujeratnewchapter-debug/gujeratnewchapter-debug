from django.http import Http404
from rest_framework.permissions import BasePermission

from .services import is_enabled


def requires_flag(key):
    class FeatureFlagPermission(BasePermission):
        def has_permission(self, request, view):
            if not is_enabled(key):
                raise Http404
            return True

    FeatureFlagPermission.__name__ = f'RequiresFeatureFlag_{key.replace("-", "_")}'
    return FeatureFlagPermission
