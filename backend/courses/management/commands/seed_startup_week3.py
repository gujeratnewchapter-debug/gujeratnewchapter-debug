from html import escape

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, Lesson, Section


WEEK3_LESSONS = [
    {
        'title': 'Week 3 Day 1: Business Model Canvas',
        'video_url': 'https://youtu.be/fYMkdYs2DkE',
        'notes': '''Introduction
The Business Model Canvas (BMC) is a one-page visual framework for describing how a venture creates, delivers, and captures value. It makes assumptions visible so founders can discuss and test them instead of hiding them in a long plan.

The nine building blocks
Customer segments identify the people or organizations served. The value proposition explains the important job, pain, or gain addressed. Channels describe how the venture reaches customers, while customer relationships explain how it acquires, supports, and retains them. Revenue streams show how money is earned. Key resources, key activities, and key partners describe what must exist and happen to deliver the promise. The cost structure captures the major costs and cost drivers.

Use the canvas as a hypothesis
A canvas is not proof of a business model. Label each block as observed, quoted, assumed, or targeted. Look for dependencies: a premium promise may require expensive resources, and a channel may change both acquisition cost and customer trust. Keep the first canvas simple and update it as evidence changes.

Ethiopian application
Consider language, connectivity, payment behavior, geography, trust, regulation, and local partnerships when drafting each block. A model that works in another country may require different channels, partners, and cost assumptions locally.

Activity
Draft all nine blocks for your startup idea. Circle the three assumptions that would most threaten viability if they were wrong and define an evidence-gathering action for each.

Video script
Introduce the nine BMC blocks, explain how they connect, and show why a canvas is a living set of testable assumptions rather than a finished business plan.''',
    },
    {
        'title': 'Week 3 Day 2: Lean Canvas vs Business Model Canvas',
        'video_url': 'https://youtu.be/01X5gHM9-9o',
        'notes': '''Introduction
The Lean Canvas adapts the Business Model Canvas for early-stage ventures facing high uncertainty. Both tools make a business model visible, but Lean Canvas places more emphasis on the problem, proposed solution, key metrics, and unfair advantage.

Key differences
Lean Canvas typically includes problem, solution, unique value proposition, customer segments, channels, key metrics, unfair advantage, revenue streams, and cost structure. BMC gives more space to partnerships, activities, resources, and customer relationships. Neither canvas is universally better; choose the one that matches the decision and stage.

When to use each
Use Lean Canvas when the problem and solution are still being discovered and rapid experiments are the priority. Use BMC when operations, partners, delivery capabilities, and the broader value-creation system need fuller treatment. Teams can use both, provided they keep the assumptions consistent.

Avoid false precision
A filled canvas can look complete while remaining speculative. Record the evidence behind each block, identify contradictions, and prioritize assumptions by risk and importance. Update the canvas after interviews and experiments rather than defending an old version.

Activity
Complete both canvases for the same idea. Compare the blocks that changed, select the riskiest assumption, and write one experiment with a metric and decision rule.

Video script
Compare the purpose and blocks of Lean Canvas and BMC, explain when each is useful, and connect both tools to evidence-based startup learning.''',
    },
    {
        'title': 'Week 3 Day 3: Value Proposition Design',
        'video_url': 'https://youtu.be/yWSO2pNFrDI',
        'notes': '''Introduction
Value Proposition Design connects what a customer is trying to accomplish with the products and services a venture offers. A strong value proposition is not a slogan; it is a testable claim about a specific customer, problem, and desired outcome.

Customer profile
Describe customer jobs, pains, and gains. Jobs may be functional, emotional, or social. Pains include obstacles, risks, costs, frustrations, and unwanted outcomes. Gains include required, expected, desired, or positively surprising outcomes. Base the profile on evidence instead of demographics alone.

Value map
List the products and services, pain relievers, and gain creators. A fit exists when the value map addresses important pains and gains for a real segment. Do not claim to solve every problem. Prioritize the few outcomes that matter enough to influence customer behavior.

Testing fit
Compare the proposed value with current alternatives and ask what would make a customer switch. Test language through interviews, prototypes, landing pages, demonstrations, or pilots. Look for behavior and commitment, not only polite approval.

Activity
Create a customer profile and value map for one narrow segment. Highlight the top three jobs, pains, and gains, then write a one-sentence value proposition and the evidence needed to validate it.

Video script
Build a customer profile, map products to pains and gains, and demonstrate how a value proposition becomes stronger when it focuses on important outcomes and real alternatives.''',
    },
    {
        'title': 'Week 3 Day 4: Minimum Viable Product',
        'video_url': 'https://youtu.be/DKWnZDG4rRw',
        'notes': '''Introduction
A Minimum Viable Product (MVP) is the smallest responsible experiment that delivers enough value to test a critical business assumption. It is not a careless or unfinished product and does not mean shipping unsafe or misleading work.

Choose the learning goal
Start with one risky assumption: a customer has the problem, the proposed solution helps, the customer can be reached, or someone will pay. Define the behavior that would count as evidence and a threshold that will guide the next decision.

MVP formats
An MVP may be a clickable prototype, concierge service, landing page, manual workflow, pilot, sample product, or limited feature release. Choose the format that produces reliable learning with the least effort while protecting users and their data.

Experiment design
State the hypothesis, target segment, test method, owner, time box, metric, success threshold, and stop rule. Track qualitative feedback alongside activation, completion, repeat use, conversion, retention, or payment where appropriate. Separate observed results from forecasts.

Activity
Design one MVP experiment for your idea. Specify the assumption, user segment, smallest test, metric, threshold, risks, and what you will change if the result is weak.

Video script
Define MVP precisely, distinguish it from a rushed full product, and show how a focused experiment turns uncertainty into a measurable learning decision.''',
    },
    {
        'title': 'Week 3 Day 5: Build Your Business Model Canvas',
        'video_url': 'https://youtu.be/xPDQFi7qEwI',
        'notes': '''Introduction
This practical lesson brings the week together by building a Business Model Canvas for a real startup idea. The goal is not to produce a perfect canvas but to make the model clear enough to test with customers and collaborators.

Build in sequence
Start with a narrow customer segment and the job or problem that matters to it. Write the value proposition in outcome language. Add the channel and customer relationship that fit how the segment makes decisions. Then map revenue, key resources, activities, partners, and costs. Check whether every promise has an operational and financial explanation.

Use real examples carefully
Examples from Indian unicorns can illustrate patterns such as digital distribution, platform effects, partnerships, and multiple revenue streams. They are not templates to copy. Adapt assumptions to Ethiopian customers, purchasing power, infrastructure, payment systems, language, and regulation.

Stress-test the canvas
Ask which block is least supported, which cost grows fastest, which partner is essential, and what customers use today. Mark assumptions and evidence separately. Use the Lean Canvas and value proposition work from earlier lessons to identify the first experiment.

Activity
Create a one-page BMC for your idea. Add an evidence note to every block, identify the top three risks, interview at least three target users, and revise the canvas based on what you learn.

Video script
Build a complete canvas through a practical startup example, connect each block to evidence, and finish with a prioritized experiment plan.''',
    },
]


