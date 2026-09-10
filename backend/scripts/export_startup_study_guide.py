from pathlib import Path
import os
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from courses.management.commands.seed_startup_proclamation import LESSONS


OUTPUT_PATH = BASE_DIR / 'media' / 'ethiopian_startup_proclamation_study_guide.docx'


def set_cell_shading(paragraph, fill='EAF4F1'):
    p_pr = paragraph._p.get_or_add_pPr()
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), fill)
    p_pr.append(shading)


def set_paragraph_border(paragraph, color='B7DCCF'):
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '8')
    bottom.set(qn('w:space'), '8')
    bottom.set(qn('w:color'), color)
    borders.append(bottom)
    p_pr.append(borders)


def set_keep_with_next(paragraph):
    p_pr = paragraph._p.get_or_add_pPr()
    keep = OxmlElement('w:keepNext')
    p_pr.append(keep)


def add_field(paragraph, field):
    run = paragraph.add_run()
    begin = OxmlElement('w:fldChar')
    begin.set(qn('w:fldCharType'), 'begin')
    instruction = OxmlElement('w:instrText')
    instruction.set(qn('xml:space'), 'preserve')
    instruction.text = field
    end = OxmlElement('w:fldChar')
    end.set(qn('w:fldCharType'), 'end')
    run._r.append(begin)
    run._r.append(instruction)
    run._r.append(end)


def configure_document(document):
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    styles = document.styles
    normal = styles['Normal']
    normal.font.name = 'Calibri'
    normal._element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(35, 45, 52)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.08

    for name, size, color, before, after in [
        ('Title', 26, '123B5D', 0, 10),
        ('Heading 1', 19, '123B5D', 18, 8),
        ('Heading 2', 15, '0F766E', 14, 5),
    ]:
        style = styles[name]
        style.font.name = 'Cambria'
        style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Cambria')
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    if 'Subtitle Custom' not in styles:
        subtitle = styles.add_style('Subtitle Custom', WD_STYLE_TYPE.PARAGRAPH)
    else:
        subtitle = styles['Subtitle Custom']
    subtitle.font.name = 'Calibri'
    subtitle._element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
    subtitle.font.size = Pt(14)
    subtitle.font.italic = True
    subtitle.font.color.rgb = RGBColor(83, 101, 109)
    subtitle.paragraph_format.space_after = Pt(18)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.style = styles['Normal']
    footer.add_run('Ethiopian Startup Proclamation Study Guide  |  Page ')
    add_field(footer, 'PAGE')


def add_body_paragraph(document, text):
    paragraph = document.add_paragraph(style='Normal')
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    match = re.match(r'^([^:]{2,60}:)\s*(.*)$', text)
    if match and not text.startswith(('http:', 'https:')):
        paragraph.add_run(match.group(1)).bold = True
        paragraph.add_run(match.group(2))
    else:
        paragraph.add_run(text)
    return paragraph


def add_callout(document, heading, text):
    paragraph = document.add_paragraph(style='Normal')
    paragraph.paragraph_format.left_indent = Inches(0.25)
    paragraph.paragraph_format.right_indent = Inches(0.15)
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(10)
    set_cell_shading(paragraph)
    set_paragraph_border(paragraph)
    run = paragraph.add_run(f'{heading}\n')
    run.bold = True
    run.font.name = 'Calibri'
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(15, 118, 110)
    body = paragraph.add_run(text)
    body.italic = True
    body.font.name = 'Calibri'
    body.font.size = Pt(11)
    return paragraph


