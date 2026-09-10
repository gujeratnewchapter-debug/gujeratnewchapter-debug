from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from html import escape
from pathlib import Path

from accounts.models import User
from courses.models import Category, Course, Section, Lesson, Resource
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


def build_content_questions(title, explanation, activity, video, source_title):
    """Create a 10-question content-aware bank from the current lesson metadata.

    Questions stay lesson-attached and content-based, avoiding generic
    learner-centered wording that would drift away from the actual lesson.
    """
    explanation_core = explanation.split('.')[0].strip()
    if len(explanation_core) < 20:
        explanation_core = explanation.strip()

    activity_core = activity.split('.')[0].strip()
    if len(activity_core) < 20:
        activity_core = activity.strip()

    video_core = video.split('.')[0].strip()
    if len(video_core) < 20:
        video_core = video.strip()

    topic = title.split(':', 1)[-1].strip() if ':' in title else title

    return [
        (f'What is the central idea emphasized in the lesson {title}?', explanation_core, [
            'A lesson that avoids any participation or evidence.',
            'A lesson that ignores the same concept described above.',
            'A lesson that repeats the title without any learning move.',
        ]),
        (f'Which activity best matches the practical learning goal of {title}?', activity_core, [
            'An activity that avoids the local problem or customer context.',
            'An activity that removes the need for evidence.',
            'An activity that avoids the next useful action tied to the lesson.',
        ]),
        (f'What should the teaching guide for {title} focus on?', video_core, [
            'A lesson that avoids comparison with local practice.',
            'A lesson that removes evidence from the explanation.',
            'A lesson that ignores the problem and opportunity structure.',
        ]),
        (f'Which statement best describes why the lesson {title} matters?', f'{topic} connects a practical entrepreneurial question, evidence, and action.', [
            'It only asks for a copied business plan.',
            'It removes all analysis of opportunity or value creation.',
            'It treats entrepreneurship as a purely personal label.',
        ]),
        (f'What type of evidence should a study flow for {title} seek?', 'Evidence that supports the lesson’s problem, opportunity, user need, or value claim.', [
            'Evidence that is unrelated to the problem being discussed.',
            'Evidence that denies all learning from experience.',
            'Evidence that removes customer or community context.',
        ]),
        (f'What is the strongest learning move after reading {title}?', 'Turn the idea into a small experiment, reflection, or activity connected to evidence.', [
            'Avoid the lesson’s practice task entirely.',
            'Replace the lesson with a random idea with no evidence.',
            'Skip reflection and describe only the title.',
        ]),
        (f'Which question belongs naturally with the lesson {title}?', f'How can this idea be tested with a real problem, user, or decision in context?', [
            'How can the lesson avoid evidence altogether?',
            'How can the lesson be disconnected from action?',
            'How can the topic be ignored entirely?',
        ]),
        (f'What should be remembered while moving through {title}?', 'The lesson should be connected to a real opportunity path, a customer problem, and a useful learning action.', [
            'The lesson should ignore people, context, and evidence.',
            'The lesson should stop at the title and never become practice.',
            'The lesson should remove any idea of improvement or action.',
        ]),
        (f'Which teaching action is most consistent with {title}?', 'Explain the concept, connect it to a local example, and guide a small evidence-based practice.', [
            'Read the title and stop before connecting the idea to evidence.',
            'Skip examples and practice completely.',
            'Treat every concept as unrelated to community learning.',
        ]),
        (f'What is the most useful outcome of completing {title}?', 'A learner can explain the idea, connect it to a local example, and identify one next evidence-producing action.', [
            'The lesson is ignored and every example is missed.',
            'The title is described but the lesson cannot connect to learning.',
            'The relationship between problem, value, and action is forgotten.',
        ]),
    ]


SOURCE_LINKS = {
    'Hisrich, Peters and Shepherd - Entrepreneurship, 10th edition (reference)': 'https://www.slideshare.net/slideshow/entrepreneurship_by_robert_hisrich_micha-pdf/274747683',
    'IDEO Design Thinking': 'https://designthinking.ideo.com/',
    'IDEO Design Thinking Process': 'https://designthinking.ideo.com/process',
    'SBA Market Research': 'https://www.sba.gov/business-guide/plan-your-business/market-research-competitive-analysis',
    'SBA Startup Costs': 'https://www.sba.gov/business-guide/plan-your-business/calculate-your-startup-costs',
    'Strategyzer Business Model Canvas': 'https://www.strategyzer.com/library/the-business-model-canvas',
    'UN Sustainable Development Goals': 'https://www.un.org/sustainabledevelopment/sustainable-development-goals/',
    'OpenLearn Entrepreneurship': 'https://www.open.edu/openlearn/money-business/entrepreneurship-and-innovation',
}

FIRST_THREE_QUESTIONS = {
    'What Is Entrepreneurship, Really?': [
        ('Which statement best describes entrepreneurship?', 'Creating value by recognizing or creating opportunities and acting under uncertainty', ['Opening any business without research', 'Avoiding all risk before acting', 'Only working inside a large company']),
        ('Which scholar is most associated with the entrepreneur as a risk-bearer?', 'Richard Cantillon', ['Jean-Baptiste Say', 'Joseph Schumpeter', 'Israel Kirzner']),
        ('What does Jean-Baptiste Say emphasize?', 'Coordinating resources toward more productive uses', ['Creative destruction', 'Opportunity alertness only', 'Avoiding all investment']),
        ('What does Schumpeter associate most closely with entrepreneurship?', 'Innovation and new combinations', ['Routine administration', 'Fixed prices', 'Family succession only']),
        ('What does Kirzner emphasize?', 'Alertness to overlooked opportunities', ['Ownership of factories', 'Government taxation', 'Formal education only']),
        ('True or false: every business is a startup.', 'False', ['True', 'Only technology businesses are startups', 'Only social enterprises are startups']),
        ('What makes a startup different from an ordinary business?', 'It searches for a repeatable and scalable model under uncertainty', ['It must have a physical store', 'It cannot earn revenue', 'It never changes its plan']),
        ('Which item is part of the Hisrich, Peters, and Shepherd working definition?', 'Creating something new and valuable through time, effort, risk, and possible reward', ['Guaranteeing profit', 'Avoiding customers', 'Using technology in every case']),
        ('What should a student do before investing heavily in a meal-delivery idea?', 'Investigate the problem and run a small evidence-gathering test', ['Rent a large office', 'Assume all students will buy', 'Build every feature first']),
        ('Why are entrepreneurial traits not a fixed checklist?', 'People can develop capabilities through education, experience, networks, and practice', ['Entrepreneurs never need skills', 'Traits do not affect behavior', 'Only age determines entrepreneurship']),
    ],
    'Types and Purposes of Entrepreneurship': [
        ('Which type usually serves a defined local market and prioritizes sustainable operation?', 'Small-business entrepreneurship', ['Scalable startup entrepreneurship', 'Corporate entrepreneurship', 'Portfolio entrepreneurship']),
        ('What is the main purpose of scalable startup entrepreneurship?', 'To build a repeatable model that can grow across a large market', ['To remain limited to one household', 'To avoid innovation', 'To operate without customers']),
        ('What distinguishes lifestyle entrepreneurship?', 'It prioritizes independence, flexibility, personal interests, and sustainable owner income', ['It always seeks the largest possible investment', 'It can only operate digitally', 'It must be family-owned']),
        ('What is central to social entrepreneurship?', 'A social or community mission supported by sustainable operations', ['Profit without considering stakeholders', 'Only government ownership', 'Avoiding revenue entirely']),
        ('What does green entrepreneurship address?', 'Environmental challenges while creating economic value', ['Only corporate hiring', 'Only retail pricing', 'Only international trade']),
        ('What is the difference between necessity and opportunity entrepreneurship?', 'Necessity responds to limited income alternatives; opportunity pursues a perceived possibility by choice', ['Necessity is always informal; opportunity is always digital', 'Necessity cannot create value', 'There is no difference']),
        ('Where does intrapreneurship occur?', 'Inside an established organization', ['Only in rural farms', 'Only after an IPO', 'Only in a family business']),
        ('What is serial entrepreneurship?', 'Creating or leading multiple ventures over time', ['Operating one shop forever', 'Selling only one product', 'Working without partners']),
        ('Can one venture belong to several categories?', 'Yes, categories can describe different purposes, sectors, ownership forms, and contexts', ['No, every venture has one permanent label', 'Only large companies can have categories', 'Only technology ventures overlap']),
        ('Why should imitation respect intellectual-property rights?', 'Because adapting a model is different from using protected names, designs, content, or technology without permission', ['Because imitation is never useful', 'Because customers dislike improvements', 'Because local markets prohibit competition']),
    ],
    'Entrepreneurship in Ethiopia and Africa': [
        ('Why does entrepreneurship matter in African economies?', 'It can create businesses, jobs, innovation, services, and community value', ['It removes the need for public institutions', 'It guarantees success for every founder', 'It replaces all formal employment']),
        ('Where can an agricultural entrepreneur create value?', 'Across production, collection, processing, storage, transport, marketing, and distribution', ['Only at the farm gate', 'Only after export', 'Only through a mobile app']),
        ('What is value addition in agriculture?', 'Improving a product or process through activities such as processing, packaging, storage, or distribution', ['Selling without changing access', 'Reducing quality to lower trust', 'Avoiding customers']),
        ('What does digital entrepreneurship use?', 'Digital tools or channels such as software, marketplaces, mobile services, payments, or online marketing', ['Only physical storefronts', 'Only imported machinery', 'Only printed advertising']),
        ('True or false: digital tools remove the need for trust and physical delivery.', 'False', ['True', 'Only for clothing businesses', 'Only in cities']),
        ('Why must African ventures adapt solutions to local markets?', 'Countries and regions differ in customers, languages, regulations, infrastructure, culture, and purchasing power', ['All African markets are identical', 'Adaptation prevents innovation', 'Technology works the same everywhere']),
        ('Which is an example of indirect employment?', 'Work created for suppliers, transport providers, distributors, or packaging businesses', ['Only the founder\'s income', 'Only a customer complaint', 'Only a government permit']),
        ('Which is a common entrepreneurial challenge?', 'Access to finance, infrastructure, skills, regulation, market access, or economic uncertainty', ['Guaranteed demand', 'Too much certainty', 'No need for planning']),
        ('What should happen before expanding a local solution to another country?', 'Test and improve it locally, then research and adapt it to the new context', ['Copy the model without research', 'Ignore local regulation', 'Scale before serving the first customer']),
        ('What is the entrepreneurial learning cycle?', 'Observe, identify, create, test, learn, adapt, and scale carefully', ['Borrow, spend, advertise, and stop', 'Design, launch, ignore, and repeat', 'Hire, expand, and avoid feedback']),
    ],
    'Creativity, innovation, and problem framing': [
        ('What is the difference between creativity and innovation?', 'Creativity generates possibilities, while innovation implements a useful possibility that creates value', ['Creativity guarantees market success, while innovation avoids implementation', 'Creativity only copies existing products, while innovation ignores customers', 'Creativity is financial planning, while innovation is legal registration']),
        ('What should an entrepreneur start with before choosing a technology?', 'A clear problem frame grounded in the situation and needs of the people affected', ['A favorite technology and a product name', 'A large investment and a finished advertising campaign', 'A solution copied from another market without evidence']),
        ('Which question is a human-centered problem frame?', 'How might farmers improve yield and income?', ['How can we sell more fertilizer?', 'How can we add more features to our app?', 'How can we make the technology more expensive?']),
        ('What does first-principles thinking help an entrepreneur do?', 'Separate facts from inherited assumptions before rebuilding an approach', ['Accept every traditional assumption without checking it', 'Avoid defining the problem so more ideas appear', 'Choose the most complex solution immediately']),
        ('Why can reframing a problem reveal new opportunities?', 'It can shift attention from one product to services, storage, finance, information, or other ways to create value', ['It removes the need to understand the affected people', 'It proves that the first solution was correct', 'It limits the opportunity to one technology']),
        ('Which sequence best represents the lesson\'s innovation formula?', 'Creativity plus implementation plus value equals innovation', ['Technology plus advertising plus funding equals innovation', 'Risk plus speed plus complexity equals innovation', 'A new name plus a new logo equals innovation']),
        ('What is a useful way to study one local problem creatively?', 'Write a symptom frame, a root-cause frame, and a human-centered How might we question', ['Write only a product description and skip the problem', 'Choose one solution and reject all alternative frames', 'Describe the problem only in technical language']),
        ('Which statement best describes a solution-first project?', 'It chooses a preferred solution before investigating the underlying problem and evidence', ['It begins with observations and tests different explanations', 'It identifies affected people before selecting a response', 'It separates facts from assumptions before designing']),
        ('What should a strong problem frame identify?', 'The situation, affected people, underlying need, and possible path to valuable improvement', ['Only the founder\'s preferred feature', 'Only the technology platform and launch date', 'Only the amount of funding available']),
        ('What is the main entrepreneurial lesson of problem framing?', 'Better questions can create more valuable possibilities than immediately building the first idea', ['Every problem has one obvious technical answer', 'Innovation requires advanced technology in every case', 'A solution should be built before anyone is consulted']),
    ],
    'Design thinking and user empathy': [
        ('What does design thinking integrate?', 'People\'s needs, technology possibilities, and organizational viability', ['Only the newest technology and the largest market', 'Only the founder\'s preferences and available funding', 'Only visual design and promotional content']),
        ('Which sequence names the design thinking process in this lesson?', 'Empathize, Define, Ideate, Prototype, and Test', ['Advertise, sell, scale, borrow, and exit', 'Forecast, fund, hire, launch, and repeat', 'Substitute, combine, adapt, modify, and eliminate']),
        ('What is the purpose of empathy research?', 'To understand people\'s experiences, needs, behaviors, and context before defining a solution', ['To persuade people to approve a finished product', 'To replace observation with the founder\'s assumptions', 'To prove that one technology must be used']),
        ('What does an empathy map record?', 'What a person says, thinks, does, and feels', ['Only the person\'s age and purchasing power', 'Only the product features they request', 'Only the founder\'s interpretation of the market']),
        ('Why should observations in an empathy map be labeled as evidence or interpretation?', 'To distinguish what was observed or reported from what the researcher inferred', ['To make every assumption appear scientifically proven', 'To avoid speaking with people directly', 'To ensure every user gives the same answer']),
        ('What should a good problem statement avoid?', 'Prescribing a technology before the user need and problem are understood', ['Naming the people affected by the problem', 'Describing a specific need and situation', 'Using evidence from observation or interviews']),
        ('Why is prototyping useful in design thinking?', 'It makes an idea tangible and inexpensive to test before major commitment', ['It guarantees that the final product will succeed', 'It eliminates the need for iteration', 'It replaces the need to understand users']),
        ('What does testing accomplish in an iterative design process?', 'It produces evidence that can improve, change, or reject the current idea', ['It confirms every original assumption without question', 'It ends the process after the first prototype', 'It focuses only on making the product look finished']),
        ('Which factors should be included in an inclusive empathy research frame?', 'Language, disability, income, gender, and connectivity', ['Only technical skill and access to premium devices', 'Only the founder\'s location and preferred communication style', 'Only the largest customer segment']),
        ('How does the post-harvest loss example illustrate design thinking?', 'It uses empathy and problem definition before developing, prototyping, and testing possible responses', ['It begins with a finished product and skips user research', 'It treats technology as the solution regardless of context', 'It uses one linear checklist that cannot be revised']),
    ],
    'SCAMPER, frugal, and disruptive innovation': [
        ('What does SCAMPER help an entrepreneur do?', 'Generate and improve ideas by changing, combining, simplifying, or repurposing an existing solution', ['Guarantee that every new idea will succeed', 'Calculate a venture budget without studying the problem', 'Replace customer evidence with personal enthusiasm']),
        ('What does the S in SCAMPER stand for?', 'Substitute', ['Simplify only', 'Scale', 'Standardize']),
        ('Which example best illustrates Combine in SCAMPER?', 'Combining coffee, study space, and high-speed internet into one cafe service', ['Removing three steps from an online order', 'Replacing plastic packaging with reusable packaging', 'Changing the order from collection to pre-order']),
        ('What does Put to another use encourage an entrepreneur to ask?', 'Whether an existing product or resource can create value for a different purpose', ['Whether every product must use advanced technology', 'Whether a solution should be copied without adaptation', 'Whether all existing features should be made more expensive']),
        ('Which action is an example of Eliminate in SCAMPER?', 'Reducing an online ordering process from eight steps to three', ['Adding more steps to make the service look advanced', 'Keeping every feature even when it adds no customer value', 'Serving only the most demanding mainstream customers']),
        ('What is the central focus of frugal innovation?', 'Delivering meaningful value with fewer resources, lower cost, and deliberate simplicity', ['Making an inferior product regardless of customer needs', 'Using the most expensive technology available', 'Adding complexity so the solution appears innovative']),
        ('Which combination is an example of a frugal agricultural transport solution?', 'Shared transport, simple scheduling, and mobile communication', ['Automated transport, premium pricing, and complex infrastructure', 'Large warehouses, imported machinery, and no communication', 'A high-cost platform designed only for affluent customers']),
        ('What makes disruptive innovation different from ordinary improvement?', 'It can enter through overlooked or new customers with a simpler offer and eventually reshape the market', ['It always uses the newest technology', 'It is any product that has a new feature', 'It only improves an existing product for its current customers']),
        ('Which sequence best describes a potential disruptive innovation pathway?', 'An accessible alternative serves overlooked customers, improves, gains adoption, and may challenge established firms', ['An expensive product launches for the largest customers and never changes', 'A company copies an incumbent and avoids serving new customers', 'A product adds features without changing who can access the market']),
        ('How should SCAMPER, frugal innovation, and disruptive innovation be distinguished?', 'SCAMPER changes an idea, frugal innovation reduces resource demands, and disruptive innovation describes a market-entry pattern', ['All three mean the same thing: inventing advanced technology', 'SCAMPER is only for finance, frugal innovation is only for agriculture, and disruption is any improvement', 'SCAMPER guarantees disruption, while frugal innovation requires large investment']),
    ],
}

DEFAULT_TEN_QUESTIONS = [
    ('What is the main learning move in this lesson?', 'Identify the lesson idea and connect it to evidence, action, and reflection', ['Ignore evidence', 'Skip action', 'Avoid reflection']),
    ('What should a learner do after reading the lesson?', 'Turn the idea into a practical activity or small test', ['Memorize it without using it', 'Stop questioning assumptions', 'Ignore the activity']),
    ('What is the best way to understand an entrepreneurial problem?', 'Observe the user, need, context, and evidence around it', ['Assume the first idea is correct', 'Avoid talking to others', 'Skip learning goals']),
    ('Which evidence improves a lesson claim?', 'A real user observation, test, or documented example', ['A random headline', 'A guessed market response', 'An unsupported statement']),
    ('What should a learner compare before choosing an opportunity?', 'The problem, the customer, the solution, and the value created', ['Only the logo', 'Only the meeting time', 'Only the instructor name']),
    ('What is a useful entrepreneurial habit?', 'Testing assumptions with small, affordable experiments', ['Skipping learning', 'Avoiding feedback', 'Acting without evidence']),
    ('Which action best supports a lesson?', 'Apply the concept to a local example or real decision', ['Memorize the chapter only', 'Skip the activity', 'Ignore the context']),
    ('What does a responsible learner need to do?', 'Separate assumptions from evidence and review the reasoning', ['Pretend uncertainty is certainty', 'Avoid collecting feedback', 'Refuse to revise the idea']),
    ('What is the value of a learning check?', 'It helps confirm that the learner can explain the lesson idea clearly', ['It removes the need for practice', 'It replaces the activity', 'It prevents all questions']),
    ('What should the learner do after a lesson?', 'Use the lesson to make a small evidence-based next step', ['Move on without reflection', 'Avoid applying the idea', 'Stop working with the material']),
]

MODULE_4_FINAL_QUESTIONS = [
    ('Which statement best describes an entrepreneurial opportunity?', 'A potentially valuable way to address a meaningful problem or unmet need', ['Any idea that sounds interesting', 'A product with no identifiable users', 'A guaranteed business result']),
    ('Which source can create an entrepreneurial opportunity?', 'Customer frustration, technological change, or a gap in an existing market', ['Only a new invention', 'Only a large amount of funding', 'Only a formal business degree']),
    ('Which is stronger evidence than a customer saying an idea is great?', 'Customers repeatedly experience the problem and demonstrate willingness to adopt or pay', ['The founder feels confident', 'Friends give positive opinions', 'A large number of features are planned']),
    ('What is the correct sequence for separating a situation from a proposed response?', 'Problem -> Need -> Opportunity -> Solution -> Value', ['Solution -> Problem -> Need -> Value -> Opportunity', 'Idea -> Investment -> Customer -> Problem -> Value', 'Value -> Product -> Problem -> Need -> Evidence']),
    ('What does a Jobs to Be Done statement describe?', 'The situation, motivation, and desired outcome a customer is trying to accomplish', ['Only the customer’s age and income', 'Only the features of a product', 'Only the company’s internal resources']),
    ('Which three lenses should be used to evaluate an opportunity?', 'Desirability, feasibility, and viability', ['Speed, popularity, and novelty', 'Technology, advertising, and scale', 'Revenue, branding, and office size']),
    ('What is the difference between risk and uncertainty?', 'Risk has outcomes whose probabilities can be estimated to some extent; uncertainty is harder to quantify', ['Risk is always harmless and uncertainty is always fatal', 'Risk concerns only money and uncertainty concerns only technology', 'There is no meaningful difference']),
    ('What does effectuation encourage an entrepreneur to do first?', 'Start with available means: who they are, what they know, and whom they know', ['Wait until the future can be predicted', 'Raise the largest possible investment', 'Build the complete product before learning']),
    ('What is opportunity cost?', 'The value of the best alternative given up when a choice is made', ['The total price of every possible option', 'The profit earned from the chosen option', 'A cost that applies only to money']),
    ('Which experiment is most useful for reducing uncertainty?', 'A small test with a hypothesis, measurable result, and continue/change/stop decision rule', ['Launching every feature at once', 'Asking only people who already agree', 'Investing heavily before testing demand']),
]

MODULE_5_FINAL_QUESTIONS = [
    ('What does a business model explain?', 'How an organization creates value, delivers it to customers, and captures enough value to remain sustainable', ['How to advertise without serving customers', 'How to avoid all business costs', 'How to guarantee profit before testing']),
    ('Which sequence best describes the basic business model logic?', 'Create value -> Deliver value -> Capture value', ['Capture value -> Ignore customers -> Create value', 'Advertise -> Borrow -> Hire', 'Spend -> Scale -> Close']),
    ('What is a channel?', 'A way a business communicates with, sells to, or delivers value to customers', ['Only a source of borrowed money', 'A fixed business expense', 'A legal ownership document']),
    ('Which statement correctly distinguishes fixed and variable costs?', 'Fixed costs generally do not change directly with short-term volume, while variable costs change with production or sales', ['All fixed costs change with every unit sold', 'Variable costs never change', 'The terms mean exactly the same thing']),
    ('Why do entrepreneurs use partners?', 'Partners can provide resources, capabilities, distribution, expertise, customers, or infrastructure', ['Partners eliminate every business risk', 'Partners make customers unnecessary', 'Partners guarantee ownership remains unchanged']),
    ('Which is an example of triple value?', 'A solar-lighting venture creates revenue, improves access to lighting, and reduces environmental harm', ['A venture creates only a logo', 'A business avoids measuring any outcome', 'A product increases cost without benefit']),
    ('Which question belongs to the five-question ethics test?', 'Who could be harmed by this decision?', ['How can we hide the decision?', 'How can we avoid all accountability?', 'How can we remove every stakeholder?']),
    ('What is the difference between revenue and profit?', 'Revenue is money generated from sales; profit is what remains after costs', ['Revenue and profit are always identical', 'Profit is sales before costs', 'Revenue is only cash withdrawn by the owner']),
    ('What does break-even mean?', 'The level of sales at which total revenue equals total costs', ['The point at which costs become infinite', 'The amount of money an owner withdraws', 'A guarantee that demand will continue']),
    ('Which financing source involves ownership dilution?', 'Equity financing', ['Bootstrapping', 'Debt', 'A conventional grant']),
]

MODULE_6_FINAL_QUESTIONS = [
    ('What is an entrepreneurial ecosystem?', 'A network of people, organizations, institutions, resources, and conditions that influence entrepreneurship', ['Only a group of competing businesses', 'A business plan owned by one founder', 'A market with no supporting relationships']),
    ('Which group can provide research, talent, incubation, and industry connections?', 'Universities and research institutions', ['Only customers', 'Only transport providers', 'Only competitors']),
    ('Why do entrepreneurial networks matter?', 'They can provide information, knowledge, customers, capital, skills, and partnerships', ['They guarantee that every idea succeeds', 'They remove the need for customer evidence', 'They replace all business operations']),
    ('Why should ecosystems be compared using specific dimensions?', 'Market, finance, talent, infrastructure, regulation, networks, and other conditions differ across contexts', ['Because one country is always best', 'Because all ecosystems are identical', 'Because scores guarantee business success']),
    ('Which statement about informal entrepreneurship is accurate?', 'It can provide income and services while also limiting access to finance, protection, records, and growth', ['It never creates economic value', 'It always has full institutional support', 'It is identical to a global corporation']),
    ('What does inclusive entrepreneurship ask?', 'Who has access to entrepreneurial opportunity and who is being left out?', ['How can support be limited to one group?', 'How can all evidence be ignored?', 'How can barriers be made permanent?']),
    ('What is an opportunity portfolio?', 'A structured collection of opportunities evaluated systematically before deeper commitment', ['A list of products already sold', 'A guarantee that every idea will be pursued', 'A financial statement only']),
    ('Which evidence is strongest in a portfolio?', 'Repeated customer behavior, transactions, commitments, or meaningful prototype usage', ['Personal enthusiasm', 'A single unsupported opinion', 'A long list of features']),
    ('What should a professional opportunity pitch lead with?', 'The problem, affected customer, evidence, opportunity, value, business logic, risks, and next step', ['Only the founder biography', 'Only a slogan and logo', 'Only a financial forecast with no assumptions']),
    ('What is the purpose of a 30-60-90 day plan?', 'To convert learning into measurable exploration, testing, decision, and action steps', ['To predict the future perfectly', 'To avoid collecting evidence', 'To commit all resources immediately']),
]

