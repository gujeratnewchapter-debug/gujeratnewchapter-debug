import uuid
from django.db import models
from django.conf import settings
from courses.models import Course


class Certificate(models.Model):
    """Automatic certificate generation with QR verification (RFP section 15)."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    certificate_number = models.CharField(max_length=64, unique=True, default=uuid.uuid4, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    verification_url = models.URLField(blank=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.certificate_number} - {self.student} - {self.course}"
