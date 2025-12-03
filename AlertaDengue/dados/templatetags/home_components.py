from typing import Any, Dict

from dados.dbdata import STATE_NAME
from django import template

register = template.Library()


@register.inclusion_tag(
    "components/home/epi_state_card.html", takes_context=True
)
def collapse_component(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Render the collapse component with the provided context.
    Parameters
    ----------
    context : Dict[str, Any]
        The context containing the data to be rendered.
    Returns
    -------
    Dict[str, Any]
        The updated context.
    """
    context["states_name"] = STATE_NAME
    context["states_abbv"] = list(STATE_NAME.keys())

    return context


@register.inclusion_tag(
    "components/home/banners_header.html", takes_context=True
)
@register.inclusion_tag("components/home/legend.html", takes_context=True)
def legend_component(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Render the legend component with the provided context.

    Parameters
    ----------
    context : Dict[str, Any]
        The context containing the data to be rendered.

    Returns
    -------
    Dict[str, Any]
        The updated context.

    """
    return context
