from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Category, Course, Section, Lesson, Resource
from quizzes.models import Quiz, QuizAttempt

User = get_user_model()


class LessonAndResourceAuthorizationTests(APITestCase):
	def setUp(self):
		self.instructor = User.objects.create_user(
			username='course-owner', email='owner@example.com', password='Password123!', role=User.Role.INSTRUCTOR,
		)
		self.other_instructor = User.objects.create_user(
			username='other-owner', email='other@example.com', password='Password123!', role=User.Role.INSTRUCTOR,
		)
		self.student = User.objects.create_user(
			username='course-student', email='student@example.com', password='Password123!', role=User.Role.STUDENT,
		)
		self.other_student = User.objects.create_user(
			username='other-student', email='other-student@example.com', password='Password123!', role=User.Role.STUDENT,
		)
		self.course = Course.objects.create(
			title='Course', slug='course', description='Course', short_description='Course',
			instructor=self.instructor, status=Course.Status.PUBLISHED,
		)
		self.section = Section.objects.create(course=self.course, title='Module 1', order=1)
		self.preview_lesson = Lesson.objects.create(section=self.section, title='Preview', order=1, is_preview=True)
		self.locked_lesson = Lesson.objects.create(section=self.section, title='Locked', order=2)
		self.quiz = Quiz.objects.create(
			course=self.course, section=self.section, lesson=self.preview_lesson,
			title='Preview Quiz', passing_score_percent=80,
		)
		self.resource = Resource.objects.create(
			lesson=self.preview_lesson, title='Resource', resource_type=Resource.ResourceType.FILE,
			url='https://example.com/resource.pdf',
		)

	def test_unauthorized_user_cannot_read_non_preview_lesson(self):
		response = self.client.get(reverse('lesson-detail', args=[self.locked_lesson.id]))
		self.assertIn(response.status_code, (403, 404))

	def test_enrolled_user_cannot_read_locked_lesson(self):
		from enrollments.models import Enrollment
		Enrollment.objects.create(student=self.student, course=self.course)
		self.client.force_authenticate(self.student)

		response = self.client.get(reverse('lesson-detail', args=[self.locked_lesson.id]))
		self.assertIn(response.status_code, (403, 404))

	def test_preview_lesson_is_publicly_readable(self):
		response = self.client.get(reverse('lesson-detail', args=[self.preview_lesson.id]))
		self.assertEqual(response.status_code, 200)

	def test_course_detail_hides_locked_lesson_identifiers_and_urls(self):
		response = self.client.get(reverse('course-detail', args=[self.course.id]))
		self.assertEqual(response.status_code, 200)
		locked = next(item for item in response.json()['sections'][0]['lessons'] if item['title'] == 'Locked')
		self.assertNotIn('id', locked)
		self.assertNotIn('video_url', locked)
		self.assertFalse(locked['is_unlocked'])

	def test_course_write_serializer_removes_unsafe_html(self):
		from .serializers import CourseWriteSerializer
		serializer = CourseWriteSerializer(data={
			'title': 'Safe course',
			'slug': 'safe-course',
			'description': '<p>Useful</p><script>alert(1)</script><a href="javascript:alert(2)">link</a>',
			'instructor': self.instructor.id,
		})
		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertNotIn('<script', serializer.validated_data['description'])
		self.assertNotIn('javascript:', serializer.validated_data['description'])

	def test_enrolled_user_can_read_unlocked_lesson(self):
		from enrollments.models import Enrollment
		Enrollment.objects.create(student=self.student, course=self.course)
		self.client.force_authenticate(self.student)

		response = self.client.get(reverse('lesson-detail', args=[self.preview_lesson.id]))
		self.assertEqual(response.status_code, 200)

	def test_passed_previous_quiz_unlocks_next_lesson_api_read(self):
		from enrollments.models import Enrollment
		Enrollment.objects.create(student=self.student, course=self.course)
		QuizAttempt.objects.create(quiz=self.quiz, student=self.student, passed=True, score_percent=80)
		self.client.force_authenticate(self.student)

		response = self.client.get(reverse('lesson-detail', args=[self.locked_lesson.id]))
		self.assertEqual(response.status_code, 200)

	def test_student_cannot_create_course(self):
		self.client.force_authenticate(self.student)
		response = self.client.post(
			reverse('course-list'),
			{'title': 'Unauthorized', 'slug': 'unauthorized', 'description': 'x'},
			format='json',
		)
		self.assertEqual(response.status_code, 403)

	def test_direct_lesson_id_does_not_bypass_lock(self):
		self.client.force_authenticate(self.other_student)
		response = self.client.get(f'/api/lessons/{self.locked_lesson.id}/')
		self.assertIn(response.status_code, (403, 404))

	def test_non_owner_cannot_update_or_delete_resource(self):
		self.client.force_authenticate(self.other_instructor)

		update_response = self.client.patch(
			reverse('resource-detail', args=[self.resource.id]), {'title': 'Changed'}, format='json',
		)
		delete_response = self.client.delete(reverse('resource-detail', args=[self.resource.id]))

		self.assertIn(update_response.status_code, (403, 404))
		self.assertIn(delete_response.status_code, (403, 404))

	def test_owner_can_update_resource(self):
		self.client.force_authenticate(self.instructor)
		response = self.client.patch(
			reverse('resource-detail', args=[self.resource.id]), {'title': 'Changed'}, format='json',
		)
		self.assertEqual(response.status_code, 200)
