from django.test import TestCase
from django.test import override_settings
from rest_framework.test import APITestCase
from unittest.mock import patch

from accounts.models import User
from courses.models import Course
from .models import Conversation, KnowledgeDocument, Message
from .services import AIServiceUnavailable, get_ai_reply, retrieve_context
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


class KnowledgeRetrievalTests(TestCase):
	def setUp(self):
		self.owner = User.objects.create_user(
			username='retrieval_owner', password='pass123', role=User.Role.INSTRUCTOR,
		)
		self.course = Course.objects.create(
			title='Customer Discovery', slug='customer-discovery', description='Course',
			instructor=self.owner, status=Course.Status.PUBLISHED,
		)

	def test_retrieval_normalizes_case_and_punctuation_and_returns_cited_sources(self):
		relevant = KnowledgeDocument.objects.create(
			title='Interview Guide',
			source_type=KnowledgeDocument.SourceType.COURSE_MATERIAL,
			raw_text='Use customer interviews to validate the problem before building a startup product.',
			is_indexed=True,
		)
		KnowledgeDocument.objects.create(
			title='Distribution',
			source_type=KnowledgeDocument.SourceType.POLICY,
			raw_text='Choose marketing channels and measure campaign performance.',
			is_indexed=True,
		)
		KnowledgeDocument.objects.create(
			title='Unindexed',
			source_type=KnowledgeDocument.SourceType.COURSE_MATERIAL,
			raw_text='Customer interviews validate the problem.',
			is_indexed=False,
		)

		context, sources = retrieve_context('CUSTOMER, discovery!')

		self.assertIn('[Source: Interview Guide]', context)
		self.assertEqual(
			sources,
			[{
				'id': relevant.id,
				'title': 'Interview Guide',
				'source_type': KnowledgeDocument.SourceType.COURSE_MATERIAL,
			}],
		)

	def test_retrieval_respects_course_filter_and_top_k(self):
		course_document = KnowledgeDocument.objects.create(
			title='Course customer guide',
			source_type=KnowledgeDocument.SourceType.COURSE_MATERIAL,
			course=self.course,
			raw_text='Interview customers to validate startup demand.',
			is_indexed=True,
		)
		KnowledgeDocument.objects.create(
			title='Course customer checklist',
			source_type=KnowledgeDocument.SourceType.COURSE_MATERIAL,
			course=self.course,
			raw_text='Interview customers and validate startup demand.',
			is_indexed=True,
		)
		KnowledgeDocument.objects.create(
			title='General customer policy',
			source_type=KnowledgeDocument.SourceType.POLICY,
			raw_text='Interview customers before launching.',
			is_indexed=True,
		)

		context, sources = retrieve_context('interview customers', course=self.course, top_k=1)

		self.assertIn('[Source: Course customer guide]', context)
		self.assertEqual([source['id'] for source in sources], [course_document.id])

	def test_title_matches_rank_above_longer_body_only_matches(self):
		title_match = KnowledgeDocument.objects.create(
			title='Customer Discovery Interviews',
			source_type=KnowledgeDocument.SourceType.COURSE_MATERIAL,
			raw_text='A short practical guide.',
			is_indexed=True,
		)
		KnowledgeDocument.objects.create(
			title='General Guide',
			source_type=KnowledgeDocument.SourceType.POLICY,
			raw_text=('Customer discovery interviews ' + 'business ' * 80),
			is_indexed=True,
		)

		_, sources = retrieve_context('customer discovery interviews')

		self.assertEqual(sources[0]['id'], title_match.id)

	def test_stopword_only_query_returns_no_context(self):
		KnowledgeDocument.objects.create(
			title='Business basics',
			source_type=KnowledgeDocument.SourceType.COURSE_MATERIAL,
			raw_text='Business startup fundamentals.',
			is_indexed=True,
		)

		self.assertEqual(retrieve_context('how do I'), ('', []))


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


class PublicBusinessAdvisorTests(APITestCase):
	@patch('ai_tutor.views.get_ai_reply', return_value=('Try a small paid pilot with five customers.', []))
	def test_anonymous_users_can_ask_startup_questions(self, get_reply):
		response = self.client.post(
			'/api/ai/advisor/',
			{'question': 'How can I test demand for a new logistics startup?'},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['content'], 'Try a small paid pilot with five customers.')
		get_reply.assert_called_once_with(
			Conversation.Mode.COACH,
			[],
			'How can I test demand for a new logistics startup?',
		)

	@patch('ai_tutor.views.get_ai_reply', side_effect=AIServiceUnavailable('The provider is unavailable.'))
	def test_provider_errors_are_reported_without_a_misleading_fallback(self, _get_reply):
		response = self.client.post(
			'/api/ai/advisor/',
			{'question': 'How should I price my startup product?'},
			format='json',
		)

		self.assertEqual(response.status_code, 503)
		self.assertEqual(response.json()['detail'], 'The provider is unavailable.')

	def test_blank_or_oversized_advisor_questions_are_rejected(self):
		blank_response = self.client.post(
			'/api/ai/advisor/',
			{'question': '   '},
			format='json',
		)
		oversized_response = self.client.post(
			'/api/ai/advisor/',
			{'question': 'x' * 4001},
			format='json',
		)

		self.assertEqual(blank_response.status_code, 400)
		self.assertEqual(oversized_response.status_code, 400)
