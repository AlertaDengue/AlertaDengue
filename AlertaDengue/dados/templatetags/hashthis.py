# from urllib.parse import quote, unquote, urlencode

from django import template

register = template.Library()


@register.filter(name="hashthis")
def hashthis(value):
    return hash(value)
