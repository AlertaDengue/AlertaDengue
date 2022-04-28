from django import template

register = template.Library()


@register.filter(name="lookup")
def cut(value, arg):
    return value[arg]
