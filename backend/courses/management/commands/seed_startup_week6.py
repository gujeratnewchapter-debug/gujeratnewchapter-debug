from html import escape

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, Lesson, Section


WEEK6_LESSONS = [
    {
        'title': 'Week 6 Day 1: Types of Funding: Bootstrapping, Angels, VC, and Crowdfunding',
        'video_url': 'https://youtu.be/v8AB-Zj00oM',
        'notes': '''Introduction
Funding is a tool for reaching a meaningful business milestone, not a measure of a founder's worth. The right source depends on stage, risk, growth model, capital needs, control preferences, and the evidence already available.

Bootstrapping
Bootstrapping uses founder savings, early revenue, careful spending, or customer-funded delivery. It can preserve ownership and encourage discipline, but it may limit speed and place pressure on personal resources. Keep business and personal funds separate and document transactions.

Angel investment
Angels are individual investors who may provide capital, experience, networks, and credibility. Evaluate more than the cheque: consider sector knowledge, decision rights, support style, conflicts, and the expectations attached to the investment.

Venture capital
Venture capital funds seek high-growth opportunities and usually invest through equity or related instruments. VC may provide substantial capital and networks, but it also brings dilution, governance expectations, reporting, and pressure to pursue a large outcome. It is not suitable for every sustainable business.

Crowdfunding and alternatives
Crowdfunding may involve donations, rewards, pre-orders, debt, or equity depending on the platform and law. Other options include grants, competitions, strategic partnerships, and revenue-based arrangements. Verify eligibility, fees, investor rights, reporting duties, and local regulation before accepting funds.

Activity
Compare three funding options for your venture. Record amount, timing, cost, dilution or repayment, control implications, eligibility, risk, and the milestone each option would fund.

Video script
Compare bootstrapping, angel investment, venture capital, and crowdfunding, then help founders choose capital that matches evidence, risk, control, and growth goals.''',
    },
    {
        'title': 'Week 6 Day 2: Funding Stages from Pre-Seed to Series A and Beyond',
        'video_url': 'https://youtu.be/0BCEhg29yqM',
        'notes': '''Introduction
Funding stages describe common patterns in a startup's development, but they are not a guaranteed ladder. A company may use revenue, grants, debt, angels, or equity at different points, and many ventures never need institutional venture capital.

Pre-seed
Pre-seed capital commonly supports problem discovery, prototypes, early research, initial hiring, and the first experiments. Investors expect a credible problem, capable team, focused plan, and learning milestones rather than mature revenue.

Seed
Seed funding generally supports an early product, customer pilots, initial traction, and a repeatable learning process. The company should explain its target segment, evidence of demand, economics, risks, and the next milestone the capital will unlock.

Series A and later rounds
Series A often supports a validated product and a stronger case for repeatable growth. Later rounds may fund expansion, infrastructure, new markets, acquisitions, or operational scale. Expectations for governance, reporting, metrics, and growth usually increase with each round.

Funding readiness
Stage labels matter less than evidence. Prepare a clear use-of-funds plan, runway model, ownership record, contracts, metrics, risks, and milestone plan. Raising too early can create dilution and expectations before the business has learned enough.

Activity
Map your venture's current evidence to a realistic funding stage. Define the next milestone, capital required, proof investors would expect, and a non-equity alternative.

Video script
Explain pre-seed, seed, Series A, and later funding stages, emphasizing that milestones and evidence matter more than labels or fundraising fashion.''',
    },
    {
        'title': 'Week 6 Day 3: Pitch Deck Essentials',
        'video_url': 'https://youtu.be/qsx8XE-MVVc',
        'notes': '''Introduction
A pitch deck is a concise decision document that helps an investor understand the problem, opportunity, solution, evidence, business model, and funding request. It should support a conversation rather than replace due diligence.

Core slides
A focused deck commonly includes the problem, target customer, solution, product or demonstration, market, competition and alternatives, business model, traction, go-to-market, team, financial outlook, funding ask, use of funds, milestones, and risks. The exact number and order can vary by stage.

Evidence and clarity
Use specific customer evidence, defined metrics, readable charts, source notes, and honest distinctions between actual results and forecasts. Explain why the team is suited to the problem and what has changed since the previous milestone. Avoid unexplained market-size claims and crowded slides.

Narrative
A strong narrative moves from an important problem to a credible solution and a plausible path to value creation. Each slide should answer one question and lead naturally to the next. Keep the audience, time limit, and decision requested in mind.

Activity
Draft a ten-to-twelve-slide outline for your venture. Write the one-sentence message for every slide and mark each claim as evidence, assumption, target, or forecast.

Video script
Walk through the essential pitch-deck sections, demonstrate an evidence-led narrative, and show how clarity and honesty improve investor conversations.''',
    },
    {
        'title': 'Week 6 Day 4: Investor Psychology and Deal Terms',
        'video_url': 'https://youtu.be/LSIGsvLq0Do',
        'notes': '''Introduction
Investors evaluate both the opportunity and the people, evidence, risks, and terms surrounding it. Understanding decision psychology can improve communication, but founders should never manipulate, exaggerate, or hide material information.

Investor evaluation
Investors may consider problem severity, market size, growth potential, customer evidence, unit economics, team capability, competition, timing, regulatory risk, and the quality of the plan. Different investors have different mandates, so fit matters.

Common deal terms
Important terms can include valuation, price per share, equity percentage, liquidation preference, anti-dilution protection, board or observer rights, information rights, vesting, option pools, pro-rata rights, and conversion features. The headline valuation does not describe the entire economic or governance outcome.

Negotiation and diligence
Compare offers by ownership, control, future flexibility, investor support, obligations, and downside outcomes. Keep a cap table, provide organized diligence materials, and obtain qualified legal and financial advice before signing. Do not treat a term sheet as equivalent to completed funding.

Activity
Create an investor-question list and a term-sheet comparison table. For each term, record its plain-language meaning, economic effect, governance effect, and adviser question.

Video script
Explain how investors assess evidence and fit, introduce common deal terms, and emphasize careful diligence and professional advice before accepting an offer.''',
    },
    {
        'title': 'Week 6 Day 5: Build a Ten-Slide Investor Pitch and Pitch Day Simulation',
        'video_url': 'https://youtu.be/2kjFXPAUk1w',
        'notes': '''Introduction
A pitch simulation turns strategy and evidence into a short, testable investor presentation. The goal is not theatrical confidence; it is a clear explanation of a real problem, credible learning, a responsible plan, and a specific request.

Ten-slide structure
Use a practical sequence: title and one-line promise; problem and customer; current alternatives; solution and demonstration; market and segment; business model; traction and learning; go-to-market; competition and advantage; team, funding ask, use of funds, milestones, and risks. Combine or split slides to fit the time limit.

Prepare the story
Write the main message before designing slides. Use one idea per slide, readable numbers, simple visuals, and source notes. Rehearse transitions, likely questions, time, and the difference between verified results and forecasts. Prepare an appendix for detailed evidence.

Simulation and feedback
Assign presenters, investors, timekeeper, and reviewers. Score clarity of problem, evidence quality, customer understanding, solution credibility, economics, ask, delivery, and response to questions. Revise the deck based on repeated feedback rather than one person's preference.

Responsible pitching
Do not promise returns, claim customers you do not have, inflate the market, or conceal risks. Protect confidential information and disclose material limitations. A clear no or not-yet decision is useful learning.

Activity
Deliver a five-minute ten-slide pitch, answer five investor questions, record feedback, and produce a revision log with three changes and the evidence behind each change.

Video script
Build and present a ten-slide investor pitch through a realistic simulation, then use structured feedback to improve the story, evidence, ask, and next milestone.''',
    },
]


def format_notes(text):
    headings = {
        'Introduction', 'Bootstrapping', 'Angel investment', 'Venture capital',
        'Crowdfunding and alternatives', 'Pre-seed', 'Seed', 'Series A and later rounds',
        'Funding readiness', 'Core slides', 'Evidence and clarity', 'Narrative',
        'Investor evaluation', 'Common deal terms', 'Negotiation and diligence',
        'Ten-slide structure', 'Prepare the story', 'Simulation and feedback',
        'Responsible pitching', 'Activity', 'Video script',
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
    help = 'Create or refresh Week 6 funding and pitching lessons for Startup Fundamentals.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        course = Course.objects.filter(slug='startup-fundamentals-idea-to-launch').first()
        if not course:
            raise CommandError('Startup Fundamentals course does not exist. Run the course seed command first.')
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(WEEK6_LESSONS)} Week 6 lessons.'))
            return

        with transaction.atomic():
            for day, item in enumerate(WEEK6_LESSONS, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=27 + day,
                    defaults={'title': f'Week 6: Day {day}'},
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
            f'Created or refreshed {len(WEEK6_LESSONS)} Week 6 lessons for {course.title}.'
        ))
