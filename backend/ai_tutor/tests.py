from django.test import TestCase
from rest_framework.exceptions import ValidationError

from accounts.models import User
from courses.models import Course
from .serializers import ConversationSerializer, KnowledgeDocumentSerializer


class AIAuthorizationTests(TestCase):
	def setUp(self):
		self.owner = User.objects.create_user(username='ai_owner', password='pass123', role=User.Role.INSTRUCTOR)
		self.other = User.objects.create_user(username='ai_other', password='pass123', role=User.Role.INSTRUCTOR)
		self.student = User.objects.create_user(username='ai_student', password='pass123', role=User.Role.STUDENT)
		self.course = Course.objects.create(
			title='AI Course', slug='ai-course', description='Course', instructor=self.owner,
			status=Course.Status.PUBLISHED,
		)

	def test_other_instructor_cannot_attach_document_to_owned_course(self):
		request = type('Request', (), {'user': self.other})()
		serializer = KnowledgeDocumentSerializer(
			data={'title': 'Private', 'source_type': 'course_material', 'course': self.course.id},
			context={'request': request},
		)

		self.assertFalse(serializer.is_valid())
		self.assertIn('course', serializer.errors)

	def test_student_must_be_enrolled_before_course_conversation(self):
		request = type('Request', (), {'user': self.student})()
		serializer = ConversationSerializer(
			data={'course': self.course.id, 'mode': 'tutor', 'title': 'Help'},
			context={'request': request},
		)

		self.assertFalse(serializer.is_valid())
		self.assertIn('course', serializer.errors)
