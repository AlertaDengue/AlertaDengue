# imports.py
import altair as alt
import pandas as pd
from ad_main.settings import get_sqla_conn
from dados.dbdata import CID10  # Ensure this is correctly imported
from django import template
from sqlalchemy import text
from typing_extensions import Optional

# Initialize Django template library
register = template.Library()

# Database engine for SQL operations
DB_ENGINE = get_sqla_conn()


def get_epiyears(
    state_name: str, disease: Optional[str] = None, db_engine=DB_ENGINE
) -> pd.DataFrame:
    """
    Fetches epidemiological data for a specified state and disease from the database.
    """
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

    return pd.crosstab(
        df["ano_notif"], df["se_notif"], df["casos"], aggfunc="sum"
    ).T


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reset_index()
    long_df = df.melt(
        id_vars=["se_notif"], var_name="ano_notif", value_name="casos"
    )

    long_df["ano_notif"] = long_df["ano_notif"].astype(str)
    long_df["se_notif_str"] = long_df["se_notif"].astype(str)

    # Correctly format the week to be compatible with %W (which expects week number as 00-53)
    # Pad single-digit week numbers with a leading zero for correct datetime parsing
    long_df["se_notif_str"] = long_df["se_notif_str"].str.zfill(2)

    # Adjusted to correctly handle datetime conversion with week numbers
    long_df["date"] = pd.to_datetime(
        long_df["ano_notif"] + long_df["se_notif_str"] + "1", format="%Y%U%w"
    )

    long_df = long_df.drop(columns=["se_notif_str"])

    return long_df


def generate_altair_line_chart(state_name: str, disease: str) -> str:
    """
    Generates an Altair line chart HTML for the specified state and disease.
    """
    df = get_epiyears(state_name, disease, DB_ENGINE)
    source_df = transform_data(df)

    chart = (
        alt.Chart(source_df)
        .mark_line(interpolate="monotone")
        .encode(x="date:T", y="casos:Q", color="ano_notif:N")
        .properties(width="container")
    )

    return chart.to_html()


@register.inclusion_tag(
    "components/alert_state/vis-echarts.html", takes_context=True
)
def vis_altair(context: dict) -> dict:
    """
    Django template tag to generate context for Altair visualization.
    """
    state_name = context.get("state_name", "Santa Catarina")
    disease = context.get("disease", "dengue")
    altair_line_chart_html = generate_altair_line_chart(state_name, disease)

    context.update(
        {
            "CID10": CID10,
            "altair_line_chart": altair_line_chart_html,
        }
    )
    return context


@register.inclusion_tag(
    "components/alert_state/epi-years.html", takes_context=True
)
def epi_years(context: dict) -> dict:
    """
    Django template tag for displaying epidemiological years data.
    """
    return context
