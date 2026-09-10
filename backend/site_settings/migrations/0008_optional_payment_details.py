from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('site_settings', '0007_seed_about_sections')]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='bank_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='bank_account_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='telebirr_number',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]