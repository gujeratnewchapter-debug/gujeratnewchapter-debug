from django.db import migrations


def seed_home_sections(apps, schema_editor):
    PageContent = apps.get_model('site_settings', 'PageContent')
    PageSection = apps.get_model('site_settings', 'PageSection')
    page, _ = PageContent.objects.get_or_create(
        slug='home',
        defaults={
            'title': 'Ethiopian Startup School',
            'description': 'Learn entrepreneurship, AI, and business skills with practical guidance.',
        },
    )
    sections = [
        ('ai-showcase', 'Three AI companions, one goal', 'Every course comes with an AI assistant that switches roles depending on what you need.', {
            'items': [
                ['AI Tutor', 'Explains concepts, summarizes lessons, and drills you with practice quizzes whenever you are stuck.', 'tutor'],
                ['AI Startup Mentor', 'Ask about fundraising, market research, MVPs, and the lean-startup playbook.', 'mentor'],
                ['AI Business Coach', 'Build business plans, SWOT analyses, and financial projections step by step.', 'coach'],
            ],
        }),
        ('how-it-works', 'How it works', '', {
            'items': [
                ['Enroll in a course', 'Pick a path in entrepreneurship, AI, finance, marketing, or leadership.'],
                ['Learn with AI at every step', 'Watch, read, and ask your AI Tutor questions when something does not click.'],
                ['Pass to unlock, then get certified', 'Clear each quiz to move forward and earn a QR-verified certificate.'],
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
    dependencies = [('site_settings', '0009_seed_ecosystem_sections')]
    operations = [migrations.RunPython(seed_home_sections, migrations.RunPython.noop)]