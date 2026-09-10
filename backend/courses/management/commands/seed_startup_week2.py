from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from html import escape

from accounts.models import User
from courses.models import Course, Section, Lesson


WEEK2_LESSONS = [
    {
        'title': 'Week 2 Day 1: Ideation, Problem-Solving, and Market Gaps',
        'video_url': 'https://youtu.be/Qg2lBfwJqPA',
        'duration_minutes': 60,
        'notes': '''Introduction
Ideation generates novel and useful possibilities, while problem-solving identifies a gap between the current state and a desired outcome and works systematically toward a solution. Together they form an iterative cycle: recognize a challenge, gather evidence, generate options, evaluate them, implement a response, and learn from feedback.

Ideation foundations
Divergent thinking expands the number and variety of possible answers. Brainstorming works best when criticism is deferred, quantity is encouraged, unusual ideas are welcomed, and ideas can be combined. Domain knowledge, creative-thinking skills, and intrinsic motivation help turn imagination into useful innovation.

Problem-solving process
Clarify the problem and distinguish root causes from symptoms. Gather information, allow time for incubation, generate alternatives, evaluate feasibility and impact, implement a prototype, and test the result. Use tools such as the 5 Whys, root-cause analysis, design thinking, TRIZ, and Lean Startup experiments.

Identifying market gaps
A market gap exists when demand is not adequately served. Unmet needs may be expressed or latent and can arise from technological, demographic, regulatory, cultural, or infrastructure changes. Combine interviews, observation, surveys, journey maps, competitor analysis, data, and Jobs to Be Done thinking to discover what customers are trying to accomplish.

Validation and context
A gap is not automatically a viable business. Test problem frequency, severity, reachable demand, existing alternatives, willingness to switch or pay, and the economics of delivery. In emerging markets, account for affordability, trust, language, connectivity, infrastructure, and inclusion.

Activity
Choose one customer group. Write a problem statement, list five observed or interview-based pain points, map current alternatives, and identify one risky assumption to test next.

Video script
Explain how ideation and structured problem-solving reinforce each other, then show how customer evidence and market-gap analysis turn creative possibilities into testable startup opportunities.''',
    },
    {
        'title': 'Week 2 Day 2: Design Thinking: Empathize, Define, and Ideate',
        'video_url': 'https://youtu.be/Y8OAZarDQkU',
        'duration_minutes': 60,
        'notes': '''Introduction
Design thinking is a human-centered, iterative approach to innovation. In uncertain startup environments, empathize, define, and ideate help teams understand real users, frame a meaningful problem, and explore multiple solutions before committing resources.

Empathize
Engage users through interviews, observation, shadowing, diary studies, and contextual inquiry. Look for motivations, frustrations, workarounds, emotional responses, and structural constraints. Empathy is systematic research, not assumption or sentiment alone.

Define
Synthesize evidence with affinity maps, personas, and journey maps. Frame the challenge around a human need rather than a preferred technology. A useful statement is specific about the user and context while remaining open enough to invite several solutions.

Ideate
Generate many possibilities through brainstorming, brainwriting, SCAMPER, mind mapping, role-play, and cross-functional collaboration. Delay feasibility judgments during divergence, then shortlist options using desirability, feasibility, viability, accessibility, and potential impact.

Iteration and responsibility
The three stages are not strictly linear. New ideas may reveal a weak problem frame and require more user research. Responsible design considers privacy, accessibility, safety, cultural context, environmental effects, and the risk of excluding underserved users.

Activity
Interview or observe three potential users. Create an affinity map, write a human-centered problem statement, and generate at least ten possible solutions before selecting two for prototyping.

Video script
Walk through empathize, define, and ideate with a startup example, showing how evidence prevents solution-first thinking and how teams move from lived experience to testable concepts.''',
    },
    {
        'title': 'Week 2 Day 3: Blue Ocean Strategy and Value Innovation',
        'video_url': 'https://youtu.be/gYeubdbxthI',
        'duration_minutes': 60,
        'notes': '''Introduction
Blue Ocean Strategy helps startups create new market space instead of competing only in crowded existing categories. A red ocean has established rules and intense rivalry; a blue ocean changes the value proposition so direct comparison becomes less important.

Value innovation
Value innovation pursues meaningful differentiation and lower cost together. It is not limited to new technology. New business models, services, distribution, pricing, or customer experiences can recombine existing resources to unlock new demand.

Strategy canvas
Plot the factors an industry competes on and compare current offerings. Identify what customers value, what the industry takes for granted, and where a startup can diverge while controlling complexity and cost.

Four Actions Framework
Ask what to eliminate, reduce, raise, and create. Use these questions to challenge industry assumptions, serve non-customers, and design a clearer value proposition. Test whether the new offering is desirable, operationally feasible, economically viable, and responsible.

Startup application
Blue oceans eventually attract competitors, so continuous learning and renewal matter. In emerging markets, value innovation can expand inclusion through simpler services, accessible pricing, local partnerships, and context-sensitive delivery. Regulatory, ecosystem, and stakeholder constraints must be considered early.

Activity
Select an existing category. Complete an eliminate-reduce-raise-create grid, sketch a strategy canvas, and state the customer evidence needed to test your proposed blue-ocean value proposition.

Video script
Contrast red and blue oceans, demonstrate the strategy canvas and Four Actions Framework, and connect value innovation to startup experimentation and inclusive market creation.''',
    },
    {
        'title': 'Week 2 Day 4: Problem-Solution Fit',
        'video_url': 'https://www.youtube.com/watch?v=MT4Ig2uqjTc',
        'duration_minutes': 60,
        'notes': '''Introduction
Problem-solution fit is the point at which a startup has evidence that a meaningful problem exists and that its proposed solution addresses it in a way users recognize and value. It comes before product-market fit and prevents teams from building impressive products for weak problems.

Start with the problem
Use interviews, observation, surveys, and usability research to test whether the problem is real, frequent, severe, and important enough to change behavior. Identify latent needs and the workarounds people use today. Avoid starting with a technology and searching for a justification afterward.

Test the solution
Represent an early solution with a sketch, wireframe, landing page, concierge service, or minimum viable product. Measure meaningful behavior such as sign-ups, pilots, repeat use, pre-orders, switching, or payment intent, and combine those measures with honest qualitative feedback.

Segment and context
Fit depends on a specific user segment and use context. Assess current alternatives, affordability, trust, infrastructure, language, regulation, accessibility, and delivery economics. A technically effective solution can still fail if it is not viable or appropriate for the people it serves.

Learning loop
Treat problem-solution fit as an evolving state. Form a hypothesis, test it with users, record evidence, identify contradictions, and refine either the problem frame or the solution. Guard against confirmation bias through clear decision rules and external challenge.

Activity
Write a problem hypothesis and solution hypothesis. Interview five target users, record their current alternatives, and define one behavior-based success threshold for a low-fidelity test.

Video script
Explain why problem-solution fit precedes product-market fit, demonstrate a low-cost validation experiment, and show how evidence guides refinement instead of premature scaling.''',
    },
    {
        'title': 'Week 2 Day 5: Empathy Mapping, Ideation Sprint, and Startup Pitch',
        'video_url': 'https://youtu.be/qg4skYIZNss',
        'duration_minutes': 60,
        'notes': '''Introduction
Empathy mapping, ideation sprints, and concise startup pitches connect user understanding to entrepreneurial communication. They help founders move from what people experience to what a team will test and how it will explain the value clearly.

Empathy map
Capture what a target user says, thinks, does, and feels, then document pains and gains. Base every observation on interviews, surveys, or contextual research and distinguish evidence from interpretation. The map should reveal emotional, functional, social, and cultural dimensions of the problem.

Ideation sprint
Run a time-boxed session that begins with a clear opportunity, moves through divergent generation, clusters ideas, and converges using desirability, feasibility, viability, and impact. Brainwriting, SCAMPER, mind mapping, and role-play can reduce fixation and make participation more inclusive.

One-minute pitch
A useful elevator pitch identifies the target user, urgent problem, current limitation, solution, differentiated value, and intended impact. Avoid unsupported market claims and technical jargon. A clear pitch is also an internal test of whether the team understands its own idea.

Example
First-year university students may experience anxiety, loneliness, and academic pressure while avoiding formal counseling because of stigma or limited access. A peer-support platform could offer anonymous connection with trained mentors, guided self-care, and emotional check-ins. The idea still requires user research, safeguarding, privacy design, and a small pilot before claims are made.

Limitations and ethics
A narrow sample can distort an empathy map, an unstructured sprint can produce shallow ideas, and a polished pitch can hide weak evidence. Protect participant privacy, obtain appropriate consent, include diverse users, and treat feedback as learning rather than proof of success.

Activity
Create an evidence-based empathy map, run a 45-minute ideation sprint, select one concept, and write a one-minute pitch with one explicit assumption and one next experiment.

Video lesson guide
Use this reading as the workshop guide for the empathy-mapping, ideation-sprint, and pitch activity. No additional video was supplied for this topic.''',
    },
]


