import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class SupportCallRequest(models.Model):
    class Mode(models.TextChoices):
        AUDIO = 'audio', 'Voice call'
        VIDEO = 'video', 'Video call'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        ENDED = 'ended', 'Ended'
        EXPIRED = 'expired', 'Expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='support_call_requests',
    )
    display_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    question = models.CharField(max_length=500, blank=True)
    mode = models.CharField(max_length=8, choices=Mode.choices)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    capability_hash = models.CharField(max_length=64, unique=True, editable=False)
    room_name = models.CharField(max_length=64, unique=True, editable=False)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='handled_support_calls',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('created_at',)
        indexes = [
            models.Index(fields=('status', 'created_at'), name='support_status_created'),
            models.Index(fields=('expires_at', 'status'), name='support_expiry_status'),
        ]

    def expire_if_needed(self, now=None):
        if self.status == self.Status.PENDING and self.expires_at <= (now or timezone.now()):
            self.status = self.Status.EXPIRED
            self.save(update_fields=('status', 'updated_at'))
        return self.status

    def __str__(self):
        return f'{self.get_mode_display()} from {self.display_name} ({self.status})'
