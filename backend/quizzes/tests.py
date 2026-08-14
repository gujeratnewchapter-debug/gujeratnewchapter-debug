from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from courses.models import Course, Section, Lesson
from enrollments.models import Enrollment, is_lesson_unlocked
from quizzes.models import Quiz, Question, Choice, QuizAttempt
from quizzes.views import QuizViewSet

User = get_user_model()


class ProgressionAndCertificateTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='inst1', email='inst1@example.com', password='pass123', role=User.Role.INSTRUCTOR,
        )
        self.student = User.objects.create_user(
            username='student1', email='student1@example.com', password='pass123', role=User.Role.STUDENT,
        )
        self.course = Course.objects.create(
            title='Entrepreneurship', slug='entrepreneurship', instructor=self.instructor,
            description='Course', short_description='Short', status=Course.Status.PUBLISHED,
        )
        self.module = Section.objects.create(course=self.course, title='Module 1', order=1)
        self.lesson_1 = Lesson.objects.create(section=self.module, title='Lesson 1', order=1)
        self.lesson_2 = Lesson.objects.create(section=self.module, title='Lesson 2', order=2)
        self.enrollment = Enrollment.objects.create(student=self.student, course=self.course)

    def _make_question_choice(self, quiz, text='Q1?', correct='A'):
        q = Question.objects.create(quiz=quiz, text=text, question_type='multiple_choice', order=1, points=1)
        choices = {
            'A': Choice.objects.create(question=q, text='A', is_correct=correct == 'A', order=1),
            'B': Choice.objects.create(question=q, text='B', is_correct=correct == 'B', order=2),
            'C': Choice.objects.create(question=q, text='C', is_correct=correct == 'C', order=3),
            'D': Choice.objects.create(question=q, text='D', is_correct=correct == 'D', order=4),
        }
        return q, choices

    def test_lesson_unlock_requires_80_percent_pass(self):
        quiz = Quiz.objects.create(course=self.course, section=self.module, lesson=self.lesson_1, title='Lesson 1 Quiz', passing_score_percent=80)
        q, choices = self._make_question_choice(quiz, correct='A')

        self.assertTrue(is_lesson_unlocked(self.student, self.lesson_1))
        self.assertFalse(is_lesson_unlocked(self.student, self.lesson_2))

        QuizAttempt.objects.create(quiz=quiz, student=self.student, score_percent=80, passed=True)
        self.assertTrue(is_lesson_unlocked(self.student, self.lesson_2))

    def test_course_final_exam_requires_all_modules_and_lessons_complete(self):
        module_2 = Section.objects.create(course=self.course, title='Module 2', order=2)
        lesson_3 = Lesson.objects.create(section=module_2, title='Lesson 3', order=1)
        course_exam = Quiz.objects.create(course=self.course, title='Course Final Exam', passing_score_percent=80, is_final_exam=True)

        q, choices = self._make_question_choice(course_exam, correct='A')
        request = APIRequestFactory().post('/api/quizzes/%s/submit/' % course_exam.id, {'answers': [{'question_id': q.id, 'selected_choice_ids': [choices['A'].id]}]}, format='json')
        force_authenticate(request, user=self.student)

        response = QuizViewSet.as_view({'post': 'submit'})(request, pk=course_exam.id)
        self.assertEqual(response.status_code, 403)

        self.enrollment.lesson_progress.create(lesson=self.lesson_1, is_completed=True)
        self.enrollment.lesson_progress.create(lesson=self.lesson_2, is_completed=True)
        self.enrollment.lesson_progress.create(lesson=lesson_3, is_completed=True)

        request = APIRequestFactory().post('/api/quizzes/%s/submit/' % course_exam.id, {'answers': [{'question_id': q.id, 'selected_choice_ids': [choices['A'].id]}]}, format='json')
        force_authenticate(request, user=self.student)

        response = QuizViewSet.as_view({'post': 'submit'})(request, pk=course_exam.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(QuizAttempt.objects.filter(quiz=course_exam, student=self.student).exists())

    def test_certificate_is_generated_after_course_final_exam_pass(self):
        course_exam = Quiz.objects.create(course=self.course, title='Course Final Exam', passing_score_percent=80, is_final_exam=True)
        q, choices = self._make_question_choice(course_exam, correct='A')
        self.enrollment.lesson_progress.create(lesson=self.lesson_1, is_completed=True)
        self.enrollment.lesson_progress.create(lesson=self.lesson_2, is_completed=True)

        request = APIRequestFactory().post('/api/quizzes/%s/submit/' % course_exam.id, {'answers': [{'question_id': q.id, 'selected_choice_ids': [choices['A'].id]}]}, format='json')
        force_authenticate(request, user=self.student)

        response = QuizViewSet.as_view({'post': 'submit'})(request, pk=course_exam.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.enrollment.course.certificates.filter(student=self.student).exists())
