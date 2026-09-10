from html import escape

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, Lesson, Section


WEEK5_LESSONS = [
    {
        'title': 'Week 5 Day 1: Unit Economics, Revenue Models, CAC and LTV',
        'video_url': 'https://youtu.be/4LI8xdlOjlU',
        'notes': '''Introduction
Unit economics explains whether serving one customer can create sustainable value. It connects pricing, variable costs, customer acquisition, usage, retention, and contribution margin so a startup can understand the quality of its growth.

Revenue models
Common models include one-time sales, subscriptions, usage-based pricing, commissions, licensing, advertising, freemium conversion, and service fees. Select a model that matches customer value, payment behavior, delivery cost, and collection timing. Revenue forecasts should separate observed results from assumptions.

Customer acquisition cost
Customer acquisition cost (CAC) estimates the cost of acquiring a paying customer. Include relevant sales, marketing, partner, onboarding, and campaign costs, then divide by the number of attributable new customers over the same period. Track CAC separately by channel and customer segment.

Lifetime value
Customer lifetime value (LTV) estimates the contribution a customer may generate over the relationship. It depends on collected revenue, gross margin, purchase frequency, retention, and service cost. LTV is a model, not a guaranteed future result, so state the assumptions and use cohorts where possible.

Healthy interpretation
Compare contribution margin and payback period with cash runway. A high LTV-to-CAC ratio based on weak assumptions can be misleading. Improve the economics by increasing value, retention, and pricing clarity or reducing avoidable acquisition and delivery costs.

Activity
Choose one customer segment. Build a simple unit-economics table with price, variable cost, contribution margin, CAC, retention assumption, LTV estimate, and the evidence needed to improve each number.

Video script
Explain revenue models, CAC, LTV, and contribution margin, then show how founders use unit economics to judge sustainable growth rather than celebrating revenue alone.''',
    },
    {
        'title': 'Week 5 Day 2: Cost Structure and Startup Budgeting',
        'video_url': 'https://youtu.be/ldc5R1_xacE',
        'notes': '''Introduction
A startup budget translates the business model into expected cash needs. It helps founders decide what to build, when to hire, how much runway remains, and which costs require evidence before commitment.

Types of cost
Fixed costs remain relatively stable over a period, such as core salaries, rent, software subscriptions, and accounting. Variable costs change with customers or transactions, such as payment fees, delivery, support, materials, and usage-based infrastructure. One-time costs include setup, equipment, registration, and initial research.

Build the budget
List each cost, owner, timing, payment terms, tax or fee assumptions, and confidence level. Separate committed costs from optional costs and distinguish cash paid from accounting expense. Include a contingency buffer for delays, refunds, repairs, and unexpected operational needs.

Runway and scenarios
Runway estimates how long available cash can support planned net spending. Create conservative, base, and upside scenarios. Update the model when actual costs or collection timing differ from the forecast. A budget is a decision tool, not a promise that the numbers will occur.

Cost discipline
Reduce waste without compromising safety, quality, legal compliance, or customer trust. Delay costs that do not support the next milestone, negotiate responsibly, and avoid hiding manual work or liabilities. Review recurring costs regularly as the venture learns.

Activity
Create a three-month budget with fixed, variable, one-time, and contingency costs. Calculate monthly net burn and runway under two scenarios, then identify the assumption most worth validating.

Video script
Classify startup costs, build a practical budget, calculate runway, and demonstrate how scenario planning supports responsible spending decisions.''',
    },
    {
        'title': 'Week 5 Day 3: Legal Structures for Startups',
        'video_url': 'https://youtu.be/8ZjoMhvh_TU',
        'notes': '''Introduction
A legal structure defines how a venture is owned, governed, taxed, financed, and held responsible for obligations. The best choice depends on local law, founder goals, risk, ownership, funding plans, and the nature of the activity.

Common structures
A sole proprietorship is generally simple and closely tied to one owner, but personal liability and continuity may be important concerns. A partnership or limited liability partnership can support multiple owners with defined rights and responsibilities, subject to applicable law. A private limited company is a separate corporate structure commonly used when formal governance, investment, ownership transfer, and limited liability are priorities.

Decision factors
Compare registration and compliance requirements, liability, taxation, ownership, decision rights, reporting, fundraising, employee participation, continuity, and closing procedures. Do not select a structure solely because another startup used it.

Responsible setup
Document founder roles, ownership expectations, intellectual property, confidentiality, decision-making, dispute handling, and exit terms. Verify current Ethiopian requirements with the appropriate authorities and qualified legal and tax professionals because laws and procedures can change.

Activity
Create a structure comparison table for your venture. List the likely owners, risks, funding needs, compliance duties, and three questions to take to a qualified local adviser.

Video script
Compare sole proprietorships, LLPs, and private limited companies, then connect legal structure to liability, governance, funding, and compliance decisions.''',
    },
    {
        'title': 'Week 5 Day 4: Creating a Startup Financial Plan',
        'video_url': 'https://youtu.be/l7RZs2rIyyU',
        'notes': '''Introduction
A financial plan turns a startup hypothesis into a set of linked operating, cash, and funding assumptions. It should help the team make decisions and communicate uncertainty honestly, not create false precision for investors.

Core model
Connect customer segments, volume, pricing, collection timing, variable costs, fixed costs, hiring, taxes and fees, capital expenditure, and funding. Build a monthly cash-flow view and reconcile it with the business model, unit economics, and budget.

Scenarios and milestones
Prepare conservative, base, and upside scenarios. State the assumptions that change between scenarios and include a cash buffer. Tie funding requests to milestones such as validated retention, a completed pilot, regulatory readiness, or a sustainable contribution margin.

Financial controls
Keep receipts, invoices, contracts, payroll records, ownership records, and bank activity organized. Reconcile actual cash regularly, separate business and personal funds, and assign responsibility for approvals. Use professional advice for tax, accounting, securities, and legal matters.

Investor communication
Explain what is known, estimated, quoted, or targeted. Show the amount requested, use of funds, runway effect, risks, and the evidence that will be created. Never guarantee returns or present forecasts as achieved results.

Activity
Build a twelve-month financial plan with monthly revenue, costs, cash balance, scenarios, funding need, milestone, and risk columns. Mark every assumption that still requires evidence.

Video script
Assemble a practical startup financial plan, connect forecasts to milestones and cash, and show how transparent assumptions improve funding and operating decisions.''',
    },
]


def format_notes(text):
    headings = {
        'Introduction', 'Revenue models', 'Customer acquisition cost', 'Lifetime value',
        'Healthy interpretation', 'Types of cost', 'Build the budget', 'Runway and scenarios',
        'Cost discipline', 'Common structures', 'Decision factors', 'Responsible setup',
        'Core model', 'Scenarios and milestones', 'Financial controls', 'Investor communication',
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
    help = 'Create or refresh Week 5 finance and legal lessons for Startup Fundamentals.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        course = Course.objects.filter(slug='startup-fundamentals-idea-to-launch').first()
        if not course:
            raise CommandError('Startup Fundamentals course does not exist. Run the course seed command first.')
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(WEEK5_LESSONS)} Week 5 lessons.'))
            return

        with transaction.atomic():
            for day, item in enumerate(WEEK5_LESSONS, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=23 + day,
                    defaults={'title': f'Week 5: Day {day}'},
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
            f'Created or refreshed {len(WEEK5_LESSONS)} Week 5 lessons for {course.title}.'
        ))
