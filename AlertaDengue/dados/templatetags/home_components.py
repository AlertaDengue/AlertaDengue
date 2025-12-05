from typing import Any, Dict

from dados.dbdata import STATE_NAME
from django import template

register = template.Library()


@register.inclusion_tag(
    "components/home/home_state_epi_section.html", takes_context=True
)
def home_state_epi_section(context: Dict[str, Any]) -> Dict[str, Any]:
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
    "components/home/home_uf_incidence_section.html", takes_context=True
)
def home_uf_incidence_component(context: Dict[str, Any]) -> Dict[str, Any]:
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


@register.inclusion_tag(
    "components/home/home_banners_section.html", takes_context=True
)
def home_banners_section(context: Dict[str, Any]) -> Dict[str, Any]:
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


@register.inclusion_tag(
    "components/home/home_functionalities_section.html", takes_context=True
)
def home_functionalities_section(context: Dict[str, Any]) -> Dict[str, Any]:
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


@register.inclusion_tag(
    "components/home/home_other_products_section.html", takes_context=True
)
def home_other_products_section(context: Dict[str, Any]) -> Dict[str, Any]:
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