HISRICH_CHAPTER_MAP = {
    1: 'Chapters 1-3: entrepreneurial action, entrepreneurial mindset, corporate entrepreneurship, and generating new entries.',
    2: 'Chapter 1: entrepreneurial intentions, self-efficacy, cognitive adaptability, support networks, and learning from uncertainty.',
    3: 'Chapter 4: sources of new ideas, creative problem solving, innovation types, opportunity recognition, and product development.',
    4: 'Chapter 5: opportunity recognition, information sources, opportunity assessment, and domestic and international market analysis.',
    5: 'Chapters 5 and 7: assessing an opportunity, gathering evidence, and moving from an opportunity to a structured business plan.',
    6: 'Chapters 1 and 3: effectuation, bricolage, information search, decision thresholds, new-entry uncertainty, and risk reduction.',
    7: 'Chapters 7-8: business-plan logic, marketing information, target markets, value communication, channels, and implementation.',
    8: 'Chapters 1, 3, and 6: sustainable entrepreneurship, ethical conduct, trust, stakeholder responsibility, and protection of ideas.',
    9: 'Chapters 9-12: organizational costs, financial planning, budgets, cash flow, break-even, debt, equity, grants, and capital sources.',
    10: 'Chapters 2, 7, and 9: entrepreneurial culture, leadership, management teams, organization design, delegation, and advisors.',
    11: 'Chapters 4-5 and 13-14: international opportunity analysis, environmental context, growth strategies, partnerships, and external resources.',
    12: 'Chapters 7-10: integrating opportunity, marketing, organization, risk, and financial reasoning into a professional venture plan.',
}

LESSON_DETAIL = {
    'entrepreneurship': 'Explain the entrepreneur as an agent who notices a mismatch between a current situation and a better possible outcome, then organizes resources and accepts responsibility for action. Distinguish an idea, an opportunity, and a venture: an idea is a possibility, an opportunity has evidence of need and a path to value, and a venture repeatedly delivers that value.',
    'mindset': 'Connect the concept to observable behavior rather than personality labels. Learners should notice how they respond to ambiguity, rejection, feedback, and incomplete information, then convert a broad belief into a small behavior they can practice and measure.',
    'innovation': 'Explain the difference between novelty and value. A new product matters only when it improves an important customer outcome and can be delivered responsibly. Show how local constraints such as cash, electricity, transport, language, and trust shape the design rather than appearing as afterthoughts.',
    'opportunit': 'Teach opportunity recognition as disciplined scanning. Ask who experiences the problem, when it occurs, what they do now, what the workaround costs, and why existing providers have not solved it. Treat every score as a hypothesis until supported by customer evidence.',
    'problem': 'Keep the learner from jumping directly to a product. Start with the situation, affected person, desired progress, current alternatives, and root cause. Then compare a proposed solution against desirability, feasibility, viability, accessibility, safety, and the economics of delivery.',
    'decision': 'Make the reasoning visible: state the decision, evidence, assumptions, downside, opportunity cost, affordable loss, deadline, and review trigger. A good entrepreneurial decision is not always successful; it is designed to produce useful learning without exposing people or the venture to uncontrolled harm.',
    'effectuation': 'Use the learner\'s actual means as the starting point: who they are, what they know, who they know, and what they can access now. Explain how small commitments and partnerships allow goals to emerge while preserving control over downside.',
    'business model': 'Trace the complete system, not only the product: customer and user, value proposition, channel, relationship, revenue, key activities, resources, partners, and costs. Ask what must be true for the model to work and which block is currently based on assumption.',
    'value': 'Define value from the customer\'s point of view and from the venture\'s ability to sustain delivery. Include functional, emotional, social, and economic value, then connect the promise to a specific segment and a measurable outcome.',
    'ethic': 'Use a stakeholder lens and examine both intended and unintended consequences. Ethical entrepreneurship includes truthful claims, fair treatment, consent, privacy, safety, responsible sourcing, and a documented response when commercial pressure conflicts with a basic duty.',
    'finance': 'Translate the idea into money timing and operating choices. Separate revenue, profit, cash, fixed costs, variable costs, working capital, and funding obligations. Label every estimate as observed, quoted, assumed, or targeted so that a spreadsheet does not create false certainty.',
    'leadership': 'Treat leadership as coordinated action under uncertainty. Clarify purpose, roles, decision rights, communication habits, feedback, delegation, conflict handling, and the culture demonstrated by what the founder rewards or tolerates.',
    'ecosystem': 'Place the venture inside its real context: customers, suppliers, finance, government, universities, mentors, infrastructure, culture, and informal networks. Compare countries for transferable mechanisms, not surface-level slogans, and identify what requires local adaptation.',
    'portfolio': 'Teach the portfolio as an evidence-backed argument. Every major claim should point to an observation, interview, calculation, source, or explicitly labeled assumption. The deliverable is a disciplined starting point for further validation, not a guarantee of success.',
}

SPECIFIC_LESSON_DETAILS = {
    'what entrepreneurship means': '''Entrepreneurship is broader than opening a business. It is the process of recognizing or creating an opportunity, organizing resources, creating something valuable, and acting despite uncertainty. A person who opens another ordinary shop has created a business. A person who notices that customers cannot reliably receive goods at home and designs a better delivery arrangement is also creating a business, but is demonstrating entrepreneurial opportunity recognition and value innovation.

There is no single definition because scholars emphasize different dimensions. Richard Cantillon presents the entrepreneur as a risk-bearer: the entrepreneur often pays known costs now while facing an uncertain future selling price. Jean-Baptiste Say emphasizes coordination: the entrepreneur moves money, people, materials, knowledge, technology, and customers toward a more productive use. Joseph Schumpeter emphasizes innovation: the entrepreneur introduces a new product, production method, market, source of supply, or organizational method. Israel Kirzner emphasizes alertness: the entrepreneur notices an unmet need, price difference, underserved group, or repeated problem that others have overlooked. These perspectives complement one another rather than compete; a venture can involve risk-bearing, resource coordination, innovation, and opportunity alertness at the same time.

For this course, use the Hisrich, Peters, and Shepherd perspective: entrepreneurship involves creating something new and valuable, investing time and effort, accepting financial, psychological, and social risks, and pursuing possible rewards such as income, independence, achievement, learning, and social contribution. This is a process of action, not a personality label. Education, work experience, role models, networks, and practice can increase a person\'s ability to recognize and assess opportunities, but no fixed checklist determines who can become an entrepreneur.

Keep three ideas separate. A business is an organization that repeatedly exchanges goods or services for value, and it does not have to be innovative. Entrepreneurship is the activity and mindset of identifying opportunities, creating value, and taking responsible action. A startup is a temporary organization searching for a repeatable and scalable model under uncertainty. All startups are businesses, but not all businesses are startups; entrepreneurship can create either, and it can also happen inside a company, government office, nonprofit, cooperative, or community project.

Consider a university student in Addis Ababa who sees classmates missing meals because they have short breaks and limited cash. The entrepreneurial process begins by observing the problem, speaking with students, and examining current alternatives. The student may then test a low-cost pre-order arrangement with one campus food provider, measure repeat orders and delivery reliability, and improve the service. The opportunity is not proven because the founder feels enthusiastic; it becomes more credible through evidence of a real problem, a reachable customer, a workable delivery method, and willingness to exchange money or another valued resource. The learner should therefore ask: What changed? Who benefits? What resources must be coordinated? What could go wrong? What small action would create useful evidence next?''',
    'types and purposes of entrepreneurship': '''A useful classification includes more than six types. Small-business entrepreneurship serves a local or defined market, such as a bakery, repair shop, salon, cafe, farm service, or neighborhood retailer. Scalable startup entrepreneurship searches for a repeatable model that can grow across cities or countries. Lifestyle entrepreneurship is designed around independence, craft, flexibility, and a sustainable owner income rather than maximum scale. Social entrepreneurship places a social or environmental mission at the center while using revenue and disciplined operations to sustain the work. Sustainable or green entrepreneurship creates economic value while protecting natural systems and communities.

Necessity entrepreneurship begins because paid employment or secure income is unavailable; opportunity entrepreneurship begins when a person chooses to pursue a perceived gap or possibility. The same person may move from necessity to opportunity as skills, savings, customers, and confidence grow. Innovative entrepreneurship introduces a new product, process, market, or business model. Imitative entrepreneurship adapts an existing model to a new location, segment, price point, language, or delivery method; imitation must respect intellectual-property rights and should still provide local value.

Corporate entrepreneurship, also called intrapreneurship, occurs inside an established organization through new ventures, new products, self-renewal, or proactive experimentation. Serial entrepreneurship involves creating or leading multiple ventures over time. Portfolio entrepreneurship means operating several related or unrelated ventures at once. Family entrepreneurship uses family ownership, labor, trust, and succession arrangements, but it still needs clear governance. Women\'s entrepreneurship and youth entrepreneurship describe the founder\'s social and demographic context and draw attention to barriers such as finance, collateral, care responsibilities, experience, safety, and credibility; they are not measures of capability.

Other classifications describe the sector or method: technology entrepreneurship uses technical knowledge as a core resource; rural entrepreneurship builds around agricultural, natural, or dispersed-market opportunities; manufacturing entrepreneurship transforms inputs into products; trading entrepreneurship buys and resells goods; service entrepreneurship sells expertise, access, care, or an experience; and digital entrepreneurship uses online channels or software. A venture can belong to several types at the same time: an Ethiopian agritech may be technology-enabled, social, rural, opportunity-driven, and scalable. Classify a venture by its purpose, customer, growth ambition, ownership, innovation, sector, and context rather than treating the list as a ranking.''',
}

def expand_explanation(module_title, title, explanation):
    lesson_text = title.lower()
    module_text = module_title.lower()
    detail = SPECIFIC_LESSON_DETAILS.get(lesson_text)
    if detail is None:
        detail = next((text for keyword, text in LESSON_DETAIL.items() if keyword in lesson_text), None)
    if detail is None:
        detail = next((text for keyword, text in LESSON_DETAIL.items() if keyword in module_text), LESSON_DETAIL['entrepreneurship'])
    return f'{explanation} {detail} Apply the idea to an Ethiopian setting: name the customer or stakeholder, describe the local constraint, and explain what would need to be learned before committing significant money or reputation. Distinguish evidence from assumption, identify the decision this lesson supports, and explain one likely beginner mistake. Then connect the concept to a small, observable action that a learner can complete in a real market, school, neighborhood, cooperative, or workplace.'

TEXTBOOK_LENSES = {
    1: 'Hisrich, Peters and Shepherd: entrepreneurship as a process of opportunity recognition, planning, resourcing, and managing a new venture. Desai: entrepreneurship development is shaped by education, institutions, and the wider economy.',
    2: 'Kaulgud: McClelland\'s need-for-achievement theory helps explain preference for meaningful challenge, feedback, and personal responsibility. Hisrich, Peters and Shepherd: confidence and risk propensity are learned and contextual, not fixed founder traits.',
    3: 'Hisrich, Peters and Shepherd: creativity and innovation are practical inputs to the entrepreneurial process. Desai: small and rural enterprises can innovate by adapting technology and resources to local conditions.',
    4: 'Hisrich, Peters and Shepherd: opportunity identification and evaluation require deliberate screening. Jain: project identification begins with systematic observation of industries, local resources, policy priorities, and unmet demand.',
    5: 'Jain: a feasibility study tests market, technical, and financial conditions before major commitment. Thomas and Norman: small-business opportunity decisions should remain grounded in customer needs and practical delivery constraints.',
    6: 'Dollinger: the resource-based view asks which resources and relationships are valuable, rare, difficult to imitate, and difficult to replace. Hisrich, Peters and Shepherd: entrepreneurial judgment operates with incomplete information and perceived risk.',
    7: 'Hisrich, Peters and Shepherd: business-plan thinking connects marketing, operations, organization, and finance. Dollinger: resources and partnerships can become competitive advantages when they are difficult for competitors to copy.',
    8: 'Hisrich, Peters and Shepherd: ethical decisions affect venture legitimacy and long-term survival. Kaulgud: women\'s entrepreneurship requires attention to structural barriers, networks, finance, and social context rather than only individual motivation.',
    9: 'Jain and Desai: institutional finance, development support, and government schemes must be matched to the entrepreneur\'s stage and eligibility. Thomas and Norman: disciplined small-business records support decisions about costs, cash, and funding.',
    10: 'Thomas and Norman: small ventures need practical hiring, motivation, communication, and people-management systems. Hisrich, Peters and Shepherd: growth changes the founder\'s role from hands-on operator to leader and manager.',
    11: 'Desai: entrepreneurship development depends on policy, institutions, rural and small-scale enterprise, and support systems. Kaulgud: Entrepreneurial Development Programs can build capability and connect founders to mentors, finance, and markets.',
    12: 'Hisrich, Peters and Shepherd: the portfolio is an early business-plan structure. Jain\'s Detailed Project Report offers a professional parallel for presenting technical, market, organizational, and financial reasoning. Dollinger: identify resources that create advantage and risks that make the model vulnerable.',
}


MODULES = [('Module 1: Entrepreneurship Foundations',
  [('What Is Entrepreneurship, Really?', 'Define entrepreneurship as a process of creating value under uncertainty. Compare the risk, resource-coordination, innovation, and opportunity-alertness perspectives. Distinguish entrepreneur, business, entrepreneurship, and startup.', 'Interview one local business owner. Ask what problem they started with, what resources they used first, what uncertainty they faced, and what changed after customers responded.', 'Begin with the question: “Is every business owner an entrepreneur?” Use a local delivery example, introduce four scholar perspectives, compare business and startup, and finish with the knowledge check and learner challenge.', 'OpenLearn Entrepreneurship'),
   ('Types and Purposes of Entrepreneurship',
    "Entrepreneurship has several overlapping classifications. Compare small-business, scalable, lifestyle, social, sustainable, necessity, opportunity, innovative, imitative, corporate, serial, portfolio, family, women's, youth, technology, rural, manufacturing, trading, service, and digital entrepreneurship. These labels describe purpose, growth ambition, ownership, method, sector, or context, not status or capability. A social enterprise still needs revenue; a small enterprise can innovate; and a necessity entrepreneur may later become opportunity-driven. The same Ethiopian venture can belong to several categories at once.",
    'Classify six Ethiopian ventures across at least four dimensions: purpose, growth ambition, ownership, innovation, sector, and founder context. For each classification, explain what it helps you understand and what it does not tell you. Finish by choosing the most useful category for planning that venture.',
    'Present the categories in families rather than a flat list: purpose and motivation; growth and ownership; innovation and strategy; sector and context. Use one Ethiopian example that changes category depending on the question being asked.',
    'OpenLearn Entrepreneurship'),
   ('Entrepreneurship in Ethiopia and Africa', 'An ecosystem combines markets, skills, finance, infrastructure, policy, culture, and networks. Ethiopia has a young population, strong informal enterprise, and changing sectors, while power, connectivity, finance, and formalization can constrain growth. Avoid romanticizing either hardship or technology: opportunity depends on evidence, inclusion, and the ability to deliver reliably. Introduce the course arc from noticing a problem to presenting an opportunity portfolio.', 'Write a 200-word reflection on an overlooked problem in your town and why solving it could create both economic and social value.', 'Present strengths and constraints with a balanced scorecard, then preview the five-module journey and the final portfolio.', 'UN Sustainable Development Goals')]),
 ('Module 2: Mindset and Entrepreneurial Readiness',
  [('Growth mindset and initiative', 'An entrepreneurial mindset is a way of thinking that helps individuals recognize opportunities, solve problems, take action, learn from experience, and create value despite uncertainty. Entrepreneurs do not always have perfect information. They often begin with: A problem + an idea + limited resources + uncertainty. What matters is how they respond. An entrepreneurial mindset encourages a person to ask: What problem can I solve? What opportunity exists? How can I test my idea? What can I learn from failure? What should I change? What action can I take now? A growth mindset is the belief that abilities, knowledge, and skills can be developed through learning, practice, effort, feedback, and experience. A person with a growth mindset does not think: “I am not good at this, so I can never do it.” Instead, they think: “I am not good at this yet, but I can improve.” The word “yet” is important. Fixed mindset: “I cannot do it.” Growth mindset: “I cannot do it yet.” The second statement creates the possibility of learning and improvement. Fixed mindset means “My abilities are limited.” Growth mindset means “I can develop my abilities.” A fixed mindset avoids difficult tasks, gives up easily, sees failure as proof of inability, avoids criticism, and wants to appear capable. A growth mindset accepts challenges, persists when difficulties arise, sees failure as feedback, uses constructive feedback, wants to become more capable, and learns from mistakes. Entrepreneurship involves continuous learning. An entrepreneur may initially lack financial knowledge, marketing skills, technical skills, leadership experience, and industry knowledge. A growth mindset allows the entrepreneur to treat these limitations as areas for development rather than permanent barriers. Example: A student wants to create an online business but does not know how to build a website. A fixed mindset says, “I do not know programming. I cannot start an online business.” A growth mindset says, “I do not know programming yet. I can learn the basics, use available tools, or work with someone who has the required skills.” The second approach opens the door to action. A growth mindset should not be confused with unrealistic optimism. It does not mean, “If I work hard enough, I will automatically succeed.” Instead, it means, “My current abilities do not have to determine my future abilities.” Entrepreneurs still need evidence, practice, resources, good decisions, feedback, strategy, and adaptation. Effort matters, but effective effort and learning matter more than effort alone. Initiative means taking purposeful action without waiting for someone else to tell you what to do. An entrepreneurial person does not simply notice problems. They ask, “What can I do about it?” Example: Two students notice that classmates struggle to find affordable study materials. Student A complains about the problem. Student B surveys classmates, identifies what materials they need, creates organized digital notes, and tests whether students find them useful. Student B is demonstrating initiative. Entrepreneurial initiative can be understood through a simple contrast: Waiting: Problem → Wait for someone else → No action. Initiative: Problem → Investigate → Take appropriate action → Learn → Improve. Initiative does not mean acting recklessly. It means taking responsible action instead of remaining passive. You can develop initiative by noticing problems, asking questions, starting small, testing assumptions, taking ownership, and learning from results. A college canteen has long queues during lunch. Students complain about the waiting time. An entrepreneurial response is pre-ordering, digital confirmation, and faster collection. The student observes the problem and proposes this response. The student conducts a small survey, creates a basic prototype, and tests it with a limited number of students. The idea may succeed, fail, or require modification. But the student has demonstrated: Observation + Initiative + Experimentation + Learning. A growth mindset views abilities as developable. Entrepreneurs constantly need to learn and adapt. Failure can provide useful information when analyzed properly. Initiative means taking purposeful action rather than waiting passively. Initiative should be informed by observation and learning, not reckless action. Entrepreneurial mindset turns “I cannot” into “How can I learn or solve this?” Growth Mindset + Initiative = Learn, Act, Improve.', 'Keep a three-day learning log. Record one action, the evidence it produced, and the next skill or tactic you will try.', 'Show two founders receiving the same rejection. Pause on their self-talk, then convert fixed statements into specific learning questions.', 'OpenLearn Entrepreneurship'),
   ('Resilience, persistence, and adaptability', 'Resilience is recovering and functioning after setbacks. Persistence protects a meaningful goal; stubbornness protects a particular plan. Strong founders stay committed to the customer outcome while adapting the route, offer, channel, or timing. Build resilience with small experiments, peer support, recovery routines, and honest post-mortems rather than treating exhaustion as proof of commitment.', 'Describe a setback using What happened? Why? What will I change? Include one part of the plan you will keep and one you will alter.', 'Use a failed market test as a case. Model a short post-mortem and distinguish a useful pivot from abandoning a goal too early.', 'OpenLearn Entrepreneurship'),
   ('Calculated risk and uncertainty tolerance', 'Risk has known possible outcomes and estimated probabilities; uncertainty includes outcomes you cannot reliably enumerate. Early ventures face uncertainty, so the goal is not certainty but learning at an affordable loss. Reduce downside with small pilots, staged commitments, safety checks, and explicit stop rules. Confidence should mean “I can learn and respond,” not “my first idea must be right.”', 'Choose one risky assumption and design a test that uses no more than one week and an amount of money you can genuinely afford to lose.', 'Contrast a dice game with launching an untested service. Explain affordable loss, experiment size, and why risk management beats risk-seeking.', 'OpenLearn Entrepreneurship')]),
 ('Module 3: Creativity and Innovation',
  [('Creativity, innovation, and problem framing', 'Creativity generates possibilities; innovation implements a useful possibility that creates value. Start with a problem frame, not a favorite technology. Reframe “How do we sell more fertilizer?” as “How might farmers improve yield and income?” to reveal services, storage, finance, and information solutions. First-principles thinking separates facts from inherited assumptions before rebuilding an approach.', 'Write three versions of one local problem: a symptom, a root-cause frame, and a human-centered “How might we” question.', 'Demonstrate a solution-first idea, then rewind to evidence and reframe it. Show the formula: creativity plus implementation plus value equals innovation.', 'IDEO Design Thinking'),
   ('Design thinking and user empathy', 'Design thinking integrates people’s needs, technology possibilities, and organizational viability. Empathize through interviews and observation; define a specific need; ideate broadly; prototype cheaply; test and iterate. An empathy map records what a person says, thinks, does, and feels, but every observation should be labeled as evidence or interpretation. Include language, disability, income, gender, and connectivity in the research frame.', 'Observe or interview three potential users. Create an evidence-labeled empathy map and a problem statement that does not prescribe a technology.', 'Walk through Empathize, Define, Ideate, Prototype, and Test using post-harvest loss. Emphasize that the loop is iterative, not a one-way checklist.', 'IDEO Design Thinking Process'),
   ('SCAMPER, frugal, and disruptive innovation', 'SCAMPER expands an existing idea by substituting, combining, adapting, modifying, putting it to another use, eliminating, or rearranging. Frugal innovation designs for constraints such as unreliable electricity or limited capital; constraint can become an advantage when the result is affordable and rugged. Disruptive innovation often begins with an underserved segment and a simpler offer, then improves over time. Do not call every new feature disruptive.', 'Apply SCAMPER to a jerry can, minibus route, or school service. Generate twenty options, then shortlist three using desirability, feasibility, and viability.', 'Live-apply SCAMPER to a familiar Ethiopian service, then compare an incremental improvement with a genuinely new market entry.', 'IDEO Design Thinking')]),
 ('Module 4: Opportunity Recognition and Decision Making',
    [('Where Opportunities Come From', 'Define an entrepreneurial opportunity; explain where opportunities come from; distinguish opportunities from ideas; identify changes that can create opportunities; recognize unmet needs and market gaps; and develop an opportunity-recognition mindset.', 'Start an opportunity journal with ten dated observations. For each, record the affected person, current workaround, and possible evidence source.', 'Use a checklist to scan a market, school, farm, workplace, or neighborhood across changes in behavior, technology, society, economics, inefficiency, frustration, and market gaps.', 'SBA Market Research'),
     ('Customer Observation and Market Evidence', 'Explain why customer observation matters, distinguish assumptions from evidence, identify primary and secondary market evidence, conduct basic interviews and observations, recognize customer behavior and pain points, and avoid confirmation bias when collecting information.', 'Conduct five problem interviews. Quote the behavior or workaround, not just the person’s opinion, and note what evidence would change your mind.', 'Role-play weak and strong interview questions. Show how leading questions produce compliments while event-based questions produce evidence.', 'SBA Market Research'),
     ('Ranking Opportunities with Evidence', 'Explain why entrepreneurs compare opportunities; identify customer need, market potential, economic potential, feasibility, competitive position, evidence strength, and timing as evaluation criteria; and use a simple weighted ranking matrix without treating a score as the truth.', 'Rank three opportunities from your opportunity journal from one to five for customer need, evidence, feasibility, market potential, and competitive advantage. State what evidence could change the ranking.', 'Score two sample problems live. Explain why a large market can still be unattractive if the customer is unreachable or the economics are poor.', 'SBA Market Research'),
     ('Problem, Need, Opportunity, Solution, and Value', 'Distinguish problem, need, opportunity, solution, and value. Follow the chain Problem -> Need -> Opportunity -> Solution -> Value without jumping from a problem to a predetermined product. Construct a clear entrepreneurial value proposition.', 'Take your highest-ranked problem and write all five links. Highlight every statement that is still an assumption.', 'Draw the chain on a whiteboard and carry one agriculture or transport example through it, showing where new evidence changes the wording.', 'IDEO Design Thinking'),
     ('Jobs to Be Done and Customer Pains', 'Explain Jobs to Be Done and identify functional, emotional, and social jobs, customer pains, desired gains, and the reasons customers hire products and services to make progress in a situation.', 'Write two job stories for one target customer using “When [situation], I want to [motivation], so I can [outcome].” List the current alternatives and the reason each has not already been replaced.', 'Turn product features into job stories. Demonstrate why “an app for farmers” is weaker than a concrete situation, motivation, and outcome.', 'OpenLearn Entrepreneurship'),
     ('Desirability, Feasibility, and Viability', 'Define desirability, feasibility, and viability; explain why all three dimensions matter; evaluate an opportunity through the three lenses; and identify weaknesses before making a major commitment.', 'Score your opportunity from one to five on all three dimensions. Write one experiment for the weakest score and one person who can challenge your reasoning.', 'Use three intentionally flawed examples: desirable but impossible, feasible but unwanted, and wanted but financially unsustainable.', 'SBA Market Research'),
     ('Deciding under Risk and Uncertainty', 'Distinguish risk from uncertainty, evaluate possible outcomes and consequences, use expected-value thinking carefully, make decisions without complete information, and use small experiments to reduce the cost of being wrong.', 'Create a one-page decision brief for your next venture step. Include a stop rule and the evidence that would make you continue, change, or stop.', 'Compare an established inventory decision with a new-product decision. Model how the evidence required changes when outcomes are unknown.', 'OpenLearn Entrepreneurship'),
     ('Effectuation - Starting with What You Have', 'Explain effectuation; distinguish effectual thinking from prediction-based planning; identify available means; understand affordable loss, partnerships, the lemonade principle, and the pilot-in-the-plane principle; and apply them to resource-constrained entrepreneurship.', 'List who you are, what you know, whom you know, your available resources, and what you can afford to lose. Design the smallest useful action possible with those means.', 'Tell one founder story five times, each time highlighting a different effectuation principle and the choice it enabled.', 'OpenLearn Entrepreneurship'),
     ('Biases, Opportunity Cost, and Experiments', 'Explain confirmation bias, overconfidence bias, escalation of commitment, availability bias, and opportunity cost. Use experiments with a question, hypothesis, test, metric, and decision rule to challenge assumptions and reduce uncertainty.', 'Choose one opportunity and state its main assumption, current evidence, biggest uncertainty, best alternative, opportunity cost, smallest useful experiment, and continue/change/stop rules.', 'Run a bias audit on a fictional founder. End by turning one vague plan into a measurable experiment.', 'OpenLearn Entrepreneurship')]),
 ('Module 5: Business Models, Ethics, Finance and Leadership',
    [('Create, Deliver, and Capture Value', 'Define value creation, value delivery, and value capture; explain how they connect; distinguish customer value from business value; and understand the basic logic of a sustainable business model.', 'Describe a familiar Ethiopian business in three sentences: value created, delivery system, and value captured.', 'Use a minibus route, food service, or tutoring business to show Create Value -> Deliver Value -> Capture Value.', 'Strategyzer Business Model Canvas'),
     ('Customers, Channels, Revenue, and Costs', 'Identify customer segments and channels, explain direct sales, subscriptions, commissions, licensing, advertising, and freemium revenue models, and distinguish fixed costs from variable costs.', 'Sketch one page answering who pays, who uses, how the offer reaches them, how money arrives, and which costs grow with each customer.', 'Build a simple model for a tutoring service and trace one customer from discovery to payment.', 'Strategyzer Business Model Canvas'),
     ('Resources, Partners, and Social Value', 'Identify human, financial, physical, intellectual, and relationship resources; explain partnerships; compare building, buying, and partnering; and recognize economic and social value.', 'Map five resources and partners for your opportunity. Add one social outcome and how you will observe it responsibly.', 'Compare build, buy, and partner decisions for a small education or agriculture venture.', 'UN Sustainable Development Goals'),
     ('Ethics, Trust, and Stakeholders', 'Define business ethics, identify stakeholders, explain why trust matters, and recognize ethical responsibilities beyond simply following the law.', 'Map stakeholders for your venture. For each, record one benefit, one possible harm, and one promise the venture must keep.', 'Start with a cost-cutting decision and expand the stakeholder map until hidden effects become visible.', 'UN Sustainable Development Goals'),
     ('Social, Environmental, and Inclusive Entrepreneurship', 'Explain social, environmental, and inclusive entrepreneurship and recognize opportunities that create economic, social, and environmental value for underserved groups.', 'Choose one exclusion risk in your idea and redesign a feature, channel, price, or process to reduce it. State how you will measure the improvement.', 'Compare a conventional enterprise, a social enterprise, and a charity using an affordable solar-lighting example.', 'UN Sustainable Development Goals'),
     ('Ethical Dilemmas and Responsible Growth', 'Identify ethical dilemmas, understand competing stakeholder interests, apply a structured ethics test, and explain why responsible growth protects quality, people, finances, and trust.', 'Analyze a supplier dilemma. Compare short- and long-term effects, identify a minimum ethical standard, and write a decision with evidence and a review date.', 'Apply the five-question ethics test: Is it legal? Is it honest? Who could be harmed? Would I explain it publicly? Does it support long-term trust?', 'UN Sustainable Development Goals'),
     ('Separate Personal and Business Money', 'Explain why personal and business finances should be separated, understand basic financial records, recognize financial discipline, and avoid treating revenue as personal income.', 'Create a one-week cash record for your opportunity. Mark each item as personal, business, expected, or collected.', 'Use a food-stall example to show how mixing household and business cash creates a false feeling of profit.', 'SBA Startup Costs'),
     ('Revenue, Costs, Profit, Cash Flow, and Break-Even', 'Define revenue and costs, calculate basic profit, distinguish profit from cash flow, explain break-even, and use break-even analysis in entrepreneurial decisions.', 'Estimate price, variable cost, and monthly fixed costs for your opportunity. Calculate break-even units and assess whether demand could reach it.', 'Work the example: fixed costs ₹100,000, price ₹500, variable cost ₹300, break-even 500 units.', 'SBA Startup Costs'),
     ('Bootstrapping, Debt, Equity, and Grants', 'Explain common sources of entrepreneurial finance, compare bootstrapping, debt, equity, and grants, understand financing trade-offs, and match capital to business stage, risk, cash flow, and growth strategy.', 'Create a funding comparison with amount needed, milestone enabled, repayment or ownership cost, eligibility, and worst-case consequence.', 'Compare which risk is transferred to the founder, lender, investor, or grant maker by each financing source.', 'SBA Startup Costs'),
     ('Vision, Mission, and Self-Leadership', 'Distinguish vision from mission, explain purpose, understand self-leadership, and connect personal discipline with entrepreneurial performance.', 'Write one vision and one mission sentence. Test each against three decisions your venture may face and revise vague words.', 'Turn a vague statement such as “empower everyone” into a concrete mission linked to a customer and outcome.', 'OpenLearn Entrepreneurship'),
     ('Communication, Influence, Delegation, and Teams', 'Explain effective communication and ethical influence, understand delegation, and identify the characteristics of effective teams.', 'List the next six months of work. Assign one accountable owner to each item and identify the capability gap to develop or contract.', 'Act out poor and good delegation, then build a responsibility map for an education or agriculture venture.', 'OpenLearn Entrepreneurship'),
     ('Conflict, Emotional Intelligence, and Culture', 'Explain constructive and destructive conflict, understand emotional intelligence, manage disagreements professionally, and recognize how leaders create organizational culture through behavior.', 'Describe a disagreement and rewrite your response using interests, evidence, options, and a follow-up commitment.', 'Use a co-founder pricing disagreement to model listening, reframing, a decision deadline, and a written decision log.', 'OpenLearn Entrepreneurship')]),
 ('Module 6: Entrepreneurial Ecosystems and the Opportunity Portfolio',
    [('How Entrepreneurial Ecosystems Work', 'Define an entrepreneurial ecosystem; identify its major actors; explain how actors interact; understand why networks matter; and identify ecosystem resources available to entrepreneurs.', 'Create an ecosystem map for one opportunity. Identify the customer, supplier, financial partner, government or institution, university, technology partner, mentor, and strategic partner.', 'Map an Ethiopian agricultural marketplace from farmers and buyers through transport, mobile payments, banks, government, universities, investors, and technology partners.', 'OpenLearn Entrepreneurship'),
     ('Comparing Ethiopia, Africa, and Global Entrepreneurial Ecosystems', 'Compare ecosystems across market, finance, talent, infrastructure, technology, regulation, networks, research, culture, and international access. Recognize Ethiopian strengths and constraints, avoid treating Africa as homogeneous, and understand why the best ecosystem depends on the venture.', 'Compare two ecosystems using market, finance, talent, infrastructure, and networks. Explain which is more suitable for your opportunity and why.', 'Use a comparison table without pretending scores are objective. Explain what can be adapted locally and what depends on context.', 'OpenLearn Entrepreneurship'),
     ('Informal, Women, Youth, and Diaspora Entrepreneurship', 'Explain informal entrepreneurship; understand the contributions and barriers affecting women and youth entrepreneurs; explain diaspora entrepreneurship; and understand why inclusive ecosystems broaden meaningful participation.', 'Identify one informal business, one youth opportunity, one women-led opportunity, and one possible diaspora connection. Name ecosystem support that could help them grow.', 'Discuss formalization as both opportunity and constraint, then build a support map around capital, knowledge, networks, markets, technology, and safety.', 'UN Sustainable Development Goals'),
     ('Portfolio Structure and Evidence', 'Explain an entrepreneurial opportunity portfolio; organize multiple opportunities; compare them using evidence; distinguish attractive from well-supported opportunities; and select an opportunity for deeper development.', 'Create a portfolio of three to five opportunities. Score customer need, evidence strength, feasibility, viability, and strategic fit from 1 to 5.', 'Build a portfolio matrix comparing evidence strength with opportunity potential and label priority, research, alternatives, and low-priority opportunities.', 'Strategyzer Business Model Canvas'),
     ('Presenting an Opportunity Professionally', 'Present an opportunity clearly; structure a professional pitch; use evidence; explain value and business logic; and respond to questions honestly and professionally.', 'Prepare a 3-5 minute opportunity presentation covering the problem, customer, evidence, opportunity, solution, value, business model, risks, and next experiment.', 'Rehearse the 60-second statement: customer, problem, evidence, solution, value, difference, and next action.', 'Strategyzer Business Model Canvas'),
     ('Reflection and the Next 30, 60, and 90 Days', 'Reflect on entrepreneurial learning; identify strengths and development areas; convert learning into action; create a measurable 30-60-90 day plan; and establish next steps.', 'Write a 30-60-90 day plan with objectives, actions, evidence or measures, a review date, and a continue, pivot, pause, or stop decision.', 'Use the loop Act -> Measure -> Learn -> Adapt -> Act Again and connect the course portfolio to the next experiment.', 'OpenLearn Entrepreneurship')])]



