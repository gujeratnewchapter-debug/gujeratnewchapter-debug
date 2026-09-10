from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course
from quizzes.models import Choice, Question, Quiz


def build_answer_choices(correct_answer, distractors, question_order):
    """Return answer choices with the correct answer placed at a rotated letter slot."""
    choices = [correct_answer, *distractors]
    target_position = (question_order - 1) % len(choices)
    if target_position == 0:
        return choices

    correct_text = choices[0]
    remaining = choices[1:]
    return remaining[:target_position] + [correct_text] + remaining[target_position:]


QUESTIONS = [
    ('What is the first step in validating a startup idea?', 'Understand a meaningful customer problem', ['Choose a logo', 'Rent an office', 'Set a valuation']),
    ('Which canvas helps make a startup business model visible?', 'Business Model Canvas', ['Payroll register', 'Balance sheet only', 'Press release']),
    ('What does an MVP primarily test?', 'A critical business assumption with limited effort', ['Every possible feature', 'A guaranteed valuation', 'A completed IPO']),
    ('Which measure is most useful for durable customer value?', 'Retention over a defined cohort period', ['Raw page views', 'Logo impressions', 'Number of pitch slides']),
    ('What does CAC mean?', 'Customer acquisition cost', ['Cash accounting cycle', 'Customer activity count', 'Capital allocation certificate']),
    ('What should a responsible financial plan distinguish?', 'Observed results, assumptions, targets, and forecasts', ['Facts and rumors as identical', 'Revenue and cash as identical', 'Risks and guarantees as identical']),
    ('What is a key purpose of a founding-team working agreement?', 'Clarify ownership, decisions, conduct, and accountability', ['Guarantee investment', 'Replace employment law', 'Avoid customer feedback']),
    ('What should a pitch deck communicate?', 'Problem, customer, solution, evidence, model, team, risks, and ask', ['Only the founder biography', 'Only the largest market number', 'Only visual effects']),
    ('What is responsible scaling?', 'Growing delivery while protecting quality, people, customers, and cash', ['Increasing spending without evidence', 'Hiding operational defects', 'Expanding before validating the core offer']),
    ('What happens when a learner passes the final exam at 80% or above?', 'The course is completed and a certificate is generated automatically', ['The account is deleted', 'All answers are erased', 'The learner must pay again']),
]


class Command(BaseCommand):
    help = 'Create or refresh the Startup Fundamentals final exam.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        course = Course.objects.filter(slug='startup-fundamentals-idea-to-launch').first()
        if not course:
            raise CommandError('Startup Fundamentals course does not exist.')
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(QUESTIONS)} final exam questions.'))
            return

        with transaction.atomic():
            exam, _ = Quiz.objects.update_or_create(
                course=course,
                lesson=None,
                section=None,
                is_final_exam=True,
                defaults={
                    'title': f'{course.title} Final Exam',
                    'passing_score_percent': 80,
                    'max_attempts': 0,
                    'time_limit_minutes': 60,
                    'randomize_questions': False,
                },
            )
            exam.questions.all().delete()
            for order, (text, answer, distractors) in enumerate(QUESTIONS, start=1):
                question = exam.questions.create(
                    text=text,
                    question_type=Question.QuestionType.MULTIPLE_CHOICE,
                    order=order,
                    points=1,
                )
                answer_choices = build_answer_choices(answer, distractors, order)
                for choice_order, choice_text in enumerate(answer_choices):
                    Choice.objects.create(
                        question=question,
                        text=choice_text,
                        is_correct=choice_text == answer,
                        order=choice_order,
                    )

        self.stdout.write(self.style.SUCCESS(f'Created or refreshed the final exam for {course.title}.'))