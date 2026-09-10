from html import escape

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, Lesson, Section


WEEK4_LESSONS = [
    {
        'title': 'Week 4 Day 1: Customer Segmentation and Persona Creation',
        'video_url': 'https://youtu.be/2gmystOnM6k',
        'notes': '''Introduction
Market research starts by deciding whose problem you are trying to understand. Customer segmentation divides a broad market into groups with meaningful differences in needs, behavior, context, urgency, or ability to pay.

Useful segments
Segment by problem and behavior before relying on age or location alone. Consider the job customers are trying to complete, the situation that triggers the need, current alternatives, purchasing authority, budget, access, and willingness to change. A segment should be specific enough to research and large enough to matter.

Personas
A persona is an evidence-based representation of a priority user, not an imaginary profile built from stereotypes. Include goals, jobs, pains, gains, behaviors, constraints, alternatives, and a representative quote. Record which details are observed, reported, or assumed.

Prioritization
Compare segments by problem severity, frequency, reachability, willingness to pay or adopt, competitive access, and fit with the startup's capabilities. Choose one initial segment for focused research while keeping other segments as hypotheses.

Activity
Define three possible segments for your idea, score them against clear criteria, and create one evidence-based persona for the highest-priority segment.

Video script
Explain why startups should begin with a focused customer segment, demonstrate persona creation, and connect segmentation choices to better research and validation decisions.''',
    },
    {
        'title': 'Week 4 Day 2: Surveys, Interviews, and Observation',
        'video_url': 'https://youtu.be/CJmWmC85mBY',
        'notes': '''Introduction
Good market research combines qualitative methods that explain why behavior happens with quantitative methods that show how often or how widely it occurs. Surveys, interviews, and observation each answer different questions.

Interviews
Ask about recent experiences, current workarounds, costs, frustrations, and decisions rather than asking people to predict whether they would like an idea. Use open questions, avoid leading language, probe for examples, and record exact evidence with consent.

Surveys
Use surveys when you need comparable responses from a larger sample. Keep questions neutral and concise, define the population, pilot the survey, and distinguish descriptive findings from conclusions. A convenient sample may not represent the target market.

Observation
Observe users in the setting where the problem occurs. Look for workarounds, interruptions, access barriers, and differences between what people say and what they do. Do not collect unnecessary personal information, and protect privacy and safety.

Triangulation
Confidence improves when different methods point to the same pattern. Compare interview themes with observed behavior and survey results, note contradictions, and document sampling limitations before changing the business model.

Activity
Prepare an interview guide, a short survey, and an observation checklist for one segment. Collect a small pilot sample and summarize three repeated patterns plus one contradiction.

Video script
Compare surveys, interviews, and observation, demonstrate neutral research questions, and show how triangulation produces stronger evidence than any single method.''',
    },
    {
        'title': 'Week 4 Day 3: Product-Market Fit Metrics',
        'video_url': 'https://youtu.be/UT_28r7MD48',
        'notes': '''Introduction
Product-market fit is not a single vanity number. It is an evidence-based pattern showing that a defined customer group receives enough value to adopt, use, retain, recommend, or pay for a product.

Metric framework
Track a small set of measures connected to the customer journey: qualified reach, activation, time to value, conversion, repeat use, retention, referral, revenue collected, support burden, and contribution margin. Define each metric precisely so the team measures the same behavior.

Leading and lagging evidence
Interviews and activation can reveal early signals, while retention, repeat purchase, and collected revenue provide stronger evidence of durable value. Sign-ups alone may measure curiosity rather than product-market fit. Segment every metric by customer type and acquisition channel.

Cohorts and quality
Cohort analysis compares users who started in the same period and reveals whether retention improves or declines. Monitor sample size, missing data, seasonality, channel differences, and selection bias. Never hide poor results by reporting only the best segment.

Decision use
Metrics should trigger decisions. Set a baseline, target, time window, owner, and action for each experiment. Use the results to improve the product, narrow the segment, change the channel, or revisit the problem.

Activity
Create a metric tree for your idea. Select one activation metric and one retention or payment metric, define the event precisely, and write the decision you will make for a weak or strong result.

Video script
Separate vanity metrics from meaningful behavior, introduce activation and retention, and show how segmented cohort metrics support product and market decisions.''',
    },
    {
        'title': 'Week 4 Day 4: Validation Techniques: Landing Pages, Pre-Sales, and Waitlists',
        'video_url': 'https://youtu.be/12zvQuAjkrE',
        'notes': '''Introduction
Validation techniques turn a business assumption into an observable test. Landing pages, pre-sales, and waitlists can reveal whether a specific audience understands a promise and is willing to take a meaningful next step.

Landing pages
A focused landing page should identify the target customer, problem, proposed outcome, evidence, call to action, and important limitations. Test one clear message at a time and measure qualified visits, sign-ups, completed forms, or requests for a conversation rather than raw traffic.

Waitlists
A waitlist can measure interest before a product is ready, but it is only an early signal. Capture segment, use case, urgency, and permission to contact. Follow up with interviews or a pilot to learn whether interest survives the effort of adoption.

Pre-sales and pilots
Pre-sales, deposits, letters of intent, and paid pilots are stronger evidence because they involve commitment. State exactly what is being offered, when it will be delivered, refund terms, risks, and any manual service involved. Never misrepresent a prototype as a finished product.

Experiment design
Write the hypothesis, audience, channel, message, time box, metric, threshold, and next decision before launching. Protect personal data, avoid deceptive urgency, and report the denominator behind every conversion rate.

Activity
Create a landing-page experiment for one segment. Define the promise, call to action, traffic source, success threshold, privacy notice, and follow-up interview plan.

Video script
Demonstrate landing pages, waitlists, and pre-sales as progressively stronger validation signals, and emphasize honest offers, clear metrics, and responsible customer treatment.''',
    },
    {
        'title': 'Week 4 Day 5: Market Research Hypothesis and Validation Loop',
        'video_url': 'https://youtu.be/cJKTCHsVVBY',
        'notes': '''Introduction
A validation loop turns market research into disciplined learning. The cycle is hypothesis, research, experiment, evidence, decision, and revision. It prevents founders from collecting information without changing what they do.

Build the hypothesis
State who has the problem, what situation creates it, how the problem is currently handled, why the proposed solution could help, and what behavior would confirm the assumption. Make the claim specific enough to be falsified.

Gather peer-reviewed feedback
Use a structured interview, research review, expert critique, or pilot feedback process. Ask participants to describe actual experiences and alternatives. Seek disconfirming evidence, include diverse contexts, and separate participant quotes from the team's interpretation.

Run the loop
Choose the riskiest important assumption, design the smallest credible test, collect evidence, compare it with a predefined threshold, and decide whether to persevere, adapt, narrow the segment, or stop. Record the date, sample, method, result, limitation, and next action.

Research quality and ethics
Avoid confirmation bias, leading questions, cherry-picked testimonials, and unsupported market-size claims. Obtain consent, minimize personal data, protect confidentiality, and communicate uncertainty honestly. Peer feedback improves a decision but does not automatically prove causation or market viability.

Activity
Create a one-page validation board with one hypothesis, evidence sources, experiment, metric, threshold, result, limitation, and next decision. Review it with a peer and revise the test.

Video script
Show how a startup moves from a market hypothesis to structured feedback and a measurable decision, closing Week 4 with a repeatable validation loop.''',
    },
]


def format_notes(text):
    headings = {
        'Introduction', 'Useful segments', 'Personas', 'Prioritization', 'Interviews',
        'Surveys', 'Observation', 'Triangulation', 'Metric framework',
        'Leading and lagging evidence', 'Cohorts and quality', 'Decision use',
        'Landing pages', 'Waitlists', 'Pre-sales and pilots', 'Experiment design',
        'Build the hypothesis', 'Gather peer-reviewed feedback', 'Run the loop',
        'Research quality and ethics', 'Activity', 'Video script',
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
    help = 'Create or refresh Week 4 lessons for Startup Fundamentals.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        course = Course.objects.filter(slug='startup-fundamentals-idea-to-launch').first()
        if not course:
            raise CommandError('Startup Fundamentals course does not exist. Run seed_startup_fundamentals first.')
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(WEEK4_LESSONS)} Week 4 lessons.'))
            return

        with transaction.atomic():
            for day, item in enumerate(WEEK4_LESSONS, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=18 + day,
                    defaults={'title': f'Week 4: Day {day}'},
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
            f'Created or refreshed {len(WEEK4_LESSONS)} Week 4 lessons for {course.title}.'
        ))
