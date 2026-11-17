import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from courses.models import Course


class Meeting(models.Model):
    class Kind(models.TextChoices):
        CLASSROOM = 'classroom', 'Live classroom'
        DISCUSSION = 'discussion', 'Group discussion'
        CONSULTATION = 'consultation', 'Private consultation'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        LIVE = 'live', 'Live'
        ENDED = 'ended', 'Ended'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CLASSROOM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_meetings')
    room_name = models.CharField(max_length=120, unique=True, db_index=True)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_start']
        indexes = [
            models.Index(fields=['status', 'scheduled_start'], name='meetings_me_status_535826_idx'),
            models.Index(fields=['kind', 'status'], name='meetings_me_kind_769295_idx'),
        ]

    def __str__(self):
        return f"{self.title} ({self.kind})"

    @property
    def is_live(self):
        return self.status == self.Status.LIVE

    @property
    def is_private(self):
        return self.kind == self.Kind.CONSULTATION

    @property
    def start_time_utc(self):
        return timezone.localtime(self.scheduled_start)

    def save(self, *args, **kwargs):
        if self.status == self.Status.LIVE and not self.started_at:
            self.started_at = timezone.now()
        if self.status in {self.Status.ENDED, self.Status.CANCELLED} and not self.ended_at:
            self.ended_at = timezone.now()
        super().save(*args, **kwargs)


class MeetingParticipant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meeting_participations')
    role = models.CharField(max_length=30, default='student')
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_host = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    is_camera_on = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('meeting', 'user')
        indexes = [models.Index(fields=['meeting', 'user'], name='meetings_me_meeting_dd9814_idx')]

    def __str__(self):
        return f"{self.user} -> {self.meeting}"


class MeetingInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='invitations')
    invited_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meeting_invitations')
    status = models.CharField(max_length=20, default=Status.PENDING, choices=Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('meeting', 'invited_user')

    def __str__(self):
        return f'{self.invited_user} invited to {self.meeting}'


class MeetingSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    host_identity = models.CharField(max_length=255, blank=True)
    room_name = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Session for {self.meeting.title}"


class MeetingAttendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='attendance_records')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meeting_attendance')
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('meeting', 'user')

    def __str__(self):
        return f"{self.user} @ {self.meeting}"
