import re
from xml.sax.saxutils import escape
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
)

def _lines(value, alignment="left"):
    result = []
    for line in (value or "").splitlines():
        line = line.strip()
        if not line:
            continue
        is_bullet = line.startswith(("- ", "* ", "•"))
        if is_bullet:
            line = line[1:].strip()
        if line:
            result.append({"text": line, "bullet": is_bullet, "alignment": alignment})
    return result

def _formatted_runs(text):
    marker = re.compile(r"(\*\*\*.+?\*\*\*|\*\*.+?\*\*|\*.+?\*)")
    runs = []
    position = 0
    for match in marker.finditer(text):
        if match.start() > position:
            runs.append((text[position:match.start()], False, False))
        token = match.group()
        if token.startswith("***"):
            runs.append((token[3:-3], True, True))
        elif token.startswith("**"):
            runs.append((token[2:-2], True, False))
        else:
            runs.append((token[1:-1], False, True))
        position = match.end()
    if position < len(text):
        runs.append((text[position:], False, False))
    return runs

def _reportlab_markup(text):
    return "".join(
        f"<b><i>{escape(value)}</i></b>" if bold and italic
        else f"<b>{escape(value)}</b>" if bold
        else f"<i>{escape(value)}</i>" if italic
        else escape(value)
        for value, bold, italic in _formatted_runs(text)
    )

def _set_alignment(paragraph, alignment):
    paragraph.alignment = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }.get(alignment, WD_ALIGN_PARAGRAPH.LEFT)

def _add_formatted_runs(paragraph, text):
    for value, bold, italic in _formatted_runs(text):
        run = paragraph.add_run(value)
        run.bold = bold
        run.italic = italic

def _add_hyperlink(paragraph, url, text):
    relationship_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    properties.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    properties.append(underline)
    run.append(properties)
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.append(text_node)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)

def _normalized_lines(items):
    return {item["text"].casefold().strip() for item in items}

def build_resume(profile):
    alignments = profile.text_alignment or {}
    experience = _lines(profile.previous_work_experience, alignments.get("previous_work_experience", "left"))
    internship = _lines(profile.internship_experience, alignments.get("internship_experience", "left"))
    existing_experience = _normalized_lines(experience)
    internship = [item for item in internship if item["text"].casefold().strip() not in existing_experience]

    contact_items = [
        {"label": "Email", "text": profile.email},
        {"label": "Phone", "text": profile.phone_number},
        {"label": "LinkedIn", "text": "LinkedIn", "url": profile.linkedin_url},
        {"label": "GitHub", "text": "GitHub", "url": profile.github_url},
    ]
    contact_items = [item for item in contact_items if item.get("url") or item.get("text")]
    contact = [
        f"{item['label']}: {item['text']}" if not item.get("url") else item["label"]
        for item in contact_items
    ]

    links = [
        {
            "label": label,
            "text": value,
            "url": value,
            "bullet": False,
            "alignment": "left",
        }
        for label, value in (
            ("Portfolio", profile.portfolio_url),
        )
        if value
    ]

    education_fields = (
        ("degree", profile.degree),
        ("study_stream", profile.study_stream),
        ("university", profile.university),
        ("graduation_year", profile.graduation_year),
        ("school", profile.school),
    )
    education_parts = [value for _, value in education_fields if value]
    if profile.cgpa_marks:
        education_parts.append(f"CGPA / Marks: {profile.cgpa_marks}")
    education_alignment = next(
        (alignments.get(field, "left") for field, value in education_fields if value),
        alignments.get("cgpa_marks", "left"),
    )

    sections = [
        (
            "Contact Information",
            [{"text": " | ".join(contact), "bullet": False, "contact_items": contact_items}] if contact_items else [],
        ),
        ("Links", links),
        ("Professional Summary", _lines(profile.summary, alignments.get("summary", "left"))),
        (
            "Technical Skills",
            [
                {"label": label, "text": value, "bullet": False, "alignment": alignments.get(field, "left")}
                for field, label, value in (
                    ("programming_languages", "Programming Languages", profile.programming_languages),
                    ("frameworks", "Frameworks", profile.frameworks),
                    ("databases", "Databases", profile.databases),
                    ("tools_technologies", "Tools & Technologies", profile.tools_technologies),
                    ("skills", "Additional Skills", profile.skills),
                )
                if value
            ],
        ),
        ("Work Experience", experience),
        (
            "Projects",
            _lines(profile.projects, alignments.get("projects", "left"))
            + (
                [{
                    "label": "Live project",
                    "text": profile.project_url,
                    "url": profile.project_url,
                    "bullet": False,
                    "alignment": alignments.get("projects", "left"),
                }]
                if profile.project_url else []
            ),
        ),
        (
            "Education",
            [{
                "text": " | ".join(education_parts),
                "bullet": False,
                "alignment": education_alignment,
            }] if education_parts else [],
        ),
        ("Certifications", _lines(profile.certifications, alignments.get("certifications", "left"))),
        ("Achievements & Awards", _lines(profile.achievements_awards, alignments.get("achievements_awards", "left"))),
    ]

    if internship or profile.internship_url:
        work_index = next(index for index, (heading, _) in enumerate(sections) if heading == "Work Experience")
        sections[work_index][1].append({"text": "Internship Experience", "subheading": True})
        sections[work_index][1].extend(internship)
        if profile.internship_url:
            sections[work_index][1].append({
                "label": "Internship link",
                "text": profile.internship_url,
                "url": profile.internship_url,
                "bullet": False,
                "alignment": alignments.get("internship_experience", "left"),
            })

    return {
        "name": profile.name,
        "job_role": profile.job_role,
        "job_role_alignment": alignments.get("job_role", "left"),
        "name_alignment": alignments.get("name", "center"),
        "contact": " | ".join(contact),
        "sections": [(heading, items) for heading, items in sections if items],
    }

