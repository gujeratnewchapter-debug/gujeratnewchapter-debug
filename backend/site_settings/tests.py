from django.test import TestCase

from .models import SiteSettings
from .serializers import SiteSettingsSerializer


class SiteSettingsSerializerTests(TestCase):
    def test_serializer_exposes_admin_editable_social_and_hero_fields(self):
        settings = SiteSettings.load()
        settings.hero_title = 'Build your next idea'
        settings.hero_subtitle = 'Learn, launch, and grow with AI-powered coaching.'
        settings.hero_cta_label = 'Start learning'
        settings.hero_cta_url = '/courses'
        settings.social_links = [
            {'platform': 'linkedin', 'url': 'https://linkedin.com/company/example'},
            {'platform': 'instagram', 'url': 'https://instagram.com/example'},
        ]
        settings.save()

        data = SiteSettingsSerializer(settings).data

        self.assertEqual(data['hero_title'], 'Build your next idea')
        self.assertEqual(data['hero_subtitle'], 'Learn, launch, and grow with AI-powered coaching.')
        self.assertEqual(data['hero_cta_label'], 'Start learning')
        self.assertEqual(data['hero_cta_url'], '/courses')
        self.assertEqual(data['social_links'][0]['platform'], 'linkedin')
        self.assertEqual(data['social_links'][1]['url'], 'https://instagram.com/example')

    def test_hero_images_are_serialized(self):
        settings = SiteSettings.load()
        settings.save()
        settings.hero_images.create(image='hero/test-1.jpg', order=0)
        settings.hero_images.create(image='hero/test-2.jpg', order=1)

        data = SiteSettingsSerializer(settings).data

        self.assertEqual(len(data['hero_images']), 2)
        self.assertTrue(data['hero_images'][0]['image'].endswith('/media/hero/test-1.jpg'))
        self.assertTrue(data['hero_images'][1]['image'].endswith('/media/hero/test-2.jpg'))
