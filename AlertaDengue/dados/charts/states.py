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
    ) -> go.Figure:
        """
        Create a notification chart using a DataFrame.

        Parameters
        ----------
            df (pd.DataFrame): The input DataFrame.

        Returns
        -------
            go.Figure[str]: The generated notification chart.
        """

        # Create a deep copy of the DataFrame and sort it
        # by 'SE' column in ascending order
        df_cp = deepcopy(
            df.sort_values(by=["SE"], ascending=True).reset_index(drop=True)
        )

        # Group the DataFrame by 'SE' column and sum
        # the 'casos_est' and 'casos' columns
        keys = ["casos_est", "casos"]
        df = df_cp.groupby(["SE"])[keys].sum()

        # Format the 'SE' index column to display as 'yyyy/mm'
        df["SE"] = df.index.map(lambda v: f"{str(v)[:4]}/{str(v)[-2:]}")

        # Create a list to hold the plotly traces
        traces = []

        # Create a bar trace for the 'casos' column
        traces.append(
            go.Bar(
                x=df["SE"],
                y=df["casos"],
                name=_("Registrados"),
                marker=dict(
                    color="#5466c0",
                    line=dict(color="white", width=1),
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

        # Create a scatter trace for the 'casos_est' column
        traces.append(
            go.Scatter(
                mode="lines+markers",
                x=df["SE"],
                y=df["casos_est"],
                name=_("Estimados"),
                line=dict(color="#ffa500", width=4),
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

        # Create a dictionary to hold the figure data and layout
        dict_of_fig = dict(
            {
                "data": traces,
                "layout": go.Layout(
                    template="plotly",
                    title={
                        "text": _("Total de casos na regional de saúde"),
                        "font": {"family": "Helvetica", "size": 16},
                        "x": 0.5,
                    },
                    xaxis=dict(
                        title=_("Semana epidemiológica"),
                        tickangle=-35,
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
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.01,
                        xanchor="left",
                    ),
                    hovermode="x",
                    hoverlabel=dict(
                        font_size=12,
                        font_family="Rockwell",
                    ),
                    autosize=True,
                    margin=dict(
                        autoexpand=False,
                        l=50,
                        r=20,
                        t=80,
                        b=75,
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

        return fig.to_html(
            full_html=False, include_plotlyjs=False, config=config
        )

    @classmethod
    def create_level_chart(
        cls,
        df: pd.DataFrame,
    ) -> px.bar:
        """
        Create a level chart using a DataFrame.

        Parameters
        ----------
            df (pd.DataFrame): The input DataFrame.

        Returns
        -------
            px.bar(): The generated level chart.
        """

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
        # print(df.head())

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
            hovertemplate="%(cases)s %(label2)s %(week)s <br>"
            "<extra></extra>"
            % {
                "cases": "%{y:1f}",
                "label2": _("Cidades na Semana"),
                "week": "%{customdata}",
            },
        )

        fig.update_layout(
            template="plotly",
            title={
                "text": _("Situação epidemiológica na regional de saúde"),
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
                b=75,
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
                tickangle=-35,
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
