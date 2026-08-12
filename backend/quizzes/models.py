from django.db import models
from django.conf import settings
from courses.models import Course, Section


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    lesson = models.OneToOneField(
        'courses.Lesson', on_delete=models.CASCADE, related_name='quiz', null=True, blank=True,
        help_text="Per-lesson quiz. Passing it (>= passing_score_percent) unlocks the next lesson.",
    )
    title = models.CharField(max_length=255)
    is_final_exam = models.BooleanField(default=False)
    time_limit_minutes = models.PositiveIntegerField(default=0, help_text="0 = no limit")
    passing_score_percent = models.PositiveIntegerField(default=80)
    randomize_questions = models.BooleanField(default=False)
    max_attempts = models.PositiveIntegerField(default=0, help_text="0 = unlimited attempts until pass")

    def __str__(self):
        return self.title


class Question(models.Model):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = 'multiple_choice', 'Multiple Choice'
        CHECKBOX = 'checkbox', 'Checkbox'
        TRUE_FALSE = 'true_false', 'True/False'
        FILL_BLANK = 'fill_blank', 'Fill in the Blank'
        ESSAY = 'essay', 'Essay'
        MATCHING = 'matching', 'Matching'
        ORDERING = 'ordering', 'Ordering'

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=30, choices=QuestionType.choices, default=QuestionType.MULTIPLE_CHOICE)
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=1)
    correct_text_answer = models.CharField(max_length=500, blank=True, help_text="For fill-in-the-blank")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text[:60]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score_percent = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student} - {self.quiz} ({self.score_percent})"


class Answer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choices = models.ManyToManyField(Choice, blank=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    points_awarded = models.FloatField(default=0)
