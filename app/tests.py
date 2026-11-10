from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from docx import Document
from pypdf import PdfReader
from .models import Profile
from .resume_export import build_resume

def make_text_pdf():
    content = b"BT /F1 12 Tf 72 720 Td (Alex Rivera) Tj 0 -18 Td (alex@example.com) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


class ResumeBuilderTests(TestCase):
    def test_builder_page_loads(self):
        response = self.client.get(reverse("accept"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A resume that feels like")
        self.assertContains(response, "LIVE PREVIEW")
        self.assertContains(response, "Already have a resume?")
        self.assertContains(response, 'class="builder-download-bar"')
        self.assertContains(response, "Save &amp; continue to downloads")
        self.assertContains(response, 'data-resume-preview-pages')
        self.assertContains(response, 'data-preview-value="summary" data-align-field="summary"')
        self.assertContains(response, "CGPA / marks")
        self.assertContains(response, 'data-text-toolbar')
        self.assertContains(response, "Target job role")
        self.assertContains(response, "Live project link")
        self.assertContains(response, "data-preview-link")
        self.assertContains(response, "LINKS")
        self.assertContains(response, "alignment-justify")
        self.assertContains(response, "Step 1 of 2: Save your resume")
        self.assertContains(response, 'class="preview-download-actions"')
        self.assertContains(response, 'data-preview-group="programming_languages,frameworks,databases,tools_technologies,skills" data-preview-page-block hidden')

    def test_txt_resume_import_prefills_profile_fields_without_saving(self):
        resume_text = (
            "Alex Morgan\n"
            "alex@example.com | +1 555 123 4567\n"
            "https://linkedin.com/in/alexmorgan\n"
            "https://github.com/alexmorgan\n"
            "https://alexmorgan.dev\n\n"
            "Professional Summary\n"
            "Software developer focused on accessible web products.\n\n"
            "Technical Skills\n"
            "Programming Languages: Python, JavaScript\n"
            "Frameworks: Django, React\n"
            "Databases: PostgreSQL\n"
            "Tools: Git, Docker\n\n"
            "Work Experience\n"
            "Example Co — Developer (2022–2025)\n"
            "- Improved service reliability by 20%.\n\n"
            "Projects\n"
            "Community Portal — Django, PostgreSQL\n"
            "- Built a portal for local organizations.\n\n"
            "Education\n"
            "B.S. Computer Science\n"
            "Example University, 2022\n"
            "CGPA: 8.6/10\n\n"
            "Certifications\n"
            "Cloud Fundamentals, 2024\n\n"
            "Achievements & Awards\n"
            "Winner, Regional Hackathon\n"
        )
        resume_file = SimpleUploadedFile(
            "resume.txt",
            resume_text.encode("utf-8"),
            content_type="text/plain",
        )

        response = self.client.post(
            reverse("accept"),
            {"import_resume": "1", "resume_file": resume_file},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["imported"])
        self.assertEqual(response.context["form"].initial["name"], "Alex Morgan")
        self.assertEqual(response.context["form"].initial["email"], "alex@example.com")
        self.assertEqual(response.context["form"].initial["phone_number"], "+1 555 123 4567")
        self.assertEqual(response.context["form"].initial["programming_languages"], "Python, JavaScript")
        self.assertEqual(response.context["form"].initial["frameworks"], "Django, React")
        self.assertEqual(response.context["form"].initial["databases"], "PostgreSQL")
        self.assertEqual(response.context["form"].initial["tools_technologies"], "Git, Docker")
        self.assertIn("20%", response.context["form"].initial["previous_work_experience"])
        self.assertEqual(response.context["form"].initial["graduation_year"], "2022")
        self.assertEqual(response.context["form"].initial["cgpa_marks"], "8.6/10")
        self.assertEqual(response.context["form"].initial["linkedin_url"], "https://linkedin.com/in/alexmorgan")
        self.assertEqual(response.context["form"].initial["github_url"], "https://github.com/alexmorgan")
        self.assertEqual(response.context["form"].initial["portfolio_url"], "https://alexmorgan.dev")
        self.assertEqual(Profile.objects.count(), 0)

    def test_docx_resume_import_prefills_profile(self):
        document_buffer = BytesIO()
        document = Document()
        document.add_paragraph("Jamie Rivera")
        document.add_paragraph("jamie@example.com")
        document.add_heading("Professional Summary", level=1)
        document.add_paragraph("Data engineer building dependable platforms.")
        document.add_heading("Education", level=1)
        document.add_paragraph("B.S. Computer Science")
        document.add_paragraph("North University, 2023")
        document.save(document_buffer)
        resume_file = SimpleUploadedFile(
            "resume.docx",
            document_buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        response = self.client.post(
            reverse("accept"),
            {"import_resume": "1", "resume_file": resume_file},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["imported"])
        self.assertEqual(response.context["form"].initial["name"], "Jamie Rivera")
        self.assertEqual(response.context["form"].initial["summary"], "Data engineer building dependable platforms.")
        self.assertEqual(response.context["form"].initial["graduation_year"], "2023")

    def test_pdf_resume_import_extracts_contact_information(self):
        resume_file = SimpleUploadedFile(
            "resume.pdf",
            make_text_pdf(),
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("accept"),
            {"import_resume": "1", "resume_file": resume_file},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["imported"])
        self.assertEqual(response.context["form"].initial["name"], "Alex Rivera")
        self.assertEqual(response.context["form"].initial["email"], "alex@example.com")

    def test_resume_import_rejects_unsupported_and_unreadable_files(self):
        for filename, contents in (("resume.rtf", b"resume"), ("broken.pdf", b"not a PDF")):
            with self.subTest(filename=filename):
                resume_file = SimpleUploadedFile(filename, contents)
                response = self.client.post(
                    reverse("accept"),
                    {"import_resume": "1", "resume_file": resume_file},
                )

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["import_form"].errors)
                self.assertEqual(Profile.objects.count(), 0)

    def test_import_keeps_work_and_internship_sections_separate(self):
        resume_text = (
            "Alex Morgan\n"
            "alex@example.com\n"
            "Work Experience\n"
            "Acme — Engineer (2023–2025)\n"
            "- Improved service reliability.\n"
            "Internship Experience\n"
            "Example Labs — Intern (2022)\n"
            "- Built a reporting tool.\n"
        )
        resume_file = SimpleUploadedFile("resume.txt", resume_text.encode("utf-8"))

        response = self.client.post(
            reverse("accept"),
            {"import_resume": "1", "resume_file": resume_file},
        )

        self.assertEqual(
            response.context["form"].initial["previous_work_experience"],
            "Acme — Engineer (2023–2025)\n- Improved service reliability.",
        )
        self.assertEqual(
            response.context["form"].initial["internship_experience"],
            "Example Labs — Intern (2022)\n- Built a reporting tool.",
        )

    def test_valid_submission_creates_profile_and_redirects(self):
        response = self.client.post(
            reverse("accept"),
            {
                "name": "Alex Morgan",
                "job_role": "Backend Developer",
                "email": "alex@example.com",
                "phone_number": "+1 555 123 4567",
                "linkedin_url": "https://linkedin.com/in/alexmorgan",
                "github_url": "https://github.com/alexmorgan",
                "portfolio_url": "https://alexmorgan.dev",
                "project_url": "https://projects.example.com/demo",
                "internship_url": "https://internships.example.com/work",
                "summary": "Product designer who loves solving problems.",
                "programming_languages": "Python, JavaScript",
                "frameworks": "Django, React",
                "databases": "PostgreSQL",
                "tools_technologies": "Git, Docker",
                "degree": "B.S. Design",
                "study_stream": "Product Design",
                "university": "State University",
                "school": "Lincoln High",
                "graduation_year": "2025",
                "cgpa_marks": "8.6/10",
                "text_alignment": '{"summary": "justify", "projects": "center"}',
                "previous_work_experience": "Product Designer at Acme",
                "internship_experience": "Design Intern at Studio",
                "projects": "Portfolio redesign",
                "certifications": "Google UX Design Certificate",
                "achievements_awards": "Hackathon winner",
                "skills": "Figma, Research, Prototyping",
            },
        )

        profile = Profile.objects.get(email="alex@example.com")
        self.assertRedirects(response, reverse("resume_detail", args=[profile.pk]))
        self.assertEqual(profile.study_stream, "Product Design")
        self.assertEqual(profile.job_role, "Backend Developer")
        self.assertEqual(profile.projects, "Portfolio redesign")
        self.assertEqual(profile.internship_experience, "Design Intern at Studio")
        self.assertEqual(profile.certifications, "Google UX Design Certificate")
        self.assertEqual(profile.programming_languages, "Python, JavaScript")
        self.assertEqual(profile.frameworks, "Django, React")
        self.assertEqual(profile.databases, "PostgreSQL")
        self.assertEqual(profile.tools_technologies, "Git, Docker")
        self.assertEqual(profile.portfolio_url, "https://alexmorgan.dev")
        self.assertEqual(profile.project_url, "https://projects.example.com/demo")
        self.assertEqual(profile.internship_url, "https://internships.example.com/work")
        self.assertEqual(profile.graduation_year, "2025")
        self.assertEqual(profile.cgpa_marks, "8.6/10")
        self.assertEqual(profile.text_alignment, {"summary": "justify", "projects": "center"})
        self.assertEqual(profile.achievements_awards, "Hackathon winner")
        self.assertEqual(profile.linkedin_url, "https://linkedin.com/in/alexmorgan")
        self.assertEqual(profile.github_url, "https://github.com/alexmorgan")

    def test_role_and_project_internship_links_render_in_resume_and_are_clickable_in_exports(self):
        profile = Profile.objects.create(
            name="Sam Rivera",
            job_role="**Backend** *Developer*",
            email="sam@example.com",
            projects="Demo service",
            project_url="https://projects.example.com/demo",
            internship_experience="Platform Intern",
            internship_url="https://internships.example.com/work",
            linkedin_url="https://linkedin.com/in/samrivera",
            github_url="https://github.com/samrivera",
        )

        page = self.client.get(reverse("resume_detail", args=[profile.pk]))
        self.assertContains(page, "<strong>Backend</strong>")
        self.assertContains(page, "<em>Developer</em>")
        self.assertContains(page, "https://projects.example.com/demo")
        self.assertContains(page, 'href="https://projects.example.com/demo"')
        self.assertContains(page, 'href="https://internships.example.com/work"')
        self.assertContains(page, "<h2>Contact Information</h2>")
        self.assertContains(page, '<strong>Email:</strong> sam@example.com')
        self.assertContains(page, 'href="https://linkedin.com/in/samrivera"')
        self.assertContains(page, 'rel="noopener noreferrer">LinkedIn</a>')
        self.assertContains(page, 'href="https://github.com/samrivera"')
        self.assertContains(page, 'rel="noopener noreferrer">GitHub</a>')
        self.assertNotContains(page, "<h2>Links</h2>")

        pdf_response = self.client.get(reverse("resume_download_pdf", args=[profile.pk]))
        pdf = PdfReader(BytesIO(pdf_response.content))
        annotations = [
            annotation.get_object().get("/A", {}).get("/URI")
            for page in pdf.pages
            for annotation in page.get("/Annots", [])
        ]
        self.assertIn("https://projects.example.com/demo", annotations)
        self.assertIn("https://internships.example.com/work", annotations)
        self.assertIn("https://linkedin.com/in/samrivera", annotations)
        self.assertIn("https://github.com/samrivera", annotations)
        extracted_pdf = "\n".join(page.extract_text() or "" for page in pdf.pages)
        self.assertIn("Email: sam@example.com | LinkedIn | GitHub", extracted_pdf)

        docx_response = self.client.get(reverse("resume_download_docx", args=[profile.pk]))
        document = Document(BytesIO(docx_response.content))
        hyperlink_targets = [
            relation.target_ref
            for relation in document.part.rels.values()
            if relation.reltype.endswith("/hyperlink")
        ]
        self.assertIn("https://projects.example.com/demo", hyperlink_targets)
        self.assertIn("https://internships.example.com/work", hyperlink_targets)
        self.assertIn("https://linkedin.com/in/samrivera", hyperlink_targets)
        self.assertIn("https://github.com/samrivera", hyperlink_targets)
        docx_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("Email: sam@example.com | LinkedIn | GitHub", docx_text)
        contact_paragraph = next(
            paragraph
            for paragraph in document.paragraphs
            if "Email: sam@example.com" in paragraph.text
        )
        self.assertEqual(contact_paragraph.alignment, 1)

    def test_education_details_render_as_one_line_in_resume_and_exports(self):
        profile = Profile.objects.create(
            name="Sam Rivera",
            email="education@example.com",
            degree="B.S. Computer Science",
            study_stream="Computer Science",
            university="State University",
            graduation_year="2025",
            school="Central High",
            cgpa_marks="8.6/10",
        )
        expected_education = (
            "B.S. Computer Science | Computer Science | State University | "
            "2025 | Central High | CGPA / Marks: 8.6/10"
        )

        education_items = next(
            items for heading, items in build_resume(profile)["sections"] if heading == "Education"
        )
        self.assertEqual(len(education_items), 1)
        self.assertEqual(education_items[0]["text"], expected_education)

        page = self.client.get(reverse("resume_detail", args=[profile.pk]))
        self.assertContains(page, f'<p class="resume-align-left">{expected_education}</p>')

        docx_response = self.client.get(reverse("resume_download_docx", args=[profile.pk]))
        document = Document(BytesIO(docx_response.content))
        education_paragraphs = [
            paragraph.text for paragraph in document.paragraphs if "B.S. Computer Science" in paragraph.text
        ]
        self.assertEqual(education_paragraphs, [expected_education])

        pdf_response = self.client.get(reverse("resume_download_pdf", args=[profile.pk]))
        extracted = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_response.content)).pages)
        for value in ("B.S. Computer Science", "State University", "Central High", "8.6/10"):
            self.assertIn(value, extracted)

    def test_formatting_alignment_applies_to_technical_and_education_fields(self):
        profile = Profile.objects.create(
            name="Taylor Kim",
            email="taylor@example.com",
            programming_languages="**Python**",
            degree="*B.S.* Computer Science",
            text_alignment={"programming_languages": "right", "degree": "center"},
        )

        response = self.client.get(reverse("resume_detail", args=[profile.pk]))
        self.assertContains(response, "resume-align-right")
        self.assertContains(response, "resume-align-center")
        self.assertContains(response, "<strong>Python</strong>")
        self.assertContains(response, "<em>B.S.</em>")

    def test_duplicate_email_shows_validation_error(self):
        Profile.objects.create(name="Existing Person", email="alex@example.com")

        response = self.client.post(
            reverse("accept"),
            {"name": "Alex Morgan", "email": "alex@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertContains(response, "Your resume hasn’t been created yet")
        self.assertContains(response, 'id="form-validation-summary"')
        self.assertEqual(Profile.objects.count(), 1)

    def test_saved_resume_displays_profile_and_print_action(self):
        profile = Profile.objects.create(
            name="Alex Morgan",
            email="alex@example.com",
            summary="Thoughtful product designer.",
            programming_languages="Python",
            frameworks="Django",
            databases="PostgreSQL",
            tools_technologies="Git",
            study_stream="Human-computer interaction",
            degree="B.S. Computer Science",
            university="State University",
            graduation_year="2025",
            internship_experience="Design intern at Studio",
            previous_work_experience="Acme — Engineer (2022–2024)\n- Improved response time by 30%.",
            projects="Accessibility toolkit\n- Built with Python and Django.",
            certifications="Google UX Design Certificate",
            achievements_awards="Hackathon winner",
            skills="Figma, Research",
            linkedin_url="https://linkedin.com/in/alexmorgan",
            github_url="https://github.com/alexmorgan",
            portfolio_url="https://alexmorgan.dev",
        )

        response = self.client.get(reverse("resume_detail", args=[profile.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alex Morgan")
        self.assertContains(response, "Thoughtful product designer.")
        self.assertContains(response, "Technical Skills")
        self.assertContains(response, "Python")
        self.assertContains(response, "Work Experience")
        self.assertContains(response, "Projects")
        self.assertContains(response, "Education")
        self.assertContains(response, "2025")
        self.assertContains(response, "Human-computer interaction")
        self.assertContains(response, "Design intern at Studio")
        self.assertContains(response, "Accessibility toolkit")
        self.assertContains(response, "Google UX Design Certificate")
        self.assertContains(response, "Achievements &amp; Awards")
        self.assertContains(response, "alexmorgan.dev")
        self.assertContains(response, "https://linkedin.com/in/alexmorgan")
        self.assertContains(response, "https://github.com/alexmorgan")
        self.assertContains(response, "Download PDF")
        self.assertContains(response, "Download DOCX")
        self.assertContains(response, 'class="resume-download-bar no-print"')
        self.assertNotContains(response, "<img")
        self.assertNotContains(response, "bootstrap-icons")
        content = response.content.decode()
        headings = [
            "Contact Information",
            "Professional Summary",
            "Technical Skills",
            "Work Experience",
            "Projects",
            "Education",
            "Certifications",
            "Achievements &amp; Awards",
        ]
        positions = [content.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))

    def test_duplicate_internship_lines_are_not_repeated_in_resume(self):
        shared_experience = "Coding Brains — Developer Intern (2026)\n- Built Django applications."
        profile = Profile.objects.create(
            name="Alex Morgan",
            email="duplicate@example.com",
            previous_work_experience=shared_experience,
            internship_experience=shared_experience,
        )

        response = self.client.get(reverse("resume_detail", args=[profile.pk]))
        content = response.content.decode()

        self.assertEqual(content.count("Coding Brains"), 1)
        self.assertNotIn("<h3>Internship Experience</h3>", content)

    def test_empty_resume_sections_are_omitted_from_page_and_downloads_stay_available(self):
        profile = Profile.objects.create(name="Taylor Reed", email="taylor@example.com")

        response = self.client.get(reverse("resume_detail", args=[profile.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contact Information")
        for heading in (
            "Professional Summary",
            "Technical Skills",
            "Work Experience",
            "Projects",
            "Education",
            "Certifications",
            "Achievements",
        ):
            self.assertNotContains(response, heading)
        self.assertContains(response, 'class="resume-download-bar no-print"')
        self.assertContains(response, reverse("resume_download_pdf", args=[profile.pk]))
        self.assertContains(response, reverse("resume_download_docx", args=[profile.pk]))

    def test_pdf_download_has_pdf_content_and_expected_section_order(self):
        profile = Profile.objects.create(
            name="Alex Morgan",
            email="pdf@example.com",
            summary="Professional summary",
            programming_languages="Python",
            previous_work_experience="Acme — Engineer\n- Improved reliability.",
            projects="Portfolio application",
            degree="B.S. Computer Science",
            certifications="Cloud certification",
            achievements_awards="Hackathon winner",
        )

        response = self.client.get(reverse("resume_download_pdf", args=[profile.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn('filename="alex-morgan-resume.pdf"', response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
        extracted = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.content)).pages)
        headings = [
            "CONTACT INFORMATION",
            "PROFESSIONAL SUMMARY",
            "TECHNICAL SKILLS",
            "WORK EXPERIENCE",
            "PROJECTS",
            "EDUCATION",
            "CERTIFICATIONS",
            "ACHIEVEMENTS & AWARDS",
        ]
        positions = [extracted.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Improved reliability.", extracted)

    def test_docx_download_contains_resume_content_in_order(self):
        profile = Profile.objects.create(
            name="Jamie Rivera",
            email="docx@example.com",
            summary="Data engineer.",
            projects="Data pipeline project",
            degree="B.S. Computer Science",
        )

        response = self.client.get(reverse("resume_download_docx", args=[profile.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertIn('filename="jamie-rivera-resume.docx"', response["Content-Disposition"])
        document = Document(BytesIO(response.content))
        content = "\n".join(paragraph.text for paragraph in document.paragraphs)
        headings = ["CONTACT INFORMATION", "PROFESSIONAL SUMMARY", "PROJECTS", "EDUCATION"]
        positions = [content.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Data pipeline project", content)

    def test_formatting_alignment_and_cgpa_are_included_in_saved_resume_and_exports(self):
        profile = Profile.objects.create(
            name="Jordan Lee",
            email="jordan@example.com",
            summary="Experienced **Python** developer with *strong* delivery.",
            projects="- Built a **secure** *analytics* platform.",
            degree="B.S. Computer Science",
            cgpa_marks="8.6/10",
            text_alignment={"summary": "justify", "projects": "center"},
        )

        page = self.client.get(reverse("resume_detail", args=[profile.pk]))
        self.assertContains(page, "<strong>Python</strong>")
        self.assertContains(page, "<em>strong</em>")
        self.assertContains(page, "CGPA / Marks:")
        self.assertContains(page, "resume-align-justify")

        docx_response = self.client.get(reverse("resume_download_docx", args=[profile.pk]))
        document = Document(BytesIO(docx_response.content))
        project_paragraph = next(paragraph for paragraph in document.paragraphs if "secure" in paragraph.text)
        self.assertEqual(project_paragraph.alignment, 1)
        self.assertTrue(next(run for run in project_paragraph.runs if "secure" in run.text).bold)
        self.assertTrue(next(run for run in project_paragraph.runs if "analytics" in run.text).italic)
        self.assertIn("8.6/10", "\n".join(paragraph.text for paragraph in document.paragraphs))

        pdf_response = self.client.get(reverse("resume_download_pdf", args=[profile.pk]))
        extracted = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_response.content)).pages)
        self.assertIn("Python", extracted)
        self.assertIn("secure", extracted)
        self.assertIn("8.6/10", extracted)

    def test_missing_resume_returns_404(self):
        response = self.client.get(reverse("resume_detail", args=[999]))

        self.assertEqual(response.status_code, 404)

    def test_non_four_digit_graduation_year_is_rejected(self):
        response = self.client.post(
            reverse("accept"),
            {
                "name": "Alex Morgan",
                "email": "invalid-year@example.com",
                "graduation_year": "25",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "four-digit graduation year")
        self.assertFalse(Profile.objects.filter(email="invalid-year@example.com").exists())

    def test_project_and_internship_links_require_http_or_https(self):
        form_data = {
            "name": "Alex Morgan",
            "email": "invalid-link@example.com",
            "project_url": "ftp://projects.example.com/demo",
            "internship_url": "javascript:alert(1)",
        }

        response = self.client.post(reverse("accept"), form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Use a full HTTP or HTTPS link.")
        self.assertFalse(Profile.objects.filter(email="invalid-link@example.com").exists())