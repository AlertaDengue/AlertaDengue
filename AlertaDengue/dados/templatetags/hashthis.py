# from urllib.parse import quote, unquote, urlencode

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(name="hashthis")
def hashthis(value):
    return hash(value)


@register.filter(name="unquote_str")
@stringfilter
def unquote_str(value):
    # print(unquote(value))
    return value.replace(" ", "_").replace("/", "-")
