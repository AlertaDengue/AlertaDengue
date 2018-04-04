from plotly.offline.offline import _plot_html

import base64
import cufflinks as cf
import datetime
import io
import matplotlib.pyplot as plt
import pandas as pd


def transform_chart_to_base64(df: pd.DataFrame):
    """
    :param df:
    :return:

    """
    buf = io.BytesIO()
    df.plot()
    plt.savefig(buf, format="png")
    img = str(base64.b64encode(buf.getvalue()).strip())
    return img[2:-1]


class ReportCityCharts:
    @classmethod
    def create_incidence_chart(
        cls, df: pd.DataFrame, year_week: int, threshold_pre_epidemic: float,
        threshold_pos_epidemic: float, threshold_epidemic: float
    ) -> 'Plotly_HTML':
        """

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

        df['Data'] = df.SE.apply(
            lambda x: datetime.datetime.strptime(str(x) + '-0', '%Y%W-%w')
        )

        k = 'incidência'

        df['alerta verde'] = df[df.level_code == 1][k]
        df['alerta amarelo'] = df[df.level_code == 2][k]
        df['alerta laranja'] = df[df.level_code == 3][k]
        df['alerta vermelho'] = df[df.level_code  == 4][k]

        df['limiar epidêmico'] = threshold_epidemic
        df['limiar pós epidêmico'] = threshold_pos_epidemic
        df['limiar pré epidêmico'] = threshold_pre_epidemic

        figure_bar = df.iplot(
            asFigure=True, kind='bar', x=['Data'], y=[
                'alerta verde',
                'alerta amarelo',
                'alerta laranja',
                'alerta vermelho'
            ],
            showlegend=False,
            yTitle='Incidência', xTitle='Período (Ano/Semana)',
            color=[
                'rgb(0,255,0)', 'rgb(255,255,0)',
                'rgb(255,150,0)', 'rgb(255,0,0)'
            ], hoverinfo='none'
        )

        figure_threshold = df.iplot(
            asFigure=True, x=['Data'], y=[
                'limiar pré epidêmico',
                'limiar pós epidêmico',
                'limiar epidêmico'
            ], showlegend=True, color=[
                'rgb(0,255,0)', 'rgb(255,150,0)', 'rgb(255,0,0)'
            ], hoverinfo='none'
        )

        figure_line = df.iplot(
            asFigure=True, x=['Data'], y=['casos notif.'],
            showlegend=False,
            secondary_y=['casos notif.'], secondary_y_title='Casos',
            hoverinfo='none'
        )

        figure_line['layout']['xaxis1'].update(
            tickangle=-60, tickformat='%Y/%W'
        )

        figure_line['layout']['legend'].update(
            x=-.1, y=1.2,
            traceorder='normal',
            font=dict(
                family='sans-serif',
                size=12,
                color='#000'
            ),
            bgcolor='#E2E2E2',
            bordercolor='#FFFFFF',
            borderwidth=2
        )

        figure_line['layout']['yaxis1'].update(
            title='Incidência'
        )

        figure_line['layout'].update(
            title=(
                'Limiares: ' +
                'pré epidêmico=%s; ' +
                'pós epidêmico=%s; ' +
                'epidêmico=%s;'
            ) % (
                threshold_pre_epidemic,
                threshold_pos_epidemic,
                threshold_epidemic
            )
        )

        figure_threshold.data.extend(figure_bar.data)
        figure_line.data.extend(figure_threshold.data)

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

        df_climate['Data'] = df_climate.SE.apply(
            lambda x: datetime.datetime.strptime(str(x) + '-0', '%Y%W-%w')
        )

        df_climate['Limiar favorável transmissão'] = climate_crit

        figure = df_climate.iplot(
            asFigure=True, x=['Data'], y=[k, 'Limiar favorável transmissão'],
            showlegend=True,
            yTitle=climate_title, xTitle='Período (Ano/Semana)'
        )

        figure['layout']['xaxis1'].update(
            tickangle=-60, tickformat='%Y/%W'
        )

        figure['layout']['legend'].update(
            x=-.1, y=1.2,
            traceorder='normal',
            font=dict(
                family='sans-serif',
                size=12,
                color='#000'
            ),
            bgcolor='#E2E2E2',
            bordercolor='#FFFFFF',
            borderwidth=2
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
        df_tweet = df.reset_index()[['SE', 'tweets', 'casos notif.']]
        df_tweet = df_tweet[
            df_tweet.SE >= year_week - 200
        ]

        df_tweet['Data'] = df_tweet.SE.apply(
            lambda x: datetime.datetime.strptime(str(x) + '-0', '%Y%W-%w')
        )

        df_tweet.rename(columns={'tweets': 'menções'}, inplace=True)

        figure = df_tweet.iplot(
            x=['Data'],
            y=['menções', 'casos notif.'], asFigure=True,
            showlegend=True, xTitle='Período (Ano/Semana)'
        )
        figure = figure.set_axis('menções', side='right')
        figure['layout']['xaxis1'].update(
            tickangle=-60, tickformat='%Y/%W'
        )
        figure['layout']['yaxis1'].update(title='Casos')
        figure['layout']['yaxis2'].update(title='Tweets')

        figure['layout']['legend'].update(
            x=-.1, y=1.2,
            traceorder='normal',
            font=dict(
                family='sans-serif',
                size=12,
                color='#000'
            ),
            bgcolor='#E2E2E2',
            bordercolor='#FFFFFF',
            borderwidth=2
        )

        return _plot_html(
            figure_or_data=figure, config={}, validate=True,
            default_width='100%', default_height=500, global_requirejs=''
        )[0]
