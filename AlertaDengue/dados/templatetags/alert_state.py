from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def render_altair_chart(context):
    line_chart = context.get("line_chart", None)
    if line_chart:
        return line_chart
    return ""


@register.simple_tag
def render_altair_map(context):
    map_geom = context.get("map_geom", None)
    if map_geom:
        return map_geom
    return ""
