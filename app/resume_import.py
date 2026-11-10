import re
import zipfile
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

class ResumeImportError(ValueError):
    pass

SECTION_NAMES = {
    "summary": {"summary", "professional summary", "profile", "about me", "objective", "career objective"},
    "skills": {"skills", "technical skills", "technical expertise", "core competencies"},
    "experience": {"experience", "work experience", "employment", "employment history", "professional experience"},
    "internship": {"internship", "internships", "internship experience"},
    "projects": {"projects", "personal projects", "academic projects", "selected projects"},
    "education": {"education", "academic background", "educational background"},
    "certifications": {"certifications", "certificates", "courses", "licenses and certifications"},
    "achievements": {"achievements", "awards", "honors", "honours", "achievements and awards"},
}
HEADING_LOOKUP = {name: section for section, names in SECTION_NAMES.items() for name in names}
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>]+", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
SKILL_CATEGORIES = {
    "programming_languages": {"programming languages", "languages", "programming"},
    "frameworks": {"frameworks", "libraries"},
    "databases": {"databases", "database"},
    "tools_technologies": {"tools", "technologies", "tools and technologies", "platforms"},
}

def _read_text(uploaded_file):
    suffix = uploaded_file.name.rsplit(".", 1)[-1].lower()
    if suffix == "txt":
        text = uploaded_file.read().decode("utf-8-sig", errors="replace")
    elif suffix == "pdf":
        try:
            reader = PdfReader(uploaded_file, strict=False)
            if reader.is_encrypted:
                raise ResumeImportError("This PDF is password-protected. Upload an unlocked copy.")
            if len(reader.pages) > 30:
                raise ResumeImportError("This resume has more than 30 pages. Upload a shorter copy.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except PdfReadError as error:
            raise ResumeImportError("We couldn’t read this PDF. Try exporting it again or upload a DOCX/TXT copy.") from error
    elif suffix == "docx":
        try:
            document = Document(uploaded_file)
        except (PackageNotFoundError, zipfile.BadZipFile) as error:
            raise ResumeImportError("We couldn’t read this Word document. Please upload a valid DOCX file.") from error
        text_parts = [paragraph.text for paragraph in document.paragraphs]
        text_parts.extend(
            cell.text
            for table in document.tables
            for row in table.rows
            for cell in row.cells
        )
        text = "\n".join(text_parts)
    else:
        raise ResumeImportError("Choose a PDF, DOCX, or TXT resume.")
    if len(text) > 100_000:
        raise ResumeImportError("This resume contains too much text to import (limit: 100,000 characters).")
    if not text.strip():
        raise ResumeImportError("No readable text was found. Scanned PDFs need OCR; try a text-based PDF or DOCX.")
    return text

def _section_heading(line):
    normalized = re.sub(r"[\s:|—–-]+$", "", line.strip().lower())
    normalized = re.sub(r"^[\d.)\s]+", "", normalized)
    return HEADING_LOOKUP.get(normalized)

def _clean_url(url):
    return url.rstrip(".,;:)]}")

def extract_resume_data(uploaded_file):
    text = _read_text(uploaded_file)
    sections = {"contact": []}
    current_section = "contact"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = _section_heading(line)
        if heading:
            current_section = heading
            sections.setdefault(current_section, [])
        else:
            sections.setdefault(current_section, []).append(line)

    all_text = "\n".join(line for lines in sections.values() for line in lines)
    contact_text = "\n".join(sections.get("contact", []))
    data = {}

    for field, pattern in (("email", EMAIL_PATTERN), ("phone_number", PHONE_PATTERN)):
        match = pattern.search(contact_text)
        if match:
            data[field] = match.group(0).strip()

    urls = [_clean_url(match.group(0)) for match in URL_PATTERN.finditer(all_text)]
    for url in urls:
        lowered = url.lower()
        normalized = url if lowered.startswith(("https://", "http://")) else f"https://{url}"
        if "linkedin.com/" in lowered and "linkedin_url" not in data:
            data["linkedin_url"] = normalized
        elif "github.com/" in lowered and "github_url" not in data:
            data["github_url"] = normalized
        elif "portfolio_url" not in data:
            data["portfolio_url"] = normalized

    contact_lines = sections.get("contact", [])
    for line in contact_lines:
        if EMAIL_PATTERN.search(line) or URL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        if line.lower() not in {"resume", "curriculum vitae", "cv"}:
            data["name"] = line
            break

    for field, section in (
        ("summary", "summary"),
        ("previous_work_experience", "experience"),
        ("internship_experience", "internship"),
        ("projects", "projects"),
        ("certifications", "certifications"),
        ("achievements_awards", "achievements"),
    ):
        lines = sections.get(section, [])
        if lines:
            data[field] = "\n".join(lines)

    skills_lines = sections.get("skills", [])
    categorized_lines = []
    other_skills = []
    for line in skills_lines:
        label, separator, value = line.partition(":")
        normalized_label = re.sub(r"^[\s*•\-]+", "", label).strip().lower()
        category = next(
            (field for field, names in SKILL_CATEGORIES.items() if normalized_label in names),
            None,
        ) if separator else None
        if category and value.strip():
            data[category] = value.strip()
            categorized_lines.append(line)
        elif line.strip():
            other_skills.append(line)
    if other_skills:
        data["skills"] = ", ".join(other_skills)
    elif skills_lines and not categorized_lines:
        data["skills"] = ", ".join(skills_lines)

    education_lines = sections.get("education", [])
    institution_terms = ("university", "college", "institute", "school")
    degree_terms = ("bachelor", "master", "ph.d", "phd", "associate", "diploma", "b.s.", "b.a.", "b.tech", "m.s.", "m.a.", "m.tech")
    for line in education_lines:
        score = re.search(
            r"\b(?:cgpa|gpa|marks?|percentage|score)\s*[:\-]?\s*([\d.]+\s*(?:/\s*[\d.]+|%)?)",
            line,
            re.IGNORECASE,
        )
        if score and "cgpa_marks" not in data:
            data["cgpa_marks"] = score.group(1).strip()
        if "degree" not in data and any(term in line.lower() for term in degree_terms):
            data["degree"] = line
        if "university" not in data and any(term in line.lower() for term in institution_terms):
            data["university"] = line
        if "graduation_year" not in data:
            year = YEAR_PATTERN.search(line)
            if year:
                data["graduation_year"] = year.group(0)
    return data