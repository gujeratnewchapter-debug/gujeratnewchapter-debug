from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from html import escape

from accounts.models import User
from courses.models import Category, Course, Lesson, Resource, Section
from quizzes.models import Choice, Question, Quiz


MODULES = [
    {
        'title': 'Business Planning Foundations',
        'lessons': [
            {
                'title': 'Lesson 1: Why business plans matter',
                'focus': 'business-case thinking',
                'summary': 'A good business plan helps founders turn a promising idea into a testable, decision-ready plan for value creation, customer problem solving, and financial viability.',
                'outcomes': ['Explain why planning reduces confusion and wasted effort.', 'Differentiate between a product idea and a business opportunity.', 'Recognize the links between evidence, decisions, and execution.'],
                'exercise': 'Draft a one-paragraph business case for a small venture idea and list the assumptions that must be tested before launching.',
                'video_url': 'https://www.youtube.com/watch?v=4fndeDfaWCg',
            },
            {
                'title': 'Lesson 2: The business planning process',
                'focus': 'planning sequence',
                'summary': 'Business planning is a sequence of discovering problems, researching markets, testing assumptions, modeling revenue, and setting an implementation roadmap.',
                'outcomes': ['Map the steps from opportunity discovery to execution.', 'Understand why plans are revised as evidence grows.', 'Identify which decisions require more data before commitment.'],
                'exercise': 'Create a simple 5-step planning sequence for your venture and identify the earliest decision gate.',
                'video_url': 'https://www.youtube.com/watch?v=IYp5jqP9dYw',
            },
            {
                'title': 'Lesson 3: Business plan audiences and decisions',
                'focus': 'audience alignment',
                'summary': 'A business plan communicates to different audiences such as partners, lenders, employees, and investors; each group needs clear logic, evidence, and risk understanding.',
                'outcomes': ['Identify the main audiences for a business plan.', 'Match each section of a plan to a key decision need.', 'Distinguish between persuasive communication and operational clarity.'],
                'exercise': 'Write a short plan for one audience: a partner, investor, or team member, and note the single decision you want them to support.',
                'video_url': 'https://www.youtube.com/watch?v=9R6jqZJtZo8',
            },
        ],
    },
    {
        'title': 'Opportunity and Market Discovery',
        'lessons': [
            {
                'title': 'Lesson 4: Problem discovery and customer pain',
                'focus': 'customer pain',
                'summary': 'Founders should begin with a genuine customer need, not a polished product idea; pain signals reveal where value and willingness to pay are strongest.',
                'outcomes': ['Describe a customer pain clearly and measurably.', 'Separate symptom from underlying problem.', 'Identify signals that a problem is worth solving.'],
                'exercise': 'Interview one person about a repeated problem they face and capture the pain, frequency, and current workaround.',
                'video_url': 'https://www.youtube.com/watch?v=4s7J7po3zM8',
            },
            {
                'title': 'Lesson 5: Market research and opportunity sizing',
                'focus': 'market research',
                'summary': 'Market research helps founders estimate the size and structure of a demand pool, understand customer segments, and judge whether the opportunity is worth pursuing.',
                'outcomes': ['Use real market indicators to estimate opportunity size.', 'Describe a customer segment and its buying behavior.', 'Recognize the danger of using assumptions without evidence.'],
                'exercise': 'Create a table with 3 customer segments, their pain points, and at least one data source for each.',
                'video_url': 'https://www.youtube.com/watch?v=6YfA0A9N8UY',
            },
            {
                'title': 'Lesson 6: Competitor and substitute analysis',
                'focus': 'competitive landscape',
                'summary': 'Understanding direct and indirect competitors helps founders define differentiation, evaluate competitive pressure, and identify gaps in the market.',
                'outcomes': ['Map direct and indirect competitors.', 'Classify substitutes and price alternatives.', 'Use competitor gaps as clues for positioning.'],
                'exercise': 'Build a competitor table showing 4 competitors and the unmet need each fails to satisfy.',
                'video_url': 'https://www.youtube.com/watch?v=0Zk5L5a5bCU',
            },
        ],
    },
    {
        'title': 'Customer and Market Analysis',
        'lessons': [
            {
                'title': 'Lesson 7: Customer segmentation',
                'focus': 'segmentation',
                'summary': 'Customer segmentation moves a broad market into smaller groups with different needs, willingness to pay, and buying behavior, making the plan more focused.',
                'outcomes': ['Identify demographic, behavioral, and need-based segments.', 'Explain why a single product rarely fits all customers equally.', 'Link segments to pricing and channel choices.'],
                'exercise': 'Choose a venture and describe 3 customer segments using needs, purchase trigger, and buying behavior.',
                'video_url': 'https://www.youtube.com/watch?v=9eS5sCk2r6Q',
            },
            {
                'title': 'Lesson 8: Customer interviews and validation',
                'focus': 'validation',
                'summary': 'Customer interviews establish whether people actually feel the pain, pay for solutions, and prefer one offer over another.',
                'outcomes': ['Design discovery questions that reveal customer behavior.', 'Separate opinions from observed buying patterns.', 'Use evidence to decide whether a problem is real and urgent.'],
                'exercise': 'Prepare five interview questions and a follow-up question for each to test problem severity and current alternatives.',
                'video_url': 'https://www.youtube.com/watch?v=YkvZkJ2qA3w',
            },
            {
                'title': 'Lesson 9: Demand, willingness to pay, and market fit',
                'focus': 'willingness to pay',
                'summary': 'Demand is not just about customer interest; it is about whether people will pay near enough to sustain the business model at target costs.',
                'outcomes': ['Explain the relationship between demand and willingness to pay.', 'Measure whether a customer problem is monetizable.', 'State the basic conditions for product-market fit.'],
                'exercise': 'Write a short demand statement for your idea and identify the evidence needed to test price sensitivity.',
                'video_url': 'https://www.youtube.com/watch?v=7nL6Tq0F7Z8',
            },
        ],
    },
    {
        'title': 'Value Proposition and Business Model',
        'lessons': [
            {
                'title': 'Lesson 10: Value proposition design',
                'focus': 'value proposition',
                'summary': 'A strong value proposition explains the customer need, the offered improvement, and the reason the solution stands out in context.',
                'outcomes': ['Define a clear value proposition.', 'Explain job-to-be-done thinking in simple terms.', 'Connect product features to customer outcomes.'],
                'exercise': 'Draft one value statement using the format: For [customer], who [pain], our [offer] helps [outcome], unlike [alternative].',
                'video_url': 'https://www.youtube.com/watch?v=Z2QG4hcT2IY',
            },
            {
                'title': 'Lesson 11: Business model fundamentals',
                'focus': 'revenue logic',
                'summary': 'A business model shows how value is created, captured, and delivered; it includes customers, channels, relationships, revenue, key activities, and cost structure.',
                'outcomes': ['Explain the parts of a viable business model.', 'Describe how value moves from customer to revenue.', 'Recognize the difference between business idea and business model.'],
                'exercise': 'Sketch a simple business-model canvas for a venture in your context and name the riskiest assumption.',
                'video_url': 'https://www.youtube.com/watch?v=6lM0I-Z73ic',
            },
            {
                'title': 'Lesson 12: Pricing and monetization strategy',
                'focus': 'monetization',
                'summary': 'Pricing is a strategic decision that reflects customer value, relative alternatives, cost structure, and market positioning, not just a number chosen by intuition.',
                'outcomes': ['Compare cost-based, value-based, and competitive pricing.', 'Explain the role of packaging and bundles in monetization.', 'Identify ways to test pricing without full product launch.'],
                'exercise': 'Write three pricing options for a product and explain which option is safest, while also showing the likely customer reaction.',
                'video_url': 'https://www.youtube.com/watch?v=5R9jJ1e6tCo',
            },
        ],
    },
    {
        'title': 'Operations and Delivery',
        'lessons': [
            {
                'title': 'Lesson 13: Product and service design',
                'focus': 'solution design',
                'summary': 'A service or product should be designed to solve a defined need with minimum complexity, manageable quality, and a realistic delivery process.',
                'outcomes': ['Describe a product in terms of user value and operating requirements.', 'Differentiate between essential features and nice-to-have extras.', 'Plan a minimum viable offer.'],
                'exercise': 'List the essential features for a basic service version and identify one feature that can be deferred.',
                'video_url': 'https://www.youtube.com/watch?v=JXH2O0E0FhA',
            },
            {
                'title': 'Lesson 14: Operations and delivery model',
                'focus': 'operations',
                'summary': 'Operations convert the plan into repeatable daily steps such as order handling, fulfillment, customer support, and quality control.',
                'outcomes': ['Map delivery from customer request to fulfillment.', 'Spot bottlenecks and operational risks.', 'Design a simple operations workflow.'],
                'exercise': 'Create a step-by-step flow for delivering a service from first inquiry to payment and follow-up.',
                'video_url': 'https://www.youtube.com/watch?v=f3oJ8jM6VgM',
            },
            {
                'title': 'Lesson 15: Supplier, partner, and logistics planning',
                'focus': 'supply chain',
                'summary': 'Reliable execution depends on choosing the right suppliers, partners, and logistics arrangements to reduce cost, risk, and delays.',
                'outcomes': ['Assess external dependencies and delivery constraints.', 'Explain how supplier relationships affect quality and timing.', 'Plan a backup option for critical inputs.'],
                'exercise': 'List your top three dependencies and the contingency plan for each.',
                'video_url': 'https://www.youtube.com/watch?v=R0sYj8KveyY',
            },
        ],
    },
    {
        'title': 'Marketing and Sales Strategy',
        'lessons': [
            {
                'title': 'Lesson 16: Positioning and messaging',
                'focus': 'positioning',
                'summary': 'Positioning defines where a business fits in the market and how it communicates a distinctive value compared with alternatives.',
                'outcomes': ['Define a clear market position.', 'Write a short core message for target customers.', 'Explain why brand consistency matters in execution.'],
                'exercise': 'Write a positioning sentence that clearly states the target customer, problem, and differentiation.',
                'video_url': 'https://www.youtube.com/watch?v=2B-F6E5j27M',
            },
            {
                'title': 'Lesson 17: Customer acquisition channels',
                'focus': 'acquisition',
                'summary': 'Customer acquisition blends awareness, trust-building, engagement, conversion, and retention across both low-cost and high-scale channels.',
                'outcomes': ['Compare digital and offline channels.', 'Choose acquisition channels that fit the customer journey.', 'Plan a test for channel effectiveness.'],
                'exercise': 'Select two channels for your venture and justify each based on customer behavior and budget.',
                'video_url': 'https://www.youtube.com/watch?v=4fndeDfaWCg',
            },
            {
                'title': 'Lesson 18: Sales process and conversion',
                'focus': 'sales funnel',
                'summary': 'The sales process turns attention into action by clarifying the decision path, objections, evidence, and conversion actions.',
                'outcomes': ['Map a basic sales conversion funnel.', 'Prepare for objections and follow-up.', 'Link sales performance to retention and revenue.'],
                'exercise': 'Design a simple sales script for a customer profile and note the most likely objections.',
                'video_url': 'https://www.youtube.com/watch?v=E3C9Lq9K6M8',
            },
        ],
    },
    {
        'title': 'Organization and Management',
        'lessons': [
            {
                'title': 'Lesson 19: Team roles and ownership',
                'focus': 'team design',
                'summary': 'A business needs a clear division of responsibilities, decision rights, and accountability to work well as it grows.',
                'outcomes': ['Identify essential roles for a small venture.', 'Explain why role clarity drives execution.', 'Distinguish leadership from task completion.'],
                'exercise': 'List the core team roles needed for a small business and show who owns each critical decision.',
                'video_url': 'https://www.youtube.com/watch?v=u8d2P4iJpC0',
            },
            {
                'title': 'Lesson 20: Governance and culture',
                'focus': 'governance',
                'summary': 'Governance and culture shape how the team makes decisions, resolves conflicts, and maintains trust as the business scales.',
                'outcomes': ['Explain why business rules matter even in small firms.', 'Describe a healthy culture in practical terms.', 'Recognize governance risks tied to growth.'],
                'exercise': 'Write 3 team agreements that reduce confusion and improve accountability in a launch phase.',
                'video_url': 'https://www.youtube.com/watch?v=0g3oX4i93gY',
            },
            {
                'title': 'Lesson 21: Management systems and reporting',
                'focus': 'management control',
                'summary': 'A simple reporting system keeps the business focused on numbers that matter: sales, cash, defect rates, conversion, and milestones.',
                'outcomes': ['Identify the key dashboard metrics for a startup.', 'Explain the role of weekly reviews.', 'Differentiate between activity and outcome metrics.'],
                'exercise': 'Design a weekly dashboard with 5 metrics for a small venture and explain how each informs action.',
                'video_url': 'https://www.youtube.com/watch?v=MXQnYzYxP8E',
            },
        ],
    },
    {
        'title': 'Financial Planning Fundamentals',
        'lessons': [
            {
                'title': 'Lesson 22: Startup costs and capital needs',
                'focus': 'startup costs',
                'summary': 'Startup cost planning shows what must be invested before initial revenue and which costs are variable, recurring, or one-time.',
                'outcomes': ['Distinguish fixed and variable startup costs.', 'Estimate the minimum capital needed at launch.', 'Recognize the cost of waiting and under-budgeting.'],
                'exercise': 'List all startup cost categories for a chosen venture and estimate one realistic first-month amount.',
                'video_url': 'https://www.youtube.com/watch?v=8mR6h8jvNQE',
            },
            {
                'title': 'Lesson 23: Revenue, profit, and cash flow',
                'focus': 'cash flow',
                'summary': 'Revenue and profit are not the same as cash flow; strong plans track the timing of money in and out for the business to survive.',
                'outcomes': ['Explain the difference between revenue, profit, and cash flow.', 'Spot the risks of growth with poor liquidity.', 'Connect pricing to operating cash needs.'],
                'exercise': 'Create a short cash-flow worksheet showing inflows, outflows, and timing for one month of operations.',
                'video_url': 'https://www.youtube.com/watch?v=Qm5A4fJQdT0',
            },
            {
                'title': 'Lesson 24: Break-even and unit economics',
                'focus': 'unit economics',
                'summary': 'Break-even analysis reveals how many units or customers are necessary before fixed costs are covered and the venture becomes sustainable.',
                'outcomes': ['Define break-even point in practical terms.', 'Calculate contribution and gross margin.', 'Use unit economics to evaluate viability.'],
                'exercise': 'Compute a simple break-even example for one product and identify the required sales volume for sustainability.',
                'video_url': 'https://www.youtube.com/watch?v=3N0yVd5P8qA',
            },
        ],
    },
    {
        'title': 'Pricing, Revenue, and Cost Structures',
        'lessons': [
            {
                'title': 'Lesson 25: Cost structures and margin design',
                'focus': 'margins',
                'summary': 'A sound cost structure identifies the core expenses that drive the business and helps founders design a margin that can sustain growth.',
                'outcomes': ['Classify cost drivers by type and behavior.', 'Explain how margin changes pricing decisions.', 'Recognize trade-offs between scale and profitability.'],
                'exercise': 'List all direct and indirect costs for a venture and estimate which cost most threatens margin.',
                'video_url': 'https://www.youtube.com/watch?v=L3q4q8_WjRg',
            },
            {
                'title': 'Lesson 26: Revenue streams and diversification',
                'focus': 'revenue mix',
                'summary': 'Revenue diversification reduces dependence on one source and creates flexibility, but it requires a clear understanding of customer behavior and operating complexity.',
                'outcomes': ['List major revenue stream options.', 'Explain the value of a balanced revenue mix.', 'Spot concentration risk in a revenue model.'],
                'exercise': 'Identify two additional revenue streams your venture could add if customer demand expands.',
                'video_url': 'https://www.youtube.com/watch?v=9hL2C5MHHvE',
            },
            {
                'title': 'Lesson 27: Financial scenarios and sensitivity analysis',
                'focus': 'scenario planning',
                'summary': 'Sensitivity analysis shows how business performance changes when key assumptions such as price, conversion, or costs shift.',
                'outcomes': ['Describe best-case, base-case, and downside scenarios.', 'Use key variables to test business resilience.', 'Explain why plans need contingency assumptions.'],
                'exercise': 'Create three scenarios for your venture based on 20% changes in price, conversion, or cost assumptions.',
                'video_url': 'https://www.youtube.com/watch?v=9JH4mZ8X3v0',
            },
        ],
    },
    {
        'title': 'Funding, Risk, and Legal Basics',
        'lessons': [
            {
                'title': 'Lesson 28: Funding options and capital structure',
                'focus': 'capital structure',
                'summary': 'Funding is not only about raising money; it is about matching the right financing mix to the business stage, risk, control needs, and repayment obligations.',
                'outcomes': ['Compare personal capital, debt, grants, and equity.', 'Explain how capital choices affect ownership and risk.', 'Select the most appropriate funding option for a stage.'],
                'exercise': 'Rank three funding options for a venture and note the main trade-off of each.',
                'video_url': 'https://www.youtube.com/watch?v=Qx6hR2vV4xY',
            },
            {
                'title': 'Lesson 29: Risk management and contingency planning',
                'focus': 'risk management',
                'summary': 'Every plan contains uncertainty; the business plan should identify key risks and state how the venture will respond if conditions worsen.',
                'outcomes': ['Identify operational, market, and financial risks.', 'Design a risk response strategy.', 'Explain why contingency planning protects execution.'],
                'exercise': 'Select one key risk and create a mitigation and contingency response for it.',
                'video_url': 'https://www.youtube.com/watch?v=0GdZxKf15dE',
            },
            {
                'title': 'Lesson 30: Legal, tax, and compliance essentials',
                'focus': 'compliance',
                'summary': 'A business plan must reflect the legal and compliance realities of the operating environment, including registration, tax obligations, contracts, and governance.',
                'outcomes': ['Identify the necessary legal and operational checks.', 'Understand why compliance reduces future disruption.', 'Recognize when professional advice is necessary.'],
                'exercise': 'Prepare a checklist of legal and tax matters that must be reviewed before launch.',
                'video_url': 'https://www.youtube.com/watch?v=srXoX9u2P7w',
            },
        ],
    },
    {
        'title': 'Business Plan Writing and Pitching',
        'lessons': [
            {
                'title': 'Lesson 31: Writing the executive summary',
                'focus': 'executive summary',
                'summary': 'The executive summary is the short, persuasive overview that allows a reader to understand the venture, opportunity, model, and next step in a few minutes.',
                'outcomes': ['Write a concise summary of the venture story.', 'Prioritize the most material information.', 'Explain why the executive summary must be decision-focused.'],
                'exercise': 'Draft a 150-word executive summary for your venture, covering market need, offer, model, and growth goal.',
                'video_url': 'https://www.youtube.com/watch?v=HoP3gUhoXw0',
            },
            {
                'title': 'Lesson 32: Building the plan sections',
                'focus': 'plan structure',
                'summary': 'A complete plan draws together market analysis, product, operations, marketing, organization, finance, and risk into a coherent document.',
                'outcomes': ['Structure a professional plan by section.', 'Connect each content area to a business decision.', 'Avoid writing that is long but unconvincing.'],
                'exercise': 'Create a plan outline with 7 sections and a one-sentence purpose for each section.',
                'video_url': 'https://www.youtube.com/watch?v=I1Zr5wD2SwQ',
            },
            {
                'title': 'Lesson 33: Pitching your plan to partners and funders',
                'focus': 'pitching',
                'summary': 'A pitch should tell a clear story: the problem, the opportunity, the business model, the traction, and the ask with evidence behind every claim.',
                'outcomes': ['Prepare a clear investor or partner pitch.', 'Explain the difference between a plan and a pitch.', 'Link narrative flow to facts and proof.'],
                'exercise': 'Write a 3-minute pitch outline with problem, solution, traction, and financing ask.',
                'video_url': 'https://www.youtube.com/watch?v=Jv1Wru9qJ7Y',
            },
        ],
    },
    {
        'title': 'Implementation Roadmap and Review',
        'lessons': [
            {
                'title': 'Lesson 34: Milestones and execution roadmap',
                'focus': 'roadmap',
                'summary': 'A roadmap turns the business plan into practical milestones that provide focus, accountability, and a way to judge progress over time.',
                'outcomes': ['Break a plan into phases and checkpoints.', 'Identify the sequence of actions needed to launch.', 'Judge progress by evidence, not guesswork.'],
                'exercise': 'Create a 90-day roadmap with 3 milestones, owners, and proof points for each.',
                'video_url': 'https://www.youtube.com/watch?v=0bT4Q2WJ6dM',
            },
            {
                'title': 'Lesson 35: Reviewing assumptions and improving the plan',
                'focus': 'plan improvement',
                'summary': 'The best plans are iterative; they revise priorities and assumptions as customer feedback, operating realities, and financial signals become clearer.',
                'outcomes': ['Identify which assumptions are most critical to validate.', 'Decide when to keep, pivot, or stop an approach.', 'Explain why iteration is a strength, not a failure.'],
                'exercise': 'Review your plan and list the three assumptions that should be validated first in the next test cycle.',
                'video_url': 'https://www.youtube.com/watch?v=VwM9AKhO8pI',
            },
            {
                'title': 'Lesson 36: Final business-plan challenge',
                'focus': 'plan synthesis',
                'summary': 'The final challenge is to synthesize all the thinking into a coherent business-plan narrative that is realistic, evidence-based, and ready for action.',
                'outcomes': ['Integrate customer insight, model, risk, and finance into one plan.', 'Prepare a realistic next-step action plan.', 'Show confidence grounded in evidence and disciplined execution.'],
                'exercise': 'Write a final plan summary covering problem, customers, offer, model, launch path, key risks, and what you will validate next.',
                'video_url': 'https://www.youtube.com/watch?v=5z3qZ8ZQ2v0',
            },
        ],
    },
]