def format_notes(text):
    headings = {
        'Introduction', 'The nine building blocks', 'Use the canvas as a hypothesis',
        'Ethiopian application', 'Key differences', 'When to use each',
        'Avoid false precision', 'Customer profile', 'Value map', 'Testing fit',
        'Choose the learning goal', 'MVP formats', 'Experiment design',
        'Build in sequence', 'Use real examples carefully', 'Stress-test the canvas',
        'Activity', 'Video script',
    }
    output = []
    for raw in text.split('\n\n'):
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            continue
        heading = lines[0]
        body = ' '.join(lines[1:])
        if heading in headings:
            if heading == 'Activity':
                output.append(f'<aside class="learning-callout"><strong>Practice activity</strong><p>{escape(body)}</p></aside>')
            elif heading == 'Video script':
                output.append(f'<aside class="learning-callout"><strong>Lesson guide</strong><p>{escape(body)}</p></aside>')
            else:
                output.append(f'<h2><strong><em>{escape(heading)}</em></strong></h2>')
                if body:
                    output.append(f'<p>{escape(body)}</p>')
        else:
            output.append(f'<p>{escape(" ".join(lines))}</p>')
    return ''.join(output)


class Command(BaseCommand):
    help = 'Create or refresh Week 3 lessons for Startup Fundamentals.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        course = Course.objects.filter(slug='startup-fundamentals-idea-to-launch').first()
        if not course:
            raise CommandError('Startup Fundamentals course does not exist. Run seed_startup_fundamentals first.')
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(WEEK3_LESSONS)} Week 3 lessons.'))
            return

        with transaction.atomic():
            for day, item in enumerate(WEEK3_LESSONS, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=13 + day,
                    defaults={'title': f'Week 3: Day {day}'},
                )
                Lesson.objects.update_or_create(
                    section=section,
                    order=1,
                    defaults={
                        'title': item['title'],
                        'lesson_type': Lesson.LessonType.VIDEO,
                        'content_text': format_notes(item['notes']),
                        'video_url': item['video_url'],
                        'duration_minutes': 60,
                        'is_preview': False,
                        'is_downloadable': True,
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            f'Created or refreshed {len(WEEK3_LESSONS)} Week 3 lessons for {course.title}.'
        ))
