from django.db import models
from django.conf import settings
from courses.models import Course, Lesson


def is_lesson_unlocked(student, lesson):
    """
    A lesson is unlocked if:
    - it's the first lesson in the course, OR
    - the previous lesson has no quiz attached, OR
        - the student has a passing QuizAttempt on the previous lesson's quiz, OR
        - when crossing a module boundary, the student has passed that module's
            section final quiz.
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
    from quizzes.models import QuizAttempt

    if quiz:
        return QuizAttempt.objects.filter(quiz=quiz, student=student, passed=True).exists()

    if previous_lesson.section_id != lesson.section_id:
        final_quiz = previous_lesson.section.quizzes.filter(
            is_final_exam=True,
            lesson__isnull=True,
        ).first()
        if final_quiz:
            return QuizAttempt.objects.filter(quiz=final_quiz, student=student, passed=True).exists()

    return True


def get_course_lesson_unlocks(student, course_id):
    lessons = list(
        Lesson.objects.filter(section__course_id=course_id)
        .select_related('section')
        .prefetch_related('quiz', 'section__quizzes')
        .order_by('section__order', 'order')
    )
    if not lessons:
        return {}

    gated_quizzes = {}
    required_quiz_ids = set()
    for index in range(1, len(lessons)):
        lesson = lessons[index]
        previous_lesson = lessons[index - 1]
        quiz = getattr(previous_lesson, 'quiz', None)
        if not quiz and previous_lesson.section_id != lesson.section_id:
            quiz = next(
                (
                    section_quiz
                    for section_quiz in previous_lesson.section.quizzes.all()
                    if section_quiz.is_final_exam and section_quiz.lesson_id is None
                ),
                None,
            )
        if quiz:
            gated_quizzes[lesson.id] = quiz.id
            required_quiz_ids.add(quiz.id)

    from quizzes.models import QuizAttempt

    passed_quiz_ids = set(
        QuizAttempt.objects.filter(
            quiz_id__in=required_quiz_ids,
            student=student,
            passed=True,
        ).values_list('quiz_id', flat=True)
    )
    return {
        lesson.id: lesson.id not in gated_quizzes or gated_quizzes[lesson.id] in passed_quiz_ids
        for lesson in lessons
    }


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
