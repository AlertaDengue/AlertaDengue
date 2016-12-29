from django import template

register = template.Library()


@register.inclusion_tag('alert_state/age.html', takes_context=True)
def age_chart(context):
    return {}


@register.inclusion_tag('alert_state/disease.html', takes_context=True)
def disease_chart(context):
    return {}


@register.inclusion_tag('alert_state/gender.html', takes_context=True)
def gender_chart(context):
    return {}


@register.inclusion_tag('alert_state/map.html', takes_context=True)
def map_chart(context):
    return {}


@register.inclusion_tag('alert_state/date.html', takes_context=True)
def date_chart(context):
    return {}
