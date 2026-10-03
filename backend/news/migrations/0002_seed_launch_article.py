from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import migrations
from django.utils import timezone


ARTICLE_SLUG = 'ethiopian-startup-school-officially-launched-for-testing'
IMAGE_NAME = 'news/ethiopian-startup-school-launch.png'


def seed_launch_article(apps, schema_editor):
    Article = apps.get_model('news', 'Article')
    image_path = Path(__file__).resolve().parent.parent / 'seed_assets' / 'launch-workshop.png'
    if not default_storage.exists(IMAGE_NAME):
        with image_path.open('rb') as image_file:
            default_storage.save(IMAGE_NAME, ContentFile(image_file.read()))

    article, created = Article.objects.get_or_create(
        slug=ARTICLE_SLUG,
        defaults={
            'title': 'Ethiopian Startup School Officially Launched for Testing',
            'short_description': (
                'Ethiopian Startup School has officially been launched for testing. The platform is '
                'designed to provide practical startup education, entrepreneurship training, and '
                'resources to help aspiring entrepreneurs develop their business ideas and build '
                'successful startups.'
            ),
            'content': (
                'Ethiopian Startup School has officially been launched for testing. The platform is '
                'designed to provide practical startup education, entrepreneurship training, and '
                'resources to help aspiring entrepreneurs develop their business ideas and build '
                'successful startups.\n\n'
                'This launch announcement introduces the school’s focus on practical learning for '
                'people developing startup ideas.'
            ),
            'featured_image': IMAGE_NAME,
            'image_alt_text': (
                'Ethiopian founders sharing ideas around a laptop in a startup learning workshop'
            ),
            'category': 'Startup',
            'author': 'Ethiopian Startup School',
            'published_at': timezone.now(),
            'is_published': True,
            'is_featured': True,
        },
    )
    if not created and (
        not article.featured_image
        or not default_storage.exists(article.featured_image.name)
    ):
        Article.objects.filter(pk=article.pk).update(featured_image=IMAGE_NAME)


class Migration(migrations.Migration):
    dependencies = [
        ('news', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_launch_article, migrations.RunPython.noop),
    ]
