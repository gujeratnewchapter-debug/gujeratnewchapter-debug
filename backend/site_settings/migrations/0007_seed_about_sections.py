from django.db import migrations, models
import django.db.models.deletion


SECTIONS = [
    ('about', 'Learn with purpose. Build with context.', 'We bring entrepreneurship education, AI guidance, business consulting, and ecosystem connections into one practical home for Ethiopia.'),
    ('mission', 'Make the next step clearer.', 'Equip Ethiopian learners and founders with relevant knowledge, practical tools, and trusted support to move from ideas to responsible action.'),
    ('vision', 'An Ethiopia where every viable idea can find a path to impact.', 'We envision a connected, skilled, and confident generation of entrepreneurs creating inclusive businesses and solving local problems.'),
    ('objectives', 'What we work toward', ''),
    ('team', 'People who build alongside you.', 'Educators, operators, technologists, and community builders focused on practical progress.'),
    ('partners', 'Better together.', "We welcome universities, innovation hubs, public institutions, companies, investors, and community organizations that want to strengthen Ethiopia's startup ecosystem."),
    ('faq', 'Frequently Asked Questions', ''),
]


def seed_sections(apps, schema_editor):
    PageContent = apps.get_model('site_settings', 'PageContent')
    PageSection = apps.get_model('site_settings', 'PageSection')
    page = PageContent.objects.get(slug='about-us')
    structured = {
        'objectives': {'items': [['Make entrepreneurship education practical and accessible'], ['Help learners turn problems into validated opportunities'], ['Connect founders with trusted ecosystem support'], ['Build Ethiopian businesses that create sustainable value']]},
        'team': {'items': [['Program & learning', 'Curriculum, courses, and learner success'], ['Venture support', 'Business, market, and startup guidance'], ['Technology & AI', 'Tools that make learning and building more useful']]},
        'partners': {'items': [['Universities'], ['Innovation hubs'], ['Industry partners'], ['Capital partners'], ['Public institutions']]},
        'faq': {'items': [['Who is Ethiopian Startup School for?', 'Learners, founders, innovators, mentors, and organizations building in or for Ethiopia.'], ['Are the courses practical?', 'Yes. Learning is organized around decisions, exercises, experiments, and real venture-building milestones.'], ['Can organizations partner with us?', 'Yes. Partners can support learning, mentorship, research, events, and startup opportunities.']]},
    }
    for order, (key, title, body) in enumerate(SECTIONS):
        PageSection.objects.get_or_create(page=page, key=key, defaults={'title': title, 'body': body, 'content': structured.get(key, {}), 'order': order})


class Migration(migrations.Migration):
    dependencies = [('site_settings', '0006_seed_platform_pages')]
    operations = [
        migrations.CreateModel(
            name='PageSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(help_text='Stable section key, for example mission or team')),
                ('title', models.CharField(blank=True, max_length=255)),
                ('body', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='page_sections/')),
                ('content', models.JSONField(blank=True, default=dict, help_text='Use en, am, om, and ti keys with title and body values.')),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_published', models.BooleanField(default=True)),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='site_settings.pagecontent')),
            ],
            options={'ordering': ['order', 'id'], 'unique_together': {('page', 'key')}},
        ),
        migrations.RunPython(seed_sections, migrations.RunPython.noop),
    ]