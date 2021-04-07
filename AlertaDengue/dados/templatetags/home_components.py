from django import template

from .. import dbdata

register = template.Library()


# TODO: Change the states_abbv context to get keys() #issue
@register.inclusion_tag('components/home/collapse.html', takes_context=True)
def collapse_component(context):
    context['states_abbv'] = sorted(dbdata.STATE_NAME.values())
    return context


@register.inclusion_tag('components/home/color_code.html', takes_context=True)
def color_code_component(context):
    return context


@register.inclusion_tag('components/home/carousel.html', takes_context=True)
def carousel_component(context):
    return context


@register.inclusion_tag('components/home/legend.html', takes_context=True)
def legend_component(context):
    return context