def build_answer_choices(correct_answer, distractors, question_order):
    choices = [correct_answer, *distractors]
    target_position = (question_order - 1) % len(choices)
    if target_position == 0:
        return choices
    correct_text = choices[0]
    remaining = choices[1:]
    return remaining[:target_position] + [correct_text] + remaining[target_position:]


def format_lesson_notes(title, summary, outcomes, exercise):
    lines = [
        f'<h2>{escape(title)}</h2>',
        f'<p>{escape(summary)}</p>',
        '<h3>Learning outcomes</h3>',
        '<ul>' + ''.join(f'<li>{escape(item)}</li>' for item in outcomes) + '</ul>',
        '<h3>Practical exercise</h3>',
        f'<p>{escape(exercise)}</p>',
    ]
    return ''.join(lines)


def build_lesson_questions(title, focus):
    focus_phrase = focus.lower()
    return [
        (
            f'What is the primary purpose of {title}?',
            f'To turn a problem, opportunity, and idea into a structured business decision about {focus_phrase}.',
            [
                'To avoid discussing customer needs or operational realities.',
                'To replace evidence with a creative slogan only.',
                'To describe one market trend without any business logic.',
            ],
        ),
        (
            f'Which evidence is most important for {title}?',
            f'Real customer pain, behavior, assumptions, and financial logic linked to {focus_phrase}.',
            [
                'A founder opinion with no customer validation.',
                'A marketing tagline without a clear customer problem.',
                'A copied business description from a different market.',
            ],
        ),
        (
            f'What should be true for a business plan section based on {title}?',
            f'It should be clear, supported by evidence, and connected to a practical decision or action.',
            [
                'It should be long and impressive without being testable.',
                'It should rely on assumptions that are never challenged.',
                'It should avoid numbers, timing, and implementation details.',
            ],
        ),
        (
            f'How should a founder respond to uncertainty in {title}?',
            'Test the key assumptions quickly, learn from evidence, and improve the plan before committing more resources.',
            [
                'Avoid testing and assume the initial idea is correct.',
                'Delay all decisions until the business proves itself fully.',
                'Treat every risk as permanent and unmanageable.',
            ],
        ),
        (
            f'What is the best next step after finishing {title}?',
            'Convert the insight into a small experiment, a decision gate, or a concrete change in the plan.',
            [
                'Stop all learning and wait for perfect certainty.',
                'Duplicate the plan without checking market reality.',
                'Rewrite the idea without measuring customer response.',
            ],
        ),
        (
            f'Why does {title} matter to a startup founder?',
            'Because it clarifies the business logic needed for sustainable value creation and action.',
            [
                'Because it lets a founder skip customer evidence.',
                'Because it guarantees market success without testing.',
                'Because it avoids any dependence on operations or costs.',
            ],
        ),
        (
            f'Which statement best captures the lesson in {title}?',
            f'A strong plan turns insight into evidence-based decisions, priorities, and realistic commitments around {focus_phrase}.',
            [
                'A strong plan should ignore customer behavior and cost assumptions.',
                'A strong plan should remain fixed even when evidence changes.',
                'A strong plan should be built only around a founder’s confidence.',
            ],
        ),
        (
            f'What should a founder review before concluding the plan topic in {title}?',
            'The assumptions, evidence, and decisions that could materially change the business outcome.',
            [
                'Only the most visually attractive slides or wording.',
                'Only past successes with no current evidence.',
                'Only legal formalities while ignoring demand and value.',
            ],
        ),
        (
            f'How should a founder treat risk during {title}?',
            'Manage it intentionally by testing, measuring, and making the plan more realistic.',
            [
                'Ignore it until after the launch has already begun.',
                'Treat risk as proof the idea should never be tested.',
                'Avoid using numbers or plans because they create uncertainty.',
            ],
        ),
        (
            f'What is the strongest practical outcome of completing {title}?',
            'A clearer and more defensible plan that connects the business idea to real customer and operational logic.',
            [
                'A longer document with no clearer decision path.',
                'A generic pitch that cannot be tested or improved.',
                'A set of assumptions that are never checked against reality.',
            ],
        ),
    ]


