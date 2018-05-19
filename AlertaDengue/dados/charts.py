from plotly.offline.offline import _plot_html

import cufflinks as cf
import pandas as pd

cf.set_config_file(theme='pearl')


class ReportCityCharts:
    @classmethod
    def create_incidence_chart(
        cls, df: pd.DataFrame, year_week: int, threshold_pre_epidemic: float,
        threshold_pos_epidemic: float, threshold_epidemic: float
    ) -> 'Plotly_HTML':
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
        df = df.reset_index()[[
            'SE', 'incidência', 'casos notif.', 'level_code'
        ]]

        # 200 = 2 years
        df = df[
            df.SE >= year_week - 200
        ]

        df['SE'] = df.SE.map(lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:]))

        k = 'incidência'

        df['alerta verde'] = df[df.level_code == 1][k]
        df['alerta amarelo'] = df[df.level_code == 2][k]
        df['alerta laranja'] = df[df.level_code == 3][k]
        df['alerta vermelho'] = df[df.level_code  == 4][k]

        df['limiar epidêmico'] = threshold_epidemic
        df['limiar pós epidêmico'] = threshold_pos_epidemic
        df['limiar pré epidêmico'] = threshold_pre_epidemic

        figure_bar = df.iplot(
            asFigure=True, kind='bar', x=['SE'], y=[
                'alerta verde',
                'alerta amarelo',
                'alerta laranja',
                'alerta vermelho'
            ],
            legend=True,
            showlegend=True,
            yTitle='Incidência', xTitle='Período (Ano/Semana)',
            color=[
                'rgb(0,255,0)', 'rgb(255,255,0)',
                'rgb(255,150,0)', 'rgb(255,0,0)'
            ], hoverinfo='x+y+name'
        )

        figure_threshold = df.iplot(
            asFigure=True, x=['SE'], y=[
                'limiar pré epidêmico',
                'limiar pós epidêmico',
                'limiar epidêmico'
            ],
            legend=False,
            showlegend=False,
            color=[
                'rgb(0,255,0)', 'rgb(255,150,0)', 'rgb(255,0,0)'
            ], hoverinfo='none'
        )

        figure_line = df.iplot(
            asFigure=True, x=['SE'], y=['casos notif.'],
            legend=False,
            showlegend=False,
            secondary_y=['casos notif.'], secondary_y_title='Casos',
            hoverinfo='x+y+name', color=['rgb(33,33,33)']
        )

        figure_line['layout']['legend'].update(
            x=-.27, y=0.5,
            traceorder='normal',
            font=dict(
                family='sans-serif',
                size=12,
                color='#000'
            ),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1,
            orientation='l',
        )

        figure_line['layout']['yaxis1'].update(
            title='Incidência'
        )

        figure_line['layout'].update(
            title=(
                'Limiares de incidência:: ' +
                'pré epidêmico=%s; ' +
                'pós epidêmico=%s; ' +
                'epidêmico=%s;'
            ) % (
                '{:.1f}'.format(threshold_pre_epidemic),
                '{:.1f}'.format(threshold_pos_epidemic),
                '{:.1f}'.format(threshold_epidemic)
            ), showlegend=True
        )

        figure_threshold.data.extend(figure_bar.data)
        figure_line.data.extend(figure_threshold.data)

        figure_line['layout']['yaxis2'].update(
            showgrid=False,
            range=[0, df['casos notif.'].max()]
        )

        figure_line['layout']['xaxis1'].update(
            tickangle=-60, nticks=len(df) // 4,
            title='Período (Ano/Semana)'
        )

        for trace in figure_line['data']:
            if trace['name'] == 'casos notif.':
                trace['visible'] = 'legendonly'

        return _plot_html(
            figure_or_data=figure_line, config={}, validate=True,
            default_width='100%', default_height=500, global_requirejs=''
        )[0]

    @classmethod
    def create_climate_chart(
        cls, df: pd.DataFrame, var_climate, year_week,
        climate_crit, climate_title
    ) -> 'Plotly_HTML':
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
        df_climate = df_climate[
            df_climate.SE >= year_week - 200
        ]

        df_climate['SE'] = df_climate.SE.map(
            lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
        )

        df_climate['Limiar favorável transmissão'] = climate_crit

        figure = df_climate.iplot(
            asFigure=True, x=['SE'], y=[k, 'Limiar favorável transmissão'],
            showlegend=True,
            yTitle=climate_title, xTitle='Período (Ano/Semana)'
        )

        figure['layout']['xaxis1'].update(
            tickangle=-60, nticks=len(df_climate)//4
        )

        figure['layout']['legend'].update(
            x=-.1, y=1.2,
            traceorder='normal',
            font=dict(
                family='sans-serif',
                size=12,
                color='#000'
            ),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1
        )

        return _plot_html(
            figure_or_data=figure, config={}, validate=True,
            default_width='100%', default_height=500, global_requirejs=''
        )[0]

    @classmethod
    def create_tweet_chart(
        cls, df: pd.DataFrame, year_week
    ) -> 'Plotly_HTML':
        """

        :param df:
        :param var_climate:
        :param year_week:
        :param climate_crit:
        :param climate_title:
        :return:
        """
        df_tweet = df.reset_index()[['SE', 'tweets']]
        df_tweet = df_tweet[
            df_tweet.SE >= year_week - 200
        ]

        df_tweet['SE'] = df_tweet.SE.map(
            lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
        )

        df_tweet.rename(columns={'tweets': 'menções'}, inplace=True)

        figure = df_tweet.iplot(
            x=['SE'],
            y=['menções'], asFigure=True,
            showlegend=True, xTitle='Período (Ano/Semana)'
        )
        figure['layout']['xaxis1'].update(
            tickangle=-60, nticks=len(df_tweet)//4
        )
        figure['layout']['yaxis1'].update(title='Tweets')

        figure['layout']['legend'].update(
            x=-.1, y=1.2,
            traceorder='normal',
            font=dict(
                family='sans-serif',
                size=12,
                color='#000'
            ),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1
        )

        return _plot_html(
            figure_or_data=figure, config={}, validate=True,
            default_width='100%', default_height=500, global_requirejs=''
        )[0]


