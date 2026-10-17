from django.contrib import admin

from .models import FeatureFlag


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ('key', 'is_enabled', 'description', 'updated_at', 'updated_by')
    list_editable = ('is_enabled',)
    list_filter = ('is_enabled',)
    search_fields = ('key', 'description')
    readonly_fields = ('updated_at',)

    def save_model(self, request, obj, form, change):
        if request.user.is_authenticated:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
