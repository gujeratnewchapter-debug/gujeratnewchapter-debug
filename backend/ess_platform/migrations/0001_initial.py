from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='ServiceRequest', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(blank=True, max_length=160)), ('email', models.EmailField(blank=True, max_length=254)), ('service', models.CharField(max_length=120)), ('notes', models.TextField()), ('status', models.CharField(choices=[('new', 'New'), ('reviewing', 'Reviewing'), ('assigned', 'Assigned'), ('in_progress', 'In progress'), ('completed', 'Completed'), ('declined', 'Declined')], default='new', max_length=20)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_service_requests', to=settings.AUTH_USER_MODEL)), ('requester', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='service_requests', to=settings.AUTH_USER_MODEL))], options={'ordering': ['-created_at']}),
        migrations.CreateModel(name='VisitorEvent', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('path', models.CharField(max_length=255)), ('session_key', models.CharField(blank=True, max_length=64)), ('created_at', models.DateTimeField(auto_now_add=True))], options={'ordering': ['-created_at']}),
    ]