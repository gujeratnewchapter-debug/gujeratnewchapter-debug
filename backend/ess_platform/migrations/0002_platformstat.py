from django.db import migrations, models


STATS = [
    ('courses', 'Published courses'),
    ('students', 'Students'),
    ('instructors', 'Instructors'),
    ('visitors', 'Website visitors'),
    ('certificates', 'Certificates issued'),
    ('service_requests', 'Service requests'),
]


def seed_stats(apps, schema_editor):
    PlatformStat = apps.get_model('ess_platform', 'PlatformStat')
    for order, (metric, label) in enumerate(STATS):
        PlatformStat.objects.get_or_create(metric=metric, defaults={'label': label, 'order': order})


class Migration(migrations.Migration):
    dependencies = [('ess_platform', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='PlatformStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric', models.CharField(choices=[('courses', 'Published courses'), ('students', 'Students'), ('instructors', 'Instructors'), ('visitors', 'Website visitors'), ('certificates', 'Certificates issued'), ('service_requests', 'Service requests')], max_length=30, unique=True)),
                ('label', models.CharField(max_length=120)),
                ('translations', models.JSONField(blank=True, default=dict, help_text='Optional labels keyed by en, am, om, and ti.')),
                ('manual_value', models.PositiveIntegerField(blank=True, help_text='Optional override. Leave blank to use the live database count.', null=True)),
                ('is_enabled', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
            ],
            options={'ordering': ['order', 'id']},
        ),
        migrations.RunPython(seed_stats, migrations.RunPython.noop),
    ]