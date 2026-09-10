from django.conf import settings
from django.db import models


class ServiceRequest(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        REVIEWING = 'reviewing', 'Reviewing'
        ASSIGNED = 'assigned', 'Assigned'
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'
        DECLINED = 'declined', 'Declined'

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_requests')
    name = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    service = models.CharField(max_length=120)
    notes = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_service_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class VisitorEvent(models.Model):
    path = models.CharField(max_length=255)
    session_key = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class PlatformStat(models.Model):
    class Metric(models.TextChoices):
        COURSES = 'courses', 'Published courses'
        STUDENTS = 'students', 'Students'
        INSTRUCTORS = 'instructors', 'Instructors'
        VISITORS = 'visitors', 'Website visitors'
        CERTIFICATES = 'certificates', 'Certificates issued'
        SERVICE_REQUESTS = 'service_requests', 'Service requests'

    metric = models.CharField(max_length=30, choices=Metric.choices, unique=True)
    label = models.CharField(max_length=120)
    translations = models.JSONField(default=dict, blank=True, help_text='Optional labels keyed by en, am, om, and ti.')
    manual_value = models.PositiveIntegerField(null=True, blank=True, help_text='Optional override. Leave blank to use the live database count.')
    is_enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.label