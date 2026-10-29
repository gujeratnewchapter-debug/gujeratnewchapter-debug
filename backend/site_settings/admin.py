from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html, format_html_join
from django.db import models
from .models import (
    Advertisement,
    AdvertisementEvent,
    SiteSettings,
    ContactMessage,
    HeroImage,
    PageContent,
    PageSection,
)


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
        ('Advertisements', {'fields': ('advertisements_enabled',)}),
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
            'description': (
                'Use the content JSON for translated copy. Page sections below control editable page blocks. '
                'The Home page Startup Designation announcement is edited using its title, body, CTA URL, '
                'CTA label, and publication controls; no JSON edits are needed. '
                'For the Home page New notices callout, add "notices_callout": {"label": "New", '
                '"visible": true, "pulse": true} inside each language content object.'
            ),
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
    fields = ('key', 'title', 'body', 'cta_url', 'cta_label', 'image', 'content', 'order', 'is_published')
    formfield_overrides = {
        models.JSONField: {'widget': admin.widgets.AdminTextareaWidget(attrs={'rows': 8})},
    }
    ordering = ('order',)


PageContentAdmin.inlines = [PageSectionInline]


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = (
        'internal_name', 'advertiser_name', 'content_type', 'is_active', 'priority',
        'impression_count', 'click_count', 'click_through_rate', 'starts_at', 'ends_at',
    )
    list_filter = ('is_active', 'content_type', 'frequency')
    search_fields = ('internal_name', 'advertiser_name', 'headline')
    readonly_fields = ('created_at', 'updated_at', 'preview')
    fieldsets = (
        ('Campaign', {'fields': ('internal_name', 'advertiser_name', 'content_type', 'is_active')}),
        ('Text content', {'fields': ('headline', 'description', 'promotional_text')}),
        ('Image content', {'fields': ('image', 'image_url', 'image_alt_text', 'advertiser_logo')}),
        ('Video content', {'fields': ('video_file', 'video_url')}),
        ('Call to action', {'fields': ('cta_label', 'destination_url')}),
        ('Schedule and display', {
            'fields': (
                'starts_at', 'ends_at', 'priority', 'display_delay_seconds',
                'close_countdown_seconds', 'frequency', 'target_routes',
            ),
        }),
        ('Preview and timestamps', {
            'description': (
                'Campaign counts are approximate browser-reported events. Blockers, lost requests, '
                'or repeated visits can affect totals; no visitor IP address or account identifier is stored.'
            ),
            'fields': ('preview', 'created_at', 'updated_at'),
        }),
    )
    formfield_overrides = {
        models.JSONField: {'widget': admin.widgets.AdminTextareaWidget(attrs={'rows': 4})},
    }

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _impression_count=Count(
                'events',
                filter=Q(events__event_type=AdvertisementEvent.EventType.IMPRESSION),
            ),
            _click_count=Count(
                'events',
                filter=Q(events__event_type=AdvertisementEvent.EventType.CLICK),
            ),
        )

    @admin.display(description='Impressions', ordering='_impression_count')
    def impression_count(self, obj):
        return obj._impression_count

    @admin.display(description='Clicks', ordering='_click_count')
    def click_count(self, obj):
        return obj._click_count

    @admin.display(description='CTR')
    def click_through_rate(self, obj):
        impressions = obj._impression_count
        if not impressions:
            return '0.0%'
        return f'{obj._click_count / impressions:.1%}'

    @admin.display(description='Preview')
    def preview(self, obj):
        if obj is None or not obj.pk:
            return 'Save the advertisement to preview it.'
        parts = [
            format_html(
                '<div style="max-width:640px;padding:16px;border:1px solid #ddd;border-radius:8px">'
            ),
        ]
        if obj.image:
            parts.append(format_html(
                '<img src="{}" alt="{}" style="max-width:100%;height:auto">',
                obj.image.url,
                obj.image_alt_text,
            ))
        elif obj.image_url:
            parts.append(format_html(
                '<img src="{}" alt="{}" style="max-width:100%;height:auto">',
                obj.image_url,
                obj.image_alt_text,
            ))
        if obj.video_file:
            parts.append(format_html(
                '<video controls preload="metadata" style="max-width:100%"><source src="{}"></video>',
                obj.video_file.url,
            ))
        elif obj.video_url:
            parts.append(format_html(
                '<p><a href="{}" target="_blank" rel="noopener noreferrer">Open approved video preview</a></p>',
                obj.video_url,
            ))
        if obj.advertiser_name:
            parts.append(format_html('<p><strong>{}</strong></p>', obj.advertiser_name))
        if obj.headline:
            parts.append(format_html('<h2>{}</h2>', obj.headline))
        if obj.description:
            parts.append(format_html('<p>{}</p>', obj.description))
        if obj.promotional_text:
            parts.append(format_html('<p>{}</p>', obj.promotional_text))
        if obj.cta_label:
            parts.append(format_html('<p>{}</p>', obj.cta_label))
        parts.append(format_html('</div>'))
        return format_html_join('', '{}', ((part,) for part in parts))
