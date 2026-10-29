import json
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from .admin import AdvertisementAdmin
from .models import Advertisement, AdvertisementEvent, SiteSettings


class AdvertisementApiTests(TestCase):
    def setUp(self):
        self.settings = SiteSettings.load()
        self.now = timezone.now()
        self.advertisement = Advertisement.objects.create(
            internal_name='Startup tools',
            advertiser_name='Startup Tools',
            content_type=Advertisement.ContentType.TEXT,
            headline='Build better',
            destination_url='https://example.org/',
            cta_label='Learn more',
            is_active=True,
            starts_at=self.now - timedelta(minutes=1),
            ends_at=self.now + timedelta(days=1),
        )

    def test_public_ads_respect_activation_schedule_and_route_targets(self):
        self.advertisement.target_routes = ['/courses/*']
        self.advertisement.save()

        self.assertEqual(self.client.get('/api/advertisements/?path=/courses/marketing/').status_code, 200)
        self.assertEqual(len(self.client.get('/api/advertisements/?path=/courses/marketing/').json()), 1)
        self.assertEqual(self.client.get('/api/advertisements/?path=/news/').json(), [])

        self.advertisement.starts_at = self.now + timedelta(days=1)
        self.advertisement.save()
        self.assertEqual(self.client.get('/api/advertisements/?path=/courses/marketing/').json(), [])

        self.advertisement.starts_at = None
        self.advertisement.ends_at = self.now - timedelta(seconds=1)
        self.advertisement.save()
        self.assertEqual(self.client.get('/api/advertisements/?path=/courses/marketing/').json(), [])

        self.advertisement.ends_at = None
        self.advertisement.is_active = False
        self.advertisement.save()
        self.assertEqual(self.client.get('/api/advertisements/?path=/courses/marketing/').json(), [])

    def test_global_switch_and_invalid_routes(self):
        self.settings.advertisements_enabled = False
        self.settings.save()
        self.assertEqual(self.client.get('/api/advertisements/?path=/').json(), [])
        self.settings.advertisements_enabled = True
        self.settings.save()

        response = self.client.get('/api/advertisements/?path=//example.org')
        self.assertEqual(response.status_code, 400)

    def test_public_event_endpoint_is_idempotent_and_does_not_store_visitor_data(self):
        payload = {
            'advertisement_id': self.advertisement.id,
            'event_type': AdvertisementEvent.EventType.IMPRESSION,
            'event_id': str(uuid.uuid4()),
        }
        response = self.client.post(
            '/api/advertisement-events/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'tracked': True})

        duplicate = self.client.post(
            '/api/advertisement-events/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json(), {'tracked': False})
        self.assertEqual(self.advertisement.events.count(), 1)
        event = self.advertisement.events.get()
        self.assertEqual(event.event_type, AdvertisementEvent.EventType.IMPRESSION)
        self.assertFalse(hasattr(event, 'ip_address'))

    def test_event_ids_cannot_be_reused_for_another_campaign_or_event_type(self):
        event_id = str(uuid.uuid4())
        payload = {
            'advertisement_id': self.advertisement.id,
            'event_type': AdvertisementEvent.EventType.IMPRESSION,
            'event_id': event_id,
        }
        self.client.post('/api/advertisement-events/', data=json.dumps(payload), content_type='application/json')
        payload['event_type'] = AdvertisementEvent.EventType.CLICK
        response = self.client.post('/api/advertisement-events/', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.advertisement.events.count(), 1)

    def test_click_events_are_included_in_campaign_statistics(self):
        response = self.client.post(
            '/api/advertisement-events/',
            data=json.dumps({
                'advertisement_id': self.advertisement.id,
                'event_type': AdvertisementEvent.EventType.CLICK,
                'event_id': str(uuid.uuid4()),
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.advertisement.events.filter(event_type=AdvertisementEvent.EventType.CLICK).count(),
            1,
        )

    def test_public_payload_contains_campaign_display_fields_only(self):
        response = self.client.get('/api/advertisements/?path=/')
        self.assertEqual(response.status_code, 200)
        advertisement = response.json()[0]
        self.assertEqual(advertisement['headline'], 'Build better')
        self.assertEqual(advertisement['close_countdown_seconds'], 4)
        self.assertEqual(advertisement['frequency'], Advertisement.Frequency.SESSION)
        self.assertNotIn('internal_name', advertisement)
        self.assertNotIn('priority', advertisement)

    def test_admin_requires_staff_and_campaign_preview_escapes_advertiser_copy(self):
        admin_url = f'/admin/site_settings/advertisement/{self.advertisement.pk}/change/'
        response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 302)

        user_model = get_user_model()
        staff_user = user_model.objects.create_superuser(
            username='ad-admin',
            email='ad-admin@example.org',
            password='strong-test-password',
        )
        self.client.force_login(staff_user)
        response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 200)

        self.advertisement.headline = '<script>alert(1)</script>'
        preview = AdvertisementAdmin(Advertisement, None).preview(self.advertisement)
        self.assertNotIn('<script>', str(preview))
        self.assertIn('&lt;script&gt;', str(preview))


class AdvertisementValidationTests(TestCase):
    def test_video_urls_are_limited_to_approved_https_providers(self):
        advertisement = Advertisement(
            internal_name='Video',
            content_type=Advertisement.ContentType.VIDEO,
            video_url='https://malicious.example/video',
        )
        with self.assertRaises(ValidationError) as error:
            advertisement.full_clean()
        self.assertIn('video_url', error.exception.message_dict)

        advertisement.video_url = 'javascript:alert(1)'
        with self.assertRaises(ValidationError):
            advertisement.full_clean()

    def test_campaign_dates_and_route_patterns_are_validated(self):
        advertisement = Advertisement(
            internal_name='Invalid routes',
            content_type=Advertisement.ContentType.TEXT,
            headline='Safe text',
            starts_at=timezone.now(),
            ends_at=timezone.now() - timedelta(seconds=1),
            target_routes=['//external.example'],
        )
        with self.assertRaises(ValidationError) as error:
            advertisement.full_clean()
        self.assertIn('ends_at', error.exception.message_dict)
        self.assertIn('target_routes', error.exception.message_dict)

    def test_image_video_and_mixed_content_require_matching_assets(self):
        for content_type in (
            Advertisement.ContentType.IMAGE,
            Advertisement.ContentType.VIDEO,
            Advertisement.ContentType.MIXED,
        ):
            advertisement = Advertisement(
                internal_name=f'Empty {content_type}',
                content_type=content_type,
            )
            with self.subTest(content_type=content_type), self.assertRaises(ValidationError):
                advertisement.full_clean()

    def test_video_upload_checks_file_signature(self):
        advertisement = Advertisement(
            internal_name='Spoofed video',
            content_type=Advertisement.ContentType.VIDEO,
            video_file=SimpleUploadedFile('not-a-video.mp4', b'not an MP4 file'),
        )
        with self.assertRaises(ValidationError) as error:
            advertisement.full_clean()
        self.assertIn('video_file', error.exception.message_dict)

        advertisement.video_file = SimpleUploadedFile(
            'valid-header.mp4',
            b'\x00\x00\x00\x18ftypisomfake-video-data',
        )
        advertisement.full_clean()