def format_notes(text):
    headings = {
        'Introduction', 'Ideation foundations', 'Problem-solving process',
        'Identifying market gaps', 'Validation and context', 'Empathize', 'Define',
        'Ideate', 'Iteration and responsibility', 'Value innovation', 'Strategy canvas',
        'Four Actions Framework', 'Startup application', 'Start with the problem',
        'Test the solution', 'Segment and context', 'Learning loop', 'Empathy map',
        'Ideation sprint', 'One-minute pitch', 'Example', 'Limitations and ethics',
        'Activity', 'Video script', 'Video lesson guide',
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
            elif heading in {'Video script', 'Video lesson guide'}:
                output.append(f'<aside class="learning-callout"><strong>Lesson guide</strong><p>{escape(body)}</p></aside>')
            else:
                output.append(f'<h2><strong><em>{escape(heading)}</em></strong></h2>')
                if body:
                    output.append(f'<p>{escape(body)}</p>')
        else:
            output.append(f'<p>{escape(" ".join(lines))}</p>')
    return ''.join(output)


class Command(BaseCommand):
    help = 'Create or refresh Week 2 lessons for Startup Fundamentals.'

    def add_arguments(self, parser):
        parser.add_argument('--instructor', help='Instructor username or numeric user id.')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        course = Course.objects.filter(slug='startup-fundamentals-idea-to-launch').first()
        if not course:
            raise CommandError('Startup Fundamentals course does not exist. Run seed_startup_fundamentals first.')
        instructor = self._get_instructor(options.get('instructor'))
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(WEEK2_LESSONS)} Week 2 lessons.'))
            return

        with transaction.atomic():
            for day, item in enumerate(WEEK2_LESSONS, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=8 + day,
                    defaults={'title': f'Week 2: Day {day}'},
                )
                Lesson.objects.update_or_create(
                    section=section,
                    order=1,
                    defaults={
                        'title': item['title'],
                        'lesson_type': item.get('lesson_type', Lesson.LessonType.VIDEO),
                        'content_text': format_notes(item['notes']),
                        'video_url': item.get('video_url', ''),
                        'duration_minutes': item['duration_minutes'],
                        'is_preview': False,
                        'is_downloadable': True,
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            f'Created or refreshed {len(WEEK2_LESSONS)} Week 2 lessons for {course.title} (instructor={instructor.username}).'
        ))

    def _get_instructor(self, identifier):
        queryset = User.objects.filter(role=User.Role.INSTRUCTOR)
        if identifier:
            try:
                return queryset.get(pk=identifier)
            except (User.DoesNotExist, ValueError):
                user = queryset.filter(username=identifier).first()
                if user:
                    return user
            raise CommandError(f'Instructor not found: {identifier}')
        user = queryset.order_by('id').first()
        if not user:
            raise CommandError('No instructor exists. Create an instructor or pass --instructor.')
        return user
