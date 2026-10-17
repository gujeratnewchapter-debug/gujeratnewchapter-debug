from datetime import timedelta
from pathlib import Path
from shutil import rmtree

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Article, Notice


User = get_user_model()
TEST_MEDIA_ROOT = Path(__file__).resolve().parent / '.test-media'
PNG_IMAGE = (Path(__file__).resolve().parent / 'seed_assets' / 'launch-workshop.png').read_bytes()


class ArticleApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='news-editor', email='editor@example.com', password='Password123!',
            is_staff=True,
        )
        cls.student = User.objects.create_user(
            username='news-reader', email='reader@example.com', password='Password123!',
        )
        cls.older = Article.objects.create(
            title='First update',
            short_description='An earlier update.',
            content='First paragraph.\n\nSecond paragraph.',
            featured_image='news/seed.png',
            image_alt_text='Founders at a workshop',
            category='Startup',
            author='Ethiopian Startup School',
            is_published=True,
            is_featured=False,
        )
        cls.newer = Article.objects.create(
            title='Second update',
            short_description='A newer update.',
            content='New article.',
            featured_image='news/seed.png',
            image_alt_text='Learners collaborating',
            category='Learning',
            published_at=cls.older.published_at + timedelta(days=365),
            is_published=True,
            is_featured=False,
        )
        cls.draft = Article.objects.create(
            title='Unpublished draft',
            short_description='Not public.',
            content='Internal draft.',
            featured_image='news/seed.png',
            image_alt_text='Draft',
            category='Startup',
            is_published=False,
        )

    def setUp(self):
        self.client = APIClient()

    def tearDown(self):
        rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def test_migration_seeds_launch_story_and_storage_image(self):
        article = Article.objects.get(slug='ethiopian-startup-school-officially-launched-for-testing')

        self.assertTrue(article.is_published)
        self.assertTrue(article.is_featured)
        self.assertEqual(article.category, 'Startup')
        self.assertEqual(article.author, 'Ethiopian Startup School')
        self.assertTrue(article.featured_image.storage.exists(article.featured_image.name))
        image_response = self.client.get(f'/media/{article.featured_image.name}')
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response['Content-Type'], 'image/png')

    def test_public_list_is_published_and_newest_first(self):
        response = self.client.get(reverse('news-article-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['slug'] for item in response.json()],
            [self.newer.slug, self.older.slug, 'ethiopian-startup-school-officially-launched-for-testing'],
        )

    def test_featured_list_excludes_unfeatured_published_articles_and_drafts(self):
        default_response = self.client.get(reverse('news-article-list'))
        featured_response = self.client.get(reverse('news-article-list'), {'featured': 'true'})
        featured_articles = Article.objects.filter(is_published=True, is_featured=True)

        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(
            {item['slug'] for item in default_response.json()},
            {self.newer.slug, self.older.slug, 'ethiopian-startup-school-officially-launched-for-testing'},
        )
        self.assertEqual(featured_response.status_code, 200)
        self.assertEqual(
            [item['slug'] for item in featured_response.json()],
            list(featured_articles.order_by('-published_at', '-created_at').values_list('slug', flat=True)),
        )
        self.assertEqual(
            [item['slug'] for item in featured_response.json()],
            ['ethiopian-startup-school-officially-launched-for-testing'],
        )

    def test_public_detail_resolves_by_slug_and_excludes_drafts(self):
        response = self.client.get(reverse('news-article-detail', args=[self.older.slug]))
        hidden = self.client.get(reverse('news-article-detail', args=[self.draft.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['content'], 'First paragraph.\n\nSecond paragraph.')
        self.assertEqual(hidden.status_code, 404)

    def test_public_writes_are_denied(self):
        response = self.client.post(reverse('news-article-list'), {}, format='json')

        self.assertIn(response.status_code, (401, 403))

    @override_settings(
        MEDIA_ROOT=TEST_MEDIA_ROOT,
        STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        },
    )
    def test_staff_can_create_upload_publish_update_and_delete(self):
        self.client.force_authenticate(self.staff)
        upload = SimpleUploadedFile('startup-workshop.png', PNG_IMAGE, content_type='image/png')
        response = self.client.post(reverse('news-article-list'), {
            'title': 'New launch',
            'short_description': 'A practical update.',
            'content': 'Launch details.',
            'featured_image': upload,
            'image_alt_text': 'Founders learning together',
            'category': 'Startup',
            'author': 'Ethiopian Startup School',
            'is_published': 'true',
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()['featured_image'].startswith('http'))
        article = Article.objects.get(slug='new-launch')
        self.assertIsNotNone(article.published_at)
        self.assertTrue(article.is_featured)
        self.assertTrue(article.featured_image.storage.exists(article.featured_image.name))
        with article.featured_image.open('rb') as stored_image:
            self.assertEqual(stored_image.read(), PNG_IMAGE)
        featured_response = self.client.get(reverse('news-article-list'), {'featured': 'true'})
        self.assertIn(article.slug, [item['slug'] for item in featured_response.json()])

        detail_url = reverse('news-article-detail', args=[article.slug])
        update = self.client.patch(detail_url, {'is_published': False}, format='json')
        self.assertEqual(update.status_code, 200, update.content)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(detail_url).status_code, 404)

        self.client.force_authenticate(self.staff)
        deleted = self.client.delete(detail_url)
        self.assertEqual(deleted.status_code, 204)

    def test_non_staff_cannot_write(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(reverse('news-article-list'), {}, format='json')

        self.assertEqual(response.status_code, 403)


class NoticeApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='notice-editor', email='notice-editor@example.com', password='Password123!',
            is_staff=True,
        )
        cls.student = User.objects.create_user(
            username='notice-reader', email='notice-reader@example.com', password='Password123!',
        )
        cls.older = Notice.objects.create(
            title='Earlier notice',
            body='An earlier public update.',
            is_published=True,
        )
        cls.newer = Notice.objects.create(
            title='Latest notice',
            body='The latest public update.',
            is_published=True,
        )
        cls.draft = Notice.objects.create(
            title='Internal draft',
            body='This notice is not ready to publish.',
            is_published=False,
        )
        Notice.objects.filter(pk=cls.older.pk).update(created_at=cls.older.created_at - timedelta(days=1))

    def setUp(self):
        self.client = APIClient()

    def test_public_list_contains_only_published_notices_newest_first(self):
        response = self.client.get(reverse('news-notice-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['slug'] for item in response.json()],
            [self.newer.slug, self.older.slug],
        )

    def test_public_detail_hides_drafts(self):
        published = self.client.get(reverse('news-notice-detail', args=[self.newer.slug]))
        draft = self.client.get(reverse('news-notice-detail', args=[self.draft.slug]))

        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.json()['body'], self.newer.body)
        self.assertEqual(draft.status_code, 404)

    def test_anonymous_and_non_staff_cannot_write_notices(self):
        anonymous_response = self.client.post(
            reverse('news-notice-list'),
            {'title': 'Unauthorized notice', 'body': 'No write access.'},
            format='json',
        )
        self.assertIn(anonymous_response.status_code, (401, 403))

        self.client.force_authenticate(self.student)
        student_response = self.client.post(
            reverse('news-notice-list'),
            {'title': 'Unauthorized notice', 'body': 'No write access.'},
            format='json',
        )
        self.assertEqual(student_response.status_code, 403)

        detail_url = reverse('news-notice-detail', args=[self.newer.slug])
        self.assertEqual(self.client.patch(detail_url, {'is_published': False}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(detail_url).status_code, 403)

    def test_staff_can_create_publish_update_and_delete_notices(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            reverse('news-notice-list'),
            {'title': 'New public notice', 'body': 'Registration opens next week.', 'is_published': True},
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        notice = Notice.objects.get(slug='new-public-notice')
        detail_url = reverse('news-notice-detail', args=[notice.slug])

        self.assertTrue(notice.is_published)
        self.assertEqual(response.data['slug'], notice.slug)
        self.assertEqual(self.client.patch(detail_url, {'is_published': False}, format='json').status_code, 200)
        self.assertEqual(self.client.delete(detail_url).status_code, 204)

    def test_staff_can_read_unpublished_notices(self):
        self.client.force_authenticate(self.staff)

        response = self.client.get(reverse('news-notice-detail', args=[self.draft.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_published'])
