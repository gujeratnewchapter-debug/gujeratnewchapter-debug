from django.db import models
from django.conf import settings
from courses.models import Course, Lesson


def is_lesson_unlocked(student, lesson):
    """
    A lesson is unlocked if:
    - it's the first lesson in the course, OR
    - the previous lesson has no quiz attached, OR
    - the student has a passing QuizAttempt on the previous lesson's quiz.
    This enforces "get 80% to pass and continue to the next lesson, with
    unlimited attempts until passing."
    """
    ordered = lesson.section.course.ordered_lessons()
    try:
        idx = ordered.index(lesson)
    except ValueError:
        return True
    if idx == 0:
        return True

    previous_lesson = ordered[idx - 1]
    quiz = getattr(previous_lesson, 'quiz', None)
    if not quiz:
        return True

    from quizzes.models import QuizAttempt
    return QuizAttempt.objects.filter(quiz=quiz, student=student, passed=True).exists()


class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_percent = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student} -> {self.course}"

    @property
    def is_completed(self):
        return self.completed_at is not None


class LessonProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('enrollment', 'lesson')


class Bookmark(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarks')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'lesson')
