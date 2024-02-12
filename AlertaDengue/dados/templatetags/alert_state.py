from typing import Optional

import altair as alt
import pandas as pd
from ad_main.settings import get_sqla_conn
from dados.dbdata import CID10  # Ensure this is correctly imported
from django import template
from sqlalchemy import text

register = template.Library()

DB_ENGINE = get_sqla_conn()


def get_epiyears(
    state_name: str, disease: Optional[str] = None, db_engine=DB_ENGINE
) -> pd.DataFrame:
    parameters = {"state_name": state_name}
    disease_filter = ""

    if disease:
        disease_code = CID10.get(disease, "")
        disease_filter = f" AND disease_code = '{disease_code}'"

    sql_text = f"""
    SELECT
      ano_notif,
      se_notif,
      casos
    FROM
      public.epiyear_summary
    WHERE uf = '{state_name}' {disease_filter}
    ORDER BY ano_notif, se_notif
    """

    with db_engine.connect() as conn:
        result = conn.execute(text(sql_text), parameters)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    df.columns = df.columns.map(str)  # Ensure column names are strings
    return (
        pd.crosstab(
            df["se_notif"], df["ano_notif"], df["casos"], aggfunc="sum"
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )


def transform_data_for_altair(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure 'se_notif' is of type string for Altair compatibility
    df["se_notif"] = df["se_notif"].astype(str)
    # Melt the DataFrame so each row represents a single observation
    melted_df = df.melt(
        id_vars="se_notif", var_name="Year", value_name="Cases"
    )
    return melted_df


def generate_altair_line_chart(
    df: pd.DataFrame, state_name: str, disease: str
) -> alt.Chart:
    source_df = transform_data_for_altair(df)

    # Interactive selector
    selection = alt.selection_point(fields=["Year"], bind="legend")

    chart = (
        alt.Chart(source_df)
        .mark_line(interpolate="monotone")
        .encode(
            x=alt.X(
                "se_notif:Q",
                title="Epidemiological Week",
                axis=alt.Axis(labelAngle=-90),
                scale=alt.Scale(domain=(1, 53)),
            ),
            y=alt.Y("Cases:Q", title="Total Cases"),
            color=alt.Color(
                "Year:N",
                legend=alt.Legend(title="Year", orient="bottom"),
                scale=alt.Scale(scheme="category20"),
            ),
            tooltip=["Year", "se_notif", "Cases"],
            opacity=alt.condition(
                selection, alt.value(1), alt.value(0.2)
            ),  # Opacity Selector
        )
        .properties(
            title=f"Cases per Epidemiological Week for {state_name} - {disease}",
            width="container",
            height=300,
        )
        .add_params(selection)
        .configure_legend(
            orient="bottom",
            titleAnchor="middle",
        )
    )

    return chart


@register.inclusion_tag(
    "components/alert_state/vis-echarts.html", takes_context=True
)
def vis_altair(context: dict):
    state_name = context.get("state", "Santa Catarina")
    disease = context.get("disease", "dengue")
    df = get_epiyears(state_name, disease, DB_ENGINE)
    altair_chart_html = generate_altair_line_chart(
        df, state_name, disease
    ).to_html()

    # Update context
    context.update(
        {
            "altair_line_chart": altair_chart_html,
        }
    )
    return context


@register.inclusion_tag(
    "components/alert_state/epi-years.html", takes_context=True
)
def epi_years(context: dict) -> dict:
    return context
