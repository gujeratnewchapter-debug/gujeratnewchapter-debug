from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('site_settings', '0004_add_heroimage_model')]
    operations = [migrations.CreateModel(
        name='PageContent',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('slug', models.SlugField(unique=True, help_text='Frontend route key, for example about-us or startup-ecosystem')),
            ('title', models.CharField(max_length=255)),
            ('description', models.TextField(blank=True)),
            ('content', models.JSONField(blank=True, default=dict, help_text='Structured page content. Use en, am, om, and ti keys for translations.')),
            ('is_published', models.BooleanField(default=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
        ],
        options={'ordering': ['slug']},
    )]