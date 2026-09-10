import json

from django.db import models


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
    image = models.ImageField(upload_to='page_sections/', blank=True, null=True)
    content = models.JSONField(default=dict, blank=True, help_text='Use en, am, om, and ti keys with title and body values.')
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('page', 'key')]

    def __str__(self):
        return f'{self.page.title} - {self.key}'
