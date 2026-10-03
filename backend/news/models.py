from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    short_description = models.CharField(max_length=500)
    content = models.TextField()
    featured_image = models.ImageField(upload_to='news/')
    image_alt_text = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    author = models.CharField(max_length=160, default='Ethiopian Startup School')
    published_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-published_at', '-created_at')
        indexes = [
            models.Index(fields=('-is_published', '-published_at'), name='news_pub_date_idx'),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:260] or 'article'
            candidate = base_slug
            suffix = 2
            while Article.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f'{base_slug[:270 - len(str(suffix))]}-{suffix}'
                suffix += 1
            self.slug = candidate
        if self.is_published and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
