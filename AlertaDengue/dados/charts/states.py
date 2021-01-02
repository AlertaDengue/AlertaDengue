'''
Module for plotting charts in the states reports
'''

import plotly.graph_objs as go
import pandas as pd
from plotly.subplots import make_subplots
from django.utils.translation import gettext as _

from copy import deepcopy


class ReportStateCharts:
    """Charts used by Report State."""

    @classmethod
    def create_tweet_chart(
        cls, df: pd.DataFrame, year_week: int, disease: str
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
        ks_cases = ['casos notif. {}'.format(disease)]

        df_tweet = df.reset_index()[['SE', 'tweets'] + ks_cases]
        df_tweet = df_tweet[df_tweet.SE >= year_week - 200]
        df_tweet.rename(columns={'tweets': 'menções'}, inplace=True)

        df_grp = (
            df_tweet.groupby(df_tweet.SE)[['menções'] + ks_cases]
            .sum()
            .reset_index()
        )

        df_grp['SE'] = df_grp.SE.map(
            lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
        )

        figure = make_subplots(specs=[[{"secondary_y": True}]])

        figure.add_trace(
            go.Scatter(
                x=df_grp['SE'],
                y=df_grp.iloc[:, 1],  # menções tweets
                name=_('Menções em tweets'),
                marker={'color': 'rgb(51, 172, 255)'},
                text=df_grp.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate=_(
                    "Semana %{text} : %{y} %{yaxis.title.text} <extra></extra>"
                ),
            ),
            secondary_y=False,
        )

        figure.add_trace(
            go.Scatter(
                x=df_grp['SE'],
                y=df_grp.iloc[:, 2],  # casos notif
                name=_('Casos notificados'),
                marker={'color': 'rgb(255,150,0)'},
                text=df_grp.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate=_(
                    "Semana %{text} : %{y} %{yaxis.title.text} <extra></extra>"
                ),
            ),
            secondary_y=True,
        )

        figure.update_layout(
            title=_('Menções na mídia social'),
            xaxis=dict(
                title=_('Período: Ano/Semana'),
                tickangle=-60,
                nticks=len(ks_cases) // 4,
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            yaxis=dict(
                # title='',
                showline=False,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            showlegend=True,
            plot_bgcolor='rgb(255, 255, 255)',
            paper_bgcolor='rgb(245, 246, 249)',
            width=1100,
            height=500,
            legend=dict(
                # x=-.1, y=1.2,
                bgcolor='#FFFFFF',
                bordercolor='#E2E2E2',
                traceorder='normal',
                font=dict(family='sans-serif', size=12, color='#000'),
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
