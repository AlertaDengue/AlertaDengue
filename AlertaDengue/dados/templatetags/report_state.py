from django import template

register = template.Library()


@register.inclusion_tag(
    "components/report_state/collapse.html", takes_context=True
)
def regional_collapse_component(context):
    return context
