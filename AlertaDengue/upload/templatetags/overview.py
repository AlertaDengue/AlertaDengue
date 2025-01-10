from django import template

register = template.Library()


@register.filter
def log_type(log: str) -> str:
    if log.startswith("SUCCESS"):
        return "log-success"
    elif log.startswith("WARNING"):
        return "log-warning"
    else:
        return "log-info"