MODULE_4_NOTES = {
    'Where Opportunities Come From': '''<h1>Where Opportunities Come From</h1><h2>Learning Objectives</h2><ul><li>Define an entrepreneurial opportunity.</li><li>Explain where opportunities come from and distinguish opportunities from ideas.</li><li>Identify changes, unmet needs, and market gaps that can create opportunities.</li><li>Develop an opportunity-recognition mindset.</li></ul><h2>What Is an Entrepreneurial Opportunity?</h2><p>An <strong>entrepreneurial opportunity</strong> is a situation in which an entrepreneur can potentially create value by addressing a problem, unmet need, inefficiency, emerging demand, or change in the environment. An opportunity is more than an idea.</p><p><strong>Idea:</strong> “I should create an app for farmers.”</p><p><strong>Opportunity:</strong> Small farmers in a particular market struggle to access reliable buyers, existing alternatives are inadequate, and there may be a sustainable way to connect farmers with customers. This statement contains evidence of a problem, users, and potential value creation.</p><h2>Ideas vs. Opportunities</h2><table><thead><tr><th>Idea</th><th>Opportunity</th></tr></thead><tbody><tr><td>A possibility</td><td>A potentially valuable possibility</td></tr><tr><td>May be based on intuition</td><td>Can be investigated with evidence</td></tr><tr><td>May have no clear customer</td><td>Has identifiable users or beneficiaries</td></tr><tr><td>May solve no important problem</td><td>Addresses a meaningful need or problem</td></tr></tbody></table><aside class="learning-callout"><strong>Key principle</strong><p>Every opportunity begins as an idea, but not every idea is an opportunity.</p></aside><h2>Where Opportunities Come From</h2><ul><li><strong>Changes in customer behavior:</strong> online shopping, convenience, new food preferences, personalized services, and new approaches to education.</li><li><strong>Technological change:</strong> artificial intelligence, mobile technology, digital payments, cloud computing, automation, and e-commerce. Technology creates an opportunity only when it solves a real problem.</li><li><strong>Social and demographic change:</strong> urbanization, changing family structures, education, and work patterns create new needs.</li><li><strong>Economic change:</strong> changes in income, prices, employment, trade, and spending can reveal new segments and lower-cost alternatives.</li><li><strong>Inefficiencies:</strong> long waits, high costs, waste, poor communication, unnecessary steps, and unreliable services.</li><li><strong>Customer frustrations:</strong> repeated complaints such as “This takes too long” or “There must be an easier way.”</li><li><strong>Gaps in existing markets:</strong> overlooked segments, expensive products, inconvenient alternatives, or markets too small for large companies.</li></ul><h2>The Opportunity-Recognition Mindset</h2><p>Two people may notice that a bus is always late. An entrepreneur asks why it happens, who is affected, what causes it, what alternatives exist, and whether a better solution could create value. The difference is attention, curiosity, and questioning.</p><p><strong>Change + Problem/Need + Potential Value = Opportunity Candidate</strong></p><p>The word candidate matters: the opportunity still needs investigation and testing. Look at colleges, workplaces, neighborhoods, transportation, shops, hospitals, agriculture, education, banking, and household activities. Ask what repeatedly causes unnecessary time, cost, effort, frustration, or risk.</p><h2>Activity</h2><p>Start an opportunity journal with ten dated observations. Record the affected person, current workaround, possible evidence source, and the change that may be creating the opportunity.</p><h2>Key Takeaways</h2><ul><li>Opportunities emerge from change, problems, unmet needs, inefficiencies, technology, and market gaps.</li><li>Entrepreneurs observe patterns rather than isolated incidents.</li><li>Opportunity recognition begins with observation and questioning.</li></ul>''',
    'Customer Observation and Market Evidence': '''<h1>Customer Observation and Market Evidence</h1><h2>Learning Objectives</h2><ul><li>Explain why customer observation matters.</li><li>Distinguish assumptions from evidence and identify useful market evidence.</li><li>Conduct basic customer interviews and observations.</li><li>Recognize customer behavior, pain points, and workarounds.</li><li>Avoid confirmation bias when collecting information.</li></ul><h2>From Assumptions to Evidence</h2><p>“Students will pay for this service” is an assumption, not evidence. A stronger process is <strong>Idea -> Assumption -> Evidence -> Experiment -> Decision</strong>. Ask what evidence would convince you that the assumption is true and what evidence could disprove it.</p><h2>Customer Observation</h2><p>Observation studies what people <strong>actually do</strong>, not only what they say. Customers may request faster service while their own uncertainty about ordering creates the delay. Observe behavior, time, money, frustration, workarounds, and unmet needs.</p><h2>Customer Interviews</h2><p>A good interview seeks to understand experience, not sell an idea. Avoid “Would you buy my app?” Ask:</p><ul><li>Tell me about the last time you experienced this problem.</li><li>How do you currently solve it?</li><li>What is most frustrating about the current approach?</li><li>How often does this happen?</li><li>What does the problem cost you?</li></ul><h2>Market Evidence</h2><p><strong>Primary evidence</strong> includes interviews, observations, surveys, experiments, prototype tests, and transactions. <strong>Secondary evidence</strong> includes industry reports, government statistics, academic research, competitor information, public market data, and existing studies. Strong evaluation combines both.</p><h2>The Evidence Ladder</h2><p><strong>Opinion -> Claim -> Observation -> Customer evidence -> Behavioral evidence -> Transaction or commitment evidence.</strong> Customers paying, switching, returning, pre-ordering, or committing time usually provide more decision-relevant evidence than compliments.</p><h2>Avoid Confirmation Bias</h2><p>If you believe students want an expensive study app, do not ask only whether they like the idea. Ask how they currently study, what problems they experience, and what resources they pay for. Evidence reduces uncertainty but never creates perfect certainty. The question is whether there is enough evidence to justify the next step.</p><h2>Mini Experiment</h2><p>For a student meal-delivery service, interview students, observe ordering, test a simple process, measure actual orders, collect feedback, and decide whether to continue, change, or stop.</p><h2>Activity and Key Takeaways</h2><p>Conduct five problem interviews. Quote behavior or workarounds, not only opinions, and note the evidence that would change your mind. Assumptions are not evidence; actual behavior and commitment are stronger signals.</p>''',
    'Ranking Opportunities with Evidence': '''<h1>Ranking Opportunities with Evidence</h1><h2>Learning Objectives</h2><ul><li>Explain why entrepreneurs compare opportunities.</li><li>Identify criteria for evaluating and ranking opportunities.</li><li>Distinguish evidence from opinion.</li><li>Build a simple opportunity-ranking matrix.</li><li>Prioritize opportunities for further testing.</li></ul><h2>Why Rank Opportunities?</h2><p>Time, money, attention, skills, and relationships are limited. Entrepreneurs therefore ask which opportunity deserves attention first rather than trying to pursue everything at once.</p><h2>Evaluation Criteria</h2><ul><li><strong>Customer need:</strong> How important is the problem?</li><li><strong>Market potential:</strong> How many potential customers could exist?</li><li><strong>Economic potential:</strong> Can revenue support the venture?</li><li><strong>Feasibility:</strong> Can the solution realistically be delivered?</li><li><strong>Competitive position:</strong> Can the venture create a meaningful advantage?</li><li><strong>Evidence strength:</strong> How strong is the evidence that the problem exists?</li><li><strong>Timing:</strong> Why is the opportunity relevant now?</li></ul><h2>Weighted Scoring</h2><p>Assign a weight to each criterion and score each opportunity from 1 to 5. A simple model is <strong>Weighted Score = Sum of (Weight x Score)</strong>. For example, customer need may receive 30%, evidence 25%, feasibility 20%, market potential 15%, and competitive advantage 10%.</p><aside class="learning-callout"><strong>The score is not the truth</strong><p>A scoring model is only as good as its assumptions. A high score with weak evidence is a research priority, not an automatic winner.</p></aside><h2>Ranking Example</h2><p>Compare online tutoring, campus food delivery, and a used textbook marketplace. Tutoring may have strong demand but many competitors; food delivery may have strong demand and clear pain; textbooks may have moderate demand but low operating complexity. A matrix makes the reasoning visible.</p><h2>Priority Model</h2><p><strong>Importance x Evidence x Feasibility</strong> helps decide what to test. A huge market with little evidence may deserve research. Strong evidence with no feasible delivery model may need redesign. Moderate demand with excellent evidence and easy execution may be worth testing first.</p><h2>Activity</h2><p>Choose three opportunities. Score customer need, evidence, feasibility, market potential, and competitive advantage from 1 to 5. State what evidence would change your ranking.</p>''',
    'Problem, Need, Opportunity, Solution, and Value': '''<h1>Problem, Need, Opportunity, Solution, and Value</h1><h2>Learning Objectives</h2><ul><li>Distinguish problem, need, opportunity, solution, and value.</li><li>Understand how the concepts connect.</li><li>Avoid jumping from a problem to a predetermined solution.</li><li>Construct a clear entrepreneurial value proposition.</li></ul><h2>The Five Concepts</h2><p><strong>Problem -> Need -> Opportunity -> Solution -> Value</strong></p><p>A <strong>problem</strong> is an undesirable situation or difficulty. A <strong>need</strong> is the underlying requirement. An <strong>opportunity</strong> is a potentially valuable and feasible way to address a meaningful need. A <strong>solution</strong> is the product, service, process, or business model designed to respond. <strong>Value</strong> is the meaningful benefit created for the customer or stakeholder.</p><p>For example, students may spend a long time waiting for lunch. Their need is convenient and timely food access. An opportunity may be faster, affordable meal access. Possible solutions include pre-ordering, subscriptions, pickup points, delivery, or digital ordering. Value may include less waiting, predictable pricing, greater choice, and a better experience.</p><h2>The Solution Trap</h2><p>Starting with “I have a great app idea” reverses the process. Start with the problem and need, then explore multiple solutions. In agriculture, produce spoilage is the problem; reliable preservation and market access are needs; cold storage, logistics, processing, and digital market connections are possible solutions. The value may be less waste and better farmer income.</p><h2>Activity</h2><p>Take your highest-ranked problem and write all five links. Highlight every statement that is still an assumption. Do not fall in love with a solution before understanding the problem.</p>''',
    'Jobs to Be Done and Customer Pains': '''<h1>Jobs to Be Done and Customer Pains</h1><h2>Learning Objectives</h2><ul><li>Explain the Jobs to Be Done perspective.</li><li>Identify functional, emotional, and social dimensions of a customer job.</li><li>Identify customer pains and desired gains.</li><li>Understand why customers “hire” products and services.</li><li>Apply Jobs to Be Done to entrepreneurial opportunities.</li></ul><h2>What Is Jobs to Be Done?</h2><p>Instead of asking only “Who is my customer?”, ask <strong>“What is the customer trying to get done?”</strong> Customers use products and services to accomplish something. A person buying a milkshake may be buying breakfast, convenience, enjoyment, a commute companion, or fullness until lunch.</p><h2>Three Dimensions of a Job</h2><ul><li><strong>Functional:</strong> the practical task, such as travelling from home to work.</li><li><strong>Emotional:</strong> how the customer wants to feel, such as relaxed and safe.</li><li><strong>Social:</strong> how the customer wants to be perceived, such as professional.</li></ul><h2>Pains and Gains</h2><p>Customer pains include cost, delay, risk, complexity, frustration, poor quality, uncertainty, effort, and stress. Desired gains include convenience, speed, savings, reliability, quality, confidence, recognition, and comfort.</p><aside class="learning-callout"><strong>JTBD statement</strong><p>When [situation], I want to [motivation], so I can [desired outcome].</p></aside><p>“When I am preparing for an exam, I want to quickly find reliable explanations so I can understand difficult topics without wasting time” is more useful than simply saying “my customer is an MBA student.” Demographics alone do not explain behavior.</p><h2>Activity</h2><p>Write two job stories for one customer. List current alternatives, the pains attached to each, the desired gain, and why the alternative has not already been replaced.</p>''',
    'Desirability, Feasibility, and Viability': '''<h1>Desirability, Feasibility, and Viability</h1><h2>Learning Objectives</h2><ul><li>Define desirability, feasibility, and viability.</li><li>Explain why all three dimensions matter.</li><li>Evaluate an opportunity using the three lenses.</li><li>Identify weaknesses in an opportunity.</li></ul><h2>The Three-Lens Test</h2><ul><li><strong>Desirability:</strong> Do people genuinely want it?</li><li><strong>Feasibility:</strong> Can we actually create and deliver it?</li><li><strong>Viability:</strong> Can it work economically and sustainably?</li></ul><p>Desirability evidence includes interviews, observed behavior, existing spending, prototype engagement, repeat usage, and willingness to pay. Feasibility considers technology, skills, resources, suppliers, infrastructure, operations, regulations, and time. Viability considers revenue, costs, pricing, margins, cash flow, customer acquisition, competition, and the business model.</p><h2>Three Examples</h2><p>A product customers love may be too expensive to produce: desirable, but not feasible or viable. A cheap working technology may solve a problem nobody cares about: feasible, but not desirable or viable. The strongest position is a solution people want, the team can deliver, and customers will support economically.</p><p>Also consider accessibility, safety, privacy, and cultural fit. “Customers like it” is not the same as “this is a viable business.”</p><h2>Activity</h2><p>Score your opportunity from 1 to 5 on each lens. Write one experiment for the weakest score and name one person who can challenge your reasoning.</p>''',
    'Deciding under Risk and Uncertainty': '''<h1>Deciding under Risk and Uncertainty</h1><h2>Learning Objectives</h2><ul><li>Distinguish risk from uncertainty.</li><li>Evaluate possible outcomes and consequences.</li><li>Understand expected-value thinking.</li><li>Make decisions without complete information.</li><li>Use experiments to improve uncertain decisions.</li></ul><h2>Risk vs. Uncertainty</h2><p><strong>Risk</strong> exists when possible outcomes are uncertain but can be estimated. <strong>Uncertainty</strong> exists when future outcomes are difficult to predict and reliable probabilities may not be available. New customers, products, competitors, technologies, regulations, and demand all create uncertainty.</p><h2>Decision Quality vs. Outcome</h2><p>A good decision can produce a bad outcome, and a poor decision can produce a good outcome by luck. Evaluate reasoning and evidence available at the time, not only the result.</p><h2>Expected-Value Thinking</h2><p><strong>Expected Value = Sum of (Probability x Outcome)</strong>. If an opportunity has a 60% chance of gaining ₹100,000 and a 40% chance of losing ₹40,000, the expected value is (0.60 x ₹100,000) + (0.40 x -₹40,000) = ₹44,000. This is an analysis tool, not a promise.</p><p>Cash constraints, timing, learning value, irreversibility, alternatives, and risk tolerance also matter. Make small bets before large commitments: test, learn, and then decide.</p><h2>Activity</h2><p>Create a decision brief with the choice, evidence, assumptions, biggest uncertainty, affordable loss, deadline, review trigger, and a continue/change/stop rule.</p>''',
    'Effectuation - Starting with What You Have': '''<h1>Effectuation - Starting with What You Have</h1><h2>Learning Objectives</h2><ul><li>Explain effectuation and distinguish it from prediction-based planning.</li><li>Identify available means and affordable loss.</li><li>Understand partnerships, flexibility, and action under uncertainty.</li></ul><h2>What Is Effectuation?</h2><p>Effectuation starts with available resources and relationships, takes manageable steps, and shapes opportunities through action and collaboration rather than relying entirely on prediction. Ask <strong>“Given what I have now, what can I create?”</strong></p><h2>Available Means</h2><ul><li><strong>Who am I?</strong> Skills, experience, interests, and knowledge.</li><li><strong>What do I know?</strong> Information and expertise.</li><li><strong>Whom do I know?</strong> Mentors, suppliers, partners, networks, and potential customers.</li></ul><p><strong>Affordable loss</strong> asks what you can afford to lose rather than only how much you might make. Partnerships add skills, technology, customers, equipment, distribution, knowledge, or credibility.</p><h2>Effectual Principles</h2><p>The lemonade principle turns surprises into inputs. The pilot-in-the-plane principle focuses on what can be influenced through action, relationships, commitments, experiments, and decisions. Effectuation does not reject planning; it is useful when the future is highly uncertain, resources are limited, and learning is possible through action.</p><h2>Activity</h2><p>List who you are, what you know, whom you know, your resources, and what you can afford to lose. Design the smallest useful venture or experiment using those means.</p>''',
    'Biases, Opportunity Cost, and Experiments': '''<h1>Biases, Opportunity Cost, and Experiments</h1><h2>Learning Objectives</h2><ul><li>Explain cognitive biases in entrepreneurial decisions.</li><li>Define opportunity cost and recognize the cost of choosing one opportunity over another.</li><li>Explain why experiments improve decision-making.</li></ul><h2>Common Biases</h2><ul><li><strong>Confirmation bias:</strong> looking only for information that supports an existing belief.</li><li><strong>Overconfidence:</strong> overestimating knowledge, ability, or the chance of success.</li><li><strong>Escalation of commitment:</strong> continuing because resources have already been invested; previous spending is usually sunk cost.</li><li><strong>Availability bias:</strong> overestimating information that is memorable or easy to recall.</li></ul><h2>Opportunity Cost</h2><p>Opportunity cost is the value of the best alternative given up when a choice is made. It includes money, time, attention, skills, employees, and equipment. Choosing one opportunity means giving up the best realistic alternative, and doing nothing also has an opportunity cost.</p><h2>Experiments</h2><p>A useful experiment has a <strong>question</strong>, <strong>hypothesis</strong>, <strong>test</strong>, <strong>metric</strong>, and <strong>decision rule</strong>. For a study service, test whether students will actually pay rather than merely say they like the idea. Measure sign-ups, payments, usage, retention, and feedback. A good experiment tests the most important uncertainty at the lowest reasonable cost.</p><h2>Experiment Loop</h2><p><strong>Assumption -> Hypothesis -> Small Test -> Evidence -> Learn -> Continue, Change, or Stop</strong></p><h2>Final Challenge</h2><p>Choose one opportunity and record the main assumption, current evidence, biggest uncertainty, best alternative, opportunity cost, smallest useful experiment, and the result that would make you continue, change direction, or stop.</p><h2>Key Takeaways</h2><ul><li>Biases can cause entrepreneurs to ignore negative evidence.</li><li>Opportunity cost is the best alternative forgone.</li><li>Experiments turn assumptions into evidence and reduce the cost of being wrong.</li></ul>''',
}


