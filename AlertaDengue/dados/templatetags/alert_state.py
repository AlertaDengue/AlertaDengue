import altair as alt
from django import template
from vega_datasets import data
import pandas as pd

from vega_datasets import data as vega_data

register = template.Library()


@register.simple_tag


def generate_altair_line_chart() -> str:
    """
    Generates a standalone HTML representation of an Altair line chart.

    Returns:
        str: The HTML representation of the Altair line chart.
    """
    # Load the data into a DataFrame and then parse the date column
    source_df = pd.DataFrame(vega_data.stocks())
    source_df['date'] = pd.to_datetime(source_df['date'], format='%Y-%m-%d')

    chart = (
        alt.Chart(source_df)
        .mark_line(interpolate="monotone")
        .encode(x="date:T", y="price:Q", color="symbol:N")
        .properties(width="container")  # Set width to "container"

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
    altair_line_chart = generate_altair_line_chart()
    context.update(
        {
            "CID10": cid10_data, 
            "altair_line_chart": altair_line_chart,
        }
        )
    return context
