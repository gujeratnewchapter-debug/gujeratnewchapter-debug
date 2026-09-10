from html import escape

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, Lesson, Section


WEEK8_LESSONS = [
    {
        'title': 'Week 8 Day 1: Scaling, Growth, and Exit',
        'video_url': 'https://youtu.be/V2v2vUYUKlU',
        'notes': '''Introduction
Scaling means increasing the value a venture delivers without allowing complexity, costs, or quality problems to grow at the same rate. Growth should be intentional, measurable, and supported by evidence rather than pursued for its own sake.

Readiness to scale
Before expanding, confirm a repeatable customer problem, reliable delivery, healthy unit economics, adequate capacity, responsible controls, and a team able to manage the next stage. Scaling a broken process multiplies customer complaints and operational risk.

Growth choices
Growth may come from deeper use in an existing segment, new customer segments, additional channels, partnerships, geographic expansion, product extensions, or improved retention. Choose one priority and define the capability, cash, and learning it requires.

Exit thinking
An exit may involve acquisition, merger, public listing, management succession, or continued independent operation. Founders should understand that exit goals affect governance, reporting, ownership, product choices, and stakeholder expectations.

Activity
Create a scale-readiness checklist for your venture. Identify one growth opportunity, one bottleneck, one metric, one risk, and the milestone that must be achieved before expansion.

Video script
Explain the difference between growth and responsible scaling, connect readiness to systems and evidence, and introduce exit as a strategic option rather than an automatic endpoint.''',
    },
    {
        'title': 'Week 8 Day 2: Growth Metrics: DAU, MAU, Churn, NPS, and Retention',
        'video_url': 'https://youtu.be/8ottgkpU0p0',
        'notes': '''Introduction
Growth metrics help a team understand whether customers are receiving continuing value. Each metric answers a different question, so no single number should be treated as proof of product-market fit.

Usage and retention
Daily active users (DAU) and monthly active users (MAU) describe activity over defined periods. Retention measures the share of a cohort that returns or continues a desired behavior. Define an active user and time window precisely before comparing results.

Churn
Churn measures customers, users, or revenue lost during a period. Separate voluntary and involuntary churn where possible, and investigate the reason rather than treating the percentage as a diagnosis. A growing user count can hide poor retention if acquisition is faster than loss.

NPS and feedback
Net Promoter Score summarizes responses to a recommendation question, but it is a perception signal rather than a complete growth measure. Combine it with interviews, retention, usage quality, support issues, and collected revenue.

Metrics discipline
Segment by customer type, channel, geography, and cohort. Record the numerator, denominator, data source, time period, and limitations. Use metrics to trigger decisions, not to decorate a pitch.

Activity
Define DAU, MAU, retention, churn, and NPS for your product. Build a weekly dashboard specification with one decision rule for each metric.

Video script
Define common growth metrics, explain how they relate, and demonstrate why segmented cohorts and behavior matter more than isolated headline numbers.''',
    },
    {
        'title': 'Week 8 Day 3: Scale-Up Challenges: Operations, Funding Gaps, and Team Management',
        'video_url': 'https://youtu.be/BLOKfAY6uzA',
        'notes': '''Introduction
Scale-up creates new pressures in operations, funding, hiring, quality, culture, and decision-making. A process that worked for ten customers may fail at one thousand, and informal knowledge may not survive a growing team.

Operational systems
Document critical workflows, service standards, ownership, controls, data practices, supplier dependencies, and incident responses. Automate only after understanding the process. Monitor quality and customer support while volume increases.

Funding gaps
Growth can consume cash before revenue is collected. Model hiring, inventory, infrastructure, marketing, payment timing, working capital, and contingency needs. Tie new funding to milestones and avoid expanding costs based only on an optimistic forecast.

Team management
Clarify roles, managers, decision rights, communication rhythms, performance expectations, and development paths. Preserve the learning and ethical behaviors that made the early team effective while introducing enough structure for consistency.

Risk management
Track regulatory, security, privacy, supplier, key-person, financial, and reputational risks. Assign owners, mitigation actions, warning indicators, and review dates. Growth should never justify hiding defects or overworking people.

Activity
Create a scale-up risk register with five risks, probability, impact, owner, mitigation, early warning sign, and review date. Add one operational process that needs documentation before growth.

Video script
Explore the operational, financial, and people challenges of scaling, then show how systems, cash planning, and responsible management reduce scale-up risk.''',
    },
    {
        'title': 'Week 8 Day 4: Exit Strategies: Acquisition, IPO, and Merger',
        'video_url': 'https://youtu.be/WbXwoH4ito0',
        'notes': '''Introduction
An exit strategy describes how founders and investors may eventually realize value or transfer control. It should not replace building a useful, responsible, and financially sound venture.

Acquisition
In an acquisition, another organization purchases some or all of the venture's assets or ownership. Buyers may value technology, customers, talent, distribution, brand, data, or strategic fit. Due diligence examines claims, contracts, intellectual property, liabilities, people, and financial records.

Merger
A merger combines organizations under an agreed structure. Success depends on strategic fit, governance, integration, culture, systems, customers, and the treatment of employees and other stakeholders. A headline deal value does not guarantee a good outcome for every owner.

IPO
An initial public offering makes shares available to public investors subject to extensive legal, financial, reporting, governance, and market requirements. It is complex, costly, and unsuitable for many ventures. Public status brings continuing disclosure and accountability.

Preparation and ethics
Maintain a clean cap table, contracts, accounts, intellectual-property records, compliance evidence, and risk register. Consider founder, employee, customer, investor, and community effects. Obtain qualified legal and financial advice before negotiating or signing.

Activity
Compare acquisition, merger, IPO, and independent operation across control, timing, cost, readiness, stakeholder effects, and risk. List the records your venture would need for diligence.

Video script
Compare acquisition, merger, IPO, and staying independent, emphasizing preparation, stakeholder consequences, due diligence, and professional advice.''',
    },
    {
        'title': 'Week 8 Day 5: One-Year Growth Roadmap and Final Team Presentation',
        'video_url': 'https://youtu.be/4GLHY49FOKw',
        'notes': '''Introduction
A one-year growth roadmap converts a venture's strategy into sequenced milestones, owners, measures, resources, and review points. It should be ambitious enough to guide action and realistic enough to reveal trade-offs.

Roadmap structure
Divide the year into quarters or monthly cycles. For each period define the customer outcome, product or service deliverable, growth experiment, operational capability, financial target, responsible owner, dependencies, and evidence required to proceed.

Prioritization
Sequence work by risk, importance, dependency, and learning value. Do not schedule expansion before validating the core offer or securing the capacity to deliver it. Include alternative plans for weak traction, funding delays, regulatory changes, and team constraints.

Final presentation
A strong team presentation connects problem, customer, solution, evidence, business model, GTM approach, team, financial plan, growth metrics, risks, roadmap, and funding or partnership request. Separate achieved results from targets and forecasts.

Review and learning
Set monthly reviews to compare actual results with the roadmap, record decisions, and revise assumptions. A roadmap is a living management tool, not a promise that conditions will remain unchanged.

Activity
Prepare a twelve-month roadmap and deliver a ten-minute final team presentation. Include three milestones, their measures, owners, dependencies, risks, and the decision rule for each review.

Video script
Build a one-year growth roadmap, connect milestones to evidence and ownership, and simulate a final team presentation with structured feedback.''',
    },
]


def format_notes(text):
    headings = {
        'Introduction', 'Scaling means increasing the value a venture delivers without allowing complexity, costs, or quality problems to grow at the same rate.',
        'Readiness to scale', 'Growth choices', 'Exit thinking', 'Usage and retention', 'Churn', 'NPS and feedback',
        'Metrics discipline', 'Operational systems', 'Funding gaps', 'Team management', 'Risk management',
        'Acquisition', 'Merger', 'IPO', 'Preparation and ethics', 'Roadmap structure', 'Prioritization',
        'Final presentation', 'Review and learning', 'Activity', 'Video script',
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
    help = 'Create or refresh Week 8 scaling, growth, and exit lessons for Startup Fundamentals.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        course = Course.objects.filter(slug='startup-fundamentals-idea-to-launch').first()
        if not course:
            raise CommandError('Startup Fundamentals course does not exist. Run the course seed command first.')
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(WEEK8_LESSONS)} Week 8 lessons.'))
            return

        with transaction.atomic():
            for day, item in enumerate(WEEK8_LESSONS, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=37 + day,
                    defaults={'title': f'Week 8: Day {day}'},
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
            f'Created or refreshed {len(WEEK8_LESSONS)} Week 8 lessons for {course.title}.'
        ))
