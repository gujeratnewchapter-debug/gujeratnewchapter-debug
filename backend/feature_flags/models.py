from django.conf import settings
from django.db import models


class FeatureFlag(models.Model):
    key = models.SlugField(max_length=64, unique=True)
    is_enabled = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_feature_flags',
    )

    class Meta:
        ordering = ['key']

    def __str__(self):
        return f'{self.key}: {"on" if self.is_enabled else "off"}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .services import invalidate_flag_cache

        invalidate_flag_cache()

    def delete(self, *args, **kwargs):
        key = self.key
        result = super().delete(*args, **kwargs)
        from .services import invalidate_flag_cache

        invalidate_flag_cache(key)
        return result
