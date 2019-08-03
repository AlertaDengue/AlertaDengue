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

        # df_ks = df[ks_alert + ['SE']].melt('SE')

        figure = make_subplots(specs=[[{"secondary_y": True}]])

        figure.add_trace(
            go.Scatter(
                x=df['SE'],
                y=df['casos notif.'],
                name='Casos notificações',
                marker={'color': 'rgb(33,33,33)'},
            ),
            secondary_y=True,
        )

        ks_limiar = [
            'limiar pré epidêmico',
            'limiar pós epidêmico',
            'limiar epidêmico',
        ]

        colors = ['rgb(0,255,0)',
                  'rgb(255,150,0)',
                  'rgb(255,0,0)',
                  ]

        for k, c in zip(ks_limiar, colors):
            figure.add_trace(
                go.Scatter(
                    x=df['SE'],
                    y=df[k],
                    name=k.title(),
                    marker={'color': c}
                ),
                secondary_y=True,
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
                    name=k.title(),
                    marker={'color': c}
                ),
                secondary_y=False,
            )

        figure.update_layout(
            xaxis=dict(
                title='Período (Ano/Semana)',
                tickangle=-60,
                nticks=len(df) // 4,
                showline=True,
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
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            showlegend=True,
            plot_bgcolor='rgb(245, 246, 249)',
            paper_bgcolor='rgb(212, 227, 249)',
            width=1100,
            height=500,
        )

        figure.update_yaxes(
            title_text="Casos",
            secondary_y=True,
            showline=True,
            showgrid=True,
            showticklabels=True,
            linecolor='rgb(204, 204, 204)',
            linewidth=0,
            gridcolor='rgb(204, 204, 204)',
        )

        figure['layout']['legend'].update(
            traceorder='normal',
            font=dict(family='sans-serif', size=12, color='#000'),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1,
        )

        figure['layout'].update(
            title=(
                'Limiares de incidência:: '
                + 'pré epidêmico=%s; '
                + 'pós epidêmico=%s; '
                + 'epidêmico=%s;'
            )
            % (
                '{:.1f}'.format(threshold_pre_epidemic),
                '{:.1f}'.format(threshold_pos_epidemic),
                '{:.1f}'.format(threshold_epidemic),
            ),
            font=dict(family='sans-serif', size=12, color='#000'),
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

        figure = go.Figure()

        figure.add_trace(
            go.Scatter(
                x=df_climate['SE'],
                y=df_climate['threshold_transmission'],
                name='Limiar Favorável',
                marker={'color': 'rgb(51, 172, 255)'},
            )
        )

        figure.add_trace(
            go.Scatter(
                x=df_climate['SE'],
                y=df_climate[k],
                name='Temperatura min.',
                marker={'color': 'rgb(255,150,0)'},
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
                title='Temperatura',
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            showlegend=True,
            plot_bgcolor='rgb(245, 246, 249)',
            paper_bgcolor='rgb(212, 227, 249)',
            width=1100,
            height=500,
        )

        figure['layout']['legend'].update(
            x=-0.1,
            y=1.2,
            traceorder='normal',
            font=dict(family='sans-serif', size=12, color='#000'),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1,
        )

        # return _plot_html(
        #     figure_or_data=figure,
        #     config={},
        #     validate=True,
        #     default_width='100%',
        #     default_height=500,
        #     global_requirejs='',
        # )[0]
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
            plot_bgcolor='rgb(245, 246, 249)',
            paper_bgcolor='rgb(212, 227, 249)',
            width=1100,
            height=500,

        )

        figure['layout']['legend'].update(
            x=-0.1,
            y=1.2,
            traceorder='normal',
            font=dict(family='sans-serif', size=12, color='#000'),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1,
        )

        return figure.to_html()


class ReportStateCharts:
    @classmethod
    def create_tweet_chart(cls, df: pd.DataFrame, year_week, disease: str):
        """

        :param df:
        :param year_week:
        :param disease:
        :return:
        """
        ks_cases = ['casos notif. {}'.format(disease)]

        df_tweet = df.reset_index()[['SE', 'tweets'] + ks_cases]
        df_tweet = df_tweet[df_tweet.SE >= year_week - 200]

        df_tweet.rename(columns={'tweets': 'menções'}, inplace=True)

        df_grp = (
            df_tweet.groupby(df.index)[['menções'] + ks_cases]
            .sum()
            .reset_index()
        )

        df_grp['SE'] = df_grp.SE.map(
            lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
        )

        # fig_tweet = df_grp.iplot(
        #     x=['SE'],
        #     y=['menções'],
        #     xTitle='Período (Ano/Semana)',
        #     color=['rgb(128,128,128)'],
        # )

        # fig_cases = df_grp.iplot(
        #     x=['SE'],
        #     y=ks_cases,
        #     secondary_y=ks_cases,
        #     secondary_y_title='Casos',
        #     xTitle='Período (Ano/Semana)',
        #     color=['rgb(0,0,255)'],
        # )

        # fig_cases.data.extend(fig_tweet.data)

        # fig_cases['layout']['xaxis1'].update(
        #     tickangle=-60, nticks=len(df_grp) // 24
        # )
        # fig_cases['layout']['yaxis1'].update(
        #     title='Tweets', range=[0, df_grp['menções'].max()]
        # )
        # fig_cases['layout']['yaxis2'].update(
        #     range=[0, df_grp[ks_cases].max().max()]
        # )

        # fig_cases['layout'].update(
        #     title='Casos {} / Menções mídia social'.format(disease)
        # )

        figure = make_subplots(specs=[[{"secondary_y": True}]])

        figure.add_trace(
            go.Scatter(
                x=['SE'],
                y=['menções'],
                name='Menciones',
                marker={'color': 'rgb(51, 172, 255)'},
            ),
            secondary_y=True,
        )

        figure.add_trace(
            go.Scatter(
                x=['SE'],
                y=ks_cases,
                name='Casos',
                marker={'color': 'rgb(255,150,0)'},
            ),
            secondary_y=False,
        )

        figure.update_layout(
            title='Menções mídia social',
            xaxis=dict(
                title='Período (Ano/Semana)',
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
                title='Temperatura',
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
            showlegend=True,
            plot_bgcolor='rgb(245, 246, 249)',
            paper_bgcolor='rgb(212, 227, 249)',
            width=1100,
            height=500,
        )

        figure.update_yaxes(
            title_text="Y_axies",
            secondary_y=True
        )

        figure['layout']['legend'].update(
            x=-0.1,
            y=1.2,
            traceorder='normal',
            font=dict(family='sans-serif', size=12, color='#000'),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1,
        )

        return figure.to_html()
