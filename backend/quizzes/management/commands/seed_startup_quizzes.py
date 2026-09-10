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


FACTS = {
    'Week 2 Day 1': [
        ('divergent thinking', 'generating many possible answers before selecting one', 'brainstorm several solutions before judging feasibility'),
        ('root cause', 'the underlying reason a problem occurs', 'use the 5 Whys to move beyond a visible symptom'),
        ('market gap', 'demand that existing offerings do not adequately satisfy', 'compare customer needs with current alternatives'),
        ('latent need', 'a need customers may not clearly express', 'observe workarounds instead of relying only on survey requests'),
        ('validation', 'testing an important assumption with evidence', 'measure behavior, willingness to switch, or willingness to pay'),
    ],
    'Week 2 Day 2': [
        ('empathy', 'understanding users in their real context', 'interview and observe users before proposing a solution'),
        ('define stage', 'turning research patterns into a focused problem statement', 'frame a human need instead of naming a preferred technology'),
        ('affinity map', 'grouping research observations into themes', 'cluster repeated frustrations from several interviews'),
        ('ideation', 'generating a range of possible solutions', 'use brainwriting before narrowing the options'),
        ('iteration', 'revising the problem or solution after learning', 'return to user research when an idea exposes a weak assumption'),
    ],
    'Week 2 Day 3': [
        ('blue ocean', 'a new market space where direct competition is less central', 'create new demand instead of copying crowded offerings'),
        ('value innovation', 'pursuing differentiation and lower cost together', 'remove low-value features while raising what customers value'),
        ('strategy canvas', 'a visual comparison of industry value factors', 'plot competitor offerings to find an opportunity to diverge'),
        ('Four Actions Framework', 'eliminate, reduce, raise, and create', 'question which industry factors should change'),
        ('non-customer', 'a potential user not currently served by the category', 'study underserved people when searching for new demand'),
    ],
    'Week 2 Day 4': [
        ('problem-solution fit', 'evidence that a meaningful problem and proposed response align', 'validate the problem before investing in a full product'),
        ('problem hypothesis', 'a testable claim about who experiences which problem', 'state the segment, situation, severity, and current workaround'),
        ('solution hypothesis', 'a testable claim about how an offering will help', 'show a prototype and observe meaningful user behavior'),
        ('MVP', 'the smallest responsible test of a critical assumption', 'run a concierge pilot instead of building every feature'),
        ('behavioral evidence', 'observable action that supports a claim', 'track a pilot commitment or repeat use rather than compliments'),
    ],
    'Week 2 Day 5': [
        ('empathy map', 'a view of what a user says, thinks, does, feels, pains, and gains', 'separate observed evidence from team interpretation'),
        ('ideation sprint', 'a time-boxed process for generating and prioritizing ideas', 'diverge first and evaluate options after the creative phase'),
        ('psychological safety', 'a team climate where people can share ideas and concerns', 'invite unusual ideas without immediate ridicule'),
        ('elevator pitch', 'a concise explanation of a startup idea and its value', 'state the user, problem, solution, difference, and impact'),
        ('ethical research', 'research that protects people and represents evidence honestly', 'obtain consent and avoid exposing private participant information'),
    ],
    'Week 3 Day 1': [
        ('Business Model Canvas', 'a visual framework for how a venture creates, delivers, and captures value', 'map assumptions across nine connected building blocks'),
        ('customer segment', 'a defined group a venture intends to serve', 'choose a researchable group with a shared problem'),
        ('value proposition', 'the outcome and benefit offered to a target customer', 'connect the offer to a meaningful job, pain, or gain'),
        ('revenue stream', 'a way the venture earns money', 'state who pays, what they pay for, and when payment occurs'),
        ('cost structure', 'the major costs and drivers required by the model', 'estimate costs that grow when customers or service volume grow'),
    ],
    'Week 3 Day 2': [
        ('Lean Canvas', 'an early-stage canvas focused on problems, solutions, and learning', 'prioritize the riskiest assumptions before scaling'),
        ('unfair advantage', 'a defensible strength competitors cannot easily copy', 'identify a relationship, insight, or asset that improves over time'),
        ('key metric', 'a measure tied to a meaningful business or user outcome', 'track activation or retention instead of page views alone'),
        ('BMC difference', 'a stronger focus on partners, activities, and resources in the BMC', 'use BMC when the wider operating system needs mapping'),
        ('assumption priority', 'ranking assumptions by importance and uncertainty', 'test the risky assumption that could invalidate the model'),
    ],
    'Week 3 Day 3': [
        ('customer job', 'what a customer is trying to accomplish', 'study functional, emotional, and social outcomes'),
        ('customer pain', 'an obstacle, risk, cost, or frustration', 'prioritize pains important enough to change behavior'),
        ('customer gain', 'a desired or improved outcome', 'distinguish required gains from merely surprising benefits'),
        ('pain reliever', 'a product or service element that reduces an important pain', 'connect a feature to a specific customer difficulty'),
        ('value fit', 'alignment between a value map and important customer needs', 'test whether users would switch from their current alternative'),
    ],
    'Week 3 Day 4': [
        ('minimum viable product', 'the smallest responsible experiment that creates learning', 'test one critical assumption with limited effort'),
        ('learning goal', 'the specific uncertainty an experiment is designed to reduce', 'decide whether customers will complete a meaningful action'),
        ('concierge MVP', 'a manually delivered service that tests value before automation', 'serve a small group while learning their workflow'),
        ('decision rule', 'a predefined threshold that guides the next action', 'pivot when conversion stays below the agreed threshold'),
        ('responsible MVP', 'a test that protects users and communicates limitations', 'obtain consent and do not present a prototype as finished'),
    ],
    'Week 3 Day 5': [
        ('canvas evidence note', 'a record of whether a block is observed, quoted, assumed, or targeted', 'attach a source or test to every canvas block'),
        ('business model dependency', 'a relationship in which one canvas block affects another', 'check how a channel changes acquisition cost and trust'),
        ('operational feasibility', 'whether the venture can actually deliver its promise', 'match key activities and resources to the value proposition'),
        ('financial viability', 'whether the model can sustain its costs and revenue logic', 'compare expected collection timing with variable and fixed costs'),
        ('canvas stress test', 'a structured challenge to the weakest model assumptions', 'ask what customers use today and which partner is essential'),
    ],
    'Week 4 Day 1': [
        ('customer segmentation', 'dividing a broad market into meaningful groups', 'segment by problem, behavior, context, and urgency'),
        ('persona', 'an evidence-based representation of a priority user', 'include goals, pains, behaviors, constraints, and alternatives'),
        ('behavioral segment', 'a group defined by actions or needs rather than demographics alone', 'separate frequent users from occasional users'),
        ('segment priority', 'choosing which group to research first', 'consider severity, reachability, adoption, and capability fit'),
        ('persona evidence', 'observed or reported information supporting a persona detail', 'label assumptions instead of presenting them as facts'),
    ],
    'Week 4 Day 2': [
        ('market interview', 'a conversation designed to learn from a user experience', 'ask about recent behavior and current workarounds'),
        ('survey', 'a structured set of questions for comparable responses', 'pilot neutral questions before distributing them widely'),
        ('observation', 'studying behavior in the setting where it occurs', 'notice interruptions and workarounds users may not mention'),
        ('leading question', 'a question that pushes a participant toward an answer', 'replace “Would you love this?” with a neutral behavior question'),
        ('triangulation', 'comparing evidence from different research methods', 'check whether interviews, observation, and surveys show the same pattern'),
    ],
    'Week 4 Day 3': [
        ('activation', 'a meaningful first action showing a user received value', 'define the event that means a new user reached value'),
        ('retention', 'continued use or return over a defined period', 'compare cohorts to see whether users come back'),
        ('cohort', 'users grouped by a shared start period or characteristic', 'compare users who began in the same month'),
        ('vanity metric', 'a number that looks positive but does not guide a decision', 'avoid treating raw page views as product-market fit'),
        ('metric decision rule', 'a predefined action linked to a metric result', 'change the experiment when retention misses its threshold'),
    ],
    'Week 4 Day 4': [
        ('landing page', 'a focused page that presents a value proposition and action', 'measure qualified visitors who complete the intended action'),
        ('waitlist', 'a record of people expressing interest before launch', 'follow sign-ups with interviews or a pilot to test commitment'),
        ('pre-sale', 'a commitment to purchase before full delivery', 'state delivery timing, terms, limitations, and refund conditions'),
        ('conversion rate', 'the share of a defined audience completing an action', 'report the numerator and denominator for a sign-up result'),
        ('validation threshold', 'the result required to support a decision', 'define the minimum qualified sign-ups before launching the next test'),
    ],
    'Week 4 Day 5': [
        ('validation loop', 'hypothesis, research, experiment, evidence, decision, and revision', 'change the next action based on what the test reveals'),
        ('falsifiable hypothesis', 'a claim that evidence could show to be wrong', 'state a measurable behavior and a clear target segment'),
        ('peer feedback', 'structured critique from informed reviewers or participants', 'ask for disconfirming evidence instead of collecting praise'),
        ('research limitation', 'a factor that reduces confidence in a finding', 'record a small sample, selection bias, or missing context'),
        ('persevere or pivot', 'a decision to continue or change direction based on evidence', 'use the threshold and learning goal rather than founder attachment'),
    ],
    'Week 5 Day 1': [
        ('unit economics', 'the value and cost of serving one customer', 'compare contribution margin, CAC, and retention'),
        ('revenue model', 'the way a venture earns money', 'match pricing and collection to customer value and delivery cost'),
        ('CAC', 'the cost of acquiring a paying customer', 'include attributable sales and marketing costs by channel'),
        ('LTV', 'an estimate of customer contribution over a relationship', 'base the estimate on collected revenue, margin, and retention'),
        ('payback period', 'the time needed to recover acquisition cost', 'compare the time to recover CAC with available runway'),
    ],
    'Week 5 Day 2': [
        ('fixed cost', 'a cost relatively stable over a period', 'plan core subscriptions or rent separately from transaction costs'),
        ('variable cost', 'a cost that changes with customers or activity', 'estimate payment fees and delivery costs per customer'),
        ('startup budget', 'a plan for expected costs and cash needs', 'list timing, owner, payment terms, and confidence for each cost'),
        ('runway', 'the time available cash can support planned spending', 'calculate runway under conservative and base scenarios'),
        ('contingency', 'a reserved amount for uncertainty or unexpected costs', 'include a buffer for delays, refunds, or repairs'),
    ],
    'Week 5 Day 3': [
        ('sole proprietorship', 'a business structure closely tied to one owner', 'consider personal liability and continuity before choosing it'),
        ('limited liability partnership', 'a partnership form with defined liability and governance rules', 'verify the applicable local requirements with an adviser'),
        ('private limited company', 'a separate corporate structure with formal ownership and governance', 'consider it when investment and ownership transfer matter'),
        ('legal structure factor', 'a consideration used to choose an entity type', 'compare liability, taxation, compliance, ownership, and funding'),
        ('founder agreement', 'a written record of founder rights and responsibilities', 'document roles, ownership expectations, decisions, and disputes'),
    ],
    'Week 5 Day 4': [
        ('financial plan', 'a linked model of revenue, costs, cash, and funding assumptions', 'connect the forecast to the business model and milestones'),
        ('cash flow', 'the timing of money received and paid', 'separate collection timing from revenue recognition'),
        ('scenario planning', 'testing a model under different assumptions', 'prepare conservative, base, and upside cases'),
        ('funding milestone', 'a measurable result funding is intended to achieve', 'tie a request to validated retention or a completed pilot'),
        ('financial control', 'a process that protects accuracy and accountability', 'reconcile cash and organize receipts, invoices, and contracts'),
    ],
    'Week 6 Day 1': [
        ('bootstrapping', 'funding a venture through founder resources and early revenue', 'preserve ownership while managing growth and personal risk'),
        ('angel investor', 'an individual who invests capital and may provide expertise or networks', 'evaluate support and control terms beyond the cheque'),
        ('venture capital', 'institutional investment generally aimed at high-growth opportunities', 'consider dilution, governance, reporting, and growth expectations'),
        ('crowdfunding', 'raising funds from many people through a platform or campaign', 'verify the model, fees, rights, and applicable regulations'),
        ('funding fit', 'matching a capital source to stage, risk, control, and milestone', 'choose capital based on evidence and business needs'),
    ],
    'Week 6 Day 2': [
        ('pre-seed', 'early capital for discovery, prototypes, and initial experiments', 'show a credible problem, team, and learning milestones'),
        ('seed funding', 'capital supporting an early product, pilots, and initial traction', 'connect the raise to evidence and the next milestone'),
        ('Series A', 'a later round commonly associated with validated growth potential', 'show stronger product, market, metrics, and repeatability'),
        ('funding stage', 'a development phase associated with certain evidence and capital needs', 'prioritize milestones over chasing a label'),
        ('use of funds', 'a clear explanation of how raised capital will be spent', 'link spending to runway and measurable risk reduction'),
    ],
    'Week 6 Day 3': [
        ('pitch deck', 'a concise document explaining an opportunity and funding request', 'use evidence, readable charts, and one message per slide'),
        ('traction', 'evidence of meaningful customer or business progress', 'report actual activation, retention, revenue, or pilots'),
        ('market slide', 'a clear explanation of the target market and reachable segment', 'state assumptions and sources behind the market estimate'),
        ('go-to-market slide', 'an explanation of how the venture will reach and serve customers', 'connect channel choice to customer behavior and economics'),
        ('funding ask', 'the amount requested and the milestone it will enable', 'state amount, use of funds, runway, and next proof point'),
    ],
    'Week 6 Day 4': [
        ('investor fit', 'alignment between a startup and an investor mandate or contribution', 'consider sector, stage, geography, support, and expectations'),
        ('valuation', 'an agreed or negotiated basis for pricing ownership', 'understand dilution together with the full terms'),
        ('liquidation preference', 'a term affecting distribution of proceeds in certain exits', 'ask advisers how the term changes downside outcomes'),
        ('vesting', 'a schedule by which ownership rights are earned over time', 'document founder and employee equity conditions clearly'),
        ('due diligence', 'review of claims, records, risks, and obligations before a deal', 'organize honest financial, legal, ownership, and metric records'),
    ],
    'Week 6 Day 5': [
        ('ten-slide pitch', 'a concise investor presentation with a structured story', 'cover problem, customer, solution, market, model, evidence, team, ask, and risks'),
        ('pitch simulation', 'a practice presentation with timed questions and feedback', 'assign presenters, investors, reviewers, and a timekeeper'),
        ('revision log', 'a record of changes made and the evidence behind them', 'update the deck after repeated feedback and learning'),
        ('investor question', 'a request for evidence about opportunity, risk, or execution', 'answer directly and distinguish facts from forecasts'),
        ('responsible pitch', 'a presentation that communicates claims, risks, and limitations honestly', 'never invent customers, returns, traction, or market size'),
    ],
    'Week 7 Day 1': [
        ('complementary team', 'a team whose capabilities cover different important venture needs', 'map product, customer, operations, and finance capabilities'),
        ('accountability', 'clear ownership for an important outcome', 'assign one owner even when several people contribute'),
        ('working agreement', 'shared rules for decisions, feedback, conduct, and information', 'write how disagreement and missed commitments will be handled'),
        ('capability gap', 'an important skill or responsibility not adequately covered', 'hire or develop the capability tied to the next milestone'),
        ('inclusive team', 'a team where different people can contribute meaningfully and safely', 'consider accessibility, language, and diverse customer perspectives'),
    ],
    'Week 7 Day 2': [
        ('startup culture', 'repeated behaviors a team rewards, tolerates, and models', 'reward honest learning and ethical customer treatment'),
        ('role scorecard', 'criteria describing the outcomes and capabilities required for a role', 'use consistent evidence-based hiring criteria'),
        ('onboarding', 'the process of helping a new team member become effective', 'provide context, tools, security practices, and a first deliverable'),
        ('ESOP', 'an employee stock option plan that may provide future ownership rights', 'explain vesting, uncertainty, and professional advice needs'),
        ('structured interview', 'a consistent interview using comparable questions and criteria', 'reduce bias by scoring evidence against the role requirements'),
    ],
    'Week 7 Day 3': [
        ('go-to-market plan', 'a plan for reaching, serving, and learning from a target customer', 'connect segment, channel, offer, owner, and measurable outcome'),
        ('acquisition channel', 'a route through which potential customers are reached', 'choose where the target customer already makes decisions'),
        ('qualification', 'checking whether a potential customer fits the target and has a relevant need', 'use a focused question before spending sales effort'),
        ('funnel metric', 'a measure of progress from reach to value or purchase', 'track activation and conversion rather than impressions alone'),
        ('responsible growth', 'customer acquisition based on honest claims and respectful treatment', 'avoid spam, fake engagement, and hidden limitations'),
    ],
    'Week 7 Day 4': [
        ('B2B', 'business-to-business selling involving organizational buyers', 'map users, champions, budget owners, procurement, and legal review'),
        ('B2C', 'business-to-consumer selling to individuals or households', 'optimize trust, convenience, onboarding, and repeat value'),
        ('sales cycle', 'the time and steps from first contact to purchase', 'measure the cycle separately for each sales motion'),
        ('buyer committee', 'multiple stakeholders involved in an organizational purchase', 'identify the user, champion, decision maker, and reviewer'),
        ('sales motion', 'the repeatable process used to acquire and serve customers', 'test the smallest credible motion before scaling a sales team'),
    ],
    'Week 7 Day 5': [
        ('GTM experiment', 'a bounded test of how a venture reaches and converts a customer', 'define channel, message, metric, threshold, and owner'),
        ('hiring scorecard', 'a structured list of role outcomes and evaluation criteria', 'assess candidates using relevant evidence and consistent standards'),
        ('co-founder alignment', 'shared understanding of roles, equity, decisions, and expectations', 'discuss conflict, time commitment, vesting, and exit scenarios'),
        ('roleplay', 'a simulated interaction used to practice and reveal assumptions', 'rehearse customer, hiring, or co-founder conversations'),
        ('feedback loop', 'using observed responses to revise a plan or decision', 'record feedback and change the GTM plan based on evidence'),
    ],
    'Week 8 Day 1': [
        ('scaling', 'increasing value without increasing complexity and cost at the same rate', 'confirm repeatable delivery before expanding'),
        ('scale readiness', 'evidence that a venture can grow responsibly', 'check demand, capacity, economics, controls, and team capability'),
        ('growth choice', 'a selected path for increasing customer or business value', 'choose one segment, channel, or retention priority'),
        ('exit strategy', 'a plan for transferring control or realizing value', 'consider acquisition, merger, IPO, or independence'),
        ('scale bottleneck', 'a constraint that limits sustainable growth', 'identify the process, cash, capacity, or people issue blocking expansion'),
    ],
    'Week 8 Day 2': [
        ('DAU', 'daily active users over a defined period', 'define active behavior before comparing daily usage'),
        ('MAU', 'monthly active users over a defined period', 'compare monthly activity with a precise user definition'),
        ('retention', 'continued use or return by a customer cohort', 'measure whether users keep receiving value'),
        ('churn', 'customers, users, or revenue lost during a period', 'investigate why customers leave instead of reading the rate alone'),
        ('NPS', 'a recommendation perception signal from customers', 'combine it with retention and behavioral evidence'),
    ],
    'Week 8 Day 3': [
        ('scale-up challenge', 'a new constraint created by increased volume or complexity', 'document processes before informal knowledge is lost'),
        ('operational system', 'a repeatable process with ownership, standards, and controls', 'monitor quality while volume increases'),
        ('funding gap', 'a cash need that arises before expected funds are available', 'model working capital and collection timing'),
        ('risk register', 'a record of risks, owners, mitigations, and warning signs', 'review security, regulatory, supplier, and key-person risks'),
        ('scale culture', 'team behaviors and management practices that support growth', 'add structure without losing learning and ethical conduct'),
    ],
    'Week 8 Day 4': [
        ('acquisition', 'a transaction in which another organization purchases a venture or its assets', 'prepare contracts, accounts, IP, and cap-table records'),
        ('merger', 'combining organizations under an agreed structure', 'evaluate governance, integration, culture, and stakeholders'),
        ('IPO', 'an initial public offering of shares to public investors', 'plan for extensive reporting, governance, and legal requirements'),
        ('due diligence', 'review of claims, records, risks, and obligations before a deal', 'organize accurate financial, legal, ownership, and customer records'),
        ('independent operation', 'continuing the venture without an exit transaction', 'choose it when control and long-term service remain priorities'),
    ],
    'Week 8 Day 5': [
        ('growth roadmap', 'a sequenced plan of milestones, owners, measures, and dependencies', 'review actual results against monthly or quarterly targets'),
        ('milestone', 'a measurable result marking progress toward an objective', 'connect each milestone to evidence and an owner'),
        ('dependency', 'a condition or task required before another can proceed', 'schedule capacity before promising expansion'),
        ('review point', 'a planned moment to compare results and revise the plan', 'use a decision rule when traction or funding changes'),
        ('final presentation', 'a concise explanation of the venture, evidence, plan, risks, and request', 'separate achieved results from targets and forecasts'),
    ],
}