MODULE_5_NOTES = {
    'Create, Deliver, and Capture Value': '''<h1>Create, Deliver, and Capture Value</h1><h2>Learning Objectives</h2><ul><li>Define value creation, delivery, and capture.</li><li>Explain how the three activities connect.</li><li>Distinguish customer value from business value.</li><li>Understand the basic logic of a business model.</li></ul><h2>What Is a Business Model?</h2><p>A business model explains how an organization creates value for customers, delivers that value, and captures enough value to remain sustainable.</p><p><strong>Create Value -> Deliver Value -> Capture Value</strong></p><h2>Create Value</h2><p>Value creation solves a meaningful customer problem or satisfies an important need. Food delivery creates convenience, tutoring creates learning value, transportation creates mobility, and repair extends the useful life of products.</p><h2>Deliver Value</h2><p>Created value must reach the customer through stores, websites, applications, salespeople, delivery networks, distributors, or partners. A farmer may grow excellent vegetables, but customers cannot benefit until the produce reaches a market.</p><h2>Capture Value</h2><p>Value capture obtains sufficient economic value to sustain the organization. Revenue may come from direct sales, subscriptions, commissions, licensing, advertising, service fees, or transaction charges. Customer value alone is not enough: serving a customer for ₹900 while receiving ₹700 is not sustainable.</p><h2>Activity</h2><p>Describe a familiar Ethiopian business in three sentences: what value it creates, how it delivers it, and how it captures value. Then identify one assumption in each part.</p><aside class="learning-callout"><strong>Key takeaway</strong><p>A strong business model connects customer value, a delivery system, and economic sustainability.</p></aside>''',
    'Customers, Channels, Revenue, and Costs': '''<h1>Customers, Channels, Revenue, and Costs</h1><h2>Learning Objectives</h2><ul><li>Identify customer segments and channels.</li><li>Explain revenue models.</li><li>Distinguish fixed and variable costs.</li><li>Understand how customers, revenue, and costs interact.</li></ul><h2>Customers</h2><p>Define the customer or beneficiary instead of saying “everyone.” Segment by needs, behavior, location, income, industry, or usage patterns. Ask who has the problem most strongly and who can make or influence the purchase.</p><h2>Channels</h2><p>A channel communicates with customers, sells to them, or delivers value. Examples include physical stores, websites, social media, sales representatives, mobile applications, distributors, and marketplaces.</p><h2>Revenue Models</h2><ul><li><strong>Direct sales:</strong> the customer buys a product.</li><li><strong>Subscription:</strong> the customer pays regularly.</li><li><strong>Commission:</strong> the business receives a share of transactions.</li><li><strong>Licensing:</strong> customers pay to use intellectual property.</li><li><strong>Advertising:</strong> a third party pays to reach an audience.</li><li><strong>Freemium:</strong> a basic service is free while advanced features require payment.</li></ul><h2>Costs</h2><p>Fixed costs generally do not change directly with short-term production volume, such as rent, salaries, insurance, and software subscriptions. Variable costs change with volume, such as packaging, materials, delivery, and transaction fees. If price is ₹500 and variable cost is ₹300, the ₹200 contribution helps cover fixed costs and profit.</p><h2>Activity</h2><p>Complete a one-page model answering who pays, who uses, how customers discover and receive the offer, how money arrives, and which costs grow with each customer.</p>''',
    'Resources, Partners, and Social Value': '''<h1>Resources, Partners, and Social Value</h1><h2>Learning Objectives</h2><ul><li>Identify resources required by a venture.</li><li>Explain the role of partners.</li><li>Compare building, buying, and partnering.</li><li>Recognize economic and social value.</li></ul><h2>Key Resources</h2><p>Resources include human resources such as founders and specialists; financial resources such as capital, cash, and credit; physical resources such as buildings, machines, and equipment; intellectual resources such as brands, software, knowledge, and patents; and relationships with customers, suppliers, mentors, and networks.</p><h2>Partnerships</h2><p>Partners may provide technology, distribution, manufacturing, expertise, customers, or infrastructure. A small business can accomplish more with fewer resources, but partnerships also create dependency and coordination risk.</p><h2>Build, Buy, or Partner</h2><p>Ask whether to build a capability, purchase it, or partner with someone who already has it. Compare cost, speed, control, quality, flexibility, and risk.</p><h2>Social Value</h2><p>Businesses can create employment, skills, better access, reduced waste, improved community infrastructure, and inclusion alongside financial returns. Economic value and social value can coexist.</p><h2>Activity</h2><p>Map five resources and partners for your opportunity. Add one social outcome and explain how you will observe it responsibly.</p>''',
    'Ethics, Trust, and Stakeholders': '''<h1>Ethics, Trust, and Stakeholders</h1><h2>Learning Objectives</h2><ul><li>Define business ethics.</li><li>Identify important stakeholders.</li><li>Explain why trust matters.</li><li>Recognize ethical responsibilities in entrepreneurship.</li></ul><h2>Business Ethics</h2><p>Business ethics concerns principles and standards that guide responsible behavior in decisions and relationships. Ask whether an action is honest, fair, harmful, misleading, and responsible.</p><h2>Stakeholders</h2><p>A stakeholder affects or is affected by the organization. Stakeholders may include customers, employees, owners, investors, suppliers, government, communities, partners, and the environment.</p><h2>Trust</h2><p>Customers trust a business to deliver what it promises, protect information, provide safe products, handle complaints honestly, and charge fairly. Trust is an economic asset: when damaged, repeat use and reputation can fall, and rebuilding is expensive.</p><p>Ethics is more than following the law. A technically legal decision can still mislead customers or shift unreasonable harm to workers or communities.</p><h2>Activity</h2><p>Map stakeholders for your venture. For each, record one benefit, one possible harm, and one promise the venture must keep.</p>''',
    'Social, Environmental, and Inclusive Entrepreneurship': '''<h1>Social, Environmental, and Inclusive Entrepreneurship</h1><h2>Learning Objectives</h2><ul><li>Explain social entrepreneurship.</li><li>Understand environmental entrepreneurship.</li><li>Explain inclusive entrepreneurship.</li><li>Recognize opportunities that create multiple forms of value.</li></ul><h2>Social Entrepreneurship</h2><p>Social entrepreneurship applies entrepreneurial approaches to significant social problems such as education, healthcare, poverty, employment, financial inclusion, and community development. Profit may support the mission rather than being the only objective.</p><h2>Environmental Entrepreneurship</h2><p>Environmental entrepreneurship creates economic value while addressing environmental challenges. Examples include renewable energy, recycling, sustainable agriculture, waste reduction, resource-efficient products, and circular business models.</p><h2>Inclusive Entrepreneurship</h2><p>Inclusive entrepreneurship expands participation in economic opportunity for underserved customers, low-income communities, people with disabilities, rural populations, women entrepreneurs, and marginalized groups. Ask: <strong>Who is excluded, underserved, or poorly served?</strong></p><h2>Triple Value</h2><p>Responsible entrepreneurship can balance economic value, social value, and environmental value. Affordable solar lighting can create revenue, improve access to lighting, and reduce dependence on polluting energy sources.</p><h2>Activity</h2><p>Choose one exclusion risk in your opportunity. Redesign a feature, channel, price, or process to reduce it and state how you will measure the improvement.</p>''',
    'Ethical Dilemmas and Responsible Growth': '''<h1>Ethical Dilemmas and Responsible Growth</h1><h2>Learning Objectives</h2><ul><li>Identify ethical dilemmas.</li><li>Understand competing stakeholder interests.</li><li>Apply a structured approach to ethical decisions.</li><li>Explain responsible growth.</li></ul><h2>Ethical Dilemmas</h2><p>An ethical dilemma occurs when an entrepreneur chooses between competing values, responsibilities, or interests. A low-price supplier may reduce costs but involve unfair labor practices. The decision includes worker welfare, reputation, responsibility, cost, and customer expectations.</p><h2>Five-Question Ethics Test</h2><ol><li>Is it legal?</li><li>Is it honest?</li><li>Who could be harmed?</li><li>Would I explain the decision publicly?</li><li>Does it support long-term trust?</li></ol><p>This is a practical framework, not a substitute for professional legal advice.</p><h2>Responsible Growth</h2><p>Growth without control can produce poor quality, employee burnout, cash shortages, service failures, ethical shortcuts, and operational breakdown. Responsible growth increases scale while protecting quality, people, finances, and trust. Ask whether the venture can handle growth, not only how quickly it can grow.</p><h2>Activity</h2><p>Analyze a supplier dilemma. Compare short- and long-term effects, identify a minimum ethical standard, and write a decision with evidence and a review date.</p>''',
    'Separate Personal and Business Money': '''<h1>Separate Personal and Business Money</h1><h2>Learning Objectives</h2><ul><li>Explain why personal and business finances should be separated.</li><li>Understand basic financial records.</li><li>Recognize financial discipline.</li><li>Avoid common small-business financial mistakes.</li></ul><h2>Why Separation Matters</h2><p>Mixing personal and business money hides performance. If customers pay ₹100,000, the business may still owe suppliers, employees, taxes, rent, loans, and other expenses. The full amount is not personal income.</p><h2>Use Separate Records</h2><p>Where practical, maintain separate business banking or mobile-wallet labels, bookkeeping, receipts and invoices, expense records, payroll records, and tax records. Record the date, source, purpose, and balance.</p><h2>Revenue Is Not Personal Income</h2><p>If sales are ₹200,000 and expenses are ₹150,000, simplified accounting profit is ₹50,000. Even that amount may not equal cash available for personal withdrawal because of timing, obligations, or reinvestment.</p><h2>Activity</h2><p>Create a one-week cash record for your opportunity. Mark every item as personal, business, expected, or collected, and identify what the business owes.</p>''',
    'Revenue, Costs, Profit, Cash Flow, and Break-Even': '''<h1>Revenue, Costs, Profit, Cash Flow, and Break-Even</h1><h2>Learning Objectives</h2><ul><li>Define revenue and costs.</li><li>Calculate basic profit.</li><li>Distinguish profit from cash flow.</li><li>Explain break-even and use it in decisions.</li></ul><h2>Revenue and Costs</h2><p>Revenue is income from selling goods or services. One hundred units at ₹500 produces ₹50,000 revenue. Costs represent resources consumed by the business and may be fixed or variable.</p><h2>Profit and Cash Flow</h2><p><strong>Profit = Revenue - Total Costs.</strong> Revenue of ₹100,000 less total costs of ₹70,000 gives ₹30,000 profit. Profit is not cash flow. Customers may buy on credit while suppliers demand immediate payment, leaving a profitable business short of cash.</p><p>Cash inflows include customer payments, loans, investment, and other receipts. Cash outflows include rent, salaries, supplier payments, equipment, and loan repayments.</p><h2>Break-Even</h2><p>Break-even is where total revenue equals total costs and profit is zero.</p><p><strong>Break-even quantity = Fixed Costs / (Selling Price per Unit - Variable Cost per Unit)</strong></p><p>With fixed costs of ₹100,000, price of ₹500, and variable cost of ₹300, contribution is ₹200 and break-even quantity is 500 units.</p><h2>Activity</h2><p>Estimate price, variable cost, and monthly fixed costs for your opportunity. Calculate break-even units and decide whether demand could realistically reach it.</p>''',
    'Bootstrapping, Debt, Equity, and Grants': '''<h1>Bootstrapping, Debt, Equity, and Grants</h1><h2>Learning Objectives</h2><ul><li>Explain common sources of entrepreneurial finance.</li><li>Compare bootstrapping, debt, equity, and grants.</li><li>Understand financing trade-offs.</li><li>Match finance to business needs.</li></ul><h2>Financing Sources</h2><p><strong>Bootstrapping</strong> uses the entrepreneur's resources and internally generated cash. It preserves control but may limit growth and expose personal finances.</p><p><strong>Debt</strong> provides borrowed capital that must generally be repaid, with interest and possible collateral. Ownership usually remains with the entrepreneur, but repayment creates cash-flow pressure.</p><p><strong>Equity</strong> exchanges an ownership interest for capital, expertise, and networks. It avoids scheduled loan repayment but can reduce ownership, control, and future upside.</p><p><strong>Grants</strong> support qualifying activities without conventional debt repayment, but usually include eligibility, reporting, and use restrictions.</p><h2>Choose Strategically</h2><p>Capital is not free. Ask what type fits the venture's stage, risk, cash flow, and growth strategy. Match funding to the milestone and risk it should reduce.</p><h2>Activity</h2><p>Compare four funding options by amount, milestone, repayment or ownership cost, eligibility, and worst-case consequence.</p>''',
    'Vision, Mission, and Self-Leadership': '''<h1>Vision, Mission, and Self-Leadership</h1><h2>Learning Objectives</h2><ul><li>Distinguish vision from mission.</li><li>Explain purpose in entrepreneurship.</li><li>Understand self-leadership.</li><li>Connect discipline with performance.</li></ul><h2>Vision and Mission</h2><p>A <strong>vision</strong> describes the future an organization wants to help create: “A future where affordable education is accessible to every learner.” A <strong>mission</strong> explains what the organization does, for whom, and often how or why: “We provide affordable digital learning resources that help students understand difficult subjects.”</p><table><thead><tr><th>Vision</th><th>Mission</th></tr></thead><tbody><tr><td>Desired future</td><td>Current purpose and action</td></tr><tr><td>Where we want to go</td><td>What we do</td></tr><tr><td>Future-oriented</td><td>Present-oriented</td></tr></tbody></table><h2>Self-Leadership</h2><p>Before leading others, entrepreneurs manage themselves through goal setting, time management, discipline, accountability, learning, emotional regulation, and decision-making. Freedom without discipline can produce missed deadlines, poor financial management, inconsistent execution, and unclear priorities.</p><h2>Activity</h2><p>Write one vision and one mission sentence. Test each against three decisions your venture may face and revise vague words. Ask what part of the situation is within your control.</p>''',
    'Communication, Influence, Delegation, and Teams': '''<h1>Communication, Influence, Delegation, and Teams</h1><h2>Learning Objectives</h2><ul><li>Explain effective entrepreneurial communication.</li><li>Understand influence without relying only on authority.</li><li>Explain delegation.</li><li>Identify effective team characteristics.</li></ul><h2>Communication and Influence</h2><p>Entrepreneurs communicate with customers, employees, investors, suppliers, partners, and regulators. Good communication is clear, concise, relevant, credible, and two-way. Influence uses evidence, trust, relationships, vision, and credibility. Ethical influence respects another person's ability to make an informed decision.</p><h2>Delegation</h2><p>Delegation assigns responsibility and authority for specific work. Define the outcome, select the person, explain authority, provide resources, set expectations and deadlines, monitor progress, and give feedback. Delegation does not abandon accountability; the leader remains accountable for the overall result.</p><h2>Teams</h2><p>Effective teams need clear goals, complementary skills, defined responsibilities, trust, communication, accountability, and psychological safety. A team coordinates different capabilities toward a shared objective.</p><h2>Activity</h2><p>List the next six months of work. Assign one accountable owner to each item and identify the capability gap to develop or contract.</p>''',
    'Conflict, Emotional Intelligence, and Culture': '''<h1>Conflict, Emotional Intelligence, and Culture</h1><h2>Learning Objectives</h2><ul><li>Explain constructive and destructive conflict.</li><li>Understand emotional intelligence.</li><li>Recognize organizational culture.</li><li>Manage disagreements professionally.</li></ul><h2>Conflict</h2><p>Conflict can arise from differences in goals, opinions, values, resources, responsibilities, or expectations. Constructive disagreement can improve decisions, creativity, risk identification, and problem solving. Destructive conflict includes personal attacks, blame, hostility, information withholding, retaliation, and persistent distrust.</p><h2>Emotional Intelligence</h2><p>Emotional intelligence is the ability to recognize, understand, and manage emotions in oneself and interactions with others. It includes self-awareness, self-management, empathy, social awareness, and relationship management. When an employee criticizes an idea, ask what specifically concerns them instead of reacting defensively.</p><h2>Culture</h2><p>Culture is the shared pattern of values, expectations, behaviors, and norms. Leaders create culture through what they repeatedly do, reward, tolerate, and punish. A leader who rewards hiding mistakes creates a culture of self-protection, regardless of what the values poster says. Healthy cultures encourage learning, accountability, respect, experimentation, ethical behavior, open communication, customer focus, and improvement.</p><h2>Activity</h2><p>Describe a disagreement and rewrite your response using interests, evidence, options, and a follow-up commitment. Then identify one leader behavior that would strengthen your desired culture.</p><aside class="learning-callout"><strong>Final takeaway</strong><p>Entrepreneurial leadership creates direction, builds trust, develops people, manages conflict, and creates a culture where people can perform well.</p></aside>''',
}

MODULE_6_NOTES = {
    'How Entrepreneurial Ecosystems Work': '''<h1>How Entrepreneurial Ecosystems Work</h1><h2>Learning Objectives</h2><ul><li>Define an entrepreneurial ecosystem.</li><li>Identify major ecosystem actors and how they interact.</li><li>Understand why networks matter.</li><li>Identify ecosystem resources available to entrepreneurs.</li></ul><h2>What Is an Entrepreneurial Ecosystem?</h2><p>An entrepreneurial ecosystem is the network of people, organizations, institutions, resources, and conditions that influence entrepreneurship in a particular environment. A venture may depend on customers, suppliers, employees, banks, investors, universities, government, technology providers, mentors, business associations, incubators, accelerators, and communities.</p><h2>The Ecosystem Perspective</h2><p>An agricultural technology venture may need university research, investor funding, government approvals, technology suppliers, farmers for testing, distribution partners, and customers. Its success depends partly on the quality of the surrounding ecosystem, not only on the founder.</p><h2>Major Actors</h2><ul><li><strong>Entrepreneurs:</strong> identify opportunities, organize resources, and create value.</li><li><strong>Customers:</strong> provide demand and market feedback.</li><li><strong>Finance:</strong> banks, investors, and microfinance can supply capital.</li><li><strong>Universities:</strong> provide knowledge, talent, research, incubation, and connections.</li><li><strong>Government:</strong> influences regulation, infrastructure, tax, programs, education, registration, and policy.</li><li><strong>Established businesses:</strong> provide supply chains, partnerships, customers, employment, technology, and market access.</li><li><strong>Support organizations:</strong> incubators, accelerators, NGOs, associations, and mentorship networks.</li></ul><h2>Networks and Conditions</h2><p>Networks provide information, knowledge, customers, capital, skills, and partnerships. Ecosystems also include culture, trust, infrastructure, digital connectivity, education, regulation, finance, markets, and attitudes toward entrepreneurship. Strong ecosystems improve access to resources; weak ecosystems may involve finance, infrastructure, skills, regulation, and market gaps. Constraints can sometimes be addressed through partnerships and resourcefulness.</p><h2>Activity</h2><p>Place one opportunity in the center of an ecosystem map. Add the customer, supplier, financial partner, government or institution, university, technology partner, mentor, strategic partner, and community. Ask which relationship is most critical.</p>''',
    'Comparing Ethiopia, Africa, and Global Entrepreneurial Ecosystems': '''<h1>Comparing Ethiopia, Africa, and Global Entrepreneurial Ecosystems</h1><h2>Learning Objectives</h2><ul><li>Compare entrepreneurial ecosystems across contexts.</li><li>Identify African entrepreneurial strengths and constraints.</li><li>Recognize Ethiopian opportunities and limitations.</li><li>Avoid simplistic country comparisons.</li></ul><h2>Why Compare?</h2><p>The same idea can perform differently because market size, infrastructure, regulation, finance, technology, skills, customer behavior, culture, networks, and international connections differ.</p><h2>Ethiopia</h2><p>Ethiopia has a large domestic population, significant agricultural activity, growing urban markets, increasing digital adoption, informal enterprise, emerging technology communities, and infrastructure-related opportunities. Entrepreneurs may also face finance, infrastructure, formalization, market access, regulatory, technology, and skills constraints. An ecosystem contains both opportunities and constraints.</p><h2>African and Global Contexts</h2><p>Africa contains many national and regional ecosystems, not one homogeneous environment. Population growth, urbanization, mobile technology, financial inclusion, unmet needs, informal markets, youth populations, cross-border trade, and infrastructure gaps create varied conditions. Global centers may provide investment, infrastructure, specialized talent, research, support, and international markets, but often have high competition and operating costs.</p><h2>Comparison Dimensions</h2><p>Compare market, finance, talent, infrastructure, technology, regulation, networks, research, culture, and international access. A technology startup may need research, talent, and venture capital, while a local food business may need demand, affordable premises, and supplier relationships.</p><h2>Activity</h2><p>Compare two ecosystems using market, finance, talent, infrastructure, and networks. Explain which ecosystem fits your opportunity and what would need local adaptation.</p>''',
    'Informal, Women, Youth, and Diaspora Entrepreneurship': '''<h1>Informal, Women, Youth, and Diaspora Entrepreneurship</h1><h2>Learning Objectives</h2><ul><li>Explain informal entrepreneurship.</li><li>Understand women and youth entrepreneurship.</li><li>Explain diaspora entrepreneurship.</li><li>Recognize group-specific barriers and opportunities.</li><li>Understand why inclusion matters.</li></ul><h2>Informal Entrepreneurship</h2><p>Informal entrepreneurship includes activities partly or entirely outside formal registration, regulation, or institutional systems. Small-scale trading, street vending, home businesses, informal services, repairs, and micro-enterprises can provide employment, income, essential services, and local economic activity.</p><p>Informality can lower entry barriers but may limit finance, legal protection, records, market access, social protection, and growth. Ask how a venture can move toward sustainable and appropriate formalization as it grows.</p><h2>Women and Youth</h2><p>Women entrepreneurs contribute to household and economic activity but may face finance, networks, property, training, time, social expectation, and market barriers. Young entrepreneurs can bring digital skills, fresh perspectives, energy, experimentation, and technology adoption, while often lacking capital, experience, networks, knowledge, and credibility. Mentorship and practical education can help.</p><h2>Diaspora and Inclusion</h2><p>Diaspora entrepreneurs can connect local ventures to capital, knowledge, technology, international networks, market access, and trusted business relationships. Inclusive ecosystems ask who has access to capital, knowledge, networks, markets, technology, and support, and who is left out.</p><h2>Reflection</h2><p>Identify one informal business, one youth opportunity, one women-led opportunity, and one possible diaspora connection. What ecosystem support could help each grow?</p>''',
    'Portfolio Structure and Evidence': '''<h1>Portfolio Structure and Evidence</h1><h2>Learning Objectives</h2><ul><li>Explain an entrepreneurial opportunity portfolio.</li><li>Organize multiple opportunities systematically.</li><li>Compare opportunities using evidence.</li><li>Distinguish attractive opportunities from supported opportunities.</li><li>Select an opportunity for deeper development.</li></ul><h2>What Is an Opportunity Portfolio?</h2><p>An opportunity portfolio is a structured collection of opportunities under consideration. Keeping several possibilities visible reduces premature commitment and allows comparison by evidence, potential, capability fit, test cost, and timing.</p><h2>Portfolio Fields</h2><p>For each opportunity record the name, customer, problem, need, proposed solution, value, evidence, key assumption, uncertainty, feasibility, viability, and next experiment.</p><h2>Evidence Strength</h2><ul><li><strong>Weak:</strong> personal opinion or speculation.</li><li><strong>Moderate:</strong> interviews, observations, or secondary research.</li><li><strong>Strong:</strong> repeated behavior, transactions, commitments, prototype use, or other meaningful behavioral evidence.</li></ul><p>Compare evidence strength against opportunity potential. High potential with strong evidence is a priority; high potential with weak evidence needs research; low potential with strong evidence suggests alternatives; low potential with weak evidence is low priority.</p><h2>Activity</h2><p>Create a portfolio of three to five opportunities. Score customer need, evidence strength, feasibility, viability, and strategic fit from 1 to 5. Explain why the highest-ranked opportunity deserves further testing.</p><aside class="learning-callout"><strong>Key takeaway</strong><p>Do not confuse the opportunity you like most with the opportunity best supported by evidence.</p></aside>''',
    'Presenting an Opportunity Professionally': '''<h1>Presenting an Opportunity Professionally</h1><h2>Learning Objectives</h2><ul><li>Present an opportunity clearly.</li><li>Structure a professional opportunity pitch.</li><li>Use evidence effectively.</li><li>Explain value and business logic.</li><li>Respond to questions professionally.</li></ul><h2>Why Presentation Matters</h2><p>Entrepreneurs present to customers, investors, partners, employees, universities, government, incubators, and accelerators. A strong opportunity can fail to receive support if it is poorly communicated.</p><h2>Opportunity Pitch</h2><ol><li>Problem</li><li>Customer</li><li>Evidence</li><li>Opportunity</li><li>Solution</li><li>Value proposition</li><li>Business model</li><li>Competitive context</li><li>Validation</li><li>Next step</li></ol><h2>60-Second Statement</h2><p><strong>“[Customer] experiences [problem]. Evidence shows [evidence]. We propose [solution], which creates [value]. Unlike [alternative], our approach [difference]. Our next step is [experiment/action].”</strong></p><p>Avoid unsupported claims such as “This will revolutionize the market.” Say what interviews, tests, or behavior actually show. When you do not know, explain that it is an assumption to test next.</p><h2>Activity</h2><p>Prepare a 3-5 minute presentation answering what problem exists, who has it, what evidence you have, what opportunity and solution exist, what value will be created, how value will be captured, what risks remain, and what you will do next.</p>''',
    'Reflection and the Next 30, 60, and 90 Days': '''<h1>Reflection and the Next 30, 60, and 90 Days</h1><h2>Learning Objectives</h2><ul><li>Reflect on entrepreneurial learning.</li><li>Identify strengths and development areas.</li><li>Convert learning into action.</li><li>Create a measurable 30-60-90 day plan.</li><li>Establish next steps.</li></ul><h2>Learning Through Action</h2><p>Completing a course does not automatically make someone an entrepreneur. The useful question is what you will do differently. Entrepreneurship develops through <strong>Learning -> Action -> Feedback -> Reflection -> Adaptation</strong>.</p><h2>Capabilities to Review</h2><p>Review opportunity recognition, creativity, customer understanding, decision-making, business modeling, financial thinking, ethics, and leadership. Identify your strongest capability, weakest capability, evidence, and improvement action.</p><h2>30-60-90 Day Framework</h2><ul><li><strong>Days 1-30 - Explore and validate:</strong> interviews, observation, competitor research, assumptions, ecosystem partners, prototype, and small experiment. Ask whether the opportunity is worth pursuing.</li><li><strong>Days 31-60 - Test and refine:</strong> solution tests, customer response, pricing, value proposition, operations, partnerships, and financial assumptions. Ask what evidence says.</li><li><strong>Days 61-90 - Decide and act:</strong> pilot, business process, model, funding, partnerships, performance measures, and continue, change, or stop decision.</li></ul><p>Make actions measurable: interview 20 customers by Day 20, or run a two-week pilot with 30 users and measure activation, usage, and willingness to pay.</p><h2>Final Reflection</h2><p>Complete: Before this course I believed... Now I understand... The most important concept is... My strongest capability is... I need to improve... The opportunity I will investigate is... My first experiment is... In 30 days I will... By Day 60... By Day 90...</p><aside class="learning-callout"><strong>Final principle</strong><p>Entrepreneurship is the ability to recognize possibilities, create value, act responsibly, learn from evidence, and adapt as the future unfolds.</p></aside>''',
}


