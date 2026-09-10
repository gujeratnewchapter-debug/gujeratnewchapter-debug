from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from html import escape
import re

from accounts.models import User
from courses.models import Category, Course, Section, Lesson
from quizzes.models import Choice, Question, Quiz


def build_answer_choices(correct_answer, distractors, question_order):
    """Return answer choices with the correct answer placed at a rotated letter slot.
    This prevents all quiz questions from always showing the answer at A/B/C/D position.
    """
    choices = [correct_answer, *distractors]
    target_position = (question_order - 1) % len(choices)
    if target_position == 0:
        return choices

    correct_text = choices[0]
    remaining = choices[1:]
    return remaining[:target_position] + [correct_text] + remaining[target_position:]


def format_learning_notes(text):
    """Render the plain-text study notes as safe, structured lesson HTML."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    output = []
    list_items = []
    has_callout = False
    index = 0

    def flush_list():
        if list_items:
            output.append('<ul>' + ''.join(f'<li>{item}</li>' for item in list_items) + '</ul>')
            list_items.clear()

    while index < len(lines):
        line = lines[index]
        upper = line.upper()
        if upper.startswith(('EXAM TAKEAWAY', 'KEY POINT')):
            flush_list()
            takeaway = lines[index + 1] if index + 1 < len(lines) else ''
            output.append(
                '<aside class="learning-callout"><strong>Exam Takeaway</strong>'
                f'<p>{escape(takeaway)}</p></aside>'
            )
            has_callout = True
            index += 2
            continue
        if upper.startswith('STUDY CARD:'):
            flush_list()
            output.append(f'<h2>{escape(line.split(":", 1)[1].strip().title())}</h2>')
            index += 1
            continue
        article = re.match(r'^(ARTICLES?)\s+([0-9-]+)\s*-\s*(.+)$', line, re.IGNORECASE)
        if article:
            flush_list()
            output.append('<hr class="learning-rule">')
            output.append(f'<h2>Article {escape(article.group(2))} - {escape(article.group(3).title())}</h2>')
            index += 1
            continue
        if upper in {'PRACTICAL MAP', 'APPLICATION CHECKLIST', 'DEADLINE CARD', 'CONTROL QUESTIONS', 'DECISION RULE', 'FINAL REVIEW'}:
            flush_list()
            output.append(f'<h3>{escape(line.title())}</h3>')
            index += 1
            continue
        bullet = re.match(r'^(?:[-*]|\d+\.)\s+(.+)$', line)
        if bullet:
            list_items.append(escape(bullet.group(1)))
            index += 1
            continue
        term = re.match(r'^([^:]{2,60}):\s+(.+)$', line)
        if term and not line.lower().startswith(('http:', 'https:')):
            flush_list()
            output.append(f'<p><strong>{escape(term.group(1))}:</strong> {escape(term.group(2))}</p>')
            index += 1
            continue
        if ' = ' in line:
            flush_list()
            left, right = line.split(' = ', 1)
            output.append(f'<li><strong>{escape(left)}</strong> = {escape(right)}</li>')
            index += 1
            continue
        flush_list()
        output.append(f'<p>{escape(line)}</p>')
        index += 1

    flush_list()
    if not has_callout and lines:
        output.append(
            '<aside class="learning-callout"><strong>Exam Takeaway</strong>'
            f'<p>{escape(lines[-1])}</p></aside>'
        )
    return ''.join(output)


def format_course_notes(text):
    """Render the course overview's lightweight Markdown as safe HTML."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    output = []
    list_items = []

    def inline(value):
        escaped = escape(value)
        return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)

    def flush_list():
        if list_items:
            output.append('<ul>' + ''.join(f'<li>{item}</li>' for item in list_items) + '</ul>')
            list_items.clear()

    for line in lines:
        if line.startswith('## '):
            flush_list()
            output.append(f'<h2>{inline(line[3:])}</h2>')
        elif line.startswith('# '):
            flush_list()
            output.append(f'<h2>{inline(line[2:])}</h2>')
        elif re.match(r'^\d+\.\s+', line):
            list_items.append(inline(re.sub(r'^\d+\.\s+', '', line)))
        elif line.startswith('- '):
            list_items.append(inline(line[2:]))
        else:
            flush_list()
            output.append(f'<p>{inline(line)}</p>')
    flush_list()
    return ''.join(output)


