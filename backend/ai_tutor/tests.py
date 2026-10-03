from django.test import TestCase
from django.test import override_settings
from rest_framework.test import APITestCase
from unittest.mock import patch

from accounts.models import User
from courses.models import Course
from .models import Conversation, Message
from .services import AIServiceUnavailable, get_ai_reply
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


class AIMessageTests(APITestCase):
	def setUp(self):
		self.student = User.objects.create_user(
			username='ai_message_student', password='pass123', role=User.Role.STUDENT,
		)
		self.conversation = Conversation.objects.create(student=self.student)
		self.client.force_authenticate(self.student)

	@patch('ai_tutor.views.get_ai_reply', side_effect=AIServiceUnavailable('AI provider is unavailable.'))
	def test_provider_failure_returns_503_without_saving_a_fake_reply(self, _get_ai_reply):
		response = self.client.post(
			f'/api/ai/conversations/{self.conversation.id}/send_message/',
			{'content': 'How do I validate a business idea?'},
			format='json',
		)

		self.assertEqual(response.status_code, 503)
		self.assertEqual(
			response.json()['detail'],
			'AI provider is unavailable.',
		)
		self.assertFalse(Message.objects.filter(conversation=self.conversation).exists())

	@override_settings(OPENAI_API_KEY='', OPENROUTER_API_KEY='')
	def test_unconfigured_provider_returns_actionable_api_error(self):
		response = self.client.post(
			f'/api/ai/conversations/{self.conversation.id}/send_message/',
			{'content': 'How do I validate a business idea?'},
			format='json',
		)

		self.assertEqual(response.status_code, 503)
		self.assertIn('not configured', response.json()['detail'])
		self.assertFalse(Message.objects.filter(conversation=self.conversation).exists())

	@patch('ai_tutor.views.get_ai_reply', return_value=('Validate with customers.', []))
	def test_current_prompt_is_not_duplicated_in_provider_history(self, get_reply):
		response = self.client.post(
			f'/api/ai/conversations/{self.conversation.id}/send_message/',
			{'content': 'How do I validate a business idea?'},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		get_reply.assert_called_once_with(
			Conversation.Mode.TUTOR,
			[],
			'How do I validate a business idea?',
			course=None,
		)
		self.assertEqual(
			list(self.conversation.messages.values_list('role', 'content')),
			[
				(Message.Role.USER, 'How do I validate a business idea?'),
				(Message.Role.ASSISTANT, 'Validate with customers.'),
			],
		)

	def test_missing_provider_key_is_reported_as_unavailable(self):
		with override_settings(OPENAI_API_KEY='', OPENROUTER_API_KEY=''):
			with self.assertRaises(AIServiceUnavailable) as context:
				get_ai_reply('tutor', [], 'How do I validate a business idea?')

		self.assertIn('not configured', str(context.exception))