def format_notes(module_title, title, explanation, activity, video, textbook_lens, source_title):
    if module_title == 'Module 4: Opportunity Recognition and Decision Making':
        return MODULE_4_NOTES[title]
    if module_title == 'Module 5: Business Models, Ethics, Finance and Leadership':
        return MODULE_5_NOTES[title]
    if module_title == 'Module 6: Entrepreneurial Ecosystems and the Opportunity Portfolio':
        return MODULE_6_NOTES[title]
    if title == 'What Is Entrepreneurship, Really?':
        return format_first_lesson(textbook_lens, source_title)
    if title == 'Types and Purposes of Entrepreneurship':
        return format_types_lesson(textbook_lens, source_title)
    if title == 'Entrepreneurship in Ethiopia and Africa':
        return format_ethiopia_africa_lesson(textbook_lens, source_title)
    if title == 'Growth mindset and initiative':
        return format_growth_mindset_initiative_lesson(textbook_lens, source_title)
    if title == 'Resilience, persistence, and adaptability':
        return format_resilience_lesson(textbook_lens, source_title)
    if title == 'Calculated risk and uncertainty tolerance':
        return format_calculated_risk_lesson(textbook_lens, source_title)
    if title == 'Creativity, innovation, and problem framing':
        return format_creativity_problem_framing_lesson(textbook_lens, source_title)
    if title == 'Design thinking and user empathy':
        return format_design_thinking_empathy_lesson(textbook_lens, source_title)
    if title == 'SCAMPER, frugal, and disruptive innovation':
        return format_scamper_frugal_disruptive_lesson(textbook_lens, source_title)
    explanation = expand_explanation(module_title, title, explanation)
    sections = [
        ('Lesson notes', explanation),
        ('Textbook connection', textbook_lens),
        ('Hisrich chapter alignment', HISRICH_CHAPTER_MAP[int(module_title.split(':', 1)[0].split()[-1])]),
        ('Practice activity', activity),
        ('Teaching guide', f'Learning objective and teaching sequence: {video} Explain the concept in plain language, unpack its components, demonstrate it with an Ethiopian or African example, and pause for the activity. Include one worked example, one common mistake, and a recap of the evidence learners should produce. {source_title} is optional supplementary reading.'),
        ('Key terms and learning check', 'Write three key terms from this lesson in your own words. Can you explain the central idea without jargon? What evidence would support or challenge it in your community? Which assumption remains untested?'),
    ]
    return ''.join(
        f'<h2><strong><em>{escape(title)}</em></strong></h2><p>{escape(body)}</p>'
        if title == 'Lesson notes' else
        f'<aside class="learning-callout"><strong>{escape(title)}</strong><p>{escape(body)}</p></aside>'
        for title, body in sections
    )


def format_growth_mindset_initiative_lesson(textbook_lens, source_title):
    return '''<h1>Growth Mindset and Initiative</h1>
<p><strong>Estimated lesson time:</strong> 10-15 minutes<br><strong>Level:</strong> Beginner<br><strong>Module:</strong> 2 - Mindset and Entrepreneurial Readiness</p>
<h2>Learning Objectives</h2>
<p>By the end of this lesson, you will be able to:</p>
<ul><li>Define an entrepreneurial mindset.</li><li>Explain a growth mindset and compare it with a fixed mindset.</li><li>Understand why mindset matters in entrepreneurship.</li><li>Explain initiative and distinguish it from waiting passively.</li><li>Identify entrepreneurial behaviors that demonstrate initiative.</li><li>Apply growth mindset and initiative to a real entrepreneurial situation.</li></ul>
<hr>
<h2>Introduction</h2>
<p><strong>Growth Mindset + Initiative = Learn, Act, Improve.</strong></p>
<p>An <strong>entrepreneurial mindset</strong> is a way of thinking that helps individuals recognize opportunities, solve problems, take action, learn from experience, and create value despite uncertainty. Entrepreneurs do not always have perfect information. They often begin with a problem, an idea, limited resources, and uncertainty. What matters is how they respond.</p>
<p>An entrepreneurial mindset encourages a person to ask: What problem can I solve? What opportunity exists? How can I test my idea? What can I learn from failure? What should I change? What action can I take now?</p>
<aside class="learning-callout"><strong>Key idea</strong><p>Entrepreneurial action starts with how a learner responds to uncertainty, difficulty, and incomplete information.</p></aside>
<h2>1. What Is a Growth Mindset?</h2>
<p>A <strong>growth mindset</strong> is the belief that abilities, knowledge, and skills can be developed through learning, practice, effort, feedback, and experience. A person with a growth mindset does not say, “I am not good at this, so I can never do it.” Instead, they say, “I am not good at this yet, but I can improve.” The word <strong>“yet”</strong> is important.</p>
<p>Compare the two statements below:</p>
<table><thead><tr><th>Fixed Mindset</th><th>Growth Mindset</th></tr></thead><tbody>
<tr><td>“I cannot do it.”</td><td>“I cannot do it yet.”</td></tr>
<tr><td>My abilities are limited.</td><td>I can develop my abilities.</td></tr>
<tr><td>I avoid difficult tasks.</td><td>I accept challenges and practice.</td></tr>
<tr><td>Failure proves I cannot succeed.</td><td>Failure gives feedback and evidence.</td></tr>
<tr><td>I want to appear capable.</td><td>I want to become more capable.</td></tr>
</tbody></table>
<h2>2. Why Growth Mindset Matters in Entrepreneurship</h2>
<p>Entrepreneurship involves continuous learning. An entrepreneur may initially lack financial knowledge, marketing skills, technical skills, leadership experience, or industry knowledge. A growth mindset allows the entrepreneur to treat these limitations as areas for development rather than permanent barriers.</p>
<p>Example: A student wants to create an online business but does not know how to build a website. A fixed mindset says, “I do not know programming. I cannot start an online business.” A growth mindset says, “I do not know programming yet. I can learn the basics, use available tools, or work with someone who has the required skills.” The second approach opens the door to action.</p>
<aside class="learning-callout"><strong>Important</strong><p>A growth mindset does not mean unrealistic optimism. It does not mean: “If I work hard enough, I will automatically succeed.” It means: “My current abilities do not have to determine my future abilities.” Entrepreneurs still need evidence, practice, resources, good decisions, feedback, strategy, and adaptation.</p></aside>
<h2>3. What Is Initiative?</h2>
<p><strong>Initiative</strong> means taking purposeful action without waiting for someone else to tell you what to do. An entrepreneurial person does not simply notice problems. They ask, “What can I do about it?”</p>
<p>Example: Two students notice that classmates struggle to find affordable study materials. Student A complains about the problem. Student B surveys classmates, identifies what materials they need, creates organized digital notes, and tests whether students find them useful. Student B is demonstrating initiative.</p>
<h2>4. Initiative vs. Waiting</h2>
<p>Entrepreneurial initiative can be understood through a simple contrast:</p>
<table><thead><tr><th>Waiting</th><th>Initiative</th></tr></thead><tbody>
<tr><td>Problem → Wait for someone else → No action</td><td>Problem → Investigate → Take appropriate action → Learn → Improve</td></tr>
</tbody></table>
<p>Initiative does not mean acting recklessly. It means taking responsible action instead of remaining passive.</p>
<h2>5. How to Develop Initiative</h2>
<ol><li><strong>Notice problems:</strong> Pay attention to inefficiencies, frustrations, and unmet needs.</li><li><strong>Ask questions:</strong> Understand why the problem exists.</li><li><strong>Start small:</strong> You do not need a perfect solution.</li><li><strong>Test assumptions:</strong> Talk to potential customers or users.</li><li><strong>Take ownership:</strong> Ask what you can personally do.</li><li><strong>Learn from results:</strong> Use evidence to improve your next action.</li></ol>
<h2>6. Mini Case Study</h2>
<p>A college canteen has long queues during lunch. Students complain about the waiting time. An entrepreneurial response is pre-ordering, digital confirmation, and faster collection. A student observes the problem and proposes this response. The student conducts a small survey, creates a basic prototype, and tests it with a limited number of students. The idea may succeed, fail, or require modification. But the student has demonstrated: Observation + Initiative + Experimentation + Learning.</p>
<h2>Think About It</h2>
<blockquote>What problem do you see in your school, neighborhood, or community? How could a growth mindset and initiative help you turn that problem into a small action?</blockquote>
<h2>Key Takeaways</h2>
<ul><li>A growth mindset views abilities as developable.</li><li>Entrepreneurs constantly need to learn and adapt.</li><li>Failure can provide useful information when analyzed properly.</li><li>Initiative means taking purposeful action rather than waiting passively.</li><li>Initiative should be informed by observation and learning, not reckless action.</li><li>Entrepreneurial mindset turns “I cannot” into “How can I learn or solve this?”</li></ul>
<h2>Lesson Challenge</h2>
<p>Identify one problem in your school or community and write down one small action you can take this week using a growth mindset and initiative.</p>
<h2>Textbook Connection</h2>
<p><strong>OpenLearn Entrepreneurship.</strong> The lesson uses the course’s original interpretation of growth mindset, initiative, and entrepreneurial learning.</p>
<p><strong>Supplementary reference:</strong> ''' + source_title + '''. The reference supports further reading; this lesson uses original explanations, examples, activities, and comparisons.</p>'''

def format_resilience_lesson(textbook_lens, source_title):
    return '''<h1>Resilience, Persistence, and Adaptability</h1>
<p><strong>Estimated lesson time:</strong> 10-15 minutes<br><strong>Level:</strong> Beginner<br><strong>Module:</strong> 2 - Mindset and Entrepreneurial Readiness</p>
<h2>Learning Objectives</h2>
<p>By the end of this lesson, you will be able to:</p>
<ul><li>Define resilience, persistence, and adaptability.</li><li>Explain why these qualities matter in entrepreneurship.</li><li>Distinguish between persistence and stubbornness.</li><li>Understand how entrepreneurs respond to setbacks.</li><li>Explain why adaptability is essential under changing conditions.</li><li>Apply these concepts to entrepreneurial situations.</li></ul>
<hr>
<h2>Introduction</h2>
<p>Entrepreneurship is often presented as:</p>
<p><strong>Idea → Business → Success</strong></p>
<p>Real entrepreneurial journeys are usually more complicated. A more realistic path is:</p>
<p><strong>Idea → Experiment → Setback → Learning → Adjustment → Experiment → Improvement → Growth</strong></p>
<p>Entrepreneurs may experience customer rejection, financial difficulties, product failures, competition, unexpected costs, operational problems, changing customer preferences, regulatory changes, and technology changes. The ability to continue learning and responding is therefore critical.</p>
<aside class="learning-callout"><strong>Key idea</strong><p>Entrepreneurial growth is not a straight line. It is a repeated cycle of learning, responding, improving, and creating value under pressure.</p></aside>
<h2>1. What Is Resilience?</h2>
<p><strong>Resilience</strong> is the ability to recover, adjust, and continue moving forward after difficulties or setbacks. A resilient entrepreneur does not assume that “nothing will ever go wrong.” Instead, they recognize that “problems will happen. I need to learn how to respond.”</p>
<p>Resilience involves a sequence: <strong>Setback → Recovery → Learning → Adaptation → Forward movement</strong>.</p>
<h2>2. What Is Persistence?</h2>
<p><strong>Persistence</strong> means continuing to pursue a meaningful goal despite obstacles and temporary setbacks. For example, an entrepreneur launches a product and only a few customers purchase it. Instead of immediately abandoning the venture, they investigate whether the product solves the right problem, whether the price is appropriate, whether customers are aware of it, whether the marketing message is clear, and whether the product needs improvement. The entrepreneur continues working toward the goal while learning from the results.</p>
<h2>3. Persistence Is Not Stubbornness</h2>
<p>Persistence means continuing the goal but remaining willing to change the method. Stubbornness means continuing to do exactly the same thing regardless of the evidence. Entrepreneurship requires persistent goals with flexible methods.</p>
<aside class="learning-callout"><strong>Remember</strong><p>Do not confuse commitment with rigidity. You can remain committed to solving a problem while completely changing the product, strategy, or business model.</p></aside>
<h2>4. What Is Adaptability?</h2>
<p><strong>Adaptability</strong> is the ability to adjust one’s actions, strategies, or plans when circumstances change. Markets change. Customers change. Technology changes. Competitors change. Therefore, entrepreneurs must be prepared to change as well.</p>
<p>Simple formula: <strong>Change in environment → New information → Adjustment → New action</strong>.</p>
<h2>5. Example of Adaptability</h2>
<p>Imagine a small business that sells products primarily through a physical store. Customer behavior changes and more customers begin shopping online. The entrepreneur could ignore the change, close immediately, or investigate the change and experiment with online sales. An adaptable entrepreneur might choose Option C and test social media marketing, online ordering, digital payments, and delivery.</p>
<h2>6. Resilience, Persistence, and Adaptability Together</h2>
<table><thead><tr><th>Quality</th><th>Main question</th></tr></thead><tbody>
<tr><td><strong>Resilience</strong></td><td>How do I recover from setbacks?</td></tr>
<tr><td><strong>Persistence</strong></td><td>Will I continue working toward the goal?</td></tr>
<tr><td><strong>Adaptability</strong></td><td>How should I change when circumstances change?</td></tr>
</tbody></table>
<p>Together, resilience helps you recover, persistence keeps you moving, and adaptability helps you change direction when necessary.</p>
<h2>7. How Entrepreneurs Respond to Failure</h2>
<p>Failure does not automatically mean the entrepreneur is incapable. A useful entrepreneurial approach is: stop and assess, separate facts from assumptions, identify the cause, learn, adapt, and test again.</p>
<h2>8. Experimentation Mindset</h2>
<p>Entrepreneurs often operate through small experiments. Instead of asking, “Will this idea definitely succeed?” they can ask, “What is the smallest test I can conduct to learn whether this idea has potential?” For example, instead of producing 10,000 units of a new product, an entrepreneur might first produce 100 units and test customer response. This can reduce unnecessary exposure while generating useful information.</p>
<h2>9. Building Entrepreneurial Resilience</h2>
<p>Resilience can be strengthened through habits such as reviewing results, continuous learning, building relationships, focusing on controllable actions, experimenting, and accepting change.</p>
<h2>10. Mini Case Study</h2>
<p>An entrepreneur creates a food-delivery service targeting office workers. However, customer demand is lower than expected. The entrepreneur investigates and discovers that students are more interested in affordable food delivery. Instead of abandoning the business, the entrepreneur studies student needs, changes the pricing model, adjusts the menu, partners with student-focused food outlets, and tests the revised model.</p>
<p><strong>What qualities are demonstrated?</strong></p>
<p><strong>Resilience:</strong> The entrepreneur recovers from the disappointing result.</p>
<p><strong>Persistence:</strong> The entrepreneur continues pursuing the broader opportunity.</p>
<p><strong>Adaptability:</strong> The entrepreneur changes the target market and business model.</p>
<h2>Key Takeaways</h2>
<ul><li><strong>Resilience</strong> is the ability to recover from setbacks.</li><li><strong>Persistence</strong> is continuing toward meaningful goals despite obstacles.</li><li><strong>Adaptability</strong> is changing one’s approach when conditions change.</li><li>Persistence does not mean repeating the same mistake.</li><li>Successful entrepreneurs often maintain their purpose while changing their method.</li><li>Failure can become useful when it produces learning.</li><li>Entrepreneurs should treat uncertainty and setbacks as part of the entrepreneurial process.</li></ul>
<h2>Lesson Challenge</h2>
<p>Identify a setback in your own work or community and write down how resilience, persistence, and adaptability could help you respond.</p>
<h2>Textbook Connection</h2>
<p><strong>OpenLearn Entrepreneurship.</strong> This lesson connects resilience, persistence, and adaptability to entrepreneurial learning and decision-making.</p>
<p><strong>Supplementary reference:</strong> ''' + source_title + '''. The reference supports further reading; this lesson uses original explanations, examples, activities, and comparisons.</p>'''

def format_calculated_risk_lesson(textbook_lens, source_title):
    return '''<h1>Calculated Risk and Uncertainty Tolerance</h1>
<p><strong>Estimated lesson time:</strong> 10-15 minutes<br><strong>Level:</strong> Beginner<br><strong>Module:</strong> 2 - Mindset and Entrepreneurial Readiness</p>
<h2>Learning Objectives</h2>
<p>By the end of this lesson, you will be able to:</p>
<ul><li>Define risk and uncertainty.</li><li>Explain the difference between risk and uncertainty.</li><li>Understand why entrepreneurship involves uncertainty.</li><li>Explain what calculated risk means.</li><li>Identify factors entrepreneurs should consider before taking risks.</li><li>Distinguish calculated risk from reckless behavior.</li><li>Understand uncertainty tolerance and its importance in entrepreneurship.</li></ul>
<hr>
<h2>Introduction</h2>
<p>Entrepreneurship rarely provides complete information. When starting a new venture, an entrepreneur may not know how many customers will buy the product, how competitors will respond, whether the price is appropriate, how quickly the business will grow, whether the business model will work, or what unexpected problems will occur. This is called <strong>uncertainty</strong>.</p>
<p>Therefore, entrepreneurship requires the ability to make decisions even when the future is not completely known.</p>
<aside class="learning-callout"><strong>Key idea</strong><p>Risk can be estimated; uncertainty is harder to estimate. Entrepreneurs act with imperfect information and use evidence to reduce avoidable surprises.</p></aside>
<h2>1. What Is Risk?</h2>
<p><strong>Risk</strong> exists when possible outcomes are uncertain but outcomes or their probabilities can be estimated to some degree. An entrepreneur may estimate that a new advertising campaign has a high chance of generating customers, a moderate chance of producing little change, and a smaller chance of losing the advertising expenditure. The entrepreneur can use available information to evaluate the decision.</p>
<h2>2. What Is Uncertainty?</h2>
<p><strong>Uncertainty</strong> refers to situations where future outcomes are difficult to predict and reliable probabilities may not be available. Imagine launching a completely new product for a market that does not yet exist. The entrepreneur may not know how customers will react, how large the market will become, what competitors will do, or which business model will work. There may simply be insufficient information.</p>
<h2>3. Risk vs. Uncertainty</h2>
<table><thead><tr><th>Risk</th><th>Uncertainty</th></tr></thead><tbody>
<tr><td>Outcomes are uncertain but some information is available.</td><td>Outcomes are highly difficult to predict and information may be limited.</td></tr>
<tr><td>Probabilities may be estimated.</td><td>Reliable probabilities may be unavailable.</td></tr>
<tr><td>Often analyzed quantitatively.</td><td>Often requires judgment and experimentation.</td></tr>
</tbody></table>
<blockquote><strong>Simple way to remember:</strong> Risk can often be estimated. Uncertainty is harder to estimate.</blockquote>
<h2>4. What Is Calculated Risk?</h2>
<p>A <strong>calculated risk</strong> is a risk that an entrepreneur evaluates carefully before taking action. It does not mean eliminating all risk. Instead, the entrepreneur asks: “What could happen, how likely is it, what could I lose, what could I gain, and how can I reduce the downside?”</p>
<h2>5. The Calculated-Risk Process</h2>
<ol><li><strong>Identify the decision:</strong> What exactly are you planning to do?</li><li><strong>Identify possible outcomes:</strong> What could go right? What could go wrong?</li><li><strong>Estimate potential impact:</strong> How much could you gain? How much could you lose?</li><li><strong>Assess available information:</strong> What evidence do you have?</li><li><strong>Consider alternatives:</strong> Is there a safer or better way to achieve the same objective?</li><li><strong>Reduce unnecessary downside:</strong> Can you test the idea on a smaller scale?</li><li><strong>Decide:</strong> Take action when the potential value justifies the risk you are prepared to accept.</li></ol>
<h2>6. Example: Calculated Risk</h2>
<p>Suppose an entrepreneur wants to launch a new food product. A reckless approach would be to produce 50,000 units immediately without testing demand. A calculated approach begins with a customer survey, a small-batch product test, feedback collection, sales measurement, product improvement, and expansion only when evidence supports the decision.</p>
<h2>7. Calculated Risk Is Not Recklessness</h2>
<p>Reckless behavior says, “I don’t know what will happen, but I’m doing it anyway.” Calculated risk says, “I don’t know exactly what will happen, so I will gather information, test my assumptions, estimate the downside, and take a reasonable step.” Entrepreneurship requires risk-taking, but successful entrepreneurship is not about taking the greatest possible risk. It is about taking informed and manageable risks.</p>
<h2>8. Simple Risk Assessment</h2>
<p>A basic way to think about risk is: <strong>Risk = Probability of an unwanted outcome × Impact of that outcome.</strong> If there is a 20% chance of losing 50,000 birr, the simplified expected loss is 0.20 × 50,000 = 10,000 birr. This is a way of thinking about expected impact, not a guarantee of a loss.</p>
<h2>9. Risk and Reward</h2>
<p>Entrepreneurs evaluate both potential downside and upside. A high potential reward does not automatically mean a good opportunity. Entrepreneurs must consider financial capacity, probability of success, strategic importance, alternatives, ability to absorb losses, timing, and opportunity cost.</p>
<h2>10. What Is Uncertainty Tolerance?</h2>
<p><strong>Uncertainty tolerance</strong> is the ability to remain functional and make reasonable decisions when outcomes are not fully known. Entrepreneurs cannot always wait for complete information before acting. Instead, they learn to operate with incomplete information.</p>
<p>Low tolerance looks like, “I need to know exactly what will happen before I act.” Higher tolerance looks like, “I cannot know everything, but I can gather enough information to take the next reasonable step.”</p>
<h2>11. Experimentation Reduces Uncertainty</h2>
<p>Entrepreneurs should not try to predict everything. They can generate information through experiments. For example, if the question is whether customers will pay 500 birr for a service, a smaller test can be run: create a small test, present the offer, measure responses, and learn. The experiment turns some uncertainty into information. This creates a cycle: uncertainty → experiment → evidence → learning → better decision.</p>
<h2>12. Importance of Data</h2>
<p>Useful information can come from customer interviews, surveys, sales data, market research, competitor analysis, small pilot programs, online analytics, and feedback. Data does not eliminate uncertainty, but it helps entrepreneurs make better-informed decisions.</p>
<h2>13. Practical Decision Framework</h2>
<p>Ask seven questions before taking an entrepreneurial risk: what am I trying to achieve? What could go wrong? What could go right? What evidence do I have? What is the worst realistic outcome? Can I test this on a smaller scale? What will I do if the result is negative?</p>
<h2>14. Ethiopian Entrepreneur Example</h2>
<p>An entrepreneur wanting to establish a small food-processing business faces uncertainty around customer demand, raw-material availability, pricing, distribution, competition, and production costs. A reckless entrepreneur may invest all available capital. A calculated approach could research customers, estimate costs, test product demand, start with limited production, collect customer feedback, evaluate financial results, improve, and scale gradually.</p>
<h2>15. Three Levels of Entrepreneurial Decision-Making</h2>
<table><thead><tr><th>Level</th><th>Purpose</th></tr></thead><tbody>
<tr><td><strong>Low-risk experiment</strong></td><td>Small amount of money, a small number of customers, and a short testing period. Purpose: learn.</td></tr>
<tr><td><strong>Moderate-risk decision</strong></td><td>More resources committed; evidence already available; potential for meaningful growth.</td></tr>
<tr><td><strong>High-risk decision</strong></td><td>Large financial commitment, major uncertainty, potential consequences; requires careful evaluation.</td></tr>
</tbody></table>
<p>The lesson is not: “Always choose low risk.” The lesson is: “Match the size of the risk to the quality of the opportunity, available evidence, and your ability to absorb the downside.”</p>
<h2>16. Entrepreneurial Mindset</h2>
<p>A strong entrepreneurial mindset does not say, “I am fearless.” Instead, it says, “I understand that uncertainty exists, and I can learn to make better decisions despite it.” Entrepreneurs need courage to act, analysis to evaluate, experimentation to learn, and adaptability to respond.</p>
<h2>Key Takeaways</h2>
<ul><li><strong>Entrepreneurship involves uncertainty.</strong> The future cannot always be predicted.</li><li><strong>Risk and uncertainty are related but different.</strong> Risk can often be estimated; uncertainty is harder to quantify.</li><li><strong>Calculated risk is informed action.</strong> Entrepreneurs evaluate potential outcomes before committing resources.</li><li><strong>Recklessness is not entrepreneurship.</strong> Taking a huge risk without understanding consequences is not automatically entrepreneurial.</li><li><strong>Experiments reduce uncertainty.</strong> Small tests can generate information before larger commitments are made.</li><li><strong>Entrepreneurs need uncertainty tolerance.</strong> They must be able to act even when complete information is unavailable.</li><li><strong>Good entrepreneurs manage risk rather than pretending risk does not exist.</strong></li></ul>
<h2>Lesson Challenge</h2>
<p>Choose a small entrepreneurial idea in your community and write a one-page decision brief that identifies the main risk, the most important uncertainty, and the smallest experiment you could run.</p>
<h2>Textbook Connection</h2>
<p><strong>OpenLearn Entrepreneurship.</strong> This lesson builds a practical link between uncertainty, risk, decision-making, and entrepreneurial learning.</p>
<p><strong>Supplementary reference:</strong> ''' + source_title + '''. The reference supports further reading; this lesson uses original explanations, examples, activities, and comparisons.</p>'''

