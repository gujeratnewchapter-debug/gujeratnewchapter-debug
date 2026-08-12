from rest_framework import serializers
from .models import Enrollment, LessonProgress, Bookmark
from courses.serializers import CourseListSerializer


class EnrollmentSerializer(serializers.ModelSerializer):
    course_detail = CourseListSerializer(source='course', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'course_detail', 'enrolled_at', 'completed_at', 'progress_percent']
        read_only_fields = ['id', 'enrolled_at', 'completed_at', 'progress_percent']


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['id', 'enrollment', 'lesson', 'is_completed', 'completed_at']
        read_only_fields = ['id', 'completed_at']


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ['id', 'lesson', 'created_at']
        read_only_fields = ['id', 'created_at']
