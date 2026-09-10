from html import escape

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, Lesson, Section


WEEK7_LESSONS = [
    {
        'title': 'Week 7 Day 1: Building the Founding Team',
        'video_url': 'https://youtu.be/P4vgl2ExOrk',
        'notes': '''Introduction
A startup team turns a promising idea into a reliable operation. Early teams need complementary capabilities, clear ownership, trust, and a working rhythm that supports fast learning without creating unnecessary bureaucracy.

Team composition
List the work required for the next milestone: customer discovery, product delivery, sales, operations, finance, compliance, and support. Map who owns each responsibility and identify capability gaps. Choose co-founders and early hires for relevant commitment and capability, not only reputation or friendship.

Roles and accountability
Define decision rights, expected outcomes, dependencies, and escalation paths. One person should be accountable for each important outcome even when several people contribute. Revisit roles as the venture learns; early titles should not become barriers to collaboration.

Working agreements
Agree how the team makes decisions, handles disagreement, shares information, gives feedback, protects customers, and responds when commitments are missed. Discuss equity, vesting, intellectual property, confidentiality, and exit arrangements with qualified advisers.

Inclusive team building
Consider local talent development, language, accessibility, remote collaboration, and different lived experiences. A diverse team can identify more risks and understand more customers when the environment makes participation safe and meaningful.

Activity
List the next six months of critical work, assign one accountable owner to each item, identify three capability gaps, and write five founding-team working agreements.

Video script
Show how to design complementary founding roles, establish accountability, and build a working agreement that supports learning, trust, and responsible execution.''',
    },
    {
        'title': 'Week 7 Day 2: Startup Culture, Hiring, ESOPs, and Onboarding',
        'video_url': 'https://youtu.be/zIG6faUFGm4',
        'notes': '''Introduction
Startup culture is the repeated pattern of behaviors a team rewards, tolerates, and models. A healthy culture supports customer focus, learning, honesty, inclusion, and responsible performance rather than relying on slogans.

Hiring
Hire to remove a capability bottleneck tied to the next milestone. Define the outcome, required skills, evidence of capability, trial or interview process, budget, and manager before recruiting. Use structured criteria and consistent questions to reduce bias.

Onboarding
An effective onboarding process explains the mission, customer, product, role expectations, decision rights, tools, security practices, and first deliverable. Give new team members context and feedback early instead of expecting them to infer everything from informal conversations.

ESOPs and incentives
An employee stock option plan may align long-term participation with company value, but it also involves dilution, vesting, exercise rules, tax, documentation, and legal obligations. Explain that equity is uncertain and never present it as guaranteed income. Obtain qualified legal and financial advice.

Culture in practice
Leaders shape culture through their response to mistakes, bad news, customer complaints, and disagreement. Reward evidence and ethical conduct, not only speed or visible enthusiasm. Protect against harassment, discrimination, burnout, and retaliation.

Activity
Draft a role scorecard, a first-week onboarding plan, and a culture decision log showing which behaviors the team will reward, address, and never compromise.

Video script
Connect culture with hiring and onboarding, explain ESOP responsibilities at a high level, and demonstrate how daily leadership behavior creates the real startup culture.''',
    },
    {
        'title': 'Week 7 Day 3: Go-To-Market Channels and Customer Acquisition',
        'video_url': 'https://youtu.be/XNNJWhyLCVc',
        'notes': '''Introduction
A go-to-market (GTM) plan explains how a startup reaches a defined customer, communicates value, delivers the offer, and learns from market response. It is a focused operating hypothesis, not simply a launch announcement.

Choose a channel
Select channels based on where the target customer already makes decisions and can be reached with trust. Options include direct sales, partnerships, universities, cooperatives, communities, referrals, content, demonstrations, marketplaces, and self-serve digital flows.

Customer acquisition motion
Define the first contact, qualification question, value message, offer, commitment or payment step, onboarding, support, and follow-up. Assign an owner and document the handoffs. Consider language, connectivity, payment preferences, geography, and local relationships.

Measure the funnel
Track qualified reach, response, activation, conversion, time to value, repeat use, retention, revenue collected, acquisition cost, and support issues. Use a small number of measures that guide decisions. Separate channel performance by segment and campaign.

Responsible growth
Do not buy fake engagement, spam communities, hide limitations, or make unsupported claims. Make consent and privacy clear, provide accessible communication, and treat customer feedback and complaints as product evidence.

Activity
Choose one target segment and create a GTM experiment with channel, message, owner, budget, funnel steps, metric, threshold, time box, and next decision.

Video script
Build a focused GTM plan, compare acquisition channels, and connect customer reach to onboarding, measurable outcomes, and responsible growth.''',
    },
    {
        'title': 'Week 7 Day 4: B2B versus B2C Sales Strategies',
        'video_url': 'https://youtu.be/0v0CpCw1d24',
        'notes': '''Introduction
Business-to-business (B2B) and business-to-consumer (B2C) sales can solve similar problems but differ in buyers, decision processes, sales cycles, pricing, evidence, and delivery expectations. The distinction should shape the GTM plan.

B2B sales
B2B purchases may involve a user, champion, technical reviewer, budget owner, procurement team, and legal or compliance stakeholders. Sales may require discovery, a demonstration, a pilot, security review, contract negotiation, implementation, and account support.

B2C sales
B2C decisions are often made by an individual or household. Convenience, trust, price, social proof, accessibility, onboarding, and repeat value can strongly influence adoption. Digital self-serve flows and community or referral channels may reduce sales friction.

Compare economics
B2B may have higher contract value but longer cycles, customization, and support costs. B2C may have faster decisions but greater acquisition volume and churn risk. Track conversion, sales cycle, retention, margin, CAC, payback, and service effort for each motion.

Choose the motion
Do not mix B2B and B2C assumptions casually. Define who pays, who uses, who decides, what evidence is required, and which channel can reach the segment. Test the smallest credible sales motion before building a large team.

Activity
Map the buyer, user, champion, decision maker, sales steps, objections, and success metrics for your chosen B2B or B2C segment. Design one pilot conversation or sales experiment.

Video script
Contrast B2B and B2C buyers, show how sales processes and economics differ, and help founders select a focused customer acquisition motion.''',
    },
    {
        'title': 'Week 7 Day 5: GTM Plan, Hiring Interviews, and Co-Founder Roleplay',
        'video_url': 'https://youtu.be/CoUo5a_XoAY',
        'notes': '''Introduction
A GTM plan becomes useful when the team can explain it, assign ownership, test it, and revise it. Roleplay makes hidden assumptions visible by simulating customer conversations, hiring interviews, and co-founder decisions.

GTM plan structure
State the target customer, problem, positioning, offer, channel, sales or onboarding motion, pricing, resources, owner, timeline, funnel metrics, risks, and learning goal. Connect every activity to a measurable customer or business outcome.

Hiring interview
Use a consistent scorecard and ask candidates for evidence from relevant work. Explain the role honestly, assess collaboration and judgment, and avoid discriminatory questions. Provide a realistic view of uncertainty, workload, compensation, and decision rights.

Co-founder discussion
Discuss vision, roles, equity, vesting, time commitment, decision rights, conflict handling, personal constraints, and exit scenarios before pressure makes the conversation harder. Record agreements and seek professional advice for formal documents.

Roleplay and feedback
Assign roles, set a time limit, observe, and score clarity, listening, evidence, respect, and decision quality. Debrief what was assumed, what was learned, and what should change in the plan.

Activity
Present your GTM plan in five minutes, conduct one mock hiring interview and one co-founder discussion, collect peer feedback, and revise three decisions with evidence.

Video script
Demonstrate a practical GTM plan through roleplay, including customer acquisition, hiring interviews, and co-founder alignment, then close with a feedback-driven revision.''',
    },
]


def format_notes(text):
    headings = {
        'Introduction', 'Team composition', 'Roles and accountability', 'Working agreements',
        'Inclusive team building', 'Hiring', 'Onboarding', 'ESOPs and incentives',
        'Culture in practice', 'Choose a channel', 'Customer acquisition motion',
        'Measure the funnel', 'Responsible growth', 'B2B sales', 'B2C sales',
        'Compare economics', 'Choose the motion', 'GTM plan structure', 'Hiring interview',
        'Co-founder discussion', 'Roleplay and feedback', 'Activity', 'Video script',
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
    help = 'Create or refresh Week 7 team and GTM lessons for Startup Fundamentals.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        course = Course.objects.filter(slug='startup-fundamentals-idea-to-launch').first()
        if not course:
            raise CommandError('Startup Fundamentals course does not exist. Run the course seed command first.')
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(WEEK7_LESSONS)} Week 7 lessons.'))
            return

        with transaction.atomic():
            for day, item in enumerate(WEEK7_LESSONS, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=32 + day,
                    defaults={'title': f'Week 7: Day {day}'},
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
            f'Created or refreshed {len(WEEK7_LESSONS)} Week 7 lessons for {course.title}.'
        ))
