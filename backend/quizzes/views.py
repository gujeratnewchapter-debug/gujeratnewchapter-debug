from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Quiz, Question, Choice, QuizAttempt, Answer
from .serializers import (
    QuizSerializer, QuizInstructorSerializer, QuizSubmitSerializer, QuizAttemptResultSerializer,
    QuestionWriteSerializer, ChoiceWriteSerializer,
)


class IsInstructorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.is_instructor or request.user.is_super_admin)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.course.instructor_id == request.user.id or request.user.is_super_admin


class IsQuestionCourseInstructorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.is_instructor or request.user.is_super_admin)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.quiz.course.instructor_id == request.user.id or request.user.is_super_admin


class IsChoiceCourseInstructorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.is_instructor or request.user.is_super_admin)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.question.quiz.course.instructor_id == request.user.id or request.user.is_super_admin


def _is_instructor_like(user):
    return user.is_authenticated and (user.is_instructor or user.is_super_admin)


class QuizViewSet(viewsets.ModelViewSet):
    """
    Quiz taking + grading (RFP sections 12 & 13).
    Auto-grades objective question types; essay questions are left for
    instructor manual grading (points_awarded stays 0 until reviewed).
    """
    queryset = Quiz.objects.prefetch_related('questions__choices')
    permission_classes = [IsInstructorOrReadOnly]

    def get_serializer_class(self):
        # Instructors/admins editing the quiz need to see which choice is
        # correct; students taking it must never receive that field.
        if _is_instructor_like(self.request.user):
            return QuizInstructorSerializer
        return QuizSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        course_id = self.request.query_params.get('course')
        if course_id:
            qs = qs.filter(course_id=course_id)
        lesson_id = self.request.query_params.get('lesson')
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        return qs

    def get_permissions(self):
        if self.action == 'submit':
            return [permissions.IsAuthenticated()]
        return [IsInstructorOrReadOnly()]

    def perform_create(self, serializer):
        course = serializer.validated_data.get('course')
        if course and course.instructor_id != self.request.user.id and not self.request.user.is_super_admin:
            raise PermissionDenied("You can only add quizzes to your own courses.")
        serializer.save()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        quiz = self.get_object()

        if quiz.lesson_id:
            from enrollments.models import is_lesson_unlocked
            if not is_lesson_unlocked(request.user, quiz.lesson):
                return Response(
                    {"detail": "Complete the previous lesson's quiz (80%+) before attempting this one."},
                    status=403,
                )

        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attempt = QuizAttempt.objects.create(quiz=quiz, student=request.user)
        total_points = 0
        earned_points = 0

        for ans in serializer.validated_data['answers']:
            question = Question.objects.get(id=ans['question_id'], quiz=quiz)
            total_points += question.points
            answer = Answer.objects.create(
                attempt=attempt, question=question, text_answer=ans.get('text_answer', ''),
            )
            is_correct = None
            points_awarded = 0

            if question.question_type in ('multiple_choice', 'true_false', 'checkbox'):
                selected_ids = set(ans.get('selected_choice_ids', []))
                correct_ids = set(question.choices.filter(is_correct=True).values_list('id', flat=True))
                is_correct = selected_ids == correct_ids and len(selected_ids) > 0
                points_awarded = question.points if is_correct else 0
                if selected_ids:
                    answer.selected_choices.set(selected_ids)
            elif question.question_type == 'fill_blank':
                is_correct = ans.get('text_answer', '').strip().lower() == question.correct_text_answer.strip().lower()
                points_awarded = question.points if is_correct else 0
            # essay/matching/ordering: left null for manual/AI-assisted grading

            answer.is_correct = is_correct
            answer.points_awarded = points_awarded
            answer.save()
            earned_points += points_awarded

        score_percent = (earned_points / total_points * 100) if total_points else 0
        attempt.score_percent = round(score_percent, 2)
        attempt.passed = score_percent >= quiz.passing_score_percent
        attempt.submitted_at = timezone.now()
        attempt.save()

        return Response(QuizAttemptResultSerializer(attempt).data)


class QuestionViewSet(viewsets.ModelViewSet):
    """
    Instructor course-builder endpoint to add/edit/delete quiz questions
    (e.g. the 10 questions x 10% each for a lesson quiz). Never exposed to
    students directly — they only ever see questions nested read-only
    inside GET /api/quizzes/{id}/.
    """
    queryset = Question.objects.all()
    serializer_class = QuestionWriteSerializer
    permission_classes = [IsQuestionCourseInstructorOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        if not _is_instructor_like(self.request.user):
            return qs.none()
        quiz_id = self.request.query_params.get('quiz')
        if quiz_id:
            qs = qs.filter(quiz_id=quiz_id)
        return qs

    def perform_create(self, serializer):
        if not _is_instructor_like(self.request.user):
            raise PermissionDenied("Instructor or admin access required.")
        quiz = serializer.validated_data.get('quiz')
        if quiz and quiz.course.instructor_id != self.request.user.id and not self.request.user.is_super_admin:
            raise PermissionDenied("You can only add questions to your own course's quizzes.")
        serializer.save()


class ChoiceViewSet(viewsets.ModelViewSet):
    """Instructor course-builder endpoint to add/edit/delete answer choices,
    including marking which one is_correct."""
    queryset = Choice.objects.all()
    serializer_class = ChoiceWriteSerializer
    permission_classes = [IsChoiceCourseInstructorOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        if not _is_instructor_like(self.request.user):
            return qs.none()
        question_id = self.request.query_params.get('question')
        if question_id:
            qs = qs.filter(question_id=question_id)
        return qs

    def perform_create(self, serializer):
        if not _is_instructor_like(self.request.user):
            raise PermissionDenied("Instructor or admin access required.")
        question = serializer.validated_data.get('question')
        if question and question.quiz.course.instructor_id != self.request.user.id and not self.request.user.is_super_admin:
            raise PermissionDenied("You can only add choices to your own course's questions.")
        serializer.save()
