from rest_framework import serializers
from .models import Category, Course, Section, Lesson, Resource


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['id', 'title', 'file']


class LessonSerializer(serializers.ModelSerializer):
    resources = ResourceSerializer(many=True, read_only=True)
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'section', 'title', 'lesson_type', 'order', 'content_text', 'video_url', 'source_url',
            'file', 'duration_minutes', 'is_preview', 'is_downloadable', 'resources', 'is_unlocked',
        ]

    def get_is_unlocked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return obj.is_preview
        from enrollments.models import is_lesson_unlocked
        return is_lesson_unlocked(request.user, obj)


class LessonSlimSerializer(serializers.ModelSerializer):
    """Used inside section/course lists - no heavy content field."""
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'lesson_type', 'order', 'duration_minutes', 'is_preview', 'is_unlocked']

    def get_is_unlocked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return obj.is_preview
        from enrollments.models import is_lesson_unlocked
        return is_lesson_unlocked(request.user, obj)


class SectionSerializer(serializers.ModelSerializer):
    lessons = LessonSlimSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ['id', 'course', 'title', 'order', 'lessons']


class CourseListSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source='instructor.get_full_name', read_only=True)
    instructor_photo = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    total_lessons = serializers.IntegerField(read_only=True)
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'short_description', 'instructor_name', 'instructor_photo',
            'category_name', 'level', 'status', 'thumbnail', 'price', 'is_free', 'duration_hours',
            'total_lessons', 'created_at',
        ]

    def get_thumbnail(self, obj):
        # Explicit absolute-URL build so the thumbnail always resolves correctly
        # from the Next.js frontend, regardless of relative-path context issues.
        request = self.context.get('request')
        if obj.thumbnail and hasattr(obj.thumbnail, 'url'):
            return request.build_absolute_uri(obj.thumbnail.url) if request else obj.thumbnail.url
        return None

    def get_instructor_photo(self, obj):
        request = self.context.get('request')
        if obj.instructor.avatar and hasattr(obj.instructor.avatar, 'url'):
            return request.build_absolute_uri(obj.instructor.avatar.url) if request else obj.instructor.avatar.url
        return None


class CourseDetailSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source='instructor.get_full_name', read_only=True)
    instructor_photo = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    sections = SectionSerializer(many=True, read_only=True)
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'subtitle', 'description', 'short_description', 'notes',
            'notes_enabled', 'learning_objectives', 'requirements', 'target_audience', 'tags',
            'instructor', 'instructor_name', 'instructor_photo', 'category', 'category_name',
            'level', 'status', 'thumbnail', 'price', 'is_free', 'language', 'duration_hours',
            'sections', 'created_at',
        ]

    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if obj.thumbnail and hasattr(obj.thumbnail, 'url'):
            return request.build_absolute_uri(obj.thumbnail.url) if request else obj.thumbnail.url
        return None

    def get_instructor_photo(self, obj):
        request = self.context.get('request')
        if obj.instructor.avatar and hasattr(obj.instructor.avatar, 'url'):
            return request.build_absolute_uri(obj.instructor.avatar.url) if request else obj.instructor.avatar.url
        return None


class CourseWriteSerializer(serializers.ModelSerializer):
    """Instructor course-builder create/update. Covers every field requested
    for the 'new course creation form': thumbnail, topic (title), subtitle,
    description, notes + notes toggle, category dropdown. Instructor
    name/photo come from the logged-in user's profile, not this form."""
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'subtitle', 'description', 'short_description', 'notes',
            'notes_enabled', 'learning_objectives', 'requirements', 'target_audience', 'tags',
            'category', 'level', 'status', 'thumbnail', 'price', 'is_free', 'language', 'duration_hours',
        ]