def build_questions(facts):
    questions = []
    for term, definition, application in facts:
        questions.append((f'What does {term} mean?', definition, ['a company registration document', 'a branding color choice', 'a guaranteed funding outcome']))
        questions.append((f'Which action best applies {term}?', application, ['ignore customer evidence', 'choose the easiest assumption without testing', 'report only the most favorable result']))
    return questions


class Command(BaseCommand):
    help = 'Create or refresh ten-question, 80% passing quizzes for Startup Fundamentals Week 2-8 lessons.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        course = Course.objects.filter(slug='startup-fundamentals-idea-to-launch').first()
        if not course:
            raise CommandError('Startup Fundamentals course does not exist.')
        lessons = [lesson for section in course.sections.all() if section.title.startswith(('Week 2:', 'Week 3:', 'Week 4:', 'Week 5:', 'Week 6:', 'Week 7:', 'Week 8:')) for lesson in section.lessons.all()]
        missing = [lesson.title for lesson in lessons if section_key(lesson.section.title, lesson.title) not in FACTS]
        if missing:
            raise CommandError(f'No question bank for: {", ".join(missing)}')
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(lessons)} lessons and {len(lessons) * 10} questions.'))
            return

        with transaction.atomic():
            for lesson in lessons:
                quiz, _ = Quiz.objects.update_or_create(
                    lesson=lesson,
                    defaults={
                        'course': course,
                        'section': lesson.section,
                        'title': f'{lesson.title} Quiz',
                        'passing_score_percent': 80,
                        'max_attempts': 0,
                        'randomize_questions': False,
                    },
                )
                quiz.questions.all().delete()
                for order, (text, answer, distractors) in enumerate(build_questions(FACTS[section_key(lesson.section.title, lesson.title)]), start=1):
                    question = quiz.questions.create(text=text, question_type=Question.QuestionType.MULTIPLE_CHOICE, order=order, points=1)
                    answer_choices = build_answer_choices(answer, distractors, order)
                    for choice_order, choice_text in enumerate(answer_choices):
                        Choice.objects.create(question=question, text=choice_text, is_correct=choice_text == answer, order=choice_order)

        self.stdout.write(self.style.SUCCESS(f'Created or refreshed quizzes for {len(lessons)} Week 2-8 lessons.'))


def section_key(section_title, lesson_title):
    return lesson_title.split(': ', 1)[0] if lesson_title.startswith('Week ') else section_title.replace(':', '')
