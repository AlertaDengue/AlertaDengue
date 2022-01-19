# from django.utils.translation import gettext as _

import plotly.graph_objs as go
import pandas as pd
from plotly.subplots import make_subplots


class ReportCityCharts:
    @classmethod
    def create_incidence_chart(
        cls,
        df: pd.DataFrame,
        year_week: int,
        threshold_pre_epidemic: float,
        threshold_pos_epidemic: float,
        threshold_epidemic: float,
    ):
        """
        @see: https://stackoverflow.com/questions/45526734/
            hide-legend-entries-in-a-plotly-figure
        :param df:
        :param year_week:
        :param threshold_pre_epidemic: float,
        :param threshold_pos_epidemic: float
        :param threshold_epidemic: float
        :return:
        """
        df = df.reset_index()[
            ['SE', 'incidência', 'casos notif.', 'level_code']
        ]

        # 200 = 2 years
        df = df[df.SE >= year_week - 200]

        df['SE'] = df.SE.map(lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:]))

        k = 'incidência'

        df['alerta verde'] = df[df.level_code == 1][k]
        df['alerta amarelo'] = df[df.level_code == 2][k]
        df['alerta laranja'] = df[df.level_code == 3][k]
        df['alerta vermelho'] = df[df.level_code == 4][k]

        df['limiar epidêmico'] = threshold_epidemic
        df['limiar pós epidêmico'] = threshold_pos_epidemic
        df['limiar pré epidêmico'] = threshold_pre_epidemic

        figure = make_subplots(specs=[[{"secondary_y": True}]])

        figure.add_trace(
            go.Scatter(
                x=df['SE'],
                y=df['casos notif.'],
                name='Notificações',
                marker={'color': 'rgb(33,33,33)'},
                text=df.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate="Semana %{text} : %{y:1f} Casos",
            ),
            secondary_y=True,
        )

        ks_limiar = [
            'limiar pré epidêmico',
            'limiar pós epidêmico',
            'limiar epidêmico',
        ]

        colors = ['rgb(0,255,0)', 'rgb(255,150,0)', 'rgb(255,0,0)']

        for k, c in zip(ks_limiar, colors):
            figure.add_trace(
                go.Scatter(
                    x=df['SE'],
                    y=df[k],
                    y0=df['incidência'],
                    name=k.title(),
                    marker={'color': c},
                    text=df.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                    hoverinfo='text',
                    hovertext=df['incidência'],
                    hovertemplate="Semana %{text} <br>Incidência=%{y:1f}",
                ),
                secondary_y=False,
            )

        ks_alert = [
            'alerta verde',
            'alerta amarelo',
            'alerta laranja',
            'alerta vermelho',
        ]

        colors = [
            'rgb(0,255,0)',
            'rgb(255,255,0)',
            'rgb(255,150,0)',
            'rgb(255,0,0)',
        ]

        for k, c in zip(ks_alert, colors):
            figure.add_trace(
                go.Bar(
                    x=df['SE'],
                    y=df[k],
                    marker={'color': c},
                    name=k.title(),
                    text=df.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                    hoverinfo='text',
                    hovertemplate="Semana %{text}<br>Incidência=%{y:1f}",
                ),
                secondary_y=False,
            )

        figure.update_layout(
            title=(
                f'''
                Limiares de incidência:<br>
                pré epidêmico={threshold_pre_epidemic:.1f}
                pós epidêmico={threshold_pos_epidemic:.1f}
                epidêmico={threshold_epidemic:.1f}
                '''
            ),
            font=dict(family='sans-serif', size=12, color='#000'),
            xaxis=dict(
                title='Período (Ano/Semana)',
                tickangle=-60,
                nticks=len(df) // 4,
                showline=False,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
                ticks='outside',
                tickfont=dict(
                    family='Arial', size=12, color='rgb(82, 82, 82)'
                ),
            ),
            yaxis=dict(
                title='Incidência',
                showline=False,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            showlegend=True,
            legend=dict(
                traceorder='normal',
                font=dict(family='sans-serif', size=12, color='#000'),
                bgcolor='#FFFFFF',
                bordercolor='#E2E2E2',
                borderwidth=1,
            ),
            plot_bgcolor='rgb(255, 255, 255)',
            paper_bgcolor='rgb(245, 246, 249)',
            width=1100,
            height=450,
        )

        figure.update_yaxes(
            title_text="Casos Notificados",
            secondary_y=True,
            showline=False,
            showgrid=True,
            showticklabels=True,
            linecolor='rgb(204, 204, 204)',
            linewidth=0,
            gridcolor='rgb(204, 204, 204)',
        )

        for trace in figure['data']:
            if trace['name'] == 'casos notif.':
                trace['visible'] = 'legendonly'

        return figure.to_html()

    @classmethod
    def create_climate_chart(
        cls,
        df: pd.DataFrame,
        var_climate,
        year_week,
        climate_crit,
        climate_title,
    ):
        """
        :param df:
        :param var_climate:
        :param year_week:
        :param climate_crit:
        :param climate_title:
        :return:
        """
        k = var_climate.replace('_', '.')

        df_climate = df.reset_index()[['SE', k]]
        df_climate = df_climate[df_climate.SE >= year_week - 200]

        df_climate['SE'] = df_climate.SE.map(
            lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
        )

        df_climate['Limiar favorável transmissão'] = climate_crit

        df_climate = df_climate.rename(
            columns={'Limiar favorável transmissão': 'threshold_transmission'}
        )

        df_climate[['SE', 'threshold_transmission', k]].melt('SE')

        if k == "temp.min":
            varclim_title = "Temperatura"
        elif k == "umid.max":
            varclim_title = "Umidade relativa do ar"
        else:
            raise Exception('Climate variable not found.')

        figure = go.Figure()

        figure.add_trace(
            go.Scatter(
                x=df_climate['SE'],
                y=df_climate['threshold_transmission'],
                name='Limiar Favorável',
                marker={'color': 'rgb(51, 172, 255)'},
                text=df_climate.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate="Semana %{text} : %{y:1f}°C",
            )
        )

        figure.add_trace(
            go.Scatter(
                x=df_climate['SE'],
                y=df_climate[k],
                name=varclim_title,
                marker={'color': 'rgb(255,150,0)'},
                text=df_climate.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate="Semana %{text} : %{y:1f}°C",
            )
        )

        figure.update_layout(
            # title = "",
            xaxis=dict(
                title='Período (Ano/Semana)',
                tickangle=-60,
                nticks=len(df_climate) // 4,
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            yaxis=dict(
                title=varclim_title,
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="left",
                font=dict(family='sans-serif', size=12, color='#000'),
                bgcolor='#FFFFFF',
                bordercolor='#E2E2E2',
                borderwidth=1,
            ),
            plot_bgcolor='rgb(255, 255, 255)',
            paper_bgcolor='rgb(245, 246, 249)',
            width=1100,
            height=450,
        )

        return figure.to_html()

    @classmethod
    def create_tweet_chart(cls, df: pd.DataFrame, year_week):
        """
        :param df:
        :param var_climate:
        :param year_week:
        :param climate_crit:
        :param climate_title:
        :return:
        """
        df_tweet = df.reset_index()[['SE', 'tweets']]
        df_tweet = df_tweet[df_tweet.SE >= year_week - 200]

        df_tweet['SE'] = df_tweet.SE.map(
            lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
        )

        df_tweet.rename(columns={'tweets': 'menções'}, inplace=True)

        figure = go.Figure()

        figure.add_trace(
            go.Scatter(
                x=df_tweet['SE'],
                y=df_tweet['menções'],
                name='Menções',
                marker={'color': 'rgb(0,0,255)'},
                text=df_tweet.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate="Semana %{text} : %{y} Tweets",
            )
        )

        figure.update_layout(
            # title="",
            xaxis=dict(
                title='Período (Ano/Semana)',
                tickangle=-60,
                nticks=len(df_tweet) // 4,
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            yaxis=go.layout.YAxis(
                title='Tweets',
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="left",
                font=dict(family='sans-serif', size=12, color='#000'),
                bgcolor='#FFFFFF',
                bordercolor='#E2E2E2',
                borderwidth=1,
            ),
            plot_bgcolor='rgb(255, 255, 255)',
            paper_bgcolor='rgb(245, 246, 249)',
            width=1100,
            height=450,
        )

        return figure.to_html()
