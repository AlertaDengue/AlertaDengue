from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def render_altair_chart(context):
    chart = context.get("chart", None)
    if chart:
        return chart
    return ""


@register.simple_tag
def render_altair_map(context):
    map = context.get("map", None)
    if map:
        return map
    return ""
