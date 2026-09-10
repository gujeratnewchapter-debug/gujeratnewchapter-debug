from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import User
from courses.models import Course, Section, Lesson
from enrollments.models import Enrollment
from quizzes.models import Quiz
from .views import EnrollmentViewSet


class EnrollmentIntegrityTests(TestCase):
	def setUp(self):
		self.instructor = User.objects.create_user(
			username='enrollment_owner', password='pass123', role=User.Role.INSTRUCTOR,
		)
		self.student = User.objects.create_user(
			username='enrollment_student', password='pass123', role=User.Role.STUDENT,
		)
		self.course = Course.objects.create(
			title='Enrollment Course', slug='enrollment-course', description='Course',
			instructor=self.instructor, status=Course.Status.PUBLISHED,
		)
		self.section = Section.objects.create(course=self.course, title='Module 1', order=1)
		self.lesson = Lesson.objects.create(section=self.section, title='Lesson 1', order=1)
		self.enrollment = Enrollment.objects.create(student=self.student, course=self.course)

	def test_lesson_with_quiz_cannot_be_completed_before_passing(self):
		quiz = Quiz.objects.create(course=self.course, section=self.section, lesson=self.lesson, title='Lesson Quiz')
		request = APIRequestFactory().post(
			f'/api/enrollments/{self.enrollment.id}/mark_lesson_complete/',
			{'lesson_id': self.lesson.id},
			format='json',
		)
		force_authenticate(request, user=self.student)

		response = EnrollmentViewSet.as_view({'post': 'mark_lesson_complete'})(request, pk=self.enrollment.id)

		self.assertEqual(response.status_code, 403)
		self.assertFalse(self.enrollment.lesson_progress.filter(lesson=self.lesson).exists())

	def test_invalid_lesson_id_returns_not_found(self):
		request = APIRequestFactory().post(
			f'/api/enrollments/{self.enrollment.id}/mark_lesson_complete/',
			{'lesson_id': 'not-a-number'},
			format='json',
		)
		force_authenticate(request, user=self.student)

		response = EnrollmentViewSet.as_view({'post': 'mark_lesson_complete'})(request, pk=self.enrollment.id)

		self.assertEqual(response.status_code, 404)
