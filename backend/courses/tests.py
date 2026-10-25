from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
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

	def test_enrolled_student_can_open_first_lesson_from_course_detail(self):
		from enrollments.models import Enrollment
		Enrollment.objects.create(student=self.student, course=self.course)
		self.client.force_authenticate(self.student)

		response = self.client.get(reverse('course-detail', args=[self.course.id]))

		self.assertEqual(response.status_code, 200)
		first_lesson = response.json()['sections'][0]['lessons'][0]
		self.assertEqual(first_lesson['id'], self.preview_lesson.id)
		self.assertTrue(first_lesson['is_unlocked'])

	def test_enrolled_student_can_access_each_lesson_without_quiz_gates(self):
		from enrollments.models import Enrollment

		course = Course.objects.create(
			title='Accessible Course', slug='accessible-course', description='Course',
			instructor=self.instructor,
			status=Course.Status.PUBLISHED,
		)
		section = Section.objects.create(course=course, title='Module 1', order=1)
		lessons = [
			Lesson.objects.create(section=section, title=f'Lesson {index}', order=index)
			for index in range(1, 4)
		]
		Enrollment.objects.create(student=self.student, course=course)
		self.client.force_authenticate(self.student)

		course_response = self.client.get(reverse('course-detail', args=[course.id]))

		self.assertEqual(course_response.status_code, 200)
		lesson_ids = [
			lesson['id']
			for section_data in course_response.json()['sections']
			for lesson in section_data['lessons']
		]
		self.assertEqual(lesson_ids, [lesson.id for lesson in lessons])
		for lesson in lessons:
			response = self.client.get(reverse('lesson-detail', args=[lesson.id]))
			self.assertEqual(response.status_code, 200)

	def test_course_detail_prefetches_curriculum_queries(self):
		for section_order in range(2, 8):
			section = Section.objects.create(course=self.course, title=f'Module {section_order}', order=section_order)
			for lesson_order in range(1, 4):
				Lesson.objects.create(section=section, title=f'Lesson {section_order}-{lesson_order}', order=lesson_order)

		with CaptureQueriesContext(connection) as queries:
			response = self.client.get(reverse('course-detail', args=[self.course.id]))

		self.assertEqual(response.status_code, 200)
		self.assertLessEqual(len(queries), 8)

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


class BusinessPlanDevelopmentSeedTests(TestCase):
	def setUp(self):
		self.instructor = User.objects.create_user(
			username='business-plan-instructor',
			email='business-plan-instructor@example.com',
			password='Password123!',
			role=User.Role.INSTRUCTOR,
		)

	def test_seed_creates_requested_curriculum_and_complete_first_lesson(self):
		call_command('seed_business_plan_development')

		course = Course.objects.get(slug='business-plan-development')
		sections = list(course.sections.order_by('order'))
		self.assertEqual(course.status, Course.Status.DRAFT)
		self.assertTrue(course.notes_enabled)
		self.assertIn('Module 1: Foundations of Business Planning', course.notes)
		self.assertIn(
			'Writing, Presenting, and Improving the Complete Business Plan',
			course.notes,
		)
		self.assertEqual(len(sections), 3)
		self.assertEqual(
			[section.title for section in sections],
			[
				'Module 1: Foundations of Business Planning',
				'Module 2: Market Research and Business Strategy',
				'Module 3: Financial Planning and the Complete Business Plan',
			],
		)
		self.assertEqual(course.total_lessons, 9)

		lesson = sections[0].lessons.get(order=1)
		self.assertEqual(lesson.title, 'Introduction to Startup Business Planning')
		self.assertEqual(lesson.lesson_type, Lesson.LessonType.TEXT)
		self.assertTrue(lesson.is_preview)
		self.assertIn('Practical assignment: one-page initial business idea brief', lesson.content_text)
		self.assertIn('Answer key:</strong> 1-B, 2-B, 3-C, 4-B, 5-C.', lesson.content_text)
		self.assertGreater(len(lesson.content_text), 5000)
		lesson_two = sections[0].lessons.get(order=2)
		self.assertEqual(
			lesson_two.title,
			'Identifying Customer Problems and Testing Business Ideas',
		)
		self.assertIn('Learner worksheet 4: experiment card', lesson_two.content_text)
		for section in sections:
			for seeded_lesson in section.lessons.all():
				self.assertNotIn(
					'Full lesson content will be added in a later update',
					seeded_lesson.content_text,
				)
				self.assertGreater(len(seeded_lesson.content_text), 3000)
		self.assertEqual(
			[
				lesson.duration_minutes
				for section in sections
				for lesson in section.lessons.all()
			],
			[90, 150, 120, 150, 135, 150, 135, 165, 150],
		)

	def test_seed_is_idempotent(self):
		call_command('seed_business_plan_development')
		course = Course.objects.get(slug='business-plan-development')
		course.status = Course.Status.PUBLISHED
		course.save(update_fields=['status'])

		call_command('seed_business_plan_development')

		course.refresh_from_db()
		self.assertEqual(course.status, Course.Status.PUBLISHED)
		self.assertTrue(course.notes_enabled)
		self.assertEqual(course.sections.count(), 3)
		self.assertEqual(course.total_lessons, 9)

	def test_seed_uses_superuser_when_no_instructor_exists(self):
		self.instructor.delete()
		administrator = User.objects.create_superuser(
			username='business-plan-admin',
			email='business-plan-admin@example.com',
			password='Password123!',
		)

		call_command('seed_business_plan_development')

		course = Course.objects.get(slug='business-plan-development')
		self.assertEqual(course.instructor, administrator)
