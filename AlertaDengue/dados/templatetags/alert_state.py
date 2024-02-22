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
    chart = context.get("map", None)
    if chart:
        return chart
    return ""
    # return f'<div id="vis"></div><script type="text/javascript">var spec = {chart_json}; vegaEmbed("#vis", spec);</script>'
