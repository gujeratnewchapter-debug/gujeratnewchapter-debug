from django.contrib import admin
from django.db import models
from .models import SiteSettings, ContactMessage, HeroImage, PageContent, PageSection


class HeroImageInline(admin.TabularInline):
    model = HeroImage
    extra = 1
    fields = ('image', 'order')
    ordering = ('order',)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    inlines = [HeroImageInline]
    fieldsets = (
        ('Branding', {'fields': ('school_name', 'tagline', 'logo')}),
        ('Contact', {'fields': ('address', 'phone', 'support_email')}),
        ('Optional payment details', {
            'description': 'Leave any payment field blank when that payment method is not available.',
            'fields': ('bank_name', 'bank_account_name', 'bank_account_number', 'telebirr_number'),
        }),
        ('Email', {'fields': ('email_sender_name', 'email_verification_subject')}),
        ('Home hero', {'fields': ('hero_title', 'hero_subtitle', 'hero_image', 'hero_cta_label', 'hero_cta_url')}),
        ('Social links', {'fields': ('social_links',)}),
    )
    formfield_overrides = {
        models.JSONField: {'widget': admin.widgets.AdminTextareaWidget(attrs={'rows': 6})},
    }

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'is_read', 'created_at')
    list_filter = ('is_read',)


@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    inlines = []
    list_display = ('slug', 'title', 'is_published', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('slug', 'title', 'description')
    fieldsets = (
        ('Page identity', {'fields': ('slug', 'title', 'description', 'is_published')}),
        ('Translations and page data', {
            'description': 'Use the content JSON for translated copy. Page sections below control editable page blocks.',
            'fields': ('content',),
        }),
    )
    formfield_overrides = {
        models.JSONField: {'widget': admin.widgets.AdminTextareaWidget(attrs={'rows': 10})},
    }
    prepopulated_fields = {'slug': ('title',)}


class PageSectionInline(admin.StackedInline):
    model = PageSection
    extra = 0
    fields = ('key', 'title', 'body', 'image', 'content', 'order', 'is_published')
    formfield_overrides = {
        models.JSONField: {'widget': admin.widgets.AdminTextareaWidget(attrs={'rows': 8})},
    }
    ordering = ('order',)


PageContentAdmin.inlines = [PageSectionInline]
