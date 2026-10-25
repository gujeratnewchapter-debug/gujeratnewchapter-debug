from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, Lesson, Section


LESSON_TITLE = 'Identifying Customer Problems and Testing Business Ideas'
CONTENT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'content'
    / 'business_plan_development_lesson_2.html'
)


class Command(BaseCommand):
    help = 'Create or update only Module 1, Lesson 2 of the Business Plan Development course.'

    def handle(self, *args, **options):
        if not CONTENT_PATH.is_file():
            raise CommandError(f'Lesson 2 content file is missing: {CONTENT_PATH}')
        content = CONTENT_PATH.read_text(encoding='utf-8')

        try:
            course = Course.objects.get(slug='business-plan-development')
        except Course.DoesNotExist as exc:
            raise CommandError(
                'Business Plan Development course does not exist. '
                'Run seed_business_plan_development first.'
            ) from exc

        try:
            section = Section.objects.get(course=course, order=1)
        except Section.DoesNotExist as exc:
            raise CommandError(
                'Module 1 does not exist for Business Plan Development. '
                'Run seed_business_plan_development first.'
            ) from exc

        with transaction.atomic():
            lesson, created = Lesson.objects.update_or_create(
                section=section,
                order=2,
                defaults={
                    'title': LESSON_TITLE,
                    'lesson_type': Lesson.LessonType.TEXT,
                    'content_text': content,
                    'duration_minutes': 150,
                    'is_preview': False,
                    'is_downloadable': True,
                },
            )

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} "{lesson.title}" in {section.title} '
            f'({len(content)} characters of lesson content).'
        ))
