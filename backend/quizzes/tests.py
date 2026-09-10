from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from courses.management.commands.seed_startup_proclamation import build_answer_choices
from courses.models import Course, Section, Lesson
from enrollments.models import Enrollment, is_lesson_unlocked
from quizzes.models import Quiz, Question, Choice, QuizAttempt
from quizzes.views import QuizViewSet

User = get_user_model()


class QuizAnswerLayoutTests(TestCase):
    def test_build_answer_choices_rotates_correct_answer_position_by_question_order(self):
        choices = build_answer_choices('Correct answer', ['Distractor A', 'Distractor B', 'Distractor C'], question_order=2)
        self.assertEqual(choices[1], 'Correct answer')
        self.assertEqual(choices[0], 'Distractor A')

    def test_content_question_bank_avoids_learner_focused_language(self):
        from courses.management.commands.seed_entrepreneurship_fundamentals import build_content_questions

        questions = build_content_questions(
            'Creativity, innovation, and problem framing',
            'This lesson frames a problem before proposing a solution.',
            'Run a short community interview and map a problem statement.',
            'Use a short conversation guide and classroom scenario.',
            'IDEO Design Thinking',
        )

        joined = ' '.join(text for text, _, _ in questions)
        self.assertNotIn('learner', joined.lower())
        self.assertIn('lesson Creativity, innovation, and problem framing', joined)


