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
    def create_tweet_chart(
        cls,
        df: pd.DataFrame,
    ) -> str:
        """
        Create chart with tweet information.
        Parameters
        ----------
        df : pd.DataFrame
            Dataframe with tweet information
        year_week : int
            Year and week desired filter e.g.: 202002
        disease : str, {'dengue', 'chik', 'zika'}
            Disease name
        Returns
        -------
        str
            HTML with Plotly chart.
        """
        df = deepcopy(df)

        figure = make_subplots(specs=[[{"secondary_y": True}]])

        figure.add_trace(
            go.Scatter(
                x=df.index.map(lambda v: "%s/%s" % (str(v)[:4], str(v)[-2:])),
                y=df.iloc[:, 0],  # menções tweets
                name=_("Menções em tweets"),
                marker={"color": "rgb(51, 172, 255)"},
                text=df.index.map(lambda v: "{}".format(str(v)[-2:])),
                hoverinfo="text",
                hovertemplate=_(
                    "Semana %{text} : %{y} %{yaxis.title.text} <extra></extra>"
                ),
            ),
            # secondary_y=False,
        )

        figure.add_trace(
            go.Bar(
                x=df.index.map(lambda v: "%s/%s" % (str(v)[:4], str(v)[-2:])),
                y=df.iloc[:, 1],  # casos notif
                name=_("Casos notificados 1"),
                marker={"color": "rgb(150,0,255)"},
                text=df.index.map(lambda v: "{}".format(str(v)[-2:])),
                hoverinfo="text",
                hovertemplate=_(
                    "Semana %{text} : %{y} %{yaxis.title.text} <extra></extra>"
                ),
            ),
            secondary_y=True,
        )

        figure.add_trace(
            go.Bar(
                x=df.index.map(lambda v: "%s/%s" % (str(v)[:4], str(v)[-2:])),
                y=df.iloc[:, 2],  # casos notif
                name=_("Casos notificados 2"),
                marker={"color": "rgb(255,150,0)"},
                text=df.index.map(lambda v: "{}".format(str(v)[-2:])),
                hoverinfo="text",
                hovertemplate=_(
                    "Semana %{text} : %{y} %{yaxis.title.text} <extra></extra>"
                ),
            ),
            secondary_y=True,
        )

        figure.add_trace(
            go.Bar(
                x=df.index.map(lambda v: "%s/%s" % (str(v)[:4], str(v)[-2:])),
                y=df.iloc[:, 3],  # casos notif
                name=_("Casos notificados 3"),
                marker={"color": "rgb(255,0,255)"},
                text=df.index.map(lambda v: "{}".format(str(v)[-2:])),
                hoverinfo="text",
                hovertemplate=_(
                    "Semana %{text} : %{y} %{yaxis.title.text} <extra></extra>"
                ),
            ),
            secondary_y=True,
        )
        figure.update_layout(
            title=_("Menções na mídia social"),
            xaxis=dict(
                title=_("Período: Ano/Semana"),
                tickangle=-60,
                # nticks=len(ks_cases) // 4,
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor="rgb(204, 204, 204)",
                linewidth=0,
                gridcolor="rgb(176, 196, 222)",
            ),
            yaxis=dict(
                # title='',
                showline=False,
                showgrid=True,
                showticklabels=True,
                linecolor="rgb(204, 204, 204)",
                linewidth=0,
                gridcolor="rgb(176, 196, 222)",
            ),
            showlegend=True,
            plot_bgcolor="rgb(255, 255, 255)",
            paper_bgcolor="rgb(245, 246, 249)",
            width=1100,
            height=450,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                xanchor="auto",
                y=1.01,
                x=0.95,
                font=dict(family="sans-serif", size=12, color="#000"),
                bgcolor="#FFFFFF",
                bordercolor="#E2E2E2",
                borderwidth=1,
            ),
        )

        # Set y-axes titles
        figure.update_yaxes(
            title_text="<b>{}</b>".format(_("Menções em tweets")),
            secondary_y=False,
        )
        figure.update_yaxes(
            title_text="<b>{}</b>".format(_("Casos notificados")),
            secondary_y=True,
        )
        return figure.to_html()
