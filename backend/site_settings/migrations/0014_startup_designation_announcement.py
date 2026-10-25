from django.db import migrations, models


def seed_startup_designation_announcement(apps, schema_editor):
    PageContent = apps.get_model('site_settings', 'PageContent')
    PageSection = apps.get_model('site_settings', 'PageSection')
    page, _ = PageContent.objects.get_or_create(
        slug='home',
        defaults={
            'title': 'Ethiopian Startup School',
            'description': 'Learn entrepreneurship, AI, and business skills with practical guidance.',
            'is_published': True,
        },
    )
    PageSection.objects.get_or_create(
        page=page,
        key='startup_designation_announcement',
        defaults={
            'title': 'Startup Designation Registration Is Now Open!',
            'body': (
                'Startups and startup ecosystem builders can now apply for official designation through '
                'Ethiopia’s digital startup platform. Designation is required to access the incentives and '
                'support provided under Ethiopia’s Startup Proclamation No. 1396/2025. Complete the '
                'application form and submit the required supporting documents at startupethiopia.et.'
            ),
            'cta_url': 'https://startupethiopia.et/',
            'cta_label': 'Complete the application',
            'order': 3,
            'is_published': True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [('site_settings', '0013_split_legacy_sign_in_steps')]

    operations = [
        migrations.AddField(
            model_name='pagesection',
            name='cta_url',
            field=models.URLField(
                'CTA URL',
                blank=True,
                help_text='External destination used by a homepage section call to action.',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='pagesection',
            name='cta_label',
            field=models.CharField(
                'CTA label',
                blank=True,
                help_text='Visible link text for the section call to action.',
                max_length=100,
            ),
        ),
        migrations.RunPython(
            seed_startup_designation_announcement,
            migrations.RunPython.noop,
        ),
    ]