class EntrepreneurshipSeederPersistenceTests(TestCase):
    def test_entrepreneurship_seeder_refresh_drops_stale_sections_for_same_course(self):
        instructor = User.objects.create_user(
            username='entrepreneurship_instructor',
            email='entrepreneurship_instructor@example.com',
            password='pass123',
            role=User.Role.INSTRUCTOR,
        )

        # Seed an intentionally stale, older section shape for the same course.
        course = Course.objects.create(
            title='Entrepreneurship Fundamentals',
            slug='entrepreneurship-fundamentals',
            instructor=instructor,
            description='Old course',
            short_description='Old course',
            status=Course.Status.PUBLISHED,
        )
        Section.objects.create(course=course, title='Module 7: Legacy Module', order=7)
        Section.objects.create(course=course, title='Module 8: Legacy Module', order=8)

        call_command('seed_entrepreneurship_fundamentals', instructor=str(instructor.pk))

        self.assertEqual(
            Section.objects.filter(course__slug='entrepreneurship-fundamentals').count(),
            6,
        )

    def test_entrepreneurship_seeder_generates_ten_questions_for_every_lesson_quiz(self):
        instructor = User.objects.create_user(
            username='entrepreneurship_instructor_ten',
            email='entrepreneurship_instructor_ten@example.com',
            password='pass123',
            role=User.Role.INSTRUCTOR,
        )

        call_command('seed_entrepreneurship_fundamentals', instructor=str(instructor.pk))

        course = Course.objects.get(slug='entrepreneurship-fundamentals')
        lesson_quizzes = Quiz.objects.filter(course=course)
        self.assertGreater(lesson_quizzes.count(), 0)
        for quiz in lesson_quizzes:
            self.assertEqual(quiz.questions.count(), 10)

    def test_module_four_has_one_final_quiz_and_no_lesson_quizzes(self):
        instructor = User.objects.create_user(
            username='entrepreneurship_instructor_module_four',
            email='entrepreneurship_instructor_module_four@example.com',
            password='pass123',
            role=User.Role.INSTRUCTOR,
        )

        call_command('seed_entrepreneurship_fundamentals', instructor=str(instructor.pk))

        course = Course.objects.get(slug='entrepreneurship-fundamentals')
        module = Section.objects.get(course=course, order=4)
        self.assertEqual(module.lessons.count(), 9)
        self.assertFalse(Quiz.objects.filter(section=module, lesson__isnull=False).exists())
        final_quizzes = Quiz.objects.filter(section=module, lesson__isnull=True, is_final_exam=True)
        self.assertEqual(final_quizzes.count(), 1)
        self.assertEqual(final_quizzes.first().questions.count(), 10)

    def test_module_four_final_quiz_controls_access_to_module_five(self):
        instructor = User.objects.create_user(
            username='entrepreneurship_instructor_unlock',
            email='entrepreneurship_instructor_unlock@example.com',
            password='pass123',
            role=User.Role.INSTRUCTOR,
        )
        student = User.objects.create_user(
            username='entrepreneurship_student_unlock',
            email='entrepreneurship_student_unlock@example.com',
            password='pass123',
            role=User.Role.STUDENT,
        )

        call_command('seed_entrepreneurship_fundamentals', instructor=str(instructor.pk))

        course = Course.objects.get(slug='entrepreneurship-fundamentals')
        module_four = Section.objects.get(course=course, order=4)
        module_five = Section.objects.get(course=course, order=5)
        final_quiz = Quiz.objects.get(section=module_four, is_final_exam=True, lesson__isnull=True)
        next_lesson = module_five.lessons.first()

        self.assertFalse(is_lesson_unlocked(student, next_lesson))
        failed_attempt = QuizAttempt.objects.create(
            quiz=final_quiz,
            student=student,
            score_percent=79,
            passed=False,
        )
        self.assertFalse(is_lesson_unlocked(student, next_lesson))
        failed_attempt.delete()
        QuizAttempt.objects.create(
            quiz=final_quiz,
            student=student,
            score_percent=80,
            passed=True,
        )
        self.assertTrue(is_lesson_unlocked(student, next_lesson))

    def test_module_five_has_one_final_quiz_and_controls_access_to_module_six(self):
        instructor = User.objects.create_user(
            username='entrepreneurship_instructor_module_five',
            email='entrepreneurship_instructor_module_five@example.com',
            password='pass123',
            role=User.Role.INSTRUCTOR,
        )
        student = User.objects.create_user(
            username='entrepreneurship_student_module_five',
            email='entrepreneurship_student_module_five@example.com',
            password='pass123',
            role=User.Role.STUDENT,
        )

        call_command('seed_entrepreneurship_fundamentals', instructor=str(instructor.pk))

        course = Course.objects.get(slug='entrepreneurship-fundamentals')
        module_five = Section.objects.get(course=course, order=5)
        module_six = Section.objects.get(course=course, order=6)
        final_quiz = Quiz.objects.get(section=module_five, is_final_exam=True, lesson__isnull=True)
        next_lesson = module_six.lessons.first()

        self.assertEqual(module_five.lessons.count(), 12)
        self.assertFalse(Quiz.objects.filter(section=module_five, lesson__isnull=False).exists())
        self.assertEqual(final_quiz.questions.count(), 10)
        self.assertFalse(is_lesson_unlocked(student, next_lesson))

        QuizAttempt.objects.create(quiz=final_quiz, student=student, score_percent=79, passed=False)
        self.assertFalse(is_lesson_unlocked(student, next_lesson))
        QuizAttempt.objects.create(quiz=final_quiz, student=student, score_percent=80, passed=True)
        self.assertTrue(is_lesson_unlocked(student, next_lesson))

    def test_module_six_has_one_final_quiz_and_no_lesson_quizzes(self):
        instructor = User.objects.create_user(
            username='entrepreneurship_instructor_module_six',
            email='entrepreneurship_instructor_module_six@example.com',
            password='pass123',
            role=User.Role.INSTRUCTOR,
        )

        call_command('seed_entrepreneurship_fundamentals', instructor=str(instructor.pk))

        course = Course.objects.get(slug='entrepreneurship-fundamentals')
        module = Section.objects.get(course=course, order=6)
        final_quizzes = Quiz.objects.filter(section=module, lesson__isnull=True, is_final_exam=True)

        self.assertEqual(module.lessons.count(), 6)
        self.assertFalse(Quiz.objects.filter(section=module, lesson__isnull=False).exists())
        self.assertEqual(final_quizzes.count(), 1)
        self.assertEqual(final_quizzes.first().questions.count(), 10)


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

    def test_quiz_submission_requires_enrollment(self):
        outsider = User.objects.create_user(
            username='quiz_outsider', email='quiz_outsider@example.com', password='pass123', role=User.Role.STUDENT,
        )
        quiz = Quiz.objects.create(course=self.course, section=self.module, lesson=self.lesson_1, title='Lesson Quiz')
        question, choices = self._make_question_choice(quiz, correct='A')
        request = APIRequestFactory().post(
            f'/api/quizzes/{quiz.id}/submit/',
            {'answers': [{'question_id': question.id, 'selected_choice_ids': [choices['A'].id]}]},
            format='json',
        )
        force_authenticate(request, user=outsider)

        response = QuizViewSet.as_view({'post': 'submit'})(request, pk=quiz.id)

        self.assertIn(response.status_code, (403, 404))
        self.assertFalse(QuizAttempt.objects.filter(student=outsider).exists())

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