LESSONS = [
    {
        'section': 'Part One: Foundations of the Proclamation',
        'title': 'Foundations, Definitions, and Scope',
        'articles': 'Articles 1-3',
        'content': '''STUDY CARD: WHY THIS PROCLAMATION EXISTS
    The Proclamation responds to the role of innovation and technology in creating industries, jobs, exports, productivity, and social welfare. It aims to build a competitive Ethiopian startup ecosystem through designation, targeted support, finance, capacity building, and coordination.

    ARTICLE 1 - SHORT TITLE
    The law may be cited as Ethiopian Startup Proclamation No. 1396/2025.

    ARTICLE 2 - DEFINITIONS TO REMEMBER
    Startup: a person or group with no or limited business history that creates economic value through an innovative, technology-enabled, scalable, or market-changing product, service, or process. The definition includes introduction, creation, transplantation, adaptation, and reverse engineering.
    Accelerator: an intensive, time-bound program supporting startup formation, growth, and development.
    Incubator: a person that provides a supportive environment and resources for startup growth.
    Angel investor: a person investing their own capital in startups.
    Grant: capital given to a designated early-stage startup for development and business-process costs.
    Venture capital: investment in startups with growth potential, including financial, technical, or managerial expertise.
    Innovation: creating, developing, and implementing a new product, service, or process, or significantly improving an existing solution.
    Scalability: the ability to increase market share at low cost while maintaining quality, efficiency, and performance under market demand.
    Economic value and factors: measurable positive economic impact, including productivity, job creation, export growth and diversification, innovation, and social welfare.
    Startup designation: recognition granted by the Ministry under this Proclamation.
    Startup ecosystem: the connected actors and organizations providing resources, knowledge, and support for startups.
    Startup ecosystem builder: an active contributor such as an incubator, accelerator, co-working space, fund, investor, education institution, research agency, or NGO.
    Foreign investor and foreign startup: the Proclamation identifies foreign nationals, foreign-owned or foreign-incorporated enterprises, qualifying joint enterprises, and Ethiopians permanently residing abroad as foreign-investor categories. A foreign startup is designated under the Proclamation and is fully foreign-owned or more than half foreign-owned jointly with an Ethiopian.
    Tech-enabled: using, adopting, transplanting, or integrating technology to improve, optimize, innovate, or transform products, services, processes, or business models.
    Region: constitutional regions plus the newly organized regions, Addis Ababa, and Dire Dawa.
    Fund of funds: an investment fund investing in startups through other investment funds.
    Person: a natural person or juridical person. Masculine wording includes the feminine.

    ARTICLE 3 - SCOPE
    The Proclamation applies at both federal and regional levels.

    EXAM TAKEAWAY
    Operating as a startup or ecosystem builder does not require designation. However, designation is the prerequisite for receiving the incentives and privileges created by this law.''',
        'questions': [
            ('What is the short title of the law?', 'Ethiopian Startup Proclamation No. 1396/2025', ['Ethiopian Innovation Code No. 1205/2020', 'Startup Finance Regulation No. 487/2022', 'Digital Economy Proclamation No. 63/2025']),
            ('Which feature is central to the definition of a startup?', 'Creating economic value through innovative or technology-enabled scalable activity', ['Operating only as a public company', 'Having at least ten years of business history', 'Providing only government services']),
            ('What does an accelerator provide?', 'An intensive, time-bound program supporting startup establishment, growth, and development', ['A permanent tax court', 'Only physical office space', 'A mandatory business license']),
            ('What is an angel investor?', 'A person who invests their own capital in startups', ['A government tax officer', 'A startup employee with a work permit', 'A commercial bank regulator']),
            ('What does scalability describe?', 'The ability to grow market share at low cost while meeting market demand', ['The number of founders in a company', 'The age of a registered business', 'The duration of a work permit']),
            ('What is startup designation?', 'Recognition granted by the Ministry under the Proclamation', ['A court declaration of bankruptcy', 'A private investment contract', 'A customs invoice']),
            ('Who is included in the startup ecosystem?', 'Actors and organizations providing resources, knowledge, and support to startups', ['Only public companies', 'Only foreign investors', 'Only commercial banks']),
            ('What does tech-enabled mean in the Proclamation?', 'Using, adopting, transplanting, or integrating technology to improve or transform activity', ['Using technology only for advertising', 'Importing any product without approval', 'Replacing all human workers']),
            ('At which levels does the Proclamation apply?', 'Federal and regional levels', ['Only Addis Ababa', 'Only federal institutions', 'Only foreign-owned businesses']),
            ('Is designation mandatory to operate as a startup?', 'No, but it is required to receive incentives under the Proclamation', ['Yes, in every case', 'Only for foreign startups', 'Only for unregistered individuals']),
        ],
    },
    {
        'section': 'Part Two: Institutions and Digital Portal',
        'title': 'Ministry, Council, and the Digital Startup Portal',
        'articles': 'Articles 4-5',
        'content': '''STUDY CARD: WHO IMPLEMENTS THE LAW?
    The Ministry is the operational authority. The Council provides national coordination, strategy, accountability, and oversight.

    ARTICLE 4 - MINISTRY POWERS AND FUNCTIONS
    The Ministry coordinates government, private-sector, and development actors to create a conducive startup environment. It grants, renews, suspends, or revokes startup and ecosystem-builder designations based on the committee process and the Proclamation, Regulations, and Directives.
    It manages the Startup Grant Program; evaluates designated startups, ecosystem builders, incentives, and the overall ecosystem annually; and publishes performance reports.
    It creates and administers the Digital Startup Portal. The portal is a single window for ecosystem information, receives designation applications, and enables interaction between ecosystem builders and relevant institutions. The Ministry may also use it for other functions connected to its legal mandate.
    The Ministry coordinates capacity building with the Ministry of Labor and Skills, works with that Ministry to create awareness of startup and innovation contributions, and collaborates with government, non-government, and private actors to hold a problem-solving competition and award at least once every year. The competition details are set by Ministry Directive.

    ARTICLE 5 - COUNCIL POWERS AND FUNCTIONS
    The national digital economy Council leads coordination among government institutions, private sector, and development partners supporting startups. It reviews and approves monitoring and evaluation reports on incentives and approves strategies for mobilizing ecosystem resources.
    The Council ensures transparent and accountable grant distribution, approves the startup-grant Directive prepared by the Ministry of Finance, and ensures implementation.
    It initiates annual audits by an external auditor licensed by the Accounting and Audit Board of Ethiopia for grant and relevant incentive accounts. Within three months after the fiscal year, it receives and reviews the general startup audit report, ensures corrective action, and ensures the annual report is published and available to the public.
    At least once each year it consults public and private stakeholders to identify barriers to Ethiopia's startup ecosystem. It approves Directives on the National Designation Committee's members and procedures and performs other necessary functions.
    The law anticipates transfer of these Council powers to a Science, Technology and Innovation Council established by law.

    PRACTICAL MAP
    Ministry = applications, designation, portal, grants, evaluation, coordination.
    Council = strategy, accountability, audits, reports, stakeholder oversight.''',
        'questions': [
            ('Which institution creates and administers the Digital Startup Portal?', 'The Ministry', ['The Customs Commission', 'The National Bank alone', 'A private fund manager']),
            ('What is the portal intended to provide?', 'Single-window access to relevant Ethiopian startup ecosystem information', ['Only a payment gateway', 'Only an employment registry', 'A court filing system']),
            ('What kind of applications does the portal receive?', 'Startup and Startup Ecosystem Builder designation applications', ['Only tax appeals', 'Only student enrollments', 'Only customs declarations']),
            ('Who grants, renews, suspends, or revokes designation subject to the committee process?', 'The Ministry', ['The Council of Ministers exclusively', 'The Ethiopian Investment Holdings exclusively', 'The applicant']),
            ('How often must the Ministry organize the problem-solving competition and award at minimum?', 'At least once a year', ['Every month', 'Every five years', 'Only once']),
            ('What does the Council do with monitoring and evaluation reports?', 'Reviews and approves them', ['Deletes them', 'Sends them to foreign investors only', 'Converts them into tax returns']),
            ('What does the Council ensure about Startup Grant disbursement?', 'Transparency and accountability', ['Confidentiality from all oversight', 'Automatic payment to every applicant', 'That only foreign startups receive funds']),
            ('How often must the Council hold a stakeholder consultation at minimum?', 'At least once a year', ['Every working day', 'Once every ten years', 'Only after a court order']),
            ('Who is expected to perform annual audits of relevant grant and incentive accounts?', 'An external auditor licensed by the Accounting and Audit Board of Ethiopia', ['Any startup founder', 'The course instructor', 'An unlicensed consultant']),
            ('What future body is to receive the Council powers stated in Article 5?', 'The Science, Technology and Innovation Council established by law', ['The National Credit Guarantee Fund', 'The Customs Commission', 'The Grievance Committee']),
        ],
    },
    {
        'section': 'Part Three: Designation',
        'title': 'Startup Eligibility and Designation Applications',
        'articles': 'Articles 6-11',
        'content': '''STUDY CARD: HOW A STARTUP BECOMES DESIGNATED

    ARTICLE 6 - PRINCIPLE
    Designation is voluntary for operating a startup or ecosystem builder. It becomes mandatory only when the applicant wants the incentives and privileges under this Proclamation.

    ARTICLE 7 - STARTUP ELIGIBILITY
    The applicant must first satisfy the definition of startup. An unregistered individual may apply if the definition is met. The applicant must be able to show ownership of the product, process, or service offered or intended for the market, including through a signed affidavit.
    At least 25 percent of the capital must be held by the founder. The applicant must not be a public company. A licensed organization may apply under the special rule if it has been established for no more than five years when it applies.
    After designation, the Ministry issues a certificate.

    ARTICLE 8 - CERTIFICATE CONTENT
    A startup certificate identifies the startup name, founder or founders, growth stage, and industry or economic sector. The detailed growth stages, eligibility criteria, and certificate requirements are left to a Directive.

    ARTICLE 9 - APPLICATION PROCESS
    The applicant completes the prescribed form, attaches required documents, and submits through the Digital Startup Portal. If accepted, the Ministry registers the application and issues the certificate. If rejected, it must give written reasons within 30 working days.
    The committee may call an applicant for an interview, practical product/service/process presentation, or in-person observation. The application must receive a response within 30 working days.

    ARTICLES 10-11 - NATIONAL DESIGNATION COMMITTEE
    The National Startup Designation Committee has at least 11 members, including the Minister, appointed by the Council. It draws from relevant ministries and government institutions, higher education and research institutions, experienced startup-industry professionals, and civil society. The Ministry chairs the committee and provides its budget.
    The committee receives applications from startups and ecosystem builders through the portal, evaluates merit and eligibility, and submits its result to the Ministry. It may issue an internal operating manual, while the Ministry sets its detailed duties by Directive.

    APPLICATION CHECKLIST
    Prove ownership; confirm founder ownership is at least 25%; confirm the company is not public; collect license and supporting documents; submit through the portal; prepare for an interview or demonstration; track the 30-working-day response period.''',
        'questions': [
            ('What founder ownership threshold is required for an eligible startup?', 'At least 25 percent of capital', ['At least 5 percent', 'At least 10 percent', 'At least 75 percent']),
            ('Can an unregistered individual apply for startup designation?', 'Yes, if the individual meets the startup definition and other requirements', ['No, never', 'Only if foreign-owned', 'Only after five years']),
            ('How old may a licensed organization be when it applies under the special rule?', 'No more than five years from establishment', ['No more than six months', 'No more than twenty years', 'Age is unlimited']),
            ('Which entity is excluded from startup eligibility?', 'A public company', ['A private startup', 'An individual founder', 'A technology-enabled enterprise']),
            ('Where must a designation application be submitted?', 'Through the Digital Startup Portal', ['Only by newspaper advertisement', 'Only to a commercial bank', 'Only to a foreign embassy']),
            ('Within how many working days must a rejected startup application be explained to the applicant?', 'Thirty working days', ['Three working days', 'Ten calendar months', 'Two years']),
            ('What may the committee request when relevant?', 'An interview, practical presentation, or in-person observation', ['A criminal sentence', 'A public share listing', 'A foreign passport from every employee']),
            ('How many members must the National Designation Committee have at minimum?', 'Eleven members', ['Three members', 'Five members', 'Seven members']),
            ('Who appoints the committee members?', 'The Council', ['The applicant', 'The Customs Commission', 'A private accelerator']),
            ('What must a startup designation certificate include?', 'The startup name, founder name, growth stage, and industry or sector', ['Only the bank account number', 'Only the founder phone number', 'Only the tax identification number']),
        ],
    },
    {
        'section': 'Part Three: Designation',
        'title': 'Ecosystem Builders, Compliance, and Grievances',
        'articles': 'Articles 12-22',
        'content': '''STUDY CARD: KEEPING DESIGNATION IN GOOD STANDING

    ARTICLE 12 - STARTUP OBLIGATIONS
    A designated startup must obey all applicable laws, pursue its growth objectives, provide requested non-personal information subject to data-protection law, and periodically report incentives received and results achieved. It must notify the Ministry within 10 working days of changes to corporate or legal structure, composition, or business activity.
    It must use incentives properly, keep proper accounting records, meet reporting duties, and comply with obligations in the Proclamation, Regulations, and Directives. If it fails, the Ministry gives notice to correct the failure within 15 working days; the startup then has 30 working days after notice to rectify the shortcomings.

    ARTICLE 13 - RENEWAL
    A startup designation lasts two years from issue. Renewal should be filed 30 working days before expiry, using the prescribed form and documents. No designation under this law can remain valid for more than eight years in total.

    ARTICLES 14-15 - SUSPENSION AND REVOCATION
    Suspension may follow failure to meet legal obligations, failure to provide accurate and timely information, failure to perform designated activities, or failure by a commercial startup to provide a renewed business license. A suspended startup cannot receive incentives. The Ministry must state the reason and corrective measures, normally allowing 30 days. Corrected defects lift the suspension. Suspension of a business license or competence certificate automatically suspends designation, but Ministry suspension does not suspend the underlying license.
    Revocation may follow voluntary closure, a merger or acquisition that removes startup eligibility, falsified documents, unauthorized use, bankruptcy, failure to renew, cancellation of commercial registration, or failure to correct suspension defects. For falsification, unauthorized use, or an eligibility-changing transaction, written objection must be allowed. The startup has 30 working days; an unsatisfactory or missing objection leads to revocation.

    ARTICLES 16-21 - ECOSYSTEM BUILDERS
    An ecosystem builder needs applicable commercial registration, business license, or investment permit; at least one useful resource such as space, technology infrastructure, finance, innovation equipment, mentorship, networking, or legal/administrative support; competent business and innovation management; and additional Directive requirements.
    Existing financial, education, TVET, research, and NGO institutions may receive an accelerated designation route. Builder applications use the portal and must be answered within 30 working days. Builders must keep accounts, obey laws, meet quality standards, provide an enabling environment, distribute incentives fairly, share relevant information, avoid misuse, and report changes within 15 days.
    Builder designation lasts five years and is renewed 30 working days before expiry. Suspension and revocation use written reasons, correction periods, objections, and exit-report requirements similar to startup designation.

    ARTICLE 22 - GRIEVANCE COMMITTEE
    An inclusive and independent committee of at least seven members handles grievances about designation, suspension, and cancellation. It is accountable to the Minister, while detailed procedures are set by Ministry Directive.

    DEADLINE CARD
    Startup change: 10 working days. Builder change: 15 days. Initial correction notices: 15 or 30 days depending on the entity. Objection: 30 working days. Renewal filing: 30 working days before expiry.''',
        'questions': [
            ('How long is a startup designation valid for each term?', 'Two years', ['Six months', 'Five years', 'Ten years']),
            ('What is the maximum total validity of a startup designation?', 'Eight years', ['Two years', 'Five years', 'Unlimited']),
            ('How long is an ecosystem builder designation valid?', 'Five years', ['One year', 'Two years', 'Eight years']),
            ('Within how many working days must a designated startup report a structural or business change?', 'Ten working days', ['Two working days', 'Thirty calendar months', 'Five years']),
            ('What may happen when a designated startup fails to meet its obligations?', 'The Ministry may notify it to correct the failure and may later suspend designation', ['It automatically receives a grant', 'It becomes a public company', 'Its founder receives a visa']),
            ('What is the effect of suspension on incentives?', 'The suspended startup is not eligible for incentives under the Proclamation', ['It receives double incentives', 'Nothing changes', 'It becomes eligible for the Fund of Funds']),
            ('Which is a ground for revocation?', 'Obtaining designation based on falsified documents', ['Hiring a local employee', 'Submitting a proper report', 'Using technology responsibly']),
            ('What should a builder do when it changes its business operation or objective?', 'Provide information to the Ministry within 15 days', ['Wait until the next decade', 'Apply for a course certificate', 'Notify only a private investor']),
            ('What does the grievance committee address?', 'Grievances involving designation, suspension, and cancellation', ['Only customs valuation', 'Only student grades', 'Only foreign exchange rates']),
            ('What is the minimum size of the grievance committee?', 'Seven members', ['Two members', 'Four members', 'Eleven members']),
        ],
    },
    {
        'section': 'Part Four: Incentives',
        'title': 'Grants, Credit Guarantees, and Responsible Use',
        'articles': 'Articles 23-29',
        'content': '''STUDY CARD: FINANCE WITH ACCOUNTABILITY

    ARTICLES 23-25 - STARTUP GRANT
    The Startup Grant Program supports designated startups and is administered by the Ministry under a Ministry of Finance Directive. Government covers launch funding; development partners and other Ministry-of-Finance-approved sources may also contribute. The Directive governs management, administration, and operation.
    The grant pays costs connected to research, implementation, development, and commercialization of designated startups in early development stages. It cannot pay unrelated personal expenses, undeclared commercial activity, personal or corporate debt, unrelated investments, unrelated real estate or fixed assets, or activities prohibited by Directive.
    The Ministry may distribute directly or through a designated ecosystem builder. Minimum and maximum amounts are determined by the Ministry with regard to the law and Finance Directive. A recipient generally cannot apply again for one year. Founders with at least 25 percent ownership who received a grant through another designated startup also face the one-year restriction. Legal liquidation removes these restrictions. The same startup cannot apply twice for the same idea.
    Applicants must disclose all other designated startups in which founders hold ownership or significant management roles. A builder distributing grants cannot use the money for its own personal or commercial activity. Both beneficiaries and distributing builders have periodic reporting duties.

    ARTICLES 26-29 - CREDIT GUARANTEE FUND
    The National Credit Guarantee Fund serves designated startups, designated ecosystem builders, and micro, small, and medium enterprises. Its objective is to increase access to credit. The National Bank of Ethiopia supervises it. Innovation, Labor and Skills, and Industry authorities set eligibility criteria for their respective beneficiaries. Government provides initial capital, and the mandate may expand with National Bank authorization. A Council of Ministers Regulation defines structure, income, leadership, administration, and operations.
    The fund issues credit guarantees, invests its assets, and pays admitted financial institutions on valid guaranteed-loan claims. Beneficiaries must repay the full loan under the loan agreement and use it only for approved purposes. Misuse, intentional default, and negligent non-repayment are prohibited. Intentional defaulters may be excluded from the guarantee scheme for 10 years; detailed consequences come from Regulation.

    CONTROL QUESTIONS
    Is the expense in the approved application? Is it connected to the designated business? Has it been recorded and reported? If any answer is no, the expenditure presents a compliance risk.''',
        'questions': [
            ('Who administers the Startup Grant Program?', 'The Ministry under a directive issued by the Ministry of Finance', ['Only private banks', 'Only the Council of Ministers directly', 'The Customs Commission']),
            ('What stage of startup development does the grant primarily support?', 'Initial or early stages of development', ['Only companies older than ten years', 'Only publicly listed companies', 'Only companies after liquidation']),
            ('Which use of grant money is prohibited?', 'Repaying personal or corporate debt', ['Research for the designated product', 'Commercialization described in the application', 'Development of the designated service']),
            ('Can grant money pay for unrelated real estate?', 'No', ['Yes, always', 'Yes, if the founder agrees', 'Only without reporting']),
            ('How long must a grant recipient generally wait before applying for another grant?', 'One year', ['One week', 'Two years', 'Eight years']),
            ('Can the same designated startup apply for a grant twice for the same idea?', 'No', ['Yes, without limit', 'Only every month', 'Only as a public company']),
            ('What must founders disclose at grant application time?', 'All designated startups in which they hold ownership or significant management roles', ['Only their social media accounts', 'Only unrelated personal expenses', 'Nothing about other startups']),
            ('Who supervises the National Credit Guarantee Fund?', 'The National Bank of Ethiopia', ['The Ministry of Education', 'The Grievance Committee', 'A startup accelerator']),
            ('Who can benefit from the guarantee fund?', 'Designated startups, ecosystem builders, and micro, small, and medium enterprises', ['Only public companies', 'Only foreign embassies', 'Only university students']),
            ('What is a consequence of intentional default under the guarantee scheme?', 'The beneficiary may be barred from the scheme for ten years', ['Automatic designation renewal', 'A lifetime grant', 'A duty-free certificate']),
        ],
    },
    {
        'section': 'Part Four and Part Five: Financial Incentives',
        'title': 'Tax, Duty-Free Privileges, and Fund of Funds',
        'articles': 'Articles 30-36',
        'content': '''STUDY CARD: TAX, CUSTOMS, AND INVESTMENT CAPITAL

    ARTICLE 30 - TAX INCENTIVES
    A designated startup benefits from incentives provided under relevant investment-incentive laws. Before designation expires, and subject to the Ministry of Finance Directive, it may qualify for exemption from income tax, tax on dividends distributed to shareholders, and withholding tax. Non-equity grants, gifts, donations, or similar contributions with no possibility of equity or debt conversion are treated as non-income proceeds for income-tax purposes.
    Income earned by foreign nationals employed by a designated startup before designation expires may be exempt. The Ministry verifies exemption applications and sends them to the Ministry of Finance for approval.

    ARTICLES 31-32 - LOSS RELIEF
    A startup loss incurred during the income-tax exemption period may be carried forward after the exemption ends for a period equal to half of the exemption period. A loss for a tax year is deducted in the next tax year, but the general carry-forward period under the Proclamation is limited to three years.
    An investor who invests for equity and later loses money in a designated startup may deduct 100 percent of that loss in its own financial statement. That investor loss may be carried forward for two years.

    ARTICLES 33-34 - DUTY-FREE CAPITAL GOODS
    A designated startup may import capital goods necessary for operation duty-free after submitting the list to and obtaining approval from the Ministry of Finance. If it buys such goods from a local manufacturer, Customs refunds duties and taxes paid on the inputs used to produce them.
    An ecosystem builder may use the same type of privilege for capital goods needed to establish, expand, or upgrade a facility. It must maintain valid designation whenever applying for incentives. Other relevant-law obligations still apply.

    ARTICLES 35-36 - STARTUP FUND OF FUNDS
    The Fund of Funds is a government/private-sector commercial enterprise and may include foreign investors. Ethiopian Investment Holdings holds the government interest; a competitively selected private fund manager manages the Fund. Commercial Code, capital-markets, and other relevant laws continue to apply.
    Its core purpose is to invest in other funds that invest in designated startups. It also aims to increase foreign venture-capital flows, international connections, and support to the domestic ecosystem. Other appropriate purposes may be set by the fund manager.

    DECISION RULE
    Designation creates access, not automatic approval. Tax exemptions, duty-free lists, and other benefits still require the applicable Directive, verification, approval, and compliance with other laws.''',
        'questions': [
            ('Which tax benefit may be available to a designated startup under the applicable directive?', 'Exemption from income tax, dividend tax, and withholding tax', ['Exemption from every law without approval', 'Only exemption from customs inspections', 'Only exemption from employee records']),
            ('How are non-equity grants generally treated for income tax purposes?', 'As non-income proceeds when they cannot convert to equity or debt', ['Always as salary', 'Always as dividend', 'Always as a customs penalty']),
            ('How long may a foreign employee income exemption apply?', 'Before the startup designation period expires', ['Only before employment begins', 'Forever regardless of designation', 'Only after liquidation']),
            ('What happens to a startup loss incurred during the tax exemption period?', 'It may be carried forward for a period equal to half of the exemption period', ['It is automatically forgiven as debt', 'It becomes founder equity', 'It is never recorded']),
            ('For how many years may the general startup loss be carried forward under Article 31?', 'Three years', ['One month', 'Two years only', 'Ten years']),
            ('What loss deduction may an investor have after losing an equity investment in a designated startup?', 'A 100 percent deduction of the loss on its financial statement', ['No deduction in any case', 'A deduction of only 1 percent', 'A deduction only after becoming a public company']),
            ('What can a designated startup import duty-free?', 'Capital goods necessary for its operation, subject to approval', ['Any personal luxury item', 'Unrelated real estate', 'Any undocumented shipment']),
            ('Who approves the list of capital goods for duty-free import?', 'The Ministry of Finance', ['The startup customer', 'The grievance committee', 'The course instructor']),
            ('What does the Startup Fund of Funds invest in?', 'Other funds that invest in designated startups', ['Only personal savings accounts', 'Only public infrastructure', 'Only imported vehicles']),
            ('One purpose of the Fund of Funds is to increase what?', 'Foreign venture capital investment and international connections', ['The number of tax audits only', 'The price of public shares', 'The duration of student visas']),
        ],
    },
    {
        'section': 'Part Six and Part Seven: Regulation and Protection',
        'title': 'Sandbox, Work Permits, Foreign Startups, and Protection',
        'articles': 'Articles 37-44',
        'content': '''STUDY CARD: INNOVATION WITH REGULATORY PROTECTION

    ARTICLE 37 - REGULATORY SANDBOX
    The Ministry may establish a supervised testing framework for new and innovative startup products, services, and processes before or during market introduction. A Directive may define additional eligibility criteria, the application process, and participation conditions. A sandbox is controlled experimentation, not a permanent exemption from regulation.

    ARTICLE 38 - COMPETENCY CERTIFICATES
    Where a competence certificate is normally required before a business license, a designated startup may fulfill it within four years of designation. Government agencies issuing competence certificates must create appropriate requirements that encourage startups. This flexibility does not apply to public-health or national-security sectors.

    ARTICLE 39 - WORK PERMITS AND VISA
    Subject to applicable work-permit law, a foreign national joining a designated startup in Ethiopia may receive a work permit valid for three years. A foreign national joining a startup as an employee is also entitled to a startup visa.

    ARTICLE 40 - FOREIGN STARTUPS AND BUILDERS
    The minimum capital requirement in Investment Proclamation No. 1180/2020 does not apply to qualifying foreign startups and foreign ecosystem builders that establish or invest in Ethiopian startups. They are entitled to the incentives under this Proclamation, but a foreign startup is specifically excluded from the Article 24 grant program. Registration and licensing details are determined by an Ethiopian Investment Board Directive.

    ARTICLE 41 - PROTECTION
    Without prior written consent of the designated startup and Ministry approval, no person may replicate, use, appropriate, or commercially exploit the product, service, or process for which designation was obtained, or falsely represent themselves as a designated startup. Protection does not apply when designation was not based on that product/process, valid intellectual-property rights exist, similarity is incidental to standard industry practice, or a significant improvement independently satisfies the startup definition.

    ARTICLES 42-44 - FINAL RULES
    An inconsistent law or custom has no effect on matters governed by this Proclamation. The Council of Ministers issues implementing Regulations, and the Ministry issues necessary Directives. The Proclamation enters into force on publication in the Federal Negarit Gazette.

    FINAL REVIEW
    Ask whether the activity is inside a sandbox, whether a competence certificate is required, whether the person is foreign, whether the startup is designated, whether the grant exclusion applies, and whether the proposed use copies a protected product or process.''',
        'questions': [
            ('What is the purpose of a regulatory sandbox?', 'To test innovative products, services, or processes under regulatory oversight', ['To avoid all regulation permanently', 'To replace the Digital Startup Portal', 'To issue university diplomas']),
            ('Who may issue additional sandbox eligibility criteria and conditions?', 'The Ministry through a directive', ['Any individual founder', 'Only a private bank', 'Only a foreign employee']),
            ('Within how long may a designated startup fulfill a required competency certificate?', 'Within four years of designation', ['Within four days', 'Within ten years', 'Only before applying']),
            ('Which sectors are excluded from the competency certificate flexibility?', 'Sectors related to public health and national security', ['All technology sectors', 'All export businesses', 'All private companies']),
            ('How long may a foreign national work permit for joining a designated startup be valid?', 'Three years', ['Three months', 'Five years automatically', 'Eight years']),
            ('What visa may a foreign national joining a startup obtain?', 'A startup visa', ['A grant visa', 'A customs visa', 'A public-company visa']),
            ('What capital requirement does Article 40 remove for qualifying foreign startups and builders?', 'The minimum capital requirement under the Investment Proclamation', ['Every accounting requirement', 'The need for a product', 'All licensing requirements']),
            ('Are foreign startups entitled to the grant program?', 'No, although they may receive other incentives under the Proclamation', ['Yes, without designation', 'Only if they are public companies', 'Only after ten years']),
            ('What does Article 41 protect?', 'The designated startup product, service, or process from unauthorized replication or appropriation', ['Only employee salaries', 'Only tax records', 'Only grant budgets']),
            ('When does the Proclamation enter into force?', 'On the date of publication in the Federal Negarit Gazette', ['Eight years after publication', 'Only after a court case', 'At the end of the first grant year']),
        ],
    },
]