def format_creativity_problem_framing_lesson(textbook_lens, source_title):
    return '''<h1>Creativity, Innovation, and Problem Framing</h1>
<p><strong>Estimated lesson time:</strong> 10-15 minutes<br><strong>Level:</strong> Beginner<br><strong>Module:</strong> 3 - Creativity and Innovation</p>
<h2>Learning Objectives</h2>
<p>By the end of this lesson, you will be able to:</p>
<ul><li>Define creativity and innovation.</li><li>Explain the difference between creativity and innovation.</li><li>Understand why creativity matters in entrepreneurship.</li><li>Distinguish between a problem, symptom, and root cause.</li><li>Explain the meaning of problem framing.</li><li>Reframe problems to discover better entrepreneurial opportunities.</li><li>Apply creative thinking to real-world problems.</li></ul>
<hr>
<h2>Introduction</h2>
<p>Entrepreneurship begins with the creation of value. But before creating value, entrepreneurs need to identify what value is actually needed. This requires creativity. Creativity allows entrepreneurs to generate new ideas, see opportunities others may overlook, connect existing ideas in new ways, find alternative solutions, and approach problems from different perspectives. However, creativity alone is not enough. A person can have hundreds of ideas without creating anything valuable. Entrepreneurship requires moving from ideas → useful solutions → value creation.</p>
<aside class="learning-callout"><strong>Key idea</strong><p>Creativity generates possibilities; innovation turns a useful possibility into a solution that creates real value.</p></aside>
<h2>1. What Is Creativity?</h2>
<p><strong>Creativity</strong> is the ability to generate ideas, possibilities, or approaches that are both novel and potentially useful. Creativity can involve creating something new, combining existing things differently, improving an existing idea, or looking at a familiar problem from a new perspective.</p>
<p>Example: A traditional grocery store sells products from shelves. An entrepreneur asks, “What if customers could order their weekly groceries automatically based on their previous purchases?” The underlying products have not changed. The entrepreneur has changed the way the problem is approached.</p>
<h2>2. What Is Innovation?</h2>
<p><strong>Innovation</strong> is the process of turning ideas into useful solutions that create value. A simple distinction is: creativity generates possibilities; innovation turns valuable possibilities into reality.</p>
<p><strong>Creativity:</strong> “What could we do differently?” <br><strong>Innovation:</strong> “How can we turn this useful idea into something people will actually use?”</p>
<h2>3. Creativity vs. Innovation</h2>
<table><thead><tr><th>Creativity</th><th>Innovation</th></tr></thead><tbody>
<tr><td>Generates ideas.</td><td>Implements useful ideas.</td></tr>
<tr><td>Focuses on possibilities.</td><td>Focuses on application.</td></tr>
<tr><td>Can happen individually.</td><td>Often involves implementation and execution.</td></tr>
<tr><td>Produces concepts.</td><td>Produces products, services, processes, or models.</td></tr>
<tr><td>Asks: “What if?”</td><td>Asks: “How can we make it work?”</td></tr>
</tbody></table>
<p>Not every creative idea becomes an innovation. An idea becomes more meaningful when it is implemented and creates value.</p>
<h2>4. What Does “Value” Mean?</h2>
<p>Innovation is not valuable simply because it is new. A solution creates value when it meaningfully improves something for its users, customers, organizations, communities, or other stakeholders. Value may include saving time, reducing cost, increasing convenience, improving quality, reducing risk, increasing accessibility, solving a frustrating problem, or creating a better experience.</p>
<p>A new payment application may not be valuable just because it is technologically advanced. It becomes valuable if it makes payments faster, easier, safer, and more accessible for its intended users.</p>
<h2>5. What Is Problem Framing?</h2>
<p><strong>Problem framing</strong> means defining a problem in a way that helps us understand what really needs to be solved. How you frame a problem influences the solutions you consider. Consider the statement: “We need a faster bus.” This assumes the solution is a bus. A better problem frame might be: “How might we help students reach campus more quickly and reliably?” Now many solutions become possible: better bus scheduling, ride-sharing, bicycle services, shuttle services, digital route planning, and flexible transportation.</p>
<aside class="learning-callout"><strong>Key idea</strong><p>Do not define the solution before you understand the problem.</p></aside>
<h2>6. Problem vs. Symptom</h2>
<p>Entrepreneurs need to distinguish between a symptom and the underlying problem. For example, a restaurant notices that customers are leaving because the waiting time is too long. This is an observed problem. But why is waiting time long? Possible causes include slow ordering, poor kitchen layout, too few employees, poor inventory management, a complicated menu, or an inefficient payment process. If the entrepreneur simply hires more workers, they may treat the symptom without solving the underlying cause.</p>
<h2>7. Finding the Root Problem</h2>
<p>A useful technique is the <strong>5 Whys</strong>. Ask “Why?” repeatedly until you reach a deeper cause. Example: Problem — Students arrive late to class. Why? Because transportation takes too long. Why? Because buses are overcrowded. Why? Because many students travel at the same time. Why? Because class schedules are concentrated around the same period. Why? Because the timetable creates overlapping demand. The original problem “Students need faster buses” may actually be connected to a broader scheduling problem.</p>
<h2>8. Reframing a Problem</h2>
<p>Problem framing can transform the question. A weak frame is “How can we sell more bottled water?” A better frame is “How might we make drinking water more convenient and accessible?” This can lead to water refill stations, delivery services, reusable containers, smart water dispensers, and subscription services.</p>
<h2>9. How-Might-We Questions</h2>
<p>One useful way to frame entrepreneurial problems is the “How might we...?” question. It creates an open space for solutions. Example: Instead of “Customers don’t like waiting,” ask “How might we reduce customer waiting time?” Instead of “Students cannot afford textbooks,” ask “How might we make learning materials more affordable?” Instead of “Farmers cannot reach customers,” ask “How might we connect farmers with reliable markets?”</p>
<h2>10. Creative Thinking Techniques</h2>
<p>Entrepreneurs can stimulate creativity by combining, adding, removing, reversing, changing the target user, and changing the context. These acts open unexpected pathways toward improvement and new opportunity.</p>
<h2>11. Local Problem Example</h2>
<p>Imagine small farmers struggle to sell fresh vegetables before they spoil. A narrow frame would be “Farmers need more trucks.” A broader frame is “How might we reduce food loss and help farmers reach buyers quickly?” Possible ideas include shared transportation, local collection centers, cold storage, digital marketplaces, processing businesses, and scheduled delivery services. One problem can produce many entrepreneurial possibilities when framed differently.</p>
<h2>Key Takeaways</h2>
<ul><li><strong>Creativity</strong> generates new and useful possibilities.</li><li><strong>Innovation</strong> turns valuable ideas into practical solutions.</li><li>Newness alone does not make something valuable.</li><li>Entrepreneurs should understand the problem before deciding on a solution.</li><li>A symptom is not always the root problem.</li><li>Problem framing determines which solutions we consider.</li><li>“How might we...?” questions encourage broader thinking.</li><li>Good problem framing can reveal entrepreneurial opportunities.</li></ul>
<h2>Lesson Challenge</h2>
<p>Take one local problem and rewrite it in a better problem frame using a “How might we...?” question. Then list three possible solution directions.</p>
<h2>Textbook Connection</h2>
<p><strong>IDEO Design Thinking.</strong> This lesson uses the problem-framing and opportunity-creation lens of creative entrepreneurial learning and situates it within the design-thinking sequence.</p>
<p><strong>Supplementary reference:</strong> ''' + source_title + '''. The reference supports further reading; this lesson uses original explanations, examples, activities, and comparisons.</p>'''

def format_design_thinking_empathy_lesson(textbook_lens, source_title):
    return '''<h1>Design Thinking and User Empathy</h1>
<p><strong>Estimated lesson time:</strong> 10-15 minutes<br><strong>Level:</strong> Beginner<br><strong>Module:</strong> 3 - Creativity and Innovation</p>
<h2>Learning Objectives</h2>
<p>By the end of this lesson, you will be able to:</p>
<ul><li>Define design thinking.</li><li>Explain the role of empathy in entrepreneurship.</li><li>Understand the major stages of the design-thinking process.</li><li>Identify user needs and pain points.</li><li>Distinguish between what users say, do, think, and feel.</li><li>Develop user-centered solutions.</li><li>Apply design thinking to an entrepreneurial problem.</li></ul>
<hr>
<h2>Introduction</h2>
<p><strong>Design thinking</strong> is a human-centered approach to solving problems by deeply understanding users, defining their needs, generating ideas, creating prototypes, and testing solutions. It is especially useful when the problem is complex, user needs are unclear, existing solutions are unsatisfactory, or there is significant uncertainty about what users want. A simplified process is: <strong>Empathize → Define → Ideate → Prototype → Test</strong>. This process is not always perfectly linear. Entrepreneurs may move backward and forward between stages as they learn.</p>
<aside class="learning-callout"><strong>Key idea</strong><p>Design thinking starts with the user’s reality instead of the entrepreneur’s assumptions.</p></aside>
<h2>1. What Is User Empathy?</h2>
<p><strong>User empathy</strong> means trying to understand a user's situation, needs, frustrations, motivations, emotions, and experiences from the user's perspective. Instead of asking only, “What product can I sell?” an entrepreneur asks, “What is this person actually experiencing?”</p>
<h2>2. Why Empathy Matters</h2>
<p>Entrepreneurs can easily make assumptions about customers. For example, “Students need an expensive learning app because technology is popular.” But students might actually say, “I don't need another app. I need simple explanations that work with limited internet access.” The entrepreneur’s assumption and the user’s actual need may be completely different. Empathy helps reduce this gap.</p>
<h2>3. The Four Perspectives of User Understanding</h2>
<p>When studying users, ask what they say, what they do, what they think, and what they feel. These four perspectives can reveal needs that a simple survey question may miss.</p>
<h2>4. User Pain Points</h2>
<p>A <strong>pain point</strong> is a specific problem, frustration, difficulty, or inconvenience experienced by a user. Examples include long waiting times, high prices, complicated procedures, lack of information, poor customer service, difficult access, unreliable delivery, or confusing technology. Entrepreneurial opportunities often exist where pain points are significant and existing solutions are inadequate.</p>
<h2>5. Stage 1 — Empathize</h2>
<p>The first stage is to understand the people experiencing the problem. Useful methods include interviews, observation, surveys, user diaries, and experience testing.</p>
<h2>6. Don’t Ask Only What Users Want</h2>
<p>Users may not always be able to describe the best solution. If you ask, “What new feature should we add to the app?” a user may suggest a feature. But if you ask, “Tell me about the last time you had difficulty using the app,” you may discover the real problem. Study behavior and experience—not just opinions.</p>
<h2>7. Stage 2 — Define</h2>
<p>After collecting information, identify the central problem. A useful format is: “[User] needs [need] because [insight].” Example: “College students need affordable and reliable access to learning materials because high textbook costs prevent them from obtaining required resources.” This is more useful than simply saying, “Textbooks are expensive.”</p>
<h2>8. Stage 3 — Ideate</h2>
<p>Once the problem is clearly defined, generate possible solutions. At this stage, avoid judging ideas too quickly. The goal is to create a range of possibilities using brainstorming, mind mapping, SCAMPER, reverse thinking, analogy, and combining existing solutions.</p>
<h2>9. Stage 4 — Prototype</h2>
<p>A <strong>prototype</strong> is an early, simplified version of a product, service, or solution used to learn and test. A prototype does not need to be perfect. It could be a paper sketch, a clickable screen design, a basic website, a sample product, a storyboard, a mock-up, or a manual version of a digital service. The principle is: build enough to learn, not enough to impress.</p>
<h2>10. Stage 5 — Test</h2>
<p>Give the prototype to real or representative users. Observe what works, what confuses them, what they like, what they ignore, what problems appear, and what should change. Then improve the solution. This creates a cycle: prototype → test → feedback → improve → test again.</p>
<h2>11. Design Thinking Is Iterative</h2>
<p>Design thinking is not plan once → build once → launch. Instead, it is understand → define → create → test → learn → improve. You may discover during testing that the original problem was misunderstood. That is not necessarily failure. It is learning.</p>
<h2>12. Mini Case Study: Student Food Service</h2>
<p>Imagine students complain that campus food is expensive. An entrepreneur assumes students need cheaper food. Empathy research reveals that students are also concerned about long queues, limited choices, inconsistent quality, and lack of information about menus. A better problem definition is: “How might we help students access affordable meals quickly and conveniently?” Possible solutions include pre-ordering, meal subscriptions, student meal bundles, multiple pickup points, and digital menus. The final solution is better because it is based on user experience rather than assumptions.</p>
<h2>13. Empathy vs. Sympathy</h2>
<p>Sympathy means I feel sorry for this person. Empathy means I am trying to understand what this person is experiencing and why. Entrepreneurial empathy focuses on understanding the user’s reality so that better solutions can be created.</p>
<h2>14. Applying Design Thinking in Ethiopia and Africa</h2>
<p>Design thinking is particularly useful when solutions must fit local conditions. An entrepreneur developing a digital service should understand internet availability, device access, language, payment methods, digital literacy, customer habits, and cost sensitivity. A solution that works perfectly in one market may fail elsewhere because the user context is different.</p>
<h2>Key Takeaways</h2>
<ul><li><strong>Design thinking</strong> is a human-centered approach to problem solving.</li><li><strong>Empathy</strong> means understanding users’ experiences rather than relying only on assumptions.</li><li>The common stages are <strong>Empathize → Define → Ideate → Prototype → Test.</strong></li><li>User interviews and observation can reveal hidden needs.</li><li>Prototypes help entrepreneurs learn before making large investments.</li><li>Testing should produce feedback that improves the solution.</li><li>Design thinking is iterative, not strictly linear.</li><li>The best solution is not necessarily the most technologically advanced; it is the one that effectively addresses a real user need.</li></ul>
<h2>Lesson Challenge</h2>
<p>Choose a problem in your community and write a design-thinking brief that includes an empathy insight, a problem definition, a prototype idea, and a user test question.</p>
<h2>Textbook Connection</h2>
<p><strong>IDEO Design Thinking.</strong> This lesson uses the design-thinking framework to connect empathy, user research, prototyping, and iterative testing to entrepreneurship.</p>
<p><strong>Supplementary reference:</strong> ''' + source_title + '''. The reference supports further reading; this lesson uses original explanations, examples, activities, and comparisons.</p>'''

def format_scamper_frugal_disruptive_lesson(textbook_lens, source_title):
    return '''<h1>SCAMPER, Frugal, and Disruptive Innovation</h1>
<p><strong>Estimated lesson time:</strong> 10-15 minutes<br><strong>Level:</strong> Beginner<br><strong>Module:</strong> 3 - Creativity and Innovation</p>
<h2>Learning Objectives</h2>
<p>By the end of this lesson, you should be able to:</p>
<ul>
<li>Explain the SCAMPER creativity technique.</li>
<li>Apply each element of SCAMPER to a product or service.</li>
<li>Define frugal innovation.</li>
<li>Explain why frugal innovation is important in resource-constrained environments.</li>
<li>Define disruptive innovation.</li>
<li>Distinguish disruptive innovation from ordinary improvement.</li>
<li>Compare SCAMPER, frugal innovation, and disruptive innovation.</li>
<li>Apply these concepts to entrepreneurial opportunities.</li>
</ul>
<hr>
<h2>1. From Problems to New Ideas</h2>
<p>Once an entrepreneur understands a problem and the user's needs, the next question is:</p>
<blockquote><strong>“What possible solutions can we create?”</strong></blockquote>
<p>There are many ways to generate ideas.</p>
<p>This lesson introduces three important concepts:</p>
<p><strong>SCAMPER</strong> — A structured technique for generating and improving ideas.</p>
<p><strong>Frugal Innovation</strong> — Creating useful solutions with limited resources and a strong focus on affordability and simplicity.</p>
<p><strong>Disruptive Innovation</strong> — A specific pattern in which a new approach can transform established markets, often by initially serving overlooked or less demanding customers before moving into the mainstream.</p>
<hr>
<h2>2. What Is SCAMPER?</h2>
<p><strong>SCAMPER</strong> is a creativity technique that uses seven types of questions to modify an existing product, service, or process.</p>
<ul>
<li><strong>S — Substitute</strong></li>
<li><strong>C — Combine</strong></li>
<li><strong>A — Adapt</strong></li>
<li><strong>M — Modify</strong></li>
<li><strong>P — Put to another use</strong></li>
<li><strong>E — Eliminate</strong></li>
<li><strong>R — Reverse / Rearrange</strong></li>
</ul>
<p>SCAMPER is useful because entrepreneurs do not always need to invent something from zero. Sometimes the opportunity is hidden in an existing solution that can be <strong>changed, combined, simplified, or repurposed</strong>.</p>
<hr>
<h2>3. S — Substitute</h2>
<p>Ask:</p>
<blockquote><strong>“What can we replace?”</strong></blockquote>
<p>Possible elements to substitute:</p>
<ul><li>Materials</li><li>People</li><li>Processes</li><li>Technology</li><li>Ingredients</li><li>Distribution methods</li></ul>
<p><strong>Example:</strong> A restaurant uses plastic containers. The question is: <strong>“Can we substitute the packaging with reusable or biodegradable alternatives?”</strong> The product remains similar, but an important component changes.</p>
<hr>
<h2>4. C — Combine</h2>
<p>Ask:</p>
<blockquote><strong>“What can we combine?”</strong></blockquote>
<p>Combine:</p>
<ul><li>Products</li><li>Services</li><li>Features</li><li>Technologies</li><li>Distribution channels</li></ul>
<p><strong>Example:</strong> A café combines <strong>Coffee + Study space + High-speed internet</strong>. The result is a café designed for students and remote workers.</p>
<hr>
<h2>5. A — Adapt</h2>
<p>Ask:</p>
<blockquote><strong>“What can we adapt from somewhere else?”</strong></blockquote>
<p>Look at solutions used in other industries, countries, customer groups, or contexts.</p>
<p><strong>Example:</strong> An entrepreneur adapts the subscription model used in streaming services to meal delivery. Instead of paying for every meal separately, the customer moves to a <strong>Monthly subscription → Regular meals</strong> relationship.</p>
<hr>
<h2>6. M — Modify</h2>
<p>Ask:</p>
<blockquote><strong>“What can we change, enlarge, reduce, or redesign?”</strong></blockquote>
<p>You could modify:</p>
<ul><li>Size</li><li>Shape</li><li>Speed</li><li>Design</li><li>Features</li><li>Packaging</li><li>Customer experience</li></ul>
<p><strong>Example:</strong> A large training program is redesigned into short, mobile-friendly lessons. The core educational purpose remains, but the <strong>format and experience</strong> are modified.</p>
<hr>
<h2>7. P — Put to Another Use</h2>
<p>Ask:</p>
<blockquote><strong>“Can this be used for a different purpose?”</strong></blockquote>
<p>An existing product or resource may have another valuable use.</p>
<p><strong>Example:</strong> Agricultural waste that is normally discarded could be used as a raw material for compost, animal feed, bio-based products, or packaging materials. The entrepreneurial opportunity comes from seeing <strong>value where others see waste</strong>.</p>
<hr>
<h2>8. E — Eliminate</h2>
<p>Ask:</p>
<blockquote><strong>“What can we remove?”</strong></blockquote>
<p>Eliminate unnecessary steps, features, costs, delays, complexity, and packaging.</p>
<p><strong>Example:</strong> An online service requires customers to complete eight steps to place an order. An entrepreneur asks, <strong>“Can we reduce this to three steps?”</strong> Simplification itself can become an innovation.</p>
<hr>
<h2>9. R — Reverse or Rearrange</h2>
<p>Ask:</p>
<blockquote><strong>“What happens if we change the order or reverse the process?”</strong></blockquote>
<p><strong>Example:</strong> Traditional model: <strong>Customer visits store → Selects product → Pays → Takes product home.</strong> Alternative: <strong>Customer orders online → Pays → Product is prepared → Customer collects.</strong> The sequence has been rearranged.</p>
<hr>
<h2>10. Complete SCAMPER Example</h2>
<p>Imagine an entrepreneur wants to improve a <strong>college cafeteria</strong>.</p>
<table>
<thead><tr><th>SCAMPER Question</th><th>Possible Idea</th></tr></thead>
<tbody>
<tr><td><strong>Substitute</strong></td><td>Replace paper menus with digital menus.</td></tr>
<tr><td><strong>Combine</strong></td><td>Food ordering + payment.</td></tr>
<tr><td><strong>Adapt</strong></td><td>Adapt online food-delivery tracking.</td></tr>
<tr><td><strong>Modify</strong></td><td>Create smaller affordable meal portions.</td></tr>
<tr><td><strong>Put to another use</strong></td><td>Use cafeteria space for evening study.</td></tr>
<tr><td><strong>Eliminate</strong></td><td>Remove unnecessary ordering steps.</td></tr>
<tr><td><strong>Reverse</strong></td><td>Pre-order before arriving.</td></tr>
</tbody>
</table>
<p><strong>Result:</strong> One ordinary problem produces <strong>multiple innovation possibilities</strong>.</p>
<hr>
<h2>11. What Is Frugal Innovation?</h2>
<p><strong>Frugal innovation</strong> involves creating solutions that deliver meaningful value while using <strong>fewer resources, lower costs, and simpler approaches</strong>.</p>
<p>It is particularly relevant where:</p>
<ul><li>Customers have limited purchasing power.</li><li>Resources are constrained.</li><li>Infrastructure may be limited.</li><li>Simplicity is valuable.</li><li>Affordability is important.</li></ul>
<p>Frugal innovation is not simply <strong>“Make something cheap.”</strong> It is about finding a way to provide <strong>essential value efficiently and affordably</strong>.</p>
<hr>
<h2>12. Principles of Frugal Innovation</h2>
<p>Frugal solutions often emphasize:</p>
<ul>
<li><strong>Affordability</strong> — Keep the solution accessible to the target users.</li>
<li><strong>Simplicity</strong> — Remove unnecessary complexity.</li>
<li><strong>Resource efficiency</strong> — Use fewer materials, energy, time, or other resources.</li>
<li><strong>Focus</strong> — Concentrate on the most important customer need.</li>
<li><strong>Flexibility</strong> — Design solutions that can work in constrained environments.</li>
</ul>
<hr>
<h2>13. Example of Frugal Innovation</h2>
<p>Imagine a community needs an affordable way to transport small quantities of agricultural products. A highly sophisticated automated transportation system may be too expensive. A frugal entrepreneur might instead develop:</p>
<p><strong>Shared transport + simple scheduling + mobile communication.</strong></p>
<p>The solution may not use the most advanced technology. But if it solves the customer's problem at an affordable cost, it can create significant value.</p>
<aside class="learning-callout"><strong>Frugal does not mean inferior.</strong><p>A frugal solution can be high-quality while being deliberately simple, affordable, and resource-efficient.</p></aside>
<hr>
<h2>14. Why Frugal Innovation Matters in Africa</h2>
<p>Many African markets contain customers who are highly sensitive to:</p>
<ul><li>Price</li><li>Reliability</li><li>Accessibility</li><li>Availability</li><li>Ease of use</li></ul>
<p>Entrepreneurs therefore often need to ask:</p>
<blockquote><strong>“What is the simplest solution that delivers the value customers actually need?”</strong></blockquote>
<p>This can create opportunities in healthcare, education, agriculture, energy, transportation, financial services, manufacturing, housing, water and sanitation.</p>
<hr>
<h2>15. What Is Disruptive Innovation?</h2>
<p><strong>Disruptive innovation</strong> is a specific pattern of market change in which a new business or solution begins by serving customers who are overlooked, underserved, or unable to use existing mainstream offerings, and then potentially improves and expands into the mainstream market.</p>
<p>It is important to understand that:</p>
<blockquote><strong>Not every new or revolutionary product is “disruptive innovation.”</strong></blockquote>
<p>The term has a specific meaning.</p>
<hr>
<h2>16. How Disruption Can Occur</h2>
<p>A simplified pattern is:</p>
<p><strong>Established market → Existing companies focus on mainstream customers → Some customers are underserved or new customers cannot afford/use the existing solution → New entrant offers a simpler, more accessible alternative → The new solution improves → More customers adopt it → The market structure may change.</strong></p>
<hr>
<h2>17. Example of a Disruption Pattern</h2>
<p>Imagine a market where professional design software is expensive and complicated. A new company creates a much simpler, affordable design platform. Initially, it attracts students, small businesses, beginners, and casual users. Over time, the platform improves. Some mainstream customers begin using it as well. The new entrant may eventually change how the market operates. This illustrates the <strong>logic of a potential disruptive pathway</strong>.</p>
<hr>
<h2>18. Disruptive Innovation vs. Ordinary Innovation</h2>
<table>
<thead><tr><th>Ordinary Innovation</th><th>Disruptive Innovation</th></tr></thead>
<tbody>
<tr><td>Improves an existing offering</td><td>Can change the competitive structure of a market</td></tr>
<tr><td>May target existing customers</td><td>Often begins with overlooked or new customers</td></tr>
<tr><td>Can be incremental or major</td><td>Follows a specific market-entry pattern</td></tr>
<tr><td>Does not necessarily threaten incumbents</td><td>Can eventually challenge established firms</td></tr>
</tbody>
</table>
<p>A product can be new, advanced, expensive, and revolutionary, and still <strong>not</strong> be disruptive innovation in the technical sense.</p>
<hr>
<h2>19. Three Concepts Compared</h2>
<table>
<thead><tr><th>Concept</th><th>Main Question</th></tr></thead>
<tbody>
<tr><td><strong>SCAMPER</strong></td><td>How can I change or rethink an existing idea?</td></tr>
<tr><td><strong>Frugal Innovation</strong></td><td>How can I create valuable solutions with fewer resources and lower cost?</td></tr>
<tr><td><strong>Disruptive Innovation</strong></td><td>Can a new business model enter through overlooked customers and eventually reshape the market?</td></tr>
</tbody>
</table>
<p>These concepts solve different entrepreneurial challenges.</p>
<hr>
<h2>20. Applying the Three Concepts to Ethiopia</h2>
<p>Imagine an entrepreneur wants to improve access to educational materials.</p>
<p><strong>SCAMPER</strong> — Ask: Can physical materials be replaced with digital versions? Can learning materials and tutoring be combined? Can existing content be adapted for mobile phones? Can unnecessary features be removed?</p>
<p><strong>Frugal Innovation</strong> — Ask: <strong>“How can students access quality learning materials at very low cost and with limited internet usage?”</strong> Possible approach: <strong>Small file sizes + offline access + affordable pricing.</strong></p>
<p><strong>Disruptive Innovation</strong> — Ask: <strong>“Could a simpler and more accessible education model initially serve students who are poorly served by traditional options and eventually expand into the mainstream education market?”</strong></p>
<p>The three approaches generate different strategic possibilities.</p>
<hr>
<h2>21. Important Entrepreneurial Lesson</h2>
<p>Innovation does not always require advanced technology, large investment, a completely new invention, or a complicated product. Innovation can also come from simplicity, affordability, better user experience, new combinations, different distribution, removing unnecessary steps, and serving overlooked customers.</p>
<h2>Textbook Connection</h2>
<p><strong>IDEO Design Thinking.</strong> This lesson uses creativity, idea generation, frugal design, and the logic of disruption to connect entrepreneurial opportunity to practical innovation.</p>
<p><strong>Supplementary reference:</strong> ''' + source_title + '''. The reference supports further reading; this lesson uses original explanations, examples, activities, and comparisons.</p>'''

