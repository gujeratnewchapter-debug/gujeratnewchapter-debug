from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Enrollment, LessonProgress, Bookmark, is_lesson_unlocked
from .serializers import EnrollmentSerializer, LessonProgressSerializer, BookmarkSerializer
from courses.models import Course, Lesson


class EnrollmentViewSet(viewsets.ModelViewSet):
    """Student dashboard: enroll in a course, track progress (RFP section 7)."""
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user).select_related('course')

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_lesson_complete(self, request, pk=None):
        enrollment = self.get_object()
        lesson_id = request.data.get('lesson_id')
        lesson = Lesson.objects.get(id=lesson_id, section__course=enrollment.course)

        if not is_lesson_unlocked(request.user, lesson):
            return Response(
                {"detail": "Pass the previous lesson's quiz (80%+) to unlock this lesson."},
                status=status.HTTP_403_FORBIDDEN,
            )

        progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save()

        total = Lesson.objects.filter(section__course=enrollment.course).count()
        done = LessonProgress.objects.filter(enrollment=enrollment, is_completed=True).count()
        enrollment.progress_percent = int((done / total) * 100) if total else 0
        if enrollment.progress_percent >= 100 and not enrollment.completed_at:
            enrollment.completed_at = timezone.now()
        enrollment.save()
        return Response(EnrollmentSerializer(enrollment).data)


class BookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Bookmark.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
