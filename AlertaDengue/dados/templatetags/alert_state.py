import altair as alt
from django import template
from vega_datasets import data

register = template.Library()


@register.simple_tag
def generate_altair_chart() -> str:
    """
    Generates a standalone HTML representation of an Altair chart.

    Returns:
        str: The HTML representation of the Altair chart.
    """
    source = data.barley()
    chart = (
        alt.Chart(source)
        .mark_bar()
        .encode(column="year:O", x="yield", y="variety", color="site")
        .properties(width=220)
    )

    return chart.to_html()


@register.inclusion_tag(
    "components/alert_state/vis-echarts.html", takes_context=True
)
def vis_altair(context: dict) -> dict:
    """
    Prepares the context for the vis-echarts inclusion tag.

    Args:
        context (dict): The original template context.

    Returns:
        dict: The updated context including CID10 data and Altair chart HTML.
    """
    cid10_data = {"dengue": "A90", "chikungunya": "A920", "zika": "A928"}
    chart_html = generate_altair_chart()
    context.update({"CID10": cid10_data, "chart_altair_html": chart_html})
    return context
