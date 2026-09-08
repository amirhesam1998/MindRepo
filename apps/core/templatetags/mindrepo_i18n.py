from django import template

from apps.core.i18n import translate_text


register = template.Library()


@register.filter
def tr(value):
    return translate_text(value)
