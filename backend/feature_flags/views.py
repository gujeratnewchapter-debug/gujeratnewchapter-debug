from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FeatureFlag


class FeatureFlagListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        flags = FeatureFlag.objects.values_list('key', 'is_enabled')
        return Response(dict(flags))