def format_types_lesson(textbook_lens, source_title):
    return '''<h1>Types and Purposes of Entrepreneurship</h1>
<p><strong>Estimated lesson time:</strong> 10-15 minutes<br><strong>Level:</strong> Beginner<br><strong>Module:</strong> 1 - Introduction to Entrepreneurship</p>
<h2>Learning Objectives</h2>
<p>By the end of this lesson, you will be able to:</p>
<ul><li>Explain why entrepreneurship takes different forms.</li><li>Identify more than six types of entrepreneurship.</li><li>Compare ventures by purpose, growth, ownership, innovation, sector, and founder context.</li><li>Classify a real venture without treating one category as better than another.</li><li>Explain how entrepreneurship contributes to income, employment, innovation, problem-solving, and development.</li></ul>
<hr>
<h2>Introduction</h2>
<p>Entrepreneurship is not limited to starting a company or becoming a business owner. People pursue it for different reasons, serve different groups, use innovation in different ways, and operate with different growth ambitions.</p>
<p>A person may open a small shop to support a family, build a technology platform for a large market, create an enterprise that addresses a community problem, or develop a new service inside an existing organization. All may be entrepreneurial, but their purposes, strategies, resources, and measures of success will differ.</p>
<aside class="learning-callout"><strong>Key idea</strong><p>Types of entrepreneurship are lenses for understanding a venture. They are not a ranking of entrepreneurs, and one venture can fit several types at the same time.</p></aside>
<h2>1. How to Classify Entrepreneurship</h2>
<p>Ask six questions before assigning a label:</p>
<ol><li><strong>Purpose:</strong> Is the priority income, social impact, environmental protection, or innovation?</li><li><strong>Growth:</strong> Is the venture designed for local stability or rapid expansion?</li><li><strong>Ownership:</strong> Is it owned by one person, a family, partners, investors, or an existing organization?</li><li><strong>Innovation:</strong> Is it creating, improving, adapting, or imitating a solution?</li><li><strong>Sector:</strong> Does it operate in agriculture, manufacturing, trade, services, technology, or another field?</li><li><strong>Context:</strong> Is it rural, digital, youth-led, women-led, necessity-driven, or opportunity-driven?</li></ol>
<h2>2. Main Types by Purpose and Growth</h2>
<h3>Small-Business Entrepreneurship</h3>
<p><strong>Simple definition:</strong> Creating and operating a relatively small venture for a local or specific market.</p>
<p><strong>Explanation:</strong> The goal is often reliable income, family support, employment, customer service, and sustainable profit. Rapid expansion is not required.</p>
<p><strong>Example:</strong> A neighborhood bakery in Addis Ababa produces fresh bread and cakes for nearby customers and employs several people.</p>
<p><strong>Why it matters:</strong> Small businesses provide livelihoods and local services. A business does not need to become a multinational company to be entrepreneurial.</p>
<h3>Scalable Startup Entrepreneurship</h3>
<p><strong>Simple definition:</strong> Building a repeatable model designed to serve a large market and grow rapidly.</p>
<p><strong>Explanation:</strong> Scalable ventures often use technology, standardized processes, partnerships, or innovative models so that customers can increase faster than costs.</p>
<p><strong>Example:</strong> An online tutoring platform is designed to connect students and teachers across Ethiopia and later other countries.</p>
<p><strong>Why it matters:</strong> Scaling requires different skills, funding, systems, and risk management from operating one stable local business.</p>
<h3>Lifestyle Entrepreneurship</h3>
<p><strong>Simple definition:</strong> Building a venture around independence, personal interests, flexibility, and a sustainable owner income.</p>
<p><strong>Example:</strong> A skilled photographer creates a small studio and training service that supports a preferred lifestyle without pursuing maximum scale.</p>
<p><strong>Why it matters:</strong> Entrepreneurial success is not defined only by company size or investment valuation.</p>
<h3>Social Entrepreneurship</h3>
<p><strong>Simple definition:</strong> Using entrepreneurial methods to address a social, community, or environmental problem.</p>
<p><strong>Example:</strong> An enterprise sells affordable solar lights to communities with unreliable electricity while earning revenue to continue operating.</p>
<p><strong>Why it matters:</strong> Social value and financial sustainability can support one another. A mission cannot continue serving people if the operation cannot survive.</p>
<h3>Sustainable or Green Entrepreneurship</h3>
<p><strong>Simple definition:</strong> Creating economic value while reducing environmental harm or protecting natural systems and communities.</p>
<p><strong>Example:</strong> A venture produces biodegradable packaging for local food sellers and measures both sales and plastic waste reduced.</p>
<p><strong>Why it matters:</strong> Environmental problems can create opportunities for cleaner energy, recycling, water efficiency, transport, and responsible production.</p>
<h2>3. Types by Motivation, Ownership, and Innovation</h2>
<table><thead><tr><th>Type</th><th>Main focus</th><th>Typical example</th></tr></thead><tbody>
<tr><td><strong>Necessity entrepreneurship</strong></td><td>Creating income when formal employment or secure income is limited.</td><td>A person starts food vending after losing a job.</td></tr>
<tr><td><strong>Opportunity entrepreneurship</strong></td><td>Choosing to pursue a perceived market gap or new possibility.</td><td>A founder notices demand for affordable school transport.</td></tr>
<tr><td><strong>Innovative entrepreneurship</strong></td><td>Introducing a new product, process, service, market, or business model.</td><td>A grocery store adds reliable phone ordering and delivery.</td></tr>
<tr><td><strong>Imitative entrepreneurship</strong></td><td>Adapting an existing model to a new segment, location, price, language, or channel.</td><td>Adapting a proven service for rural customers while respecting intellectual property.</td></tr>
<tr><td><strong>Family entrepreneurship</strong></td><td>Using family ownership, labor, trust, and succession arrangements.</td><td>A textile business passed from grandparents to children.</td></tr>
<tr><td><strong>Corporate entrepreneurship / intrapreneurship</strong></td><td>Creating new products, services, or ventures inside an established organization.</td><td>A bank employee develops a faster mobile-payment service.</td></tr>
<tr><td><strong>Serial entrepreneurship</strong></td><td>Creating or leading multiple ventures over time.</td><td>A founder starts, exits, or hands over one venture and begins another.</td></tr>
<tr><td><strong>Portfolio entrepreneurship</strong></td><td>Operating several ventures at the same time.</td><td>An owner manages a farm input business, transport service, and training center.</td></tr>
</tbody></table>
<h2>4. Types by Sector and Context</h2>
<ul><li><strong>Technology entrepreneurship:</strong> technical knowledge or digital systems are central resources.</li><li><strong>Digital entrepreneurship:</strong> online platforms, software, digital marketing, or electronic channels are central to delivery.</li><li><strong>Rural entrepreneurship:</strong> the venture builds around agricultural, natural-resource, or dispersed rural-market opportunities.</li><li><strong>Manufacturing entrepreneurship:</strong> the venture transforms materials or components into products.</li><li><strong>Trading entrepreneurship:</strong> the venture purchases and resells goods, creating value through access, assortment, timing, or distribution.</li><li><strong>Service entrepreneurship:</strong> the venture sells expertise, care, access, convenience, or an experience.</li><li><strong>Women’s entrepreneurship:</strong> the venture is women-led or women-owned; analysis should include access to finance, networks, care responsibilities, safety, and markets without assuming lower capability.</li><li><strong>Youth entrepreneurship:</strong> the venture is youth-led; analysis should include experience, credibility, finance, mentorship, and market access.</li></ul>
<aside class="learning-callout"><strong>Important distinction</strong><p>Women’s and youth entrepreneurship describe founder context, not a separate level of ability. Rural, digital, technology, manufacturing, trading, and service entrepreneurship describe operating context or sector. These dimensions can overlap.</p></aside>
<h2>5. Purposes of Entrepreneurship</h2>
<table><thead><tr><th>Purpose</th><th>How entrepreneurship contributes</th></tr></thead><tbody>
<tr><td><strong>Income and wealth creation</strong></td><td>Converts an idea and resources into revenue, profit, owner income, and sometimes long-term wealth.</td></tr>
<tr><td><strong>Employment creation</strong></td><td>Creates direct jobs and indirect opportunities for suppliers, distributors, freelancers, and service providers.</td></tr>
<tr><td><strong>Innovation</strong></td><td>Improves products, services, processes, technologies, customer experiences, and business models.</td></tr>
<tr><td><strong>Problem solving</strong></td><td>Responds to unmet needs and repeated difficulties in communities, markets, schools, workplaces, and households.</td></tr>
<tr><td><strong>Social and community development</strong></td><td>Expands access to education, health, finance, housing, clean energy, water, and other important services.</td></tr>
<tr><td><strong>Economic development</strong></td><td>Builds businesses, markets, investment, skills, tax activity, productivity, and local economic connections.</td></tr>
<tr><td><strong>Environmental sustainability</strong></td><td>Creates solutions that reduce waste, pollution, resource use, and environmental risk.</td></tr>
</tbody></table>
<h2>6. One Venture Can Have Several Identities</h2>
<p>Imagine an Ethiopian agritech that helps smallholder farmers access crop information and buyers. It may be classified as:</p>
<ul><li><strong>Technology entrepreneurship</strong> because it uses a digital platform.</li><li><strong>Rural entrepreneurship</strong> because it serves rural producers.</li><li><strong>Social entrepreneurship</strong> if improving farmer income is central to its mission.</li><li><strong>Opportunity entrepreneurship</strong> if the founder chooses to pursue a recognized market gap.</li><li><strong>Scalable entrepreneurship</strong> if the model is designed to expand across regions.</li><li><strong>Innovative entrepreneurship</strong> if it introduces a new way to connect farmers and buyers.</li></ul>
<p>No single label tells the whole story. The useful classification depends on the question being asked.</p>
<h2>Think About It</h2>
<blockquote>Is a woman selling vegetables at a roadside stall an entrepreneur? Use at least two classifications and explain what additional information you would need.</blockquote>
<h2>Common Beginner Mistakes</h2>
<ul><li><strong>Assuming only technology companies are entrepreneurial:</strong> innovation can occur in agriculture, trade, manufacturing, education, services, and community work.</li><li><strong>Believing rapid growth is always the goal:</strong> a stable, profitable local business can be the correct choice for its owner and customers.</li><li><strong>Treating necessity entrepreneurs as less legitimate:</strong> necessity and opportunity describe motivation, not dignity or potential.</li><li><strong>Forcing a venture into one category:</strong> use several lenses when they clarify different aspects of the venture.</li><li><strong>Confusing imitation with copying illegally:</strong> adapting a model is different from using protected names, designs, content, or technology without permission.</li></ul>
<h2>Practical Application</h2>
<ol><li>Select six real Ethiopian ventures from your community, online research, or personal experience.</li><li>For each venture, record its purpose, growth ambition, ownership, innovation approach, sector, and founder context.</li><li>Classify each venture using at least four types.</li><li>Write one benefit and one limitation of each classification.</li><li>Choose one venture and explain which purpose best describes its current priorities.</li></ol>
<h2>Knowledge Check</h2>
<ol><li>Which type primarily serves a defined local market and seeks sustainable operation rather than rapid scale?</li><li>What is the main difference between necessity and opportunity entrepreneurship?</li><li>True or false: social entrepreneurship cannot earn revenue.</li><li>Which type occurs inside an existing organization?</li><li>Can one venture be both rural entrepreneurship and technology entrepreneurship? Explain briefly.</li></ol>
<h3>Answers and Explanations</h3>
<ol><li><strong>Small-business entrepreneurship.</strong> It commonly serves a local or specific market and aims for sustainable income and service.</li><li><strong>Motivation.</strong> Necessity entrepreneurship responds to limited income alternatives, while opportunity entrepreneurship pursues a perceived possibility by choice; the two can overlap over time.</li><li><strong>False.</strong> A social enterprise may earn revenue. Financial sustainability helps it continue creating social value.</li><li><strong>Corporate entrepreneurship or intrapreneurship.</strong> Employees create or improve products, services, processes, or ventures within an established organization.</li><li><strong>Yes.</strong> A rural venture can use technology as a core resource while serving rural customers or producers.</li></ol>
<h2>Key Takeaways</h2>
<ul><li><strong>Small-business entrepreneurship</strong> can be locally focused and highly valuable without rapid expansion.</li><li><strong>Scalable entrepreneurship</strong> searches for repeatable growth across a large market.</li><li><strong>Social and green entrepreneurship</strong> combine enterprise with social or environmental value.</li><li><strong>Necessity and opportunity</strong> describe why a person starts; they do not describe ability.</li><li><strong>Intrapreneurship</strong> is entrepreneurial action inside an existing organization.</li><li><strong>Sector and context labels</strong> include technology, digital, rural, manufacturing, trading, service, women’s, youth, family, serial, and portfolio entrepreneurship.</li><li>One venture may fit several types, so classify it according to the decision being made.</li></ul>
<h2>Lesson Challenge</h2>
<p>Find one entrepreneur in your community and ask: What is the main purpose of the venture? Who owns it? How does it create value? How much growth does the owner want? What makes the venture innovative, if anything? Classify it in a short paragraph using at least four types.</p>
<h2>Textbook Connection</h2>
<p><strong>Robert D. Hisrich, Michael P. Peters, and Dean A. Shepherd, <em>Entrepreneurship</em>, 10th edition.</strong> This lesson connects with the entrepreneurial perspective, corporate entrepreneurship, new-entry strategies, sustainable entrepreneurship, innovation, opportunity recognition, and the different purposes and contexts of new ventures. It also connects with the broader course references on entrepreneurship development, small business, women’s entrepreneurship, and resource strategy.</p>
<p><strong>Supplementary reference:</strong> ''' + source_title + '''. The reference supports further reading; this lesson uses original explanations, examples, activities, and comparisons.</p>'''