def build_module_final_questions(module_title):
    return [
        (
            f'What is the main purpose of the {module_title} module?',
            'To build the business logic needed for a realistic and evidence-based plan.',
            [
                'To replace all customer research with a founder’s intuition.',
                'To postpone all decisions until after launch.',
                'To make the plan more complex than the business requires.',
            ],
        ),
        (
            f'Which action best reflects strong planning in {module_title}?',
            'Testing assumptions with evidence and improving the plan when reality differs from expectation.',
            [
                'Keeping a plan fixed even when new information appears.',
                'Avoiding all numbers and operational decisions.',
                'Assuming customers will pay without validation.',
            ],
        ),
        (
            f'Why is evidence important in {module_title}?',
            'Because it reduces mistakes, reveals actual demand, and supports better decisions.',
            [
                'Because evidence is only needed after fundraising.',
                'Because it replaces the need for execution.',
                'Because it makes an idea less competitive in the market.',
            ],
        ),
        (
            f'What is the best way to reduce strategic risk in {module_title}?',
            'Identify the riskiest assumptions, collect evidence, and revise the plan based on what the market shows.',
            [
                'Increase the number of features before learning customer needs.',
                'Avoid measuring performance for early-stage decisions.',
                'Wait for perfect information before making any move.',
            ],
        ),
        (
            f'Which statement is most accurate for {module_title}?',
            'The business plan should connect market insight, financial logic, and execution into a realistic path.',
            [
                'The business plan should be a one-time document that never changes.',
                'The business plan should focus only on the founder’s vision.',
                'The business plan should ignore pricing, operations, and timing.',
            ],
        ),
        (
            f'What should a founder do after finding a strong business opportunity in {module_title}?',
            'Validate it with customers, define the offer, and test the model under realistic assumptions.',
            [
                'Begin full-scale production without testing demand.',
                'Wait for investors to solve the business problem.',
                'Ignore unit economics and cash flow until after growth begins.',
            ],
        ),
        (
            f'How should a founder interpret negative feedback in {module_title}?',
            'As useful evidence to refine the idea, positioning, or execution strategy.',
            [
                'As proof the market is always wrong.',
                'As a reason to stop learning altogether.',
                'As a sign that the business model cannot be improved.',
            ],
        ),
        (
            f'What makes a plan practical in {module_title}?',
            'It is clear, measurable, testable, and tied to decisions the business can realistically make.',
            [
                'It is long, detailed, and impressive without being based on evidence.',
                'It relies only on generic statements and broad assumptions.',
                'It avoids customer segments, costs, and risks.',
            ],
        ),
        (
            f'What is the best way to measure progress in {module_title}?',
            'Progress should be judged by customer evidence, decisions taken, and the quality of the business logic.',
            [
                'Progress is judged only by the number of slides produced.',
                'Progress is judged only by confidence without validation.',
                'Progress is judged only by the amount of money spent.',
            ],
        ),
        (
            f'What should the final takeaway from {module_title} be?',
            'A stronger plan that is more realistic, more testable, and more ready for action.',
            [
                'A document that never changes and never requires evidence.',
                'A pitch that hides the real business challenge.',
                'A fixed idea that ignores market feedback.',
            ],
        ),
    ]


