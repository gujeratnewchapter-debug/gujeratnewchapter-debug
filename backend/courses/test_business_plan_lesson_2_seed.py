from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

from courses.models import Course, Lesson, Section


class BusinessPlanDevelopmentLessonTwoSeedTests(TestCase):
    def setUp(self):
        instructor = get_user_model().objects.create_user(
            username='lesson-two-instructor',
            email='lesson-two-instructor@example.com',
            password='Password123!',
            role='instructor',
        )
        self.course = Course.objects.create(
            title='Business Plan Development',
            slug='business-plan-development',
            description='Business planning course',
            instructor=instructor,
        )
        self.module_one = Section.objects.create(
            course=self.course,
            title='Module 1: Foundations of Business Planning',
            order=1,
        )
        self.lesson_one = Lesson.objects.create(
            section=self.module_one,
            title='Introduction to Startup Business Planning',
            lesson_type=Lesson.LessonType.TEXT,
            order=1,
            content_text='<p>Existing Lesson 1 content remains unchanged.</p>',
            is_preview=True,
        )
        self.lesson_two = Lesson.objects.create(
            section=self.module_one,
            title='Old Lesson 2 placeholder',
            lesson_type=Lesson.LessonType.TEXT,
            order=2,
            content_text='<p>Placeholder to be replaced.</p>',
        )
        self.other_module = Section.objects.create(
            course=self.course,
            title='Existing additional section',
            order=4,
        )
        self.other_lesson = Lesson.objects.create(
            section=self.other_module,
            title='Existing additional lesson',
            lesson_type=Lesson.LessonType.TEXT,
            order=1,
            content_text='<p>Must remain unchanged.</p>',
        )

    def test_seed_updates_only_module_one_lesson_two_with_full_attachment_content(self):
        call_command('seed_business_plan_development_lesson_2')

        self.lesson_one.refresh_from_db()
        self.lesson_two.refresh_from_db()
        self.other_module.refresh_from_db()
        self.other_lesson.refresh_from_db()

        self.assertEqual(self.lesson_one.content_text, '<p>Existing Lesson 1 content remains unchanged.</p>')
        self.assertEqual(self.lesson_one.title, 'Introduction to Startup Business Planning')
        self.assertEqual(self.lesson_two.title, 'Identifying Customer Problems and Testing Business Ideas')
        self.assertEqual(self.lesson_two.lesson_type, Lesson.LessonType.TEXT)
        self.assertEqual(self.lesson_two.duration_minutes, 150)
        self.assertFalse(self.lesson_two.is_preview)
        self.assertGreater(len(self.lesson_two.content_text), 10000)
        for expected in (
            'Learning outcomes',
            'Detailed 150-minute facilitation plan',
            'Learner worksheet 1: define the customer and problem',
            'Learner worksheet 4: experiment card',
            'Homework assignment: customer problem evidence and test plan',
            'Source materials and references',
            'https://www.designkit.org/methods/2.html',
        ):
            self.assertIn(expected, self.lesson_two.content_text)

        self.assertEqual(self.other_module.title, 'Existing additional section')
        self.assertEqual(self.other_lesson.content_text, '<p>Must remain unchanged.</p>')

    def test_seed_is_idempotent(self):
        call_command('seed_business_plan_development_lesson_2')
        first_content = self.module_one.lessons.get(order=2).content_text

        call_command('seed_business_plan_development_lesson_2')

        self.assertEqual(self.module_one.lessons.count(), 2)
        self.assertEqual(self.module_one.lessons.get(order=2).content_text, first_content)

    def test_seed_fails_clearly_when_parent_course_is_missing(self):
        self.course.delete()

        with self.assertRaisesMessage(CommandError, 'Business Plan Development course does not exist'):
            call_command('seed_business_plan_development_lesson_2')
