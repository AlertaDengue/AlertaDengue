"""
Module for plotting charts in the states reports
"""

from copy import deepcopy

import pandas as pd
import plotly.graph_objs as go
from django.utils.translation import gettext as _
from plotly.subplots import make_subplots


class ReportStateCharts:
    """Charts used by Report State."""

    @classmethod
    def create_notific_chart(
        cls,
        df: pd.DataFrame,
    ) -> str:
        df = deepcopy(df)

        df["SE"] = df.index.map(lambda v: f"{str(v)[:4]}/{str(v)[-2:]}")
        traces = []

        traces.append(
            go.Bar(
                x=df["SE"],
                y=df.iloc[:, 1],
                name=_("Registrados"),
                marker=dict(
                    color="#BDC3C7",
                    line=dict(color="#3A4750", width=1),
                ),
                width=0.5,
                text=df.index.map(lambda v: f"{str(v)[-2:]}"),
                hovertemplate=_(
                    "<br>SE %{text}<br>"
                    "%{y:1f} Casos notificados"
                    "<extra></extra>"
                ),
            )
        )

        dict_of_fig = dict(
            {
                "data": traces,
                "layout": go.Layout(
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

        return fig.to_html()

    @classmethod
    def create_level_chart(
        cls,
        df: pd.DataFrame,
    ) -> str:
        df = deepcopy(df)
        df["SE"] = df.index.map(lambda v: f"{str(v)[:4]}/{str(v)[-2:]}")
        traces = []

        traces.append(
            go.Bar(
                x=df["SE"],
                y=df.iloc[:, 1],
                name=_("Registrados"),
                marker=dict(
                    color="#BDC3C7",
                    line=dict(color="#3A4750", width=1),
                ),
                width=0.5,
                text=df.index.map(lambda v: f"{str(v)[-2:]}"),
                hovertemplate=_(
                    "<br>SE %{text}<br>"
                    "%{y:1f} Casos notificados"
                    "<extra></extra>"
                ),
            )
        )

        dict_of_fig = dict(
            {
                "data": traces,
                "layout": go.Layout(
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

        return fig.to_html()

    @classmethod
    def create_tweet_chart(
        cls,
        df: pd.DataFrame,
    ) -> str:
        df = deepcopy(df)
        df["SE"] = df.index.map(lambda v: f"{str(v)[:4]}/{str(v)[-2:]}")
        traces = []

        traces.append(
            go.Bar(
                x=df["SE"],
                y=df.iloc[:, 1],
                name=_("Registrados"),
                marker=dict(
                    color="#BDC3C7",
                    line=dict(color="#3A4750", width=1),
                ),
                width=0.5,
                text=df.index.map(lambda v: f"{str(v)[-2:]}"),
                hovertemplate=_(
                    "<br>SE %{text}<br>"
                    "%{y:1f} Casos notificados"
                    "<extra></extra>"
                ),
            )
        )

        dict_of_fig = dict(
            {
                "data": traces,
                "layout": go.Layout(
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

        return fig.to_html()
