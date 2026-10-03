from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APITestCase

from courses.models import Course, Lesson, Section
from enrollments.models import Enrollment
from quizzes.models import Quiz, QuizAttempt


User = get_user_model()


class EnrolledCourseDetailPerformanceTests(APITestCase):
    def setUp(self):
        instructor = User.objects.create_user(
            username='performance-instructor',
            email='performance-instructor@example.com',
            password='Password123!',
            role=User.Role.INSTRUCTOR,
        )
        student = User.objects.create_user(
            username='performance-student',
            email='performance-student@example.com',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        course = Course.objects.create(
            title='Large Course',
            slug='large-course',
            description='Course with a large curriculum.',
            instructor=instructor,
            status=Course.Status.PUBLISHED,
        )
        section = Section.objects.create(course=course, title='Module 1', order=1)
        lessons = [
            Lesson.objects.create(section=section, title=f'Lesson {order}', order=order)
            for order in range(1, 43)
        ]
        quiz = Quiz.objects.create(
            course=course,
            section=section,
            lesson=lessons[0],
            title='Lesson 1 quiz',
        )
        Enrollment.objects.create(student=student, course=course)
        QuizAttempt.objects.create(
            quiz=quiz,
            student=student,
            passed=True,
            score_percent=100,
        )
        self.client.force_authenticate(student)
        self.course = course
        self.lessons = lessons

    def test_enrolled_large_course_detail_uses_bounded_queries(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('course-detail', args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        serialized_lessons = [
            lesson
            for section_data in response.data['sections']
            for lesson in section_data['lessons']
        ]
        self.assertEqual(len(serialized_lessons), len(self.lessons))
        self.assertTrue(all(lesson['is_unlocked'] for lesson in serialized_lessons))
        self.assertLessEqual(len(queries), 12)

    def test_enrolled_large_course_lesson_uses_bounded_queries(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('lesson-detail', args=[self.lessons[0].id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.lessons[0].id)
        self.assertLessEqual(len(queries), 12)
