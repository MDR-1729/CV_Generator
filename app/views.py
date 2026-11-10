from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .forms import ProfileForm, ResumeImportForm
from .models import Profile
from .resume_export import build_resume, create_docx, create_pdf
from .resume_import import ResumeImportError, extract_resume_data


def accept(request):
    import_form = ResumeImportForm()
    if request.method == "POST" and "import_resume" in request.POST:
        import_form = ResumeImportForm(request.POST, request.FILES)
        if import_form.is_valid():
            try:
                imported_data = extract_resume_data(import_form.cleaned_data["resume_file"])
            except ResumeImportError as error:
                import_form.add_error("resume_file", str(error))
            else:
                form = ProfileForm(initial=imported_data)
                return render(
                    request,
                    "app/accept.html",
                    {"form": form, "import_form": import_form, "imported": True},
                )
        return render(request, "app/accept.html", {"form": ProfileForm(), "import_form": import_form})

    form = ProfileForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        profile = form.save()
        return redirect("resume_detail", profile_id=profile.pk)
    return render(request, "app/accept.html", {"form": form, "import_form": import_form})


def resume(request, profile_id=None):
    if profile_id is None:
        return redirect("accept")
    profile = get_object_or_404(Profile, pk=profile_id)
    return render(request, "app/resume.html", {"profile": profile, "resume": build_resume(profile)})


def download_resume_pdf(request, profile_id):
    profile = get_object_or_404(Profile, pk=profile_id)
    output = BytesIO()
    create_pdf(profile, output)
    filename = slugify(profile.name) or "resume"
    response = HttpResponse(output.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}-resume.pdf"'
    return response


def download_resume_docx(request, profile_id):
    profile = get_object_or_404(Profile, pk=profile_id)
    output = BytesIO()
    create_docx(profile).save(output)
    filename = slugify(profile.name) or "resume"
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}-resume.docx"'
    return response