from django.contrib import admin
from .models import Category, Course, Section, Lesson, Resource


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0


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


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'lesson_type', 'order')


admin.site.register(Resource)
