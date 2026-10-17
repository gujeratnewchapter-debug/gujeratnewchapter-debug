from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import Article, Notice


@admin.action(description='Publish selected articles')
def publish_articles(modeladmin, request, queryset):
    for article in queryset:
        if not article.is_published:
            article.is_published = True
            article.save(update_fields=['is_published', 'published_at', 'updated_at'])


@admin.action(description='Unpublish selected articles')
def unpublish_articles(modeladmin, request, queryset):
    queryset.update(is_published=False)


@admin.action(description='Feature selected articles')
def feature_articles(modeladmin, request, queryset):
    queryset.update(is_featured=True)


@admin.action(description='Remove selected articles from featured')
def unfeature_articles(modeladmin, request, queryset):
    queryset.update(is_featured=False)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'is_published', 'is_featured', 'published_at')
    list_filter = ('is_published', 'is_featured', 'category')
    search_fields = ('title', 'slug', 'short_description', 'content', 'author')
    date_hierarchy = 'published_at'
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'image_preview')
    actions = (publish_articles, unpublish_articles, feature_articles, unfeature_articles)
    fieldsets = (
        ('Article', {'fields': ('title', 'slug', 'category', 'author', 'short_description', 'content')}),
        ('Featured image', {'fields': ('featured_image', 'image_alt_text', 'image_preview')}),
        ('Publication', {'fields': ('is_published', 'is_featured', 'published_at')}),
        ('Audit', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='Current image')
    def image_preview(self, article):
        if not article.featured_image:
            return 'No image uploaded'
        return format_html(
            '<img src="{}" alt="{}" style="max-height: 180px; max-width: 320px; object-fit: cover;">',
            article.featured_image.url,
            article.image_alt_text,
        )


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'created_at', 'updated_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'slug', 'body')
    readonly_fields = ('slug', 'created_at', 'updated_at')
    actions = ('publish_notices', 'unpublish_notices')

    @admin.action(description='Publish selected notices')
    def publish_notices(self, request, queryset):
        queryset.update(is_published=True, updated_at=timezone.now())

    @admin.action(description='Unpublish selected notices')
    def unpublish_notices(self, request, queryset):
        queryset.update(is_published=False, updated_at=timezone.now())