def create_docx(profile):
    resume = build_resume(profile)
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)

    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9)
    normal.paragraph_format.space_after = Pt(2)

    title = document.add_paragraph()
    title.alignment = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }.get(resume["name_alignment"], WD_ALIGN_PARAGRAPH.CENTER)
    title.paragraph_format.space_after = Pt(2)
    _add_formatted_runs(title, resume["name"])
    for title_run in title.runs:
        title_run.bold = True
        title_run.font.name = "Arial"
        title_run.font.size = Pt(18)

    if resume["job_role"]:
        role_paragraph = document.add_paragraph()
        _set_alignment(role_paragraph, resume["job_role_alignment"])
        role_paragraph.paragraph_format.space_after = Pt(3)
        _add_formatted_runs(role_paragraph, resume["job_role"])
        for role_run in role_paragraph.runs:
            role_run.bold = True

    for section_index, (heading, items) in enumerate(resume["sections"]):
        heading_paragraph = document.add_paragraph()
        heading_paragraph.paragraph_format.space_before = Pt(6)
        heading_paragraph.paragraph_format.space_after = Pt(2)
        heading_run = heading_paragraph.add_run(heading.upper())
        heading_run.bold = True
        heading_run.font.name = "Arial"
        heading_run.font.size = Pt(10)

        for item in items:
            if item.get("contact_items"):
                paragraph = document.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.space_after = Pt(1)
                for index, contact_item in enumerate(item["contact_items"]):
                    if index:
                        paragraph.add_run(" | ")
                    if contact_item.get("url"):
                        _add_hyperlink(paragraph, contact_item["url"], contact_item["label"])
                    else:
                        paragraph.add_run(f"{contact_item['label']}: {contact_item['text']}")
            elif item.get("subheading"):
                paragraph = document.add_paragraph()
                paragraph.paragraph_format.space_before = Pt(2)
                run = paragraph.add_run(item["text"])
                run.bold = True
            else:
                paragraph = document.add_paragraph(style="List Bullet" if item["bullet"] else "Normal")
                paragraph.paragraph_format.space_after = Pt(1)
                _set_alignment(paragraph, item.get("alignment", "left"))
                if item.get("label"):
                    run = paragraph.add_run(f"{item['label']}: ")
                    run.bold = True
                if item.get("url"):
                    _add_hyperlink(paragraph, item["url"], item["text"])
                else:
                    _add_formatted_runs(paragraph, item["text"])
        if items and section_index > 0:
            paragraph_properties = paragraph._p.get_or_add_pPr()
            borders = paragraph_properties.find(qn("w:pBdr"))
            if borders is None:
                borders = OxmlElement("w:pBdr")
                paragraph_properties.append(borders)
            bottom_border = OxmlElement("w:bottom")
            bottom_border.set(qn("w:val"), "single")
            bottom_border.set(qn("w:sz"), "4")
            bottom_border.set(qn("w:space"), "3")
            bottom_border.set(qn("w:color"), "B7BEC9")
            borders.append(bottom_border)
    return document

