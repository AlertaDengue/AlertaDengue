from django import template

register = template.Library()


@register.inclusion_tag('components/home/grid_charts.html', takes_context=True)
def state_component(context):

    return context
