from django.db import migrations


def generalize_advisor_page_copy(apps, schema_editor):
    PageContent = apps.get_model('site_settings', 'PageContent')
    PageContent.objects.filter(
        slug='ai-business-advisor',
        title='Ethiopia-focused AI Business Advisor',
    ).update(title='AI Startup & Business Advisor')
    PageContent.objects.filter(
        slug='ai-business-advisor',
        description='Turn a business question into a practical next step.',
    ).update(
        description=(
            'Ask about startup ideas, customers, markets, products, pricing, operations, '
            'funding, marketing, growth, and related business questions.'
        )
    )


class Migration(migrations.Migration):
    dependencies = [('site_settings', '0010_seed_home_sections')]

    operations = [
        migrations.RunPython(generalize_advisor_page_copy, migrations.RunPython.noop),
    ]
