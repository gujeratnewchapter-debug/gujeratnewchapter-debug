from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('certificates', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='certificate',
            name='time_taken_seconds',
            field=models.PositiveIntegerField(default=0),
        ),
    ]