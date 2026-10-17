from django.test import TestCase
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.views import APIView

from .models import FeatureFlag
from .permissions import requires_flag
from .services import CACHE_TTL_SECONDS, invalidate_flag_cache, is_enabled


class FeatureFlagPermissionTestView(APIView):
    permission_classes = [requires_flag('feature-flag-test')]

    def get(self, request):
        return Response({'ok': True})


class FeatureFlagServiceTests(TestCase):
    def setUp(self):
        invalidate_flag_cache()

    def tearDown(self):
        invalidate_flag_cache()

    def test_enabled_values_are_cached_until_expiry(self):
        flag = FeatureFlag.objects.create(key='test-cached', is_enabled=True)
        with self.assertNumQueries(1):
            self.assertTrue(is_enabled(flag.key))
            self.assertTrue(is_enabled(flag.key))

        flag.is_enabled = False
        flag.save(update_fields=('is_enabled',))

        self.assertFalse(is_enabled(flag.key))

    def test_cache_expires_after_thirty_seconds(self):
        flag = FeatureFlag.objects.create(key='test-expiry', is_enabled=True)
        from unittest.mock import patch

        with patch('feature_flags.services.monotonic', return_value=100):
            invalidate_flag_cache(flag.key)
            self.assertTrue(is_enabled(flag.key))
            self.assertEqual(CACHE_TTL_SECONDS, 30)
            FeatureFlag.objects.filter(pk=flag.pk).update(is_enabled=False)
        with patch('feature_flags.services.monotonic', return_value=100 + CACHE_TTL_SECONDS - 1):
            self.assertTrue(is_enabled(flag.key))
        with patch('feature_flags.services.monotonic', return_value=100 + CACHE_TTL_SECONDS + 1):
            self.assertFalse(is_enabled(flag.key))

    def test_missing_flags_are_disabled(self):
        self.assertFalse(is_enabled('not-seeded'))


class FeatureFlagEndpointTests(APITestCase):
    def test_public_endpoint_returns_seeded_flag_values(self):
        FeatureFlag.objects.create(key='visible-enabled', is_enabled=True)
        FeatureFlag.objects.create(key='visible-disabled', is_enabled=False)

        response = self.client.get(reverse('feature-flag-list'))

        self.assertEqual(response.status_code, 200)
        flags = response.data
        self.assertFalse(flags['visible-disabled'])
        self.assertTrue(flags['visible-enabled'])
        self.assertIn('email_center', flags)
        self.assertFalse(flags['email_center'])
        self.assertEqual(len(flags), 32)


class RequiresFlagTests(APITestCase):
    def setUp(self):
        invalidate_flag_cache()
        self.factory = APIRequestFactory()
        self.view = FeatureFlagPermissionTestView.as_view()

    def tearDown(self):
        invalidate_flag_cache()

    def test_disabled_flag_returns_not_found(self):
        FeatureFlag.objects.create(key='feature-flag-test', is_enabled=False)

        response = self.view(self.factory.get('/protected/'))

        self.assertEqual(response.status_code, 404)

    def test_enabled_flag_allows_request(self):
        FeatureFlag.objects.create(key='feature-flag-test', is_enabled=True)

        response = self.view(self.factory.get('/protected/'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'ok': True})