class ReportStateCharts:
    @classmethod
    def create_tweet_chart(
        cls, df: pd.DataFrame, year_week
    ) -> 'Plotly_HTML':
        """

        :param df:
        :param year_week:
        :return:
        """
        ks_cases = [
            'casos notif. dengue',
            'casos notif. chik',
            'casos notif. zika'
        ]

        df_tweet = df.reset_index()[['SE', 'tweets'] + ks_cases]
        df_tweet = df_tweet[
            df_tweet.SE >= year_week - 200
        ]

        df_tweet['SE'] = df_tweet.SE.map(
            lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
        )

        df_tweet.rename(columns={'tweets': 'menções'}, inplace=True)

        fig_tweet = df_tweet.iplot(
            x=['SE'],
            y=['menções'], asFigure=True,
            showlegend=True, xTitle='Período (Ano/Semana)',
            color=['rgb(0,0,0)']
        )

        fig_cases = df_tweet.iplot(
            x=['SE'], y=ks_cases, asFigure=True,
            secondary_y=ks_cases, secondary_y_title='Casos',
            showlegend=True, xTitle='Período (Ano/Semana)'
        )

        fig_cases.data.extend(fig_tweet.data)

        fig_cases['layout']['xaxis1'].update(
            tickangle=-60,
            nticks=len(df_tweet) // 24
        )
        fig_cases['layout']['yaxis1'].update(
            title='Tweets',
            range=[0, df_tweet['menções'].max()]
        )
        fig_cases['layout']['yaxis2'].update(
            range=[0, df_tweet[ks_cases].max().max()]
        )

        fig_cases['layout']['legend'].update(
            x=-.1, y=1.2,
            traceorder='normal',
            font=dict(
                family='sans-serif',
                size=12,
                color='#000'
            ),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1
        )

        return _plot_html(
            figure_or_data=fig_cases, config={}, validate=True,
            default_width='100%', default_height=500, global_requirejs=''
        )[0]