def add_topic(document, topic_number, lesson):
    document.add_heading(f'Topic {topic_number}: {lesson["title"]}', level=1)
    intro = document.add_paragraph(style='Subtitle Custom')
    intro.add_run(lesson['articles'])
    intro.add_run('  |  Professional learning notes')

    lines = [line.strip() for line in lesson['content'].splitlines() if line.strip()]
    current_list = False
    for line in lines:
        upper = line.upper()
        if upper.startswith('STUDY CARD:'):
            heading = line.split(':', 1)[1].strip().title()
            document.add_heading(heading, level=2)
            continue
        article_match = re.match(r'ARTICLE(?:S)?\s+([0-9-]+)\s*-\s*(.+)', line, re.IGNORECASE)
        if article_match:
            document.add_heading(f'Article {article_match.group(1)} - {article_match.group(2).title()}', level=2)
            current_list = 'DEFINITIONS' in upper
            continue
        if upper in {'EXAM TAKEAWAY', 'KEY POINT', 'FINAL REVIEW'}:
            if document.paragraphs and document.paragraphs[-1].text:
                document.add_paragraph()
            continue
        if upper.endswith('TAKEAWAY') or upper.endswith('MAP') or upper.endswith('CHECKLIST') or upper.endswith('CARD') or upper.startswith('DECISION RULE') or upper.startswith('CONTROL QUESTIONS'):
            document.add_heading(line.title(), level=2)
            current_list = False
            continue
        if re.match(r'^(\d+\.|[-*])\s+', line):
            paragraph = document.add_paragraph(style='List Bullet' if line.startswith(('-', '*')) else 'List Number')
            paragraph.add_run(re.sub(r'^(\d+\.|[-*])\s+', '', line))
            continue
        if current_list and re.match(r'^[A-Z][A-Za-z -]{1,50}:', line):
            paragraph = document.add_paragraph(style='List Bullet')
            term, definition = line.split(':', 1)
            paragraph.add_run(f'{term}: ').bold = True
            paragraph.add_run(definition.strip())
            continue
        if upper.startswith('EXAM TAKEAWAY') or upper.startswith('KEY POINT'):
            add_callout(document, 'Exam Takeaway', line.split(':', 1)[-1].strip())
            continue
        add_body_paragraph(document, line)

    # Normalize the source's varying closing labels into one consistent study callout.
    takeaway_text = None
    for index, line in enumerate(lines):
        if line.upper() in {'EXAM TAKEAWAY', 'KEY POINT'} and index + 1 < len(lines):
            takeaway_text = lines[index + 1]
            break
    if not takeaway_text:
        takeaway_text = lines[-1]
    add_callout(document, 'Exam Takeaway', takeaway_text)


def build_document():
    document = Document()
    configure_document(document)

    title = document.add_paragraph(style='Title')
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run('Ethiopian Startup Proclamation')
    subtitle = document.add_paragraph(style='Subtitle Custom')
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run('Professional Course Study Guide')
    source = document.add_paragraph(style='Normal')
    source.alignment = WD_ALIGN_PARAGRAPH.CENTER
    source.add_run('Proclamation No. 1396/2025  |  Federal Negarit Gazette No. 63  |  August 2025').italic = True
    document.add_paragraph()

    document.add_heading('Why This Exists', level=1)
    add_body_paragraph(document, 'This guide organizes the Ethiopian Startup Proclamation into a practical learning sequence. It explains the legal framework for startup designation, ecosystem support, finance, incentives, regulatory experimentation, foreign participation, and protection of designated startup products and processes.')
    add_body_paragraph(document, 'Use each topic as a study unit: read the article notes, review the bold defined terms and deadline cards, then complete the corresponding lesson quiz in the course portal.')
    add_callout(document, 'Key Point', 'Designation is voluntary for operating as a startup or ecosystem builder, but it is the gateway to the incentives and privileges established by the Proclamation.')

    document.add_heading('Contents', level=1)
    for number, lesson in enumerate(LESSONS, start=1):
        paragraph = document.add_paragraph(style='List Number')
        paragraph.add_run(f'Topic {number}: {lesson["title"]} ({lesson["articles"]})')

    for number, lesson in enumerate(LESSONS, start=1):
        document.add_page_break()
        add_topic(document, number, lesson)

    document.add_page_break()
    document.add_heading('Final Review: Exam Takeaways', level=1)
    final_points = [
        'A startup is an early-stage person or group creating economic value through innovative, technology-enabled, scalable, or market-changing activity.',
        'The Ministry manages designations, the Digital Startup Portal, grants, coordination, and evaluation; the Council provides strategy, audit, transparency, and stakeholder oversight.',
        'Startup eligibility includes ownership evidence, at least 25 percent founder capital, and non-public-company status.',
        'Designation terms, renewal windows, correction periods, reporting deadlines, and objection rights are central compliance facts.',
        'Grants support approved early-stage work and cannot be diverted to unrelated personal expenses, debts, investments, or property.',
        'Tax, duty-free, and foreign-worker benefits remain subject to the applicable laws, Directives, verification, and approvals.',
        'The sandbox supports controlled innovation; protection prevents unauthorized replication while preserving intellectual-property and significant-improvement exceptions.',
    ]
    for point in final_points:
        paragraph = document.add_paragraph(style='List Bullet')
        paragraph.add_run(point)
    add_callout(document, 'Important Note', 'This study guide is educational material based on the supplied proclamation text. It is not a substitute for professional legal advice or the implementing Regulations and Directives.')

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT_PATH)
    print(OUTPUT_PATH)


if __name__ == '__main__':
    build_document()