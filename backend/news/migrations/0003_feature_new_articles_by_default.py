from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0002_seed_launch_article'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='is_featured',
            field=models.BooleanField(default=True),
        ),
    ]
