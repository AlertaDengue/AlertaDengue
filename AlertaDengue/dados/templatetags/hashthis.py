from django import template


register = template.Library()


@register.filter(name='hashthis')
def hashthis(value):
    return hash(value)
