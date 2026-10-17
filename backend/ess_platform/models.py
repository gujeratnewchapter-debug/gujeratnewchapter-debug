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


class StartupProject(models.Model):
    class Stage(models.TextChoices):
        IDEA = 'idea', 'Idea'
        VALIDATION = 'validation', 'Validation'
        MVP = 'mvp', 'Minimum viable product'
        LAUNCH = 'launch', 'Launch'
        GROWTH = 'growth', 'Growth'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='startup_projects')
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.IDEA)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    problem = models.TextField(blank=True)
    solution = models.TextField(blank=True)
    target_market = models.TextField(blank=True)
    value_proposition = models.TextField(blank=True)
    business_model = models.TextField(blank=True)
    next_steps = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return self.title


class StartupMilestone(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not started'
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'

    project = models.ForeignKey(StartupProject, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=160)
    details = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.project.title} - {self.title}'