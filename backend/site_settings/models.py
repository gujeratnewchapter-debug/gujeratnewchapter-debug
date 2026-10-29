import json
import os
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


MAX_AD_IMAGE_SIZE = 10 * 1024 * 1024
MAX_AD_VIDEO_SIZE = 100 * 1024 * 1024
APPROVED_VIDEO_HOSTS = {
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'youtu.be',
    'youtube-nocookie.com',
    'www.youtube-nocookie.com',
    'vimeo.com',
    'www.vimeo.com',
    'player.vimeo.com',
}


def validate_https_url(value):
    if not value:
        return
    parsed = urlparse(value)
    if parsed.scheme != 'https' or not parsed.hostname:
        raise ValidationError('Use a valid HTTPS URL.')


def validate_video_url(value):
    validate_https_url(value)
    if value and urlparse(value).hostname.lower() not in APPROVED_VIDEO_HOSTS:
        raise ValidationError('Use a YouTube or Vimeo video URL.')


def validate_target_routes(value):
    if not isinstance(value, list) or len(value) > 50:
        raise ValidationError('Target routes must be a list of at most 50 paths.')
    for route in value:
        if (
            not isinstance(route, str)
            or not route.startswith('/')
            or route.startswith('//')
            or '?' in route
            or '#' in route
            or (('*' in route) and not route.endswith('/*'))
        ):
            raise ValidationError('Each target must be a path such as /courses or /courses/*.')


def validate_ad_image_size(upload):
    if upload.size > MAX_AD_IMAGE_SIZE:
        raise ValidationError('Advertisement images must be 10 MB or smaller.')


def validate_ad_video_size(upload):
    if upload.size > MAX_AD_VIDEO_SIZE:
        raise ValidationError('Advertisement videos must be 100 MB or smaller.')
    extension = os.path.splitext(upload.name)[1].lower()
    position = upload.tell()
    upload.seek(0)
    header = upload.read(12)
    upload.seek(position)
    is_mp4 = extension == '.mp4' and header[4:8] == b'ftyp'
    is_webm = extension == '.webm' and header.startswith(b'\x1aE\xdf\xa3')
    if not (is_mp4 or is_webm):
        raise ValidationError('The uploaded file does not match the MP4 or WebM format.')


