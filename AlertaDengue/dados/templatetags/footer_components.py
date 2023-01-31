from django import template

register = template.Library()


@register.inclusion_tag("components/main/footer.html", takes_context=True)
def githubsponsor_component(context):
    return context
