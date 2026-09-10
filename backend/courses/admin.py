from django.contrib import admin
from .models import Category, Course, Section, Lesson, Resource


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0


class ResourceInline(admin.TabularInline):
    model = Resource
    extra = 1
    fields = ('title', 'resource_type', 'url', 'file', 'order')


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category', 'status', 'price', 'created_at')
    list_filter = ('status', 'level', 'category')
    search_fields = ('title', 'description')
    inlines = [SectionInline]
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        ('Course identity', {
            'fields': ('title', 'slug', 'subtitle', 'description', 'short_description', 'thumbnail'),
        }),
        ('Instructor and publishing', {
            'description': 'The instructor photo is managed on the instructor user profile.',
            'fields': ('instructor', 'category', 'level', 'status', 'published_at'),
        }),
        ('Learning details', {
            'fields': ('notes', 'notes_enabled', 'learning_objectives', 'requirements', 'target_audience', 'tags'),
        }),
        ('Pricing and delivery', {
            'fields': ('price', 'is_free', 'language', 'duration_hours'),
        }),
    )


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'lesson_type', 'order')
    list_filter = ('lesson_type',)
    search_fields = ('title', 'video_url', 'source_url')
    inlines = [ResourceInline]


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'resource_type', 'order')
    list_filter = ('resource_type',)
    search_fields = ('title', 'url', 'lesson__title')