def create_pdf(profile, output):
    resume = build_resume(profile)
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=13 * mm,
        bottomMargin=13 * mm,
        title=f"{resume['name']} - Resume",
        author=resume["name"],
    )
    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ResumeTitle",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=2,
    )
    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        spaceAfter=7,
    )
    heading_style = ParagraphStyle(
        "ResumeHeading",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=11,
        textColor=colors.black,
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "ResumeBody",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        textColor=colors.black,
        spaceAfter=2,
    )
    alignment_styles = {
        "left": body_style,
        "center": ParagraphStyle("ResumeBodyCenter", parent=body_style, alignment=TA_CENTER),
        "right": ParagraphStyle("ResumeBodyRight", parent=body_style, alignment=TA_RIGHT),
        "justify": ParagraphStyle("ResumeBodyJustify", parent=body_style, alignment=TA_JUSTIFY),
    }
    bullet_styles = {
        alignment: ParagraphStyle(
            f"ResumeBullet-{alignment}",
            parent=style,
            leftIndent=11,
            firstLineIndent=-8,
            spaceAfter=1,
        )
        for alignment, style in alignment_styles.items()
    }
    subheading_style = ParagraphStyle(
        "ResumeSubheading",
        parent=body_style,
        fontName="Helvetica-Bold",
        spaceBefore=2,
        keepWithNext=True,
    )

    title_style.alignment = {
        "left": 0,
        "center": TA_CENTER,
        "right": TA_RIGHT,
        "justify": TA_JUSTIFY,
    }.get(resume["name_alignment"], TA_CENTER)
    story = [Paragraph(_reportlab_markup(resume["name"]), title_style)]
    if resume["job_role"]:
        role_style = ParagraphStyle(
            "ResumeTargetRole",
            parent=contact_style,
            alignment={
                "left": 0,
                "center": TA_CENTER,
                "right": TA_RIGHT,
                "justify": TA_JUSTIFY,
            }.get(resume["job_role_alignment"], TA_CENTER),
            fontName="Helvetica-Bold",
            textColor=colors.black,
        )
        story.append(Paragraph(_reportlab_markup(resume["job_role"]), role_style))
    for section_index, (heading, items) in enumerate(resume["sections"]):
        section_flowables = [Paragraph(escape(heading.upper()), heading_style)]
        for item in items:
            if item.get("contact_items"):
                contact_markup = []
                for contact_item in item["contact_items"]:
                    if contact_markup:
                        contact_markup.append(" | ")
                    if contact_item.get("url"):
                        safe_url = escape(contact_item["url"], {'"': "&quot;"})
                        contact_markup.append(
                            f"<link href=\"{safe_url}\">{escape(contact_item['label'])}</link>"
                        )
                    else:
                        contact_markup.append(
                            f"<b>{escape(contact_item['label'])}:</b> {escape(contact_item['text'])}"
                        )
                section_flowables.append(Paragraph("".join(contact_markup), contact_style))
            elif item.get("subheading"):
                section_flowables.append(Paragraph(escape(item["text"]), subheading_style))
            else:
                alignment = item.get("alignment", "left")
                style = (bullet_styles if item["bullet"] else alignment_styles).get(alignment, body_style)
                text = (
                    f"<b>{escape(item['label'])}:</b> {_reportlab_markup(item['text'])}"
                    if item.get("label")
                    else _reportlab_markup(item["text"])
                )
                if item.get("url"):
                    safe_url = escape(item["url"], {'"': "&quot;"})
                    linked_text = _reportlab_markup(item["text"])
                    text = f"<b>{escape(item['label'])}:</b> <link href=\"{safe_url}\">{linked_text}</link>"
                section_flowables.append(
                    Paragraph(text, style, bulletText="-" if item["bullet"] else None)
                )
        if 0 < section_index < len(resume["sections"]) - 1:
            section_flowables.append(
                HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#B7BEC9"), spaceBefore=2, spaceAfter=2)
            )
        story.append(KeepTogether(section_flowables))
    document.build(story)