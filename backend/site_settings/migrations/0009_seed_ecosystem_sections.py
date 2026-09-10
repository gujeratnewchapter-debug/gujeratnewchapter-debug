from django.db import migrations


def seed_ecosystem_sections(apps, schema_editor):
    PageContent = apps.get_model('site_settings', 'PageContent')
    PageSection = apps.get_model('site_settings', 'PageSection')
    page = PageContent.objects.get(slug='startup-ecosystem')

    sections = [
        ('dashboard', 'Explore the market', 'Ecosystem overview', {}),
        ('summary', 'Summary metrics', '', {
            'items': [
                ['Companies', '1,240', '+12% this year'],
                ['Funding rounds', '88', 'Tracked across Ethiopia'],
                ['Startup employees', '15.4k', 'Estimated ecosystem jobs'],
                ['Organizations', '417', 'Programs and partners'],
            ],
        }),
        ('categories', 'Ecosystem categories', '', {
            'items': [
                ['Startups', '1,240', 'Discover ventures by sector, stage, and location.'],
                ['Investors', '86', 'Connect capital providers with investable ventures.'],
                ['Mentors', '214', 'Find operators and experts ready to share experience.'],
                ['Incubators & accelerators', '38', 'Compare programs, cohorts, and application windows.'],
                ['Innovation hubs', '52', 'Explore communities, labs, and collaboration spaces.'],
                ['Universities & stakeholders', '67', 'Build bridges across research, talent, and public support.'],
            ],
        }),
    ]

    for order, (key, title, body, content) in enumerate(sections):
        PageSection.objects.get_or_create(
            page=page,
            key=key,
            defaults={'title': title, 'body': body, 'content': content, 'order': order},
        )


class Migration(migrations.Migration):
    dependencies = [('site_settings', '0008_optional_payment_details')]
    operations = [migrations.RunPython(seed_ecosystem_sections, migrations.RunPython.noop)]