class Command(BaseCommand):
    help = 'Create or refresh the Business Plan Development course content.'

    def add_arguments(self, parser):
        parser.add_argument('--instructor', help='Instructor username or user ID.')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        instructor = self._get_instructor(options.get('instructor'))
        if options['dry_run']:
            total_lessons = sum(len(module['lessons']) for module in MODULES)
            self.stdout.write(self.style.SUCCESS(f'Validated {len(MODULES)} modules and {total_lessons} lessons.'))
            return

        with transaction.atomic():
            category, _ = Category.objects.get_or_create(slug='business', defaults={'name': 'Business'})
            course, _ = Course.objects.update_or_create(
                slug='business-plan-development',
                defaults={
                    'title': 'Business Plan Development',
                    'subtitle': 'From opportunity discovery to a practical, evidence-based plan',
                    'description': '<h2>Business Plan Development</h2><p>This course turns an idea into a credible, implementation-ready business plan. Learners work from customer pain, market evidence, value creation, business-model logic, operations, financial planning, and risk management into a realistic plan they can use for execution or fundraising.</p><p>Each lesson is designed to be practical and action-oriented, emphasizing hypotheses, evidence, and decision-making rather than generic theory.</p>',
                    'short_description': 'Build a realistic business plan grounded in evidence, numbers, and execution.',
                    'notes': '<h2>Course study guide</h2><p>Work through each module in order. Every lesson includes a practical exercise, a short reflection, and a quiz to reinforce the business logic behind the plan.</p><p>Complete the final capstone by combining your validated assumptions, market analysis, pricing logic, and financial plan into a coherent business proposal.</p>',
                    'notes_enabled': True,
                    'learning_objectives': 'Identify promising business opportunities; analyze customer needs and market structure; design a value proposition and business model; estimate costs, cash flow, and break-even; write a practical business plan; prepare a pitch and execution roadmap.',
                    'requirements': 'No prior business degree required. Basic literacy and a willingness to test real assumptions with evidence are recommended.',
                    'target_audience': 'Aspiring founders, startup teams, students, SME owners, and professionals designing a new venture or growth plan.',
                    'tags': 'business plan, entrepreneurship, startup, market research, operations, finance, pitch',
                    'instructor': instructor,
                    'category': category,
                    'level': Course.Level.INTERMEDIATE,
                    'status': Course.Status.PUBLISHED,
                    'price': 0,
                    'is_free': True,
                    'language': 'English',
                    'duration_hours': 12,
                },
            )

            total_lessons = 0
            for module_order, module in enumerate(MODULES, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=module_order,
                    defaults={'title': f'Module {module_order}: {module["title"]}'},
                )

                for lesson_order, lesson in enumerate(module['lessons'], start=1):
                    total_lessons += 1
                    lesson_obj, _ = Lesson.objects.update_or_create(
                        section=section,
                        order=lesson_order,
                        defaults={
                            'title': lesson['title'],
                            'lesson_type': Lesson.LessonType.VIDEO,
                            'content_text': format_lesson_notes(
                                lesson['title'],
                                lesson['summary'],
                                lesson['outcomes'],
                                lesson['exercise'],
                            ),
                            'video_url': lesson.get('video_url', ''),
                            'source_url': 'https://www.sba.gov/business-guide/plan-your-business',
                            'duration_minutes': 35,
                            'is_preview': total_lessons == 1,
                            'is_downloadable': True,
                        },
                    )

                    Resource.objects.filter(lesson=lesson_obj).delete()
                    Resource.objects.create(
                        lesson=lesson_obj,
                        title=f'{lesson["title"]} - Template reference',
                        resource_type=Resource.ResourceType.VIDEO,
                        url='https://www.youtube.com/results?search_query=business+plan+template',
                        order=1,
                    )

                    quiz, _ = Quiz.objects.update_or_create(
                        lesson=lesson_obj,
                        defaults={
                            'course': course,
                            'section': section,
                            'title': f'{lesson["title"]} Quiz',
                            'passing_score_percent': 80,
                        },
                    )
                    quiz.questions.all().delete()

                    questions = build_lesson_questions(lesson['title'], lesson['focus'])
                    for question_order, (question_text, answer, distractors) in enumerate(questions, start=1):
                        question = Question.objects.create(
                            quiz=quiz,
                            text=question_text,
                            question_type=Question.QuestionType.MULTIPLE_CHOICE,
                            order=question_order,
                        )
                        answer_choices = build_answer_choices(answer, distractors, question_order)
                        for choice_order, choice_text in enumerate(answer_choices):
                            Choice.objects.create(
                                question=question,
                                text=choice_text,
                                is_correct=choice_text == answer,
                                order=choice_order,
                            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Created course {course.title} (id={course.id}) with {len(MODULES)} modules and {sum(len(m["lessons"]) for m in MODULES)} lessons.'
            )
        )

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
