"""
Module for plotting charts in the states reports
"""

from copy import deepcopy

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from django.utils.translation import gettext as _

# from plotly.subplots import make_subplots


class ReportStateCharts:
    """Charts used by Report State."""

    @classmethod
    def create_notific_chart(
        cls,
        df: pd.DataFrame,
    ) -> str:

        df = deepcopy(
            df.sort_values(by=["SE"], ascending=True).reset_index(drop=True)
        )

        traces = []

        traces.append(
            go.Bar(
                x=df["SE"].map(lambda v: f"{str(v)[:4]}/{str(v)[-2:]}"),
                y=df.casos,
                name=_("Casos por municípios"),
                orientation="v",
                marker=dict(
                    color="#5466c0",
                    line=dict(color="white", width=1),
                ),  # text=df.SE.map(lambda v: f"{str(v)[-2:]}"),
            )
        )

        dict_of_figa = dict(
            {
                "data": traces,
                "layout": go.Layout(
                    template="plotly",
                    title={
                        "text": _("Total de casos por cidades na regional"),
                        "font": {"family": "Helvetica", "size": 16},
                        "x": 0.5,
                    },
                    xaxis=dict(
                        title=_("Semana epidemiológica"),
                        tickangle=-25,
                        showline=True,
                        showgrid=True,
                        showticklabels=True,
                        linecolor="rgb(204, 204, 204)",
                        linewidth=0,
                        gridcolor="rgb(176, 196, 222)",
                    ),
                    yaxis=dict(
                        title=_("Total de Casos"),
                        showline=True,
                        showgrid=True,
                        showticklabels=True,
                        linecolor="rgb(204, 204, 204)",
                        linewidth=0,
                        gridcolor="rgb(176, 196, 222)",
                    ),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.01,
                        xanchor="left",
                    ),
                    # hovermode="x",
                    hoverlabel=dict(
                        bgcolor="#4169e1",
                        font_size=12,
                    ),
                    autosize=True,
                    # height=275,
                    # width=350,
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

        fig = go.Figure(dict_of_figa)

        fig.update_traces(
            customdata=df["municipio_nome"],
            text=df["casos"],
            textposition="inside",
            textfont=dict(color="white"),
            hovertemplate=_(
                "<br>SE: %{x}</br>"
                "Munincipio: %{customdata} </br>"
                "%{y:1f} Casos Notificados"
                "<extra></extra>"
            ),
        )

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

        return fig.to_html(
            full_html=False, include_plotlyjs=False, config=config
        )

    @classmethod
    def create_level_chart(
        cls,
        df: pd.DataFrame,
    ) -> str:
        df_nivel = (
            df.groupby(["SE", "nivel"])["municipio_geocodigo"]
            .count()
            .reset_index()
        )
        color_alert = {1: "Green", 2: "Yellow", 3: "Orange", 4: "Red"}
        df_nivel.nivel = df_nivel.nivel.apply(
            lambda v: f"{color_alert[v]} Alert"
        )

        df_alert = df_nivel.sort_values(by=["SE"], ascending=True).reset_index(
            drop=True
        )

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
            # layout=dict(template='plotly'),
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
            customdata=df_alert.SE.map(lambda v: f"{str(v)[-2:]}"),
            hovertemplate=_(
                "%{y} Cidades na semana %{customdata} <extra></extra>"
            ),
        )

        fig.update_layout(
            template="plotly",
            title={
                "text": _("Situação epidemiológica das cidades na regional"),
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
            modebar={
                "orientation": "h",
                "bgcolor": "rgba(255 ,255 ,255 ,0.7)",
            },
            autosize=True,
            # height=275,
            # width=350,
            xaxis=dict(
                title=_("Semana epidemiológica"),
                tickangle=-25,
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

        return fig.to_html(
            full_html=False, include_plotlyjs=False, config=config
        )