class SiteSettings(models.Model):
    """
    Singleton model holding editable branding, contact, and footer content.
    Admins edit this via /api/site-settings/ (or Django admin) instead of
    hardcoding text in the frontend.
    """
    school_name = models.CharField(max_length=255, default="Ethiopian Startup School")
    tagline = models.CharField(max_length=255, blank=True, default="Learn to build. Build to grow.")
    logo = models.ImageField(upload_to='branding/', blank=True, null=True)

    address = models.CharField(max_length=255, default="Addis Ababa, Ethiopia")
    phone = models.CharField(max_length=50, default="+251 94 188 3746")
    support_email = models.EmailField(default="tilahunalenee@gmail.com")

    # Support us / donation details
    bank_name = models.CharField(max_length=255, blank=True, default="")
    bank_account_name = models.CharField(max_length=255, blank=True, default="")
    bank_account_number = models.CharField(max_length=100, blank=True, default="")
    telebirr_number = models.CharField(max_length=50, blank=True, default="")

    # Email branding
    email_sender_name = models.CharField(max_length=255, default="Ethiopian Startup School")
    email_verification_subject = models.CharField(
        max_length=255, default="Verify your email for Ethiopian Startup School"
    )

    # Home page hero section and social links managed from admin
    hero_title = models.CharField(max_length=255, blank=True, default='AI Tutor, Mentor & Business Coach included')
    hero_subtitle = models.TextField(blank=True, default='Learn entrepreneurship, AI, and business skills with practical guidance from industry experts.')
    hero_image = models.ImageField(upload_to='hero/', blank=True, null=True)
    hero_cta_label = models.CharField(max_length=100, blank=True, default='Explore courses')
    hero_cta_url = models.CharField(max_length=255, blank=True, default='/courses')
    social_links = models.JSONField(default=list, blank=True)
    advertisements_enabled = models.BooleanField(
        default=True,
        help_text='Turn off all advertisement popups without deactivating individual campaigns.',
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.school_name

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        if isinstance(self.social_links, str):
            self.social_links = json.loads(self.social_links or '[]')
        if not isinstance(self.social_links, list):
            self.social_links = []
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Advertisement(models.Model):
    class ContentType(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        TEXT = 'text', 'Text'
        MIXED = 'mixed', 'Mixed'

    class Frequency(models.TextChoices):
        SESSION = 'session', 'Once per browser session'
        DAILY = 'daily', 'Once per day'
        EVERY_VISIT = 'every_visit', 'Every new visit'

    internal_name = models.CharField(max_length=160, unique=True)
    advertiser_name = models.CharField(max_length=160, blank=True)
    content_type = models.CharField(max_length=10, choices=ContentType.choices, default=ContentType.MIXED)
    headline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    promotional_text = models.CharField(max_length=300, blank=True)
    image = models.ImageField(
        upload_to='advertisements/images/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_ad_image_size],
    )
    image_url = models.URLField(max_length=1000, blank=True, validators=[validate_https_url])
    image_alt_text = models.CharField(max_length=255, blank=True)
    video_file = models.FileField(
        upload_to='advertisements/videos/',
        blank=True,
        validators=[FileExtensionValidator(['mp4', 'webm']), validate_ad_video_size],
    )
    video_url = models.URLField(max_length=1000, blank=True, validators=[validate_video_url])
    advertiser_logo = models.ImageField(
        upload_to='advertisements/logos/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_ad_image_size],
    )
    cta_label = models.CharField(max_length=80, blank=True)
    destination_url = models.URLField(max_length=1000, blank=True, validators=[validate_https_url])
    is_active = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    priority = models.PositiveIntegerField(default=0)
    display_delay_seconds = models.PositiveSmallIntegerField(default=0)
    close_countdown_seconds = models.PositiveSmallIntegerField(default=4)
    frequency = models.CharField(max_length=12, choices=Frequency.choices, default=Frequency.SESSION)
    target_routes = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_target_routes],
        help_text='JSON list of exact routes or prefix patterns such as ["/courses/*"]. Empty targets all routes.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'starts_at', 'id']

    def __str__(self):
        return self.internal_name

    def clean(self):
        super().clean()
        errors = {}
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            errors['ends_at'] = 'End date must be after the start date.'
        if self.display_delay_seconds > 60:
            errors['display_delay_seconds'] = 'Display delay cannot exceed 60 seconds.'
        if self.close_countdown_seconds > 30:
            errors['close_countdown_seconds'] = 'Close countdown cannot exceed 30 seconds.'
        try:
            validate_target_routes(self.target_routes)
        except ValidationError as error:
            errors['target_routes'] = error.messages

        has_image = bool(self.image or self.image_url)
        has_video = bool(self.video_file or self.video_url)
        has_text = bool(self.headline or self.description or self.promotional_text)
        required_content = {
            self.ContentType.IMAGE: (has_image, 'Add an image or image URL.'),
            self.ContentType.VIDEO: (has_video, 'Add a video file or approved video URL.'),
            self.ContentType.TEXT: (has_text, 'Add a headline, description, or promotional text.'),
            self.ContentType.MIXED: (
                has_image or has_video or has_text,
                'Add image, video, or text content.',
            ),
        }
        is_valid, message = required_content.get(self.content_type, (False, 'Select a valid content type.'))
        if not is_valid:
            errors['content_type'] = message
        if errors:
            raise ValidationError(errors)

    @classmethod
    def active_for_route(cls, route, now=None):
        now = now or timezone.now()
        queryset = cls.objects.filter(is_active=True).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now),
        )
        matching = []
        for advertisement in queryset:
            routes = advertisement.target_routes
            if not routes or any(
                route == target
                or (target.endswith('/*') and route.startswith(target[:-1]))
                for target in routes
            ):
                matching.append(advertisement)
        return matching


class AdvertisementEvent(models.Model):
    class EventType(models.TextChoices):
        IMPRESSION = 'impression', 'Impression'
        CLICK = 'click', 'Click'

    advertisement = models.ForeignKey(
        Advertisement,
        on_delete=models.CASCADE,
        related_name='events',
    )
    event_type = models.CharField(max_length=12, choices=EventType.choices)
    event_id = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['advertisement', 'event_type', 'created_at'])]


class HeroImage(models.Model):
    site_settings = models.ForeignKey(
        SiteSettings,
        related_name='hero_images',
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to='hero/')
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Hero image'
        verbose_name_plural = 'Hero images'

    def __str__(self):
        return f'Hero image #{self.id}'


class ContactMessage(models.Model):
    """Submissions from the footer 'Contact Us' form."""
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} — {self.name}"


class PageContent(models.Model):
    """Admin-managed content for any public frontend page."""
    slug = models.SlugField(unique=True, help_text='Frontend route key, for example about-us or startup-ecosystem')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content = models.JSONField(default=dict, blank=True, help_text='Structured page content. Use en, am, om, and ti keys for translations.')
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        return self.title


class PageSection(models.Model):
    page = models.ForeignKey(PageContent, on_delete=models.CASCADE, related_name='sections')
    key = models.SlugField(help_text='Stable section key, for example mission or team')
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    cta_url = models.URLField(
        'CTA URL',
        max_length=500,
        blank=True,
        help_text='External destination used by a homepage section call to action.',
    )
    cta_label = models.CharField(
        'CTA label',
        max_length=100,
        blank=True,
        help_text='Visible link text for the section call to action.',
    )
    image = models.ImageField(upload_to='page_sections/', blank=True, null=True)
    content = models.JSONField(default=dict, blank=True, help_text='Use en, am, om, and ti keys with title and body values.')
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('page', 'key')]

    def __str__(self):
        return f'{self.page.title} - {self.key}'
