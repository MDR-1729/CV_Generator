from urllib.parse import urlsplit

from django import forms
from .models import Profile

class ResumeImportForm(forms.Form):
    resume_file = forms.FileField(
        label="Choose an existing resume",
        help_text="PDF, Word (.docx), or plain text (.txt), up to 8 MB.",
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": ".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain",
        }),
    )

    def clean_resume_file(self):
        uploaded_file = self.cleaned_data["resume_file"]
        allowed_extensions = {".pdf", ".docx", ".txt"}
        filename_parts = uploaded_file.name.rsplit(".", 1)
        suffix = f".{filename_parts[-1].lower()}" if len(filename_parts) > 1 else ""
        if suffix not in allowed_extensions:
            raise forms.ValidationError("Choose a PDF, DOCX, or TXT resume.")
        if uploaded_file.size > 8 * 1024 * 1024:
            raise forms.ValidationError("Choose a resume smaller than 8 MB.")
        return uploaded_file


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = (
            "name",
            "job_role",
            "email",
            "phone_number",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "project_url",
            "internship_url",
            "summary",
            "programming_languages",
            "frameworks",
            "databases",
            "tools_technologies",
            "skills",
            "previous_work_experience",
            "internship_experience",
            "projects",
            "degree",
            "study_stream",
            "university",
            "school",
            "graduation_year",
            "cgpa_marks",
            "text_alignment",
            "certifications",
            "achievements_awards",
        )
        labels = {
            "name": "Full name",
            "job_role": "Target job role",
            "email": "Email address",
            "phone_number": "Phone number",
            "summary": "Professional summary",
            "programming_languages": "Programming languages",
            "frameworks": "Frameworks",
            "databases": "Databases",
            "tools_technologies": "Tools and technologies",
            "skills": "Other technical skills",
            "previous_work_experience": "Work experience",
            "internship_experience": "Internship experience",
            "projects": "Projects",
            "degree": "Degree or qualification",
            "study_stream": "Stream / field of study",
            "university": "University or college",
            "school": "School",
            "graduation_year": "Graduation year",
            "cgpa_marks": "CGPA / marks",
            "certifications": "Certifications",
            "linkedin_url": "LinkedIn profile",
            "github_url": "GitHub profile",
            "portfolio_url": "Portfolio",
            "project_url": "Live project link",
            "internship_url": "Internship link",
            "achievements_awards": "Achievements and awards",
        }
        help_texts = {
            "summary": "A few lines about your experience, strengths, and goals.",
            "programming_languages": "List languages, separated by commas.",
            "frameworks": "List frameworks and libraries, separated by commas.",
            "databases": "List databases and data platforms, separated by commas.",
            "tools_technologies": "List tools and technologies, separated by commas.",
            "study_stream": "For example: Computer Science, Commerce, or Graphic Design.",
            "previous_work_experience": "For each role, include company, job title, and dates, then add achievements on separate lines.",
            "internship_experience": "Use the same format as work experience: organization, role, dates, and achievement lines.",
            "projects": "For each project, include its name, technologies, description, and your contributions on separate lines.",
            "certifications": "Add certification names and issuing organizations, one per line.",
            "skills": "Optional additional technical skills, separated by commas.",
            "graduation_year": "Enter a four-digit year, for example 2025.",
            "cgpa_marks": "Optional. Include your score and scale, for example 8.6/10 or 82%.",
            "achievements_awards": "Add technical accomplishments, awards, or recognition, one per line.",
            "job_role": "The position you are applying for, for example Backend Developer.",
            "linkedin_url": "Shown as a clickable link in the resume’s Links section.",
            "github_url": "Shown as a clickable link in the resume’s Links section.",
            "portfolio_url": "Shown as a clickable link in the resume’s Links section.",
            "project_url": "Optional. Add the live URL for your project; it will be clickable in the PDF.",
            "internship_url": "Optional. Add a link related to your internship; it will be clickable in the PDF.",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Alex Morgan", "autocomplete": "name", "data-preview": "name", "data-format-editable": "true"}),
            "job_role": forms.TextInput(attrs={"placeholder": "e.g. Backend Developer", "data-preview": "job_role", "data-format-editable": "true"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email", "data-preview": "email"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "e.g. +1 555 123 4567", "autocomplete": "tel", "data-preview": "phone_number"}),
            "summary": forms.Textarea(attrs={"placeholder": "Write a short introduction that makes a great first impression.", "rows": 4, "data-preview": "summary", "data-format-editable": "true"}),
            "programming_languages": forms.TextInput(attrs={"placeholder": "Python, JavaScript, Java", "data-preview": "programming_languages", "data-format-editable": "true"}),
            "frameworks": forms.TextInput(attrs={"placeholder": "Django, React, Node.js", "data-preview": "frameworks", "data-format-editable": "true"}),
            "databases": forms.TextInput(attrs={"placeholder": "PostgreSQL, MySQL, MongoDB", "data-preview": "databases", "data-format-editable": "true"}),
            "tools_technologies": forms.TextInput(attrs={"placeholder": "Git, Docker, AWS, Linux", "data-preview": "tools_technologies", "data-format-editable": "true"}),
            "skills": forms.TextInput(attrs={"placeholder": "Additional skills, separated by commas", "data-preview": "skills", "data-format-editable": "true"}),
            "previous_work_experience": forms.Textarea(attrs={"placeholder": "Company — Job Title (2022–2025)\n- Led a redesign that improved onboarding for 30,000+ users.\n- Reduced task completion time by 25%.", "rows": 5, "data-preview": "experience", "data-format-editable": "true"}),
            "internship_experience": forms.Textarea(attrs={"placeholder": "Company — Intern, Engineering (Summer 2024)\n- Built a dashboard used by 12 teams.", "rows": 4, "data-preview": "internship_experience", "data-format-editable": "true"}),
            "projects": forms.Textarea(attrs={"placeholder": "Project name — Technologies: Django, PostgreSQL\n- Built an application for managing community events.\n- Implemented search used by 500+ members.", "rows": 4, "data-preview": "projects", "data-format-editable": "true"}),
            "degree": forms.TextInput(attrs={"placeholder": "e.g. B.S. Computer Science", "data-preview": "degree", "data-format-editable": "true"}),
            "study_stream": forms.TextInput(attrs={"placeholder": "e.g. Computer Science", "data-preview": "study_stream", "data-format-editable": "true"}),
            "university": forms.TextInput(attrs={"placeholder": "e.g. State University", "data-preview": "university", "data-format-editable": "true"}),
            "school": forms.TextInput(attrs={"placeholder": "e.g. Lincoln High School", "data-preview": "school", "data-format-editable": "true"}),
            "graduation_year": forms.TextInput(attrs={"placeholder": "e.g. 2025", "inputmode": "numeric", "maxlength": "4", "data-preview": "graduation_year", "data-format-editable": "true"}),
            "cgpa_marks": forms.TextInput(attrs={"placeholder": "e.g. 8.6/10 or 82%", "data-preview": "cgpa_marks", "data-format-editable": "true"}),
            "text_alignment": forms.HiddenInput(),
            "certifications": forms.Textarea(attrs={"placeholder": "Google UX Design Certificate · Google, 2025", "rows": 3, "data-preview": "certifications", "data-format-editable": "true"}),
            "achievements_awards": forms.Textarea(attrs={"placeholder": "Winner, University Hackathon — built an award-winning accessibility tool.\nDean's List, 2024.", "rows": 3, "data-preview": "achievements_awards", "data-format-editable": "true"}),
            "linkedin_url": forms.URLInput(attrs={"placeholder": "https://linkedin.com/in/yourname", "data-preview": "linkedin_url"}),
            "github_url": forms.URLInput(attrs={"placeholder": "https://github.com/yourname", "data-preview": "github_url"}),
            "portfolio_url": forms.URLInput(attrs={"placeholder": "https://yourportfolio.com", "data-preview": "portfolio_url"}),
            "project_url": forms.URLInput(attrs={"placeholder": "https://yourproject.example.com", "data-preview": "project_url"}),
            "internship_url": forms.URLInput(attrs={"placeholder": "https://example.com/internship-work", "data-preview": "internship_url"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        alignment = (kwargs.get("initial") or {}).get("text_alignment")
        if alignment is None and self.instance.pk:
            alignment = self.instance.text_alignment
        self.fields["text_alignment"].initial = alignment or {}
        self.fields["graduation_year"].validators.append(self.validate_graduation_year)

    def clean_text_alignment(self):
        alignment = self.cleaned_data.get("text_alignment") or {}
        supported_fields = {
            "name", "job_role", "summary", "programming_languages", "frameworks",
            "databases", "tools_technologies", "skills", "previous_work_experience",
            "internship_experience", "projects", "degree", "study_stream", "university",
            "school", "graduation_year", "cgpa_marks", "certifications",
            "achievements_awards",
        }
        valid_alignments = {"left", "center", "right", "justify"}
        if not isinstance(alignment, dict) or any(
            field not in supported_fields or value not in valid_alignments
            for field, value in alignment.items()
        ):
            raise forms.ValidationError("Choose a valid text alignment.")
        return alignment

    def clean_project_url(self):
        return self._clean_web_link("project_url")

    def clean_internship_url(self):
        return self._clean_web_link("internship_url")

    def _clean_web_link(self, field_name):
        value = self.cleaned_data.get(field_name)
        if value and urlsplit(value).scheme not in {"http", "https"}:
            raise forms.ValidationError("Use a full HTTP or HTTPS link.")
        return value

    @staticmethod
    def validate_graduation_year(value):
        if value and (len(value) != 4 or not value.isdigit()):
            raise forms.ValidationError("Enter a four-digit graduation year.")