from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from .admin import PageContentAdmin, PageSectionInline
from .models import PageContent, PageSection, SiteSettings
from .serializers import SiteSettingsSerializer


class PageContentAdminTests(TestCase):
    def test_page_sections_remain_inline_editable_with_json_content(self):
        self.assertIn(PageSectionInline, PageContentAdmin.inlines)
        self.assertIn('content', PageSectionInline.fields)

    def test_home_sign_in_guide_cms_content_is_exposed_in_public_page_payload(self):
        page = PageContent.objects.get(slug='home')
        content = {
            'en': {
                'account_setup_title': 'Your account',
                'learning_title': 'Your learning',
                'account_setup_steps': [{'title': f'Account {i}', 'desc': f'Account detail {i}'} for i in range(1, 8)],
                'learning_steps': [{'title': f'Learning {i}', 'desc': f'Learning detail {i}'} for i in range(1, 7)],
            },
        }
        PageSection.objects.update_or_create(
            page=page,
            key='sign-in-process',
            defaults={'title': 'Sign in and get started', 'content': content},
        )

        response = self.client.get('/api/page-content/home/')
        payload = response.json()
        section = next(item for item in payload['sections'] if item['key'] == 'sign-in-process')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(section['content'], content)
        self.assertEqual(section['content']['en']['account_setup_title'], 'Your account')
        self.assertEqual(section['content']['en']['learning_title'], 'Your learning')
        self.assertEqual(len(section['content']['en']['account_setup_steps']), 7)
        self.assertEqual(len(section['content']['en']['learning_steps']), 6)


class SiteSettingsSerializerTests(TestCase):
    def test_payment_details_are_optional(self):
        settings = SiteSettings.load()
        settings.bank_name = ''
        settings.bank_account_name = ''
        settings.bank_account_number = ''
        settings.telebirr_number = ''
        settings.save()

        data = SiteSettingsSerializer(settings).data

        self.assertEqual(data['bank_name'], '')
        self.assertEqual(data['bank_account_name'], '')
        self.assertEqual(data['bank_account_number'], '')
        self.assertEqual(data['telebirr_number'], '')

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


class SignInProcessMigrationTests(TransactionTestCase):
    migrate_from = ('site_settings', '0011_generalize_advisor_page_copy')
    migrate_to = ('site_settings', '0012_seed_sign_in_process')

    def migrate_to_target(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def setUp(self):
        super().setUp()
        apps = self.migrate_to_target(self.migrate_from)
        PageContent = apps.get_model('site_settings', 'PageContent')
        self.PageSection = apps.get_model('site_settings', 'PageSection')
        self.home, _ = PageContent.objects.get_or_create(
            slug='home',
            defaults={
                'title': 'Ethiopian Startup School',
                'description': 'Learn entrepreneurship, AI, and business skills with practical guidance.',
            },
        )

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_migration_creates_sign_in_process_with_seven_and_six_steps(self):
        apps = self.migrate_to_target(self.migrate_to)
        PageSection = apps.get_model('site_settings', 'PageSection')

        section = PageSection.objects.get(page__slug='home', key='sign-in-process')

        self.assertEqual(section.content['en']['account_setup_title'], 'Set up your account')
        self.assertEqual(section.content['en']['learning_title'], 'Start learning')
        self.assertEqual(len(section.content['en']['account_setup_steps']), 7)
        self.assertEqual(len(section.content['en']['learning_steps']), 6)

    def test_migration_preserves_existing_admin_edited_section(self):
        content = {
            'en': {
                'account_setup_steps': [{'title': 'Admin title', 'desc': 'Admin description'}],
                'learning_steps': [],
            },
            'am': {'account_setup_steps': [], 'learning_steps': []},
        }
        self.PageSection.objects.create(
            page=self.home,
            key='sign-in-process',
            title='Admin heading',
            body='Admin body',
            content=content,
            order=27,
            is_published=False,
        )

        apps = self.migrate_to_target(self.migrate_to)
        PageSection = apps.get_model('site_settings', 'PageSection')
        section = PageSection.objects.get(page__slug='home', key='sign-in-process')

        self.assertEqual(section.title, 'Admin heading')
        self.assertEqual(section.body, 'Admin body')
        self.assertEqual(section.content, content)
        self.assertEqual(section.order, 27)
        self.assertFalse(section.is_published)
