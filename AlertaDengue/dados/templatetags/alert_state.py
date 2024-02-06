import altair as alt
import pandas as pd
from django import template

register = template.Library()


@register.simple_tag
def generate_altair_line_chart() -> str:
    """
    Generates a standalone HTML representation of an Altair line chart using dummy data,
    with three different stock symbols over varying periods.

    Returns
    -------
    str
        The HTML representation of the Altair line chart.
    """
    # Adjusted to match the total length of the combined symbol and price arrays
    total_days = 51 + 100 + 200  # Total periods for all symbols
    date_range = pd.date_range(
        start="2020-01-01", periods=total_days, freq="D"
    )

    # Extend the 'symbol' and 'price' arrays to match the 'date' array length
    data = {
        "date": date_range,
        "symbol": ["AAPL"] * 51 + ["MSFT"] * 100 + ["ESLOCH"] * 200,
        "price": list(range(1, 52))
        + list(range(1, 101))
        + list(range(1, 201)),
    }
    source_df = pd.DataFrame(data)

    # Generate the chart
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


@register.inclusion_tag(
    "components/alert_state/epi-years.html", takes_context=True
)
def epi_years(context: dict) -> dict:
    return context
