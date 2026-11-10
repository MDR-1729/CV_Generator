from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
import re

register = template.Library()


@register.filter
def split_lines(value):
    return [line.strip().lstrip("-*• ").strip() for line in value.splitlines() if line.strip()]


@register.filter
def format_resume_text(value):
    marker = re.compile(r"(\*\*\*.+?\*\*\*|\*\*.+?\*\*|\*.+?\*)")
    output = []
    position = 0
    for match in marker.finditer(value or ""):
        output.append(escape(value[position:match.start()]))
        token = match.group()
        if token.startswith("***"):
            output.append(f"<strong><em>{escape(token[3:-3])}</em></strong>")
        elif token.startswith("**"):
            output.append(f"<strong>{escape(token[2:-2])}</strong>")
        else:
            output.append(f"<em>{escape(token[1:-1])}</em>")
        position = match.end()
    output.append(escape((value or "")[position:]))
    return mark_safe("".join(output))


@register.filter
def resume_alignment_class(value):
    alignment = value if value in {"left", "center", "right", "justify"} else "left"
    return f"resume-align-{alignment}"
