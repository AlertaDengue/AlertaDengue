"""
Module for plotting in the homepage charts
"""

from copy import deepcopy

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from django.utils.translation import gettext as _


def _create_scatter_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create chart with historical data from data cases and cases_est.

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe with cases and cases_est information
    uf: str
        State abbreviation
    disease : str, {'dengue', 'chik', 'zika'}
        Disease name

    Returns
    -------
    str
        HTML with Plotly chart.
    """

    df = deepcopy(df)
    df["SE"] = df.index.map(lambda v: f"{str(v)[:4]}/{str(v)[-2:]}")
    traces = []

    traces.append(
        go.Bar(
            x=df["SE"],
            y=df["casos"],
            name=_("Registrados"),
            marker=dict(
                color="#BDC3C7",
                line=dict(color="#3A4750", width=1),
            ),
            width=0.5,
            text=df.index.map(lambda v: f"{str(v)[-2:]}"),
            hovertemplate="%(label1)s %(week)s <br>"
            "%(cases)s %(label2)s"
            "<extra></extra>"
            % {
                "label1": _("SE"),
                "week": "%{text}",
                "cases": "%{y:1f}",
                "label2": _("Casos Notificados"),
            },
        )
    )
    traces.append(
        go.Scatter(
            mode="lines+markers",
            x=df["SE"],
            y=df["casos_est"],
            name=_("Estimados"),
            line=dict(color="#4169e1", width=4),
            text=df.index.map(lambda v: f"{str(v)[-2:]}"),
            hovertemplate="%(label1)s %(week)s <br>"
            "%(cases)s %(label2)s"
            "<extra></extra>"
            % {
                "label1": _("SE"),
                "week": "%{text}",
                "cases": "%{y:1f}",
                "label2": _("Casos Estimados"),
            },
        )
    )

    dict_of_fig = dict(
        {
            "data": traces,
            "layout": go.Layout(
                template="plotly",
                title={
                    "text": _("Total de casos no estado"),
                    "font": {"family": "Helvetica", "size": 16},
                    "x": 0.5,
                },
                xaxis=dict(
                    title=_("Semana epidemiológica"),
                    tickangle=-15,
                    showline=True,
                    showgrid=True,
                    showticklabels=True,
                    linecolor="rgb(204, 204, 204)",
                    linewidth=0,
                    gridcolor="rgb(176, 196, 222)",
                ),
                yaxis=dict(
                    title=_("Casos"),
                    showline=True,
                    showgrid=True,
                    showticklabels=True,
                    linecolor="rgb(204, 204, 204)",
                    linewidth=0,
                    gridcolor="rgb(176, 196, 222)",
                ),
                # yaxis={'title': _('Casos')},
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.01,
                    xanchor="left",
                    # x=1,
                ),
                hovermode="x",
                hoverlabel=dict(
                    # bgcolor="white",
                    font_size=12,
                    font_family="Rockwell",
                ),
                autosize=False,
                height=275,
                width=310,
                margin=dict(
                    autoexpand=False,
                    l=50,
                    r=20,
                    t=80,
                    b=55,
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                modebar={
                    "orientation": "h",
                    "bgcolor": "rgba(255 ,255 ,255 ,0.7)",
                },
            ),
        }
    )

    fig = go.Figure(dict_of_fig)

    config = {
        "modeBarButtonsToRemove": [
            "zoom2d",
            "pan2d",
            "select2d",
            "lasso2d",
            "autoScale2d",
        ],
        "displaylogo": False,
        "responsive": True,
    }

    return fig.to_html(full_html=False, include_plotlyjs=False, config=config)


def _create_indicator_chart(df: pd.DataFrame, state_abbv: str) -> go.Indicator:
    """
    Create the charts with the number of favorable cities for transmission
    when the receptivity is different from 0.
    Parameters
    ----------
    df : pd.DataFrame
        Dataframe with cases and cases_est information
    uf: str
        State abbreviation
    disease : str, {'dengue', 'chik', 'zika'}
        Disease name
    Returns
    -------
    str
        HTML with Plotly chart.
    """

    df = deepcopy(df)
    filter_uf = df[(df["state_abbv"] == state_abbv)]

    total_cities_uf = len(filter_uf.municipio_geocodigo.unique())
    receptivity_uf = filter_uf[filter_uf["receptivo"] != 0]

    # Filter last week
    this_week = receptivity_uf.SE.max()
    last_week = this_week - 1
    df_this_week = receptivity_uf[
        receptivity_uf["SE"] == this_week
    ].receptivo.count()
    df_last_week = receptivity_uf[
        receptivity_uf["SE"] == last_week
    ].receptivo.count()

    traces = []
    traces.append(
        go.Indicator(
            domain={"x": [0.1, 1], "y": [0, 1]},
            value=df_this_week,
            name="Cities",
            mode="gauge+delta",
            delta={
                "reference": df_last_week,
                "increasing": {"color": "#e60000"},
                "decreasing": {"color": "#1e824c"},
                "font": {"size": 36},
            },
            gauge={
                "axis": {
                    "range": [None, total_cities_uf],
                    "dtick": 25,
                    "tickangle": 0.90,
                    "tickfont": {"color": "grey", "size": 8},
                },
                "bar": {"color": "#900C3F"},
                "borderwidth": 1,
                "bordercolor": "#3A4750",
                "steps": [{"range": [0, 1000], "color": "#edf0f1"}],
                "threshold": {"thickness": 0.75, "value": total_cities_uf},
            },
        )
    )

    dict_of_fig = dict(
        {
            "data": traces,
            "layout": go.Layout(
                template="plotly",
                title={
                    "text": f"{df_this_week} "
                    + _("Cidades com clima favorável <br>para transmissão"),
                    "font": {"family": "Helvetica", "size": 16},
                    "x": 0.5,
                },
                xaxis={"title": _("Semana epidemiológica")},
                showlegend=False,
                hovermode="x",
                autosize=False,
                height=310,
                width=310,
                margin=dict(
                    autoexpand=False,
                    l=5,
                    r=50,
                    t=80,
                    b=55,
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                modebar={
                    "orientation": "h",
                    "bgcolor": "rgba(255 ,255 ,255 ,0.7)",
                },
            ),
        }
    )

    fig = go.Figure(dict_of_fig)

    config = {
        "modeBarButtonsToRemove": [
            "zoom2d",
            "pan2d",
            "select2d",
            "lasso2d",
            "autoScale2d",
        ],
        "displaylogo": False,
        "responsive": True,
    }

    return fig.to_html(full_html=False, include_plotlyjs=False, config=config)


def _create_stack_chart(df: pd.DataFrame) -> px.bar():
    """
    Create chart of the epidemiological situation of cities
    by levels in the week.

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe with cases and cases_est information
    uf: str
        State abbreviation
    disease : str, {'dengue', 'chik', 'zika'}
        Disease name

    Returns
    -------
    str
        HTML with Plotly chart.
    """

    df_alert = df.sort_values(by=["SE"], ascending=True).reset_index(drop=True)

    color_map_alert_y = {
        "Green Alert": "#00e640",
        "Yellow Alert": "#f0ff00",
        "Orange Alert": "#f89406",
        "Red Alert": "#f03434",
    }

    # Trace
    fig = px.bar(
        df_alert,
        y="municipio_geocodigo",
        x=df_alert.SE.map(lambda v: f"{str(v)[:4]}/{str(v)[-2:]}"),
        color="nivel",
        color_discrete_map=color_map_alert_y,
        hover_data={"nivel"},
        category_orders={
            "nivel": [
                "Green Alert",
                "Yellow Alert",
                "Orange Alert",
                "Red Alert",
            ],
        },
    )

    fig.update_traces(
        hovertemplate="%(cases)s %(label2)s %(week)s <br>"
        "<extra></extra>"
        % {
            "label2": _("Cidades na Semana"),
            "week": "%{x}",
            "cases": "%{y:1f}",
        },
    )

    fig.update_layout(
        title={
            "text": _("Situação epidemiológica das cidades"),
            "font": {"family": "Helvetica", "size": 16},
            "x": 0.5,
        },
        showlegend=False,
        hovermode="x",
        hoverlabel=dict(font_size=12, font_family="Rockwell"),
        margin=dict(
            autoexpand=False,
            l=40,
            r=20,
            t=80,
            b=55,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        modebar={"orientation": "h", "bgcolor": "rgba(255 ,255 ,255 ,0.7)"},
        autosize=False,
        height=275,
        width=310,
        xaxis=dict(
            title=_("Semana epidemiológica"),
            tickangle=-15,
            showline=True,
            showgrid=True,
            showticklabels=True,
            linecolor="rgb(204, 204, 204)",
            linewidth=0,
            gridcolor="rgb(176, 196, 222)",
        ),
        yaxis=dict(
            title=_("Número de cidades"),
            showline=True,
            showgrid=True,
            showticklabels=True,
            linecolor="rgb(204, 204, 204)",
            linewidth=0,
            gridcolor="rgb(176, 196, 222)",
        ),
    )

    for data in fig.data:
        data["width"] = 0.45  # Change this value for bar widths

    config = {
        "modeBarButtonsToRemove": [
            "zoom2d",
            "pan2d",
            "select2d",
            "lasso2d",
            "autoScale2d",
        ],
        "displaylogo": False,
        "responsive": True,
    }

    return fig.to_html(full_html=False, include_plotlyjs=False, config=config)
