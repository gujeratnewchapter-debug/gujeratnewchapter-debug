from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('courses', '0004_course_learning_objectives_course_requirements_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='resource',
            name='resource_type',
            field=models.CharField(choices=[('file', 'File'), ('video', 'Video')], default='file', max_length=20),
        ),
        migrations.AddField(
            model_name='resource',
            name='url',
            field=models.URLField(blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='resources/'),
        ),
    ]
