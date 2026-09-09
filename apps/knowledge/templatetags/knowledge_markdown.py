from django import template
from django.utils.safestring import mark_safe

from apps.knowledge.markdown import render_markdown


register = template.Library()


@register.filter(is_safe=True)
def markdown(value):
    return mark_safe(render_markdown(value))  # trusted only after centralized sanitization
