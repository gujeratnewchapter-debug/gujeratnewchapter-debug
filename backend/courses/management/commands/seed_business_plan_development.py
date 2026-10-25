from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.html import escape

from courses.models import Category, Course, Lesson, Section


MODULES = (
    (
        'Foundations of Business Planning',
        (
            'Introduction to Startup Business Planning',
            'Identifying Customer Problems and Testing Business Ideas',
            'Developing a Value Proposition and Setting Business Objectives',
        ),
    ),
    (
        'Market Research and Business Strategy',
        (
            'Market Research, Target Customers, and Competitor Analysis',
            'Business Models, Revenue Streams, and Pricing',
            'Marketing, Sales, Operations, and Team Planning',
        ),
    ),
    (
        'Financial Planning and the Complete Business Plan',
        (
            'Startup Costs, Funding Requirements, and Financial Assumptions',
            'Financial Projections: Income Statement, Cash Flow, Balance Sheet, and Break-Even Analysis',
            'Writing, Presenting, and Improving the Complete Business Plan',
        ),
    ),
)

LESSON_CONTENT_DIR = Path(__file__).resolve().parents[2] / 'content'
LESSON_DURATIONS_MINUTES = (90, 150, 120, 150, 135, 150, 135, 165, 150)


def build_course_outline():
    modules = []
    for module_order, (module_title, lesson_titles) in enumerate(MODULES, start=1):
        lessons = ''.join(f'<li>{escape(title)}</li>' for title in lesson_titles)
        modules.append(f'<h3>Module {module_order}: {escape(module_title)}</h3><ol>{lessons}</ol>')
    return '<h2>Course structure</h2>' + ''.join(modules)


class Command(BaseCommand):
    help = 'Create or update the Business Plan Development course and all nine detailed lessons.'

    def add_arguments(self, parser):
        parser.add_argument('--instructor', help='Instructor username or user ID.')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        instructor = self._get_instructor(options.get('instructor'))
        lesson_contents = {}
        for lesson_number in range(1, 10):
            content_path = LESSON_CONTENT_DIR / f'business_plan_development_lesson_{lesson_number}.html'
            if not content_path.is_file():
                raise CommandError(f'Lesson content file is missing: {content_path}')
            lesson_contents[lesson_number] = content_path.read_text(encoding='utf-8')
        total_lessons = sum(len(lessons) for _, lessons in MODULES)
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'Validated 3 modules, {total_lessons} lesson entries, and all nine detailed lesson files.'
            ))
            return

        with transaction.atomic():
            category, _ = Category.objects.get_or_create(
                slug='business',
                defaults={'name': 'Business'},
            )
            course, created = Course.objects.update_or_create(
                slug='business-plan-development',
                defaults={
                    'title': 'Business Plan Development',
                    'subtitle': 'From startup foundations to a complete, evidence-informed plan',
                    'description': (
                        '<h2>Business Plan Development</h2>'
                        '<p>Build a practical business plan, starting with a customer problem and progressing '
                        'through market research, business strategy, operations, financial planning, and a '
                        'clear final presentation.</p>'
                    ),
                    'short_description': (
                        'Learn to develop an evidence-informed business plan, one practical step at a time.'
                    ),
                    'notes': build_course_outline(),
                    'notes_enabled': True,
                    'learning_objectives': (
                        'Explain startup planning; identify and test customer problems; develop a value proposition '
                        'and objectives; research customers and competitors; choose a business model and pricing '
                        'approach; plan marketing, operations, and a team; estimate startup costs and funding needs; '
                        'prepare financial projections; and write and present a complete business plan.'
                    ),
                    'requirements': 'No prior business experience is required.',
                    'target_audience': (
                        'Aspiring entrepreneurs, startup teams, students, and small-business owners.'
                    ),
                    'tags': (
                        'business plan, business planning, entrepreneurship, startup, market research, finance'
                    ),
                    'instructor': instructor,
                    'category': category,
                    'level': Course.Level.BEGINNER,
                    'price': 0,
                    'is_free': True,
                    'language': 'English',
                    'duration_hours': (sum(LESSON_DURATIONS_MINUTES) + 59) // 60,
                },
            )

            lesson_number = 0
            section_ids = []
            extra_lessons = 0
            for module_order, (module_title, lesson_titles) in enumerate(MODULES, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=module_order,
                    defaults={'title': f'Module {module_order}: {module_title}'},
                )
                section_ids.append(section.pk)
                lesson_ids = []

                for lesson_order, lesson_title in enumerate(lesson_titles, start=1):
                    lesson_number += 1
                    lesson, _ = Lesson.objects.update_or_create(
                        section=section,
                        order=lesson_order,
                        defaults={
                            'title': lesson_title,
                            'lesson_type': Lesson.LessonType.TEXT,
                            'content_text': lesson_contents[lesson_number],
                            'duration_minutes': LESSON_DURATIONS_MINUTES[lesson_number - 1],
                            'is_preview': lesson_number == 1,
                            'is_downloadable': True,
                        },
                    )
                    lesson_ids.append(lesson.pk)

                stale_lessons = Lesson.objects.filter(section=section).exclude(pk__in=lesson_ids)
                extra_lessons += stale_lessons.count()
                stale_lessons.delete()

            stale_sections = Section.objects.filter(course=course).exclude(pk__in=section_ids)
            extra_sections = stale_sections.count()
            extra_lessons += Lesson.objects.filter(section__in=stale_sections).count()
            stale_sections.delete()

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} course "{course.title}" with 3 modules and {total_lessons} detailed lessons.'
        ))
        if extra_sections or extra_lessons:
            self.stdout.write(self.style.WARNING(
                f'Removed {extra_sections} outdated module(s) and {extra_lessons} outdated lesson(s) '
                'from this course. Related lesson/module records are also removed by database cascades.'
            ))

    def _get_instructor(self, identifier):
        user_model = get_user_model()
        instructors = user_model.objects.filter(role='instructor')
        if identifier:
            try:
                user = instructors.filter(pk=identifier).first()
            except (TypeError, ValueError):
                user = None
            if user is None:
                user = instructors.filter(username=identifier).first()
            if user:
                return user
            raise CommandError(f'Instructor not found: {identifier}')

        instructor = instructors.order_by('id').first()
        if instructor:
            return instructor

        administrator = user_model.objects.filter(is_superuser=True).order_by('id').first()
        if administrator:
            self.stdout.write(self.style.WARNING(
                'No instructor account exists; assigning the course to the first superuser.'
            ))
            return administrator

        raise CommandError(
            'No instructor or superuser exists. Create one in Django admin or pass --instructor.'
        )
