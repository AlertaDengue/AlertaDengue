from django import template

register = template.Library()


@register.inclusion_tag("report_state/map_dengue.html", takes_context=True)
def map_chart_dengue(context):
    return context


@register.inclusion_tag("report_state/map_chik.html", takes_context=True)
def map_chart_chik(context):
    return context


@register.inclusion_tag("report_state/map_zika.html", takes_context=True)
def map_chart_zika(context):
    return context
