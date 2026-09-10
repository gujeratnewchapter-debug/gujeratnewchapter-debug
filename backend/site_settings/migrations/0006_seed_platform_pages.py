from django.db import migrations


PAGES = [
    ('about-us', 'About Ethiopian Startup School', "A practical learning and venture-building platform for Ethiopia's next generation of founders, innovators, and business leaders."),
    ('analytics', 'Platform intelligence', 'A clear view of reach, learning activity, and the startup-support pipeline.'),
    ('ai-business-advisor', 'Ethiopia-focused AI Business Advisor', 'Turn a business question into a practical next step.'),
    ('business-consultant', 'Business Consultant', 'Request focused help from the Ethiopian Startup School network.'),
    ('startup-ecosystem', "Ethiopia's startup ecosystem", 'A structured directory for finding ventures, capital, expertise, programs, hubs, universities, and other stakeholders across Ethiopia.'),
    ('ethiopian-legal-business', 'Ethiopian Legal Business', 'A practical course map for starting, registering, and operating a business in Ethiopia.'),
]


def create_pages(apps, schema_editor):
    PageContent = apps.get_model('site_settings', 'PageContent')
    for slug, title, description in PAGES:
        PageContent.objects.get_or_create(slug=slug, defaults={'title': title, 'description': description})


class Migration(migrations.Migration):
    dependencies = [('site_settings', '0005_pagecontent')]
    operations = [migrations.RunPython(create_pages, migrations.RunPython.noop)]