def format_ethiopia_africa_lesson(textbook_lens, source_title):
    return '''<h1>Entrepreneurship in Ethiopia and Africa</h1>
<p><strong>Estimated lesson time:</strong> 10-15 minutes<br><strong>Level:</strong> Beginner<br><strong>Module:</strong> 1 - Introduction to Entrepreneurship</p>
<h2>Learning Objectives</h2>
<p>By the end of this lesson, you will be able to:</p>
<ul><li>Explain why entrepreneurship matters for Ethiopia and Africa.</li><li>Identify opportunities in agriculture, digital services, manufacturing, trade, logistics, and social enterprise.</li><li>Describe common constraints involving finance, infrastructure, skills, regulation, markets, and uncertainty.</li><li>Explain how innovation can be simple, affordable, and adapted to local conditions.</li><li>Connect entrepreneurship with employment, economic development, and social transformation.</li></ul>
<hr>
<h2>Introduction: A Problem Can Also Be an Opportunity</h2>
<p>African economies are changing through population growth, urbanization, expanding consumer markets, and increased use of digital technology. These changes create serious challenges, but they also create situations in which entrepreneurs can design useful solutions.</p>
<p>Imagine farmers who produce vegetables but cannot reliably find urban buyers. One response is to describe the situation only as a problem. An entrepreneur asks a second question: can a service connect farmers, transporters, storage providers, and buyers in a way that creates value for each participant?</p>
<aside class="learning-callout"><strong>Key idea</strong><p>Entrepreneurship links local knowledge to action: identify a problem, understand the context, create a solution, test it, learn, adapt, and deliver value responsibly.</p></aside>
<h2>1. Why Entrepreneurship Matters in Africa</h2>
<p>Entrepreneurs create value through new businesses, employment, innovative products and services, sustainable solutions, digital tools, and community development. They often work close to problems that large organizations may not notice or may be slow to address.</p>
<p>Entrepreneurship is not a substitute for public policy, infrastructure, education, or decent employment. Its contribution is strongest when individual initiative is supported by institutions, markets, finance, skills, and fair rules.</p>
<h2>2. Ethiopia’s Entrepreneurial Landscape</h2>
<p>Ethiopian entrepreneurs operate across agriculture and agribusiness, retail and trade, manufacturing, food and hospitality, information and communication technology, transport and logistics, construction, textiles and fashion, recycling, and financial or digital services.</p>
<p>Entrepreneurship is not limited to technology startups. A farmer who changes a production and marketing model, a woman who establishes a food-processing enterprise, and a young person who creates a digital service can all demonstrate entrepreneurial action. The relevant question is what value is created and for whom.</p>
<h2>3. Agriculture and Value-Chain Opportunities</h2>
<p>Agriculture creates opportunities beyond primary production. An entrepreneur can create value at multiple stages of the chain:</p>
<p><strong>Production → Collection → Processing → Packaging → Transportation → Storage → Marketing → Distribution → Consumption</strong></p>
<p>For example, a tomato venture might grow tomatoes, process them into sauce, package the product, work with retailers, and promote it through local digital channels. Value addition can improve convenience, shelf life, quality, market access, and income, but it also introduces requirements such as food safety, equipment, working capital, reliable supply, and customer research.</p>
<aside class="learning-callout"><strong>Think like a value-chain entrepreneur</strong><p>Do not ask only, “What can I produce?” Ask, “Where is value lost, delayed, wasted, or made unnecessarily expensive, and what could improve that stage?”</p></aside>
<h2>4. Digital Entrepreneurship</h2>
<p>Digital entrepreneurship uses software, online channels, mobile applications, electronic payments, marketplaces, remote services, or digital marketing to create and deliver value. A clothing business may display products online, receive orders by phone, accept digital payment, and coordinate delivery without operating a large physical store.</p>
<p>Digital tools can reduce some barriers to reach, information, and coordination, but they do not remove the need for trust, affordable access, language support, customer service, data protection, reliable connectivity, and physical fulfillment. A digital platform that cannot deliver its promised service is not valuable simply because it uses an app.</p>
<h2>5. African Innovation and Local Fit</h2>
<p>Innovation is not limited to advanced technology. A simple, affordable, reliable improvement can be highly innovative when it solves an important local problem. African entrepreneurs often design around constraints such as limited capital, unreliable electricity, transport distances, purchasing power, language diversity, informal markets, and uneven internet access.</p>
<p>A solution designed for one country cannot automatically be transferred to another. Before expanding, study local customer needs, culture, regulations, infrastructure, supply chains, payment habits, and competitive alternatives. Local adaptation is part of the entrepreneurial work, not a final translation step.</p>
<h2>6. Employment and Economic Development</h2>
<table><thead><tr><th>Contribution</th><th>How it appears</th><th>Example</th></tr></thead><tbody>
<tr><td><strong>Direct employment</strong></td><td>People work inside the venture.</td><td>A bakery hires bakers, sales workers, cleaners, and delivery staff.</td></tr>
<tr><td><strong>Indirect employment</strong></td><td>Connected suppliers and service providers gain work.</td><td>The bakery buys flour, packaging, transport, equipment, and maintenance.</td></tr>
<tr><td><strong>Income and investment</strong></td><td>Successful operations generate income and may attract reinvestment.</td><td>Revenue supports wages, suppliers, expansion, and new equipment.</td></tr>
<tr><td><strong>Innovation and productivity</strong></td><td>Better processes and products improve how resources are used.</td><td>Processing reduces spoilage and makes a crop available for longer.</td></tr>
<tr><td><strong>Market development</strong></td><td>New offerings connect previously separated customers and providers.</td><td>A service links rural producers with urban buyers.</td></tr>
</tbody></table>
<p>A simplified development pathway is <strong>business creation → employment → income → innovation → investment → wider economic activity</strong>. The pathway is not automatic: ventures must remain productive, responsible, and financially sustainable.</p>
<h2>7. Social Entrepreneurship</h2>
<p>Social entrepreneurship places a social, community, or environmental problem at the center of the venture while using entrepreneurial methods to sustain operations. Possible areas include education, healthcare, clean water, renewable energy, waste management, food security, financial inclusion, women’s economic participation, and affordable community services.</p>
<p>Consider a low-cost solar-light business for a community with unreliable electricity. It may create economic value through sales, social value through improved study or work conditions, and environmental value through cleaner energy. The founder still needs to understand affordability, maintenance, distribution, product quality, and the evidence that the claimed benefit is actually occurring.</p>
<h2>8. Challenges Entrepreneurs Face</h2>
<table><thead><tr><th>Challenge</th><th>Why it matters</th><th>Entrepreneurial response</th></tr></thead><tbody>
<tr><td><strong>Finance</strong></td><td>Equipment, inventory, staff, technology, premises, and marketing require cash.</td><td>Start with an affordable pilot, separate personal and business funds, and match funding to a clear milestone.</td></tr>
<tr><td><strong>Infrastructure</strong></td><td>Power, roads, water, logistics, telecommunications, and internet affect cost and reliability.</td><td>Design alternatives, build buffers, choose realistic service areas, and make reliability part of the value proposition.</td></tr>
<tr><td><strong>Skills and knowledge</strong></td><td>A good idea can fail through weak finance, marketing, leadership, negotiation, or customer service.</td><td>Use mentors, training, partners, records, and deliberate capability development.</td></tr>
<tr><td><strong>Regulation</strong></td><td>Registration, taxes, licenses, permits, standards, and compliance shape what is legal and feasible.</td><td>Verify current requirements with official authorities and obtain qualified advice for legal or safety issues.</td></tr>
<tr><td><strong>Market access</strong></td><td>A product creates no sustainable value if the venture cannot reach or retain customers.</td><td>Define the customer, current alternative, payment behavior, channel, and reason to switch.</td></tr>
<tr><td><strong>Economic uncertainty</strong></td><td>Prices, exchange rates, demand, supply, regulation, technology, and competition can change.</td><td>Use scenarios, staged commitments, cash records, feedback, and adaptation.</td></tr>
</tbody></table>
<h2>9. From Challenges to Opportunities</h2>
<table><thead><tr><th>Observed need</th><th>Possible opportunity</th></tr></thead><tbody>
<tr><td>Agricultural losses</td><td>Storage, processing, packaging, quality control, or distribution.</td></tr>
<tr><td>Limited market access</td><td>Digital marketplaces, aggregation, buyer networks, or market information.</td></tr>
<tr><td>Transport difficulty</td><td>Logistics coordination, route optimization, collection services, or shared transport.</td></tr>
<tr><td>Waste accumulation</td><td>Collection, recycling, repair, reuse, composting, or products made from recovered materials.</td></tr>
<tr><td>Energy access</td><td>Renewable energy, efficient appliances, maintenance, financing, or distribution.</td></tr>
<tr><td>Skills gaps</td><td>Affordable training, tutoring, apprenticeships, assessment, or remote services.</td></tr>
<tr><td>Healthcare access</td><td>Appointment coordination, health information, transport, supplies, or service partnerships.</td></tr>
<tr><td>Financial access</td><td>Responsible digital payments, bookkeeping, savings support, or financial education.</td></tr>
<tr><td>Urban growth and food demand</td><td>Food processing, delivery, housing services, maintenance, mobility, or neighborhood commerce.</td></tr>
</tbody></table>
<aside class="learning-callout"><strong>Critical test</strong><p>A widespread problem is not automatically a business opportunity. The opportunity becomes more credible when a defined group values the solution, the venture can deliver it, and the model can remain financially and ethically sustainable.</p></aside>
<h2>10. From a Local Problem to an African Opportunity</h2>
<p>Many ventures should begin locally. A founder can test a logistics service in one Ethiopian city, learn about routes and customer behavior, improve the model, and then study whether similar conditions exist elsewhere.</p>
<p><strong>Local problem → local solution → test and improve → other cities → adapted entry into other markets → possible African scale</strong></p>
<p>Africa is not one single market. Every country has different customers, languages, regulations, infrastructure, culture, purchasing power, payment systems, and business environments. Scaling across borders requires research and adaptation, not simply copying the original launch.</p>
<h2>11. The African Entrepreneurial Learning Cycle</h2>
<ol><li><strong>Observe:</strong> notice repeated problems and environmental changes.</li><li><strong>Identify:</strong> define who is affected and what they do now.</li><li><strong>Create:</strong> develop a solution suited to local resources and constraints.</li><li><strong>Test:</strong> run a small experiment with a clear measure.</li><li><strong>Learn:</strong> compare results with the original assumption.</li><li><strong>Adapt:</strong> change the offer, process, segment, or channel when evidence requires it.</li><li><strong>Scale carefully:</strong> expand only when delivery, economics, responsibility, and local fit support expansion.</li></ol>
<h2>Mini Case Study: Ethiopian Agribusiness</h2>
<p>Farmers in a rural area receive low prices because they cannot reliably reach urban buyers. An entrepreneur begins by interviewing farmers and buyers, then tests a collection and distribution service for one crop and one route. A simple digital tool coordinates orders, but the business also needs physical collection, quality standards, transport, payment, and customer support.</p>
<p>The entrepreneur creates value when farmers gain better access to buyers and buyers receive more reliable supply. The idea still requires evidence: repeat orders, delivery reliability, farmer participation, acceptable prices, spoilage rates, and enough margin to sustain the service.</p>
<h2>Think About It</h2>
<blockquote>Which challenge in your community could become an opportunity? Who experiences it, what workaround do they use, and what would you need to learn before calling it a viable opportunity?</blockquote>
<h2>Common Beginner Mistakes</h2>
<ul><li><strong>Calling every problem an opportunity:</strong> test value, reachability, feasibility, viability, and responsible delivery.</li><li><strong>Assuming technology is the solution:</strong> begin with the customer and operating context, then choose the simplest useful tool.</li><li><strong>Treating Africa as one market:</strong> investigate each country and region separately.</li><li><strong>Ignoring physical operations:</strong> digital ordering still depends on people, infrastructure, inventory, transport, trust, and support.</li><li><strong>Measuring only sales:</strong> also monitor reliability, customer outcomes, worker conditions, environmental effects, and cash flow.</li></ul>
<h2>Practical Application</h2>
<ol><li>Select one specific problem in your community.</li><li>Identify the affected group, current workaround, frequency, severity, and cost.</li><li>Map the relevant value chain or ecosystem actors.</li><li>Design one affordable solution and identify one local constraint it must respect.</li><li>Write a one-week test with a measure and a continue/change/stop rule.</li><li>State how the idea could create economic, social, or environmental value.</li></ol>
<h2>Knowledge Check</h2>
<ol><li>Name two ways agriculture creates entrepreneurial opportunities beyond production.</li><li>True or false: digital entrepreneurship removes the need for trust and reliable physical delivery.</li><li>Which challenge refers to electricity, roads, water, telecommunications, and logistics?</li><li>Why is Africa not one single market?</li><li>What should happen between identifying a local problem and expanding to another country?</li></ol>
<h3>Answers and Explanations</h3>
<ol><li><strong>Examples include collection, processing, packaging, storage, transportation, marketing, and distribution.</strong> Each can reduce waste or improve access and value.</li><li><strong>False.</strong> Digital ventures still depend on trust, connectivity, customer service, payment systems, and physical fulfillment where goods or services must move.</li><li><strong>Infrastructure.</strong> Infrastructure affects operating cost, reach, reliability, and the feasibility of the business model.</li><li><strong>Countries and regions differ in customers, languages, regulations, infrastructure, culture, purchasing power, payments, and competition.</strong></li><li><strong>Test and improve the model locally, then conduct research and adapt it to the new context.</strong> Expansion should be evidence-based rather than assumed.</li></ol>
<h2>Key Takeaways</h2>
<ul><li><strong>Entrepreneurship</strong> can connect local problems to economic and social value.</li><li><strong>Agriculture</strong> offers opportunities across the entire value chain.</li><li><strong>Digital entrepreneurship</strong> can improve reach and coordination but does not remove operational constraints.</li><li><strong>Local innovation</strong> can be simple, affordable, reliable, and highly valuable.</li><li><strong>Finance, infrastructure, skills, regulation, markets, and uncertainty</strong> shape entrepreneurial outcomes.</li><li><strong>Africa is diverse:</strong> solutions must be adapted to each market.</li><li><strong>Entrepreneurial progress</strong> follows observation, testing, learning, adaptation, and careful scaling.</li></ul>
<h2>Lesson Challenge</h2>
<p>Complete a one-page “local opportunity map.” Record one problem, affected people, current workaround, ecosystem or value-chain actors, possible solution, one constraint, one test, and the economic, social, or environmental value that could result.</p>
<h2>Textbook Connection</h2>
<p><strong>Robert D. Hisrich, Michael P. Peters, and Dean A. Shepherd, <em>Entrepreneurship</em>, 10th edition.</strong> This lesson connects to new-entry opportunity generation, market and technological knowledge, resource bundles, sustainable entrepreneurship, international opportunity analysis, and the need to assess environmental, political, economic, social, technological, cultural, and distribution conditions.</p>
<p>It also connects to Vasant Desai’s entrepreneurship-development perspective on institutions, small-scale and rural enterprise; Aruna Kaulgud’s focus on entrepreneurial development programs and women’s entrepreneurship; P. C. Jain’s project identification and institutional support; and Marc J. Dollinger’s resource and strategy lens.</p>
<p><strong>Supplementary reference:</strong> ''' + source_title + '''. The reference supports further reading; this lesson uses original explanations, examples, activities, and comparisons.</p>'''


def format_first_lesson(textbook_lens, source_title):
    return '''<h1>What Is Entrepreneurship, Really?</h1>
<p><strong>Estimated lesson time:</strong> 7-10 minutes<br><strong>Level:</strong> Beginner<br><strong>Module:</strong> 1 - Introduction to Entrepreneurship</p>
<h2>Learning Objectives</h2>
<p>By the end of this lesson, you will be able to:</p>
<ul><li>Explain entrepreneurship and define an entrepreneur.</li><li>Compare four influential scholarly perspectives.</li><li>Distinguish entrepreneurship from a business and a startup.</li><li>Recognize the roles of opportunity, innovation, resources, action, risk, value, effort, and reward.</li></ul>
<hr>
<h2>Introduction</h2>
<p>Is every person who opens a shop an entrepreneur? A shop owner creates a business, but entrepreneurship asks a wider question: how does a person notice an opportunity, organize resources, create value, and act when the result is uncertain?</p>
<p>For example, one person may open a shop selling the same products as nearby shops. Another may notice that customers cannot reliably receive goods at home and test a phone-based delivery service. Both operate businesses; the second example also shows opportunity recognition and a new way of delivering value.</p>
<aside class="learning-callout"><strong>Key idea</strong><p>Entrepreneurship is not only starting a business. It is creating something valuable, organizing action, and accepting uncertainty while pursuing an opportunity.</p></aside>
<h2>1. Why There Is No Single Definition</h2>
<p>Entrepreneurship has been studied from several angles. Some scholars emphasize uncertainty and risk; others focus on coordinating resources, introducing innovation, or noticing opportunities that other people overlook. These perspectives are complementary, not mutually exclusive.</p>
<h2>2. Four Scholarly Perspectives</h2>
<table><thead><tr><th>Scholar</th><th>Main emphasis</th><th>Easy way to remember</th></tr></thead><tbody>
<tr><td>Richard Cantillon</td><td>The entrepreneur buys or commits resources at known or relatively certain costs while facing uncertainty about future selling prices and outcomes.</td><td><strong>Risk-bearer</strong></td></tr>
<tr><td>Jean-Baptiste Say</td><td>The entrepreneur moves money, people, materials, knowledge, technology, and customers toward more productive uses.</td><td><strong>Coordinator</strong></td></tr>
<tr><td>Joseph Schumpeter</td><td>The entrepreneur introduces new products, production methods, markets, sources of supply, or organizational methods.</td><td><strong>Innovator</strong></td></tr>
<tr><td>Israel Kirzner</td><td>The entrepreneur is alert to unmet needs, price differences, underserved groups, and problems that others have not noticed.</td><td><strong>Opportunity alert</strong></td></tr>
</tbody></table>
<h3>Richard Cantillon: Risk-Bearer</h3>
<p>An entrepreneur may know the cost of purchasing goods today but not the price or demand tomorrow. If someone buys 100 kilograms of coffee for 50,000 birr, the cost is known, but the eventual selling price may produce a profit or a loss. The entrepreneur accepts responsibility for acting under this uncertainty.</p>
<h3>Jean-Baptiste Say: Resource Coordinator</h3>
<p>Entrepreneurs combine resources that are separate or underused. A vegetable-market venture might coordinate farmers, transport, storage, information, and urban customers. The entrepreneur creates value by organizing a system, not merely by reselling an item.</p>
<h3>Joseph Schumpeter: Innovator</h3>
<p>Innovation can be a new product, a new production method, a new market, a new source of supply, or a new organizational method. Schumpeter’s idea of creative destruction describes how new combinations can replace older ways of producing, communicating, paying, or delivering services.</p>
<h3>Israel Kirzner: Opportunity-Alert</h3>
<p>Kirzner emphasizes alertness. When people repeatedly say that a neighborhood lacks reliable delivery, most listeners hear a complaint; an alert entrepreneur asks whether the complaint signals a customer problem worth investigating. Alertness is not proof of an opportunity. It is the beginning of evidence gathering.</p>
<aside class="learning-callout"><strong>Memory trick</strong><p><strong>Cantillon</strong> = Risk<br><strong>Say</strong> = Resources<br><strong>Schumpeter</strong> = Innovation<br><strong>Kirzner</strong> = Opportunity</p></aside>
<h2>3. The Course Working Definition</h2>
<p>Following the perspective of Hisrich, Peters, and Shepherd, this course treats entrepreneurship as a process of creating something new and valuable, investing time and effort, accepting risk, and pursuing possible rewards. Rewards may include financial return, independence, achievement, learning, personal satisfaction, or contribution to a community.</p>
<table><thead><tr><th>Element</th><th>What it means</th><th>Question to ask</th></tr></thead><tbody>
<tr><td>New and valuable creation</td><td>Something improves an outcome for a customer, user, organization, or community.</td><td>Who benefits, and what improves?</td></tr>
<tr><td>Time and effort</td><td>Ideas require investigation, coordination, testing, and follow-through.</td><td>What work must happen before value is delivered?</td></tr>
<tr><td>Risk and uncertainty</td><td>Money, reputation, relationships, wellbeing, and time may be exposed to uncertain outcomes.</td><td>What could go wrong, and how can the downside be limited?</td></tr>
<tr><td>Reward</td><td>The venture may create financial and non-financial returns for the entrepreneur and others.</td><td>What return makes the effort worthwhile and sustainable?</td></tr>
</tbody></table>
<h2>4. Business, Entrepreneurship, and Startup</h2>
<table><thead><tr><th>Concept</th><th>Meaning</th><th>Example</th></tr></thead><tbody>
<tr><td><strong>Business</strong></td><td>An organization that repeatedly exchanges goods or services for money or another form of value.</td><td>A grocery store, restaurant, barber shop, or transport company.</td></tr>
<tr><td><strong>Entrepreneurship</strong></td><td>The process and activity of recognizing opportunities, creating value, organizing resources, and acting under uncertainty.</td><td>Creating a new service or improving a community solution.</td></tr>
<tr><td><strong>Startup</strong></td><td>A temporary organization searching for a repeatable and scalable business model, usually around a new or unproven idea.</td><td>A platform designed to connect customers with service providers across several cities.</td></tr>
</tbody></table>
<aside class="learning-callout"><strong>Remember</strong><p>All startups are businesses, but not all businesses are startups. Entrepreneurship can create either one and can also occur inside an existing company, cooperative, nonprofit, government office, or community project.</p></aside>
<h2>5. Real-World Ethiopian Example</h2>
<p>Imagine a student in Addis Ababa noticing that classmates miss meals because breaks are short and nearby food is expensive. The student should not assume that a business opportunity exists simply because the problem sounds serious.</p>
<ol><li><strong>Observe:</strong> document when the problem occurs and who experiences it.</li><li><strong>Investigate:</strong> speak with students and food providers about current alternatives.</li><li><strong>Design:</strong> propose a small pre-order arrangement rather than building a large platform immediately.</li><li><strong>Test:</strong> measure paid orders, repeat use, delivery reliability, and customer feedback.</li><li><strong>Learn:</strong> decide whether to continue, change the offer, or stop based on evidence.</li></ol>
<p>This example includes all four scholarly perspectives: the student bears uncertainty, coordinates resources, may introduce a new delivery method, and notices an opportunity in a repeated complaint.</p>
<h2>Think About It</h2>
<blockquote>You notice that students at your university regularly struggle with a problem. Is that automatically a business opportunity? What evidence would you need before spending money?</blockquote>
<h2>Common Beginner Mistakes</h2>
<ul><li><strong>Confusing an idea with an opportunity:</strong> an idea becomes more credible only after evidence of need, reachability, feasibility, and value.</li><li><strong>Assuming every entrepreneur is a risk-lover:</strong> effective entrepreneurs manage and reduce downside through small tests and staged commitments.</li><li><strong>Using the word startup for every new business:</strong> a new local shop may be a business without searching for rapid, scalable growth.</li><li><strong>Treating traits as a fixed checklist:</strong> initiative, self-efficacy, persistence, and knowledge can develop through practice and support.</li></ul>
<h2>Practical Application</h2>
<ol><li>Identify one recurring problem in your school, workplace, neighborhood, or market.</li><li>Name the people who experience it and describe their current workaround.</li><li>Explain how Cantillon, Say, Schumpeter, and Kirzner would each view the situation.</li><li>Write one possible value-creating response and one assumption that must be tested.</li><li>Choose a small action that can produce evidence within one week.</li></ol>
<h2>Knowledge Check</h2>
<ol><li>Which scholar is most associated with the entrepreneur as a risk-bearer?</li><li>Which perspective focuses on combining people, money, materials, and knowledge?</li><li>True or false: every business is a startup.</li><li>What makes entrepreneurship broader than simply owning a business?</li><li>A student sees a food-delivery problem. What should happen before a large investment?</li></ol>
<h3>Answers and Explanations</h3>
<ol><li><strong>Richard Cantillon.</strong> His perspective emphasizes acting with uncertain future outcomes.</li><li><strong>Jean-Baptiste Say.</strong> He highlights coordination and productive use of resources.</li><li><strong>False.</strong> A business may operate with a stable local model; a startup searches for a repeatable and scalable model.</li><li><strong>Entrepreneurship includes opportunity recognition, value creation, resource organization, innovation, and action under uncertainty.</strong></li><li><strong>Gather evidence through observation, conversations, and a small test.</strong> A serious problem is not automatically a viable business.</li></ol>
<h2>Key Takeaways</h2>
<ul><li><strong>Entrepreneurship</strong> is a process, not only a job title.</li><li><strong>Cantillon</strong> emphasizes risk-bearing.</li><li><strong>Say</strong> emphasizes resource coordination.</li><li><strong>Schumpeter</strong> emphasizes innovation.</li><li><strong>Kirzner</strong> emphasizes opportunity alertness.</li><li>A <strong>business</strong> is not necessarily a startup.</li><li>Entrepreneurial action should turn assumptions into evidence through manageable steps.</li></ul>
<h2>Lesson Challenge</h2>
<p>Before moving on, speak with one entrepreneur or self-employed person in your community. Ask what problem they began with, what resources they coordinated, what uncertainty they faced, and what they learned from customers. Write a 150-word summary.</p>
<h2>Textbook Connection</h2>
<p><strong>Robert D. Hisrich, Michael P. Peters, and Dean A. Shepherd, <em>Entrepreneurship</em>, 10th edition.</strong> The lesson connects to the entrepreneurial mindset, entrepreneurial action, opportunity recognition, effectuation, innovation, support networks, uncertainty, and sustainable entrepreneurship. It also previews the book’s progression from the entrepreneurial perspective to new entries, business planning, finance, and venture growth.</p>
<p><strong>Supplementary reference:</strong> ''' + source_title + '''. The course uses this reference for framework orientation and provides original explanations and examples rather than reproducing textbook pages.</p>'''


class Command(BaseCommand):
    help = 'Create or refresh the 6-module Entrepreneurship Fundamentals course.'

    def add_arguments(self, parser):
        parser.add_argument('--instructor', help='Instructor username or numeric user id.')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        instructor = self._get_instructor(options.get('instructor'))
        lesson_count = sum(len(lessons) for _, lessons in MODULES)
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Validated {len(MODULES)} modules and {lesson_count} lessons.'))
            return

        with transaction.atomic():
            category, _ = Category.objects.get_or_create(slug='entrepreneurship', defaults={'name': 'Entrepreneurship'})
            course, _ = Course.objects.update_or_create(slug='entrepreneurship-fundamentals', defaults={
                'title': 'Entrepreneurship Fundamentals',
                'subtitle': 'From local problems to a responsible opportunity portfolio',
                'description': 'A 6-module introduction to entrepreneurship for Ethiopian and African learners. Students move from mindset and opportunity recognition through business models, ethics, finance, leadership, ecosystems, and a final opportunity portfolio.',
                'short_description': 'Learn to notice problems, test opportunities, and present a responsible venture concept.',
                'notes': '<h2>How to use this course</h2><p>Complete the three short lessons in each module, do the practice activity, and keep your evidence in one portfolio. The linked resources are public supplementary references; the notes and video guides are original course material written for this portal.</p><p><strong>Source note:</strong> Online references were consulted for framework orientation. Learners should verify current Ethiopian legal, funding, and policy requirements with official sources.</p>',
                'notes_enabled': True,
                'learning_objectives': 'Define entrepreneurship; recognize and rank opportunities; apply design thinking and effectuation; sketch a business model; reason about ethics, finance, leadership, and ecosystems; present an opportunity portfolio.',
                'requirements': 'No prior business experience required. A notebook and access to several potential customers are recommended.',
                'target_audience': 'Students, aspiring entrepreneurs, innovators, community problem-solvers, and early-stage founders.',
                'tags': 'entrepreneurship, Ethiopia, innovation, opportunity recognition, business model, ethics, finance, leadership',
                'instructor': instructor, 'category': category, 'level': Course.Level.BEGINNER,
                'status': Course.Status.PUBLISHED, 'price': 0, 'is_free': True, 'language': 'English', 'duration_hours': 24,
                'thumbnail': self._thumbnail_path(),
            })

            # Remove every previously generated Section for this course so the
            # 6-module source list cannot leave stale module rows behind.
            Section.objects.filter(course=course).delete()

            for module_order, (module_title, lessons) in enumerate(MODULES, start=1):
                section, _ = Section.objects.update_or_create(course=course, order=module_order, defaults={'title': module_title})
                for lesson_order, (title, explanation, activity, video, source_title) in enumerate(lessons, start=1):
                    lesson, _ = Lesson.objects.update_or_create(section=section, order=lesson_order, defaults={
                        'title': title,
                        'lesson_type': Lesson.LessonType.TEXT,
                        'content_text': format_notes(module_title, title, explanation, activity, video, TEXTBOOK_LENSES[module_order], source_title),
                        'video_url': '',
                        'duration_minutes': 20,
                        'is_preview': module_order == 1 and lesson_order == 1,
                        'is_downloadable': False,
                    })
                    Resource.objects.filter(
                        Q(lesson=lesson, title__startswith='Suggested online school reference') |
                        Q(lesson=lesson, title__startswith='Supplementary study reference') |
                        Q(lesson=lesson, title__startswith='Related videos') |
                        Q(lesson=lesson, title__startswith='Primary textbook reference') |
                        Q(lesson=lesson, resource_type=Resource.ResourceType.VIDEO)
                    ).delete()
                    Resource.objects.create(lesson=lesson, title=f'Supplementary study reference: {source_title}', resource_type=Resource.ResourceType.FILE, url=SOURCE_LINKS[source_title], order=1)
                    Resource.objects.create(
                        lesson=lesson,
                        title='Primary textbook reference: Hisrich, Peters and Shepherd, Entrepreneurship',
                        resource_type=Resource.ResourceType.FILE,
                        url=SOURCE_LINKS['Hisrich, Peters and Shepherd - Entrepreneurship, 10th edition (reference)'],
                        order=2,
                    )
                    if module_order not in (4, 5, 6):
                        quiz, _ = Quiz.objects.update_or_create(lesson=lesson, defaults={
                            'course': course, 'section': section, 'title': f'{title} Quiz', 'passing_score_percent': 80,
                        })
                        quiz.questions.all().delete()
                        questions = FIRST_THREE_QUESTIONS.get(title, build_content_questions(title, explanation, activity, video, source_title))
                        for question_order, (text, answer, distractors) in enumerate(questions, start=1):
                            question = Question.objects.create(quiz=quiz, text=text, question_type=Question.QuestionType.MULTIPLE_CHOICE, order=question_order, points=10)
                            answer_choices = build_answer_choices(answer, distractors, question_order)
                            for choice_order, choice_text in enumerate(answer_choices):
                                Choice.objects.create(question=question, text=choice_text, is_correct=choice_text == answer, order=choice_order)

                if module_order in (4, 5, 6):
                    final_questions = {
                        4: MODULE_4_FINAL_QUESTIONS,
                        5: MODULE_5_FINAL_QUESTIONS,
                        6: MODULE_6_FINAL_QUESTIONS,
                    }[module_order]
                    quiz, _ = Quiz.objects.update_or_create(
                        course=course,
                        section=section,
                        lesson=None,
                        defaults={
                            'title': f'Module {module_order} Final Quiz',
                            'is_final_exam': True,
                            'passing_score_percent': 80,
                        },
                    )
                    quiz.questions.all().delete()
                    for question_order, (text, answer, distractors) in enumerate(final_questions, start=1):
                        question = Question.objects.create(quiz=quiz, text=text, question_type=Question.QuestionType.MULTIPLE_CHOICE, order=question_order, points=10)
                        answer_choices = build_answer_choices(answer, distractors, question_order)
                        for choice_order, choice_text in enumerate(answer_choices):
                            Choice.objects.create(question=question, text=choice_text, is_correct=choice_text == answer, order=choice_order)

        self.stdout.write(self.style.SUCCESS(f'Created course {course.title} with {len(MODULES)} modules, {lesson_count} text lessons, lesson quizzes outside Modules 4, 5, and 6, and one final quiz for each of those modules.'))

    def _thumbnail_path(self):
        source = Path(__file__).resolve().parents[3] / 'media' / 'course_thumbnails' / 'entrepreneurship-fundamentals.svg'
        if not source.exists():
            raise CommandError(f'Course thumbnail is missing: {source}')
        return 'course_thumbnails/entrepreneurship-fundamentals.svg'

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