class Command(BaseCommand):
    help = 'Create or refresh the Ethiopian Startup Proclamation course and its lesson quizzes.'

    def add_arguments(self, parser):
        parser.add_argument('--instructor', help='Instructor username or numeric user id.')
        parser.add_argument('--dry-run', action='store_true', help='Validate the content without writing records.')

    def handle(self, *args, **options):
        instructor = self._get_instructor(options.get('instructor'))
        if len(LESSONS) != 7 or any(len(item['questions']) != 10 for item in LESSONS):
            raise CommandError('The course content must contain seven lessons with ten questions each.')

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS('Validated 7 lessons and 70 questions. No records changed.'))
            return

        with transaction.atomic():
            category, _ = Category.objects.get_or_create(
                slug='startup', defaults={'name': 'Startup'},
            )
            course, _ = Course.objects.update_or_create(
                slug='ethiopian-startup-proclamation',
                defaults={
                    'title': 'Ethiopian Startup Proclamation',
                    'subtitle': 'A practical guide to Proclamation No. 1396/2025',
                    'description': 'Study the Ethiopian Startup Proclamation No. 1396/2025 through seven focused lessons covering designation, incentives, regulation, and protection.',
                    'short_description': "Understand Ethiopia's startup designation system, incentives, and regulatory framework.",
                    'notes': format_course_notes('''# Course Study Guide

## How to use these notes
Read one lesson, make a short definition or deadline card, then complete its 10-question quiz. The quiz requires 80 percent to unlock the next lesson. These learning notes summarize the English text supplied from Federal Negarit Gazette No. 63 and are educational material, not legal advice.

## The proclamation in one page
1. **Purpose:** build a conducive startup ecosystem and accelerate technology-led economic growth.
2. **Recognition:** designation is voluntary for operation but required for incentives.
3. **Authority:** the Ministry manages designations, the portal, grants, coordination, and evaluation; the Council provides strategy, accountability, audits, and stakeholder oversight.
4. **Eligibility:** demonstrate a startup or builder definition, meet ownership/licensing requirements, and apply through the Digital Startup Portal.
5. **Finance:** grants support early-stage development; guarantees improve credit access; misuse and intentional default have consequences.
6. **Tax and customs:** incentives are available through the relevant laws, Directives, verification, and approvals.
7. **Capital:** the Fund of Funds invests through other funds and attracts foreign venture capital.
8. **Regulation:** sandbox testing, delayed competence certificates, work permits, and startup visas support controlled growth.
9. **Protection:** designated products, services, and processes receive protection against unauthorized replication, subject to exceptions.
10. **Implementation:** Regulations come from the Council of Ministers; Directives come from the Ministry; the law starts on Gazette publication.

## Deadline and threshold card
- Founder ownership for startup eligibility: **at least 25%**.
- Startup application response: **30 working days**.
- Startup structural/business change notice: **10 working days**.
- Builder change notice: **15 days**.
- Startup designation term: **2 years**; maximum total: **8 years**.
- Builder designation term: **5 years**.
- Renewal filing: **30 working days before expiry**.
- Foreign startup employee work permit: **3 years**.
- Competency certificate completion: **4 years from designation**.
- Grant reapplication restriction: generally **1 year**.
- Intentional guarantee-fund default exclusion: **10 years**.
- Investor loss carry-forward: **2 years**; startup loss carry-forward: **3 years**.
- National Designation Committee: **at least 11 members**.
- Grievance Committee: **at least 7 members**.

## Final learner checklist
You should be able to define startup, innovation, scalability, designation, ecosystem builder, grant, guarantee fund, and regulatory sandbox; distinguish Ministry duties from Council duties; prepare a designation application; explain suspension versus revocation; identify permitted and prohibited grant uses; explain the tax, duty-free, foreign-worker, and Fund-of-Funds provisions; and identify the exceptions to startup protection.'''),
                    'notes_enabled': True,
                    'learning_objectives': 'Explain key legal definitions; identify designation requirements; describe grants, guarantees, tax and duty incentives; apply compliance and protection rules.',
                    'requirements': 'No prior legal or business knowledge required.',
                    'target_audience': 'Startup founders, ecosystem builders, investors, students, and innovation professionals.',
                    'tags': 'startup, Ethiopia, proclamation, designation, grants, innovation, regulation',
                    'instructor': instructor,
                    'category': category,
                    'level': Course.Level.BEGINNER,
                    'status': Course.Status.PUBLISHED,
                    'price': 0,
                    'is_free': True,
                    'language': 'English',
                    'duration_hours': 7,
                },
            )
            expected_orders = set(range(1, len(LESSONS) + 1))
            course.sections.exclude(order__in=expected_orders).delete()
            for section_order, item in enumerate(LESSONS, start=1):
                section, _ = Section.objects.update_or_create(
                    course=course,
                    order=section_order,
                    defaults={'title': item['section']},
                )
                section.lessons.exclude(order=1).delete()
                lesson, _ = Lesson.objects.update_or_create(
                    section=section,
                    order=1,
                    defaults={
                        'title': item['title'],
                        'lesson_type': Lesson.LessonType.TEXT,
                        'content_text': format_learning_notes(f"{item['articles']}\n\n{item['content']}"),
                        'duration_minutes': 45,
                        'is_preview': section_order == 1,
                    },
                )
                quiz, _ = Quiz.objects.update_or_create(
                    lesson=lesson,
                    defaults={
                        'course': course,
                        'section': section,
                        'title': f"{item['title']} Quiz",
                        'passing_score_percent': 80,
                        'randomize_questions': False,
                    },
                )
                quiz.questions.all().delete()
                for question_order, (text, correct, distractors) in enumerate(item['questions'], start=1):
                    question = Question.objects.create(
                        quiz=quiz,
                        text=text,
                        question_type=Question.QuestionType.MULTIPLE_CHOICE,
                        order=question_order,
                        points=1,
                    )
                    answer_choices = build_answer_choices(correct, distractors, question_order)
                    for choice_order, choice_text in enumerate(answer_choices):
                        Choice.objects.create(
                            question=question,
                            text=choice_text,
                            is_correct=choice_text == correct,
                            order=choice_order,
                        )

        self.stdout.write(self.style.SUCCESS(
            f"Created course '{course.title}' (id={course.id}) with 7 lessons and 70 questions."
        ))

    def _get_instructor(self, identifier):
        queryset = User.objects.filter(role=User.Role.INSTRUCTOR)
        if identifier:
            try:
                user = queryset.get(pk=identifier)
            except (User.DoesNotExist, ValueError):
                user = queryset.filter(username=identifier).first()
            if not user:
                raise CommandError(f'Instructor not found: {identifier}')
            return user
        user = queryset.order_by('id').first()
        if not user:
            raise CommandError('No instructor exists. Create an instructor or pass --instructor.')
        return user