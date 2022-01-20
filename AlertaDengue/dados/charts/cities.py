from django.utils.translation import gettext as _

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
        '''
        @see: https://stackoverflow.com/questions/45526734/
            hide-legend-entries-in-a-plotly-figure
        :param df:
        :param year_week:
        :param threshold_pre_epidemic: float,
        :param threshold_pos_epidemic: float
        :param threshold_epidemic: float
        :return:
        '''
        df = df.reset_index()[
            ['SE', 'incidência', 'casos notif.', 'level_code']
        ]

        # 200 = 2 years
        df = df[df.SE >= year_week - 200]

        df['SE'] = df.SE.map(lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:]))

        k = 'incidência'

        df[_('alerta verde')] = df[df.level_code == 1][k]
        df[_('alerta amarelo')] = df[df.level_code == 2][k]
        df[_('alerta laranja')] = df[df.level_code == 3][k]
        df[_('alerta vermelho')] = df[df.level_code == 4][k]

        df[_('limiar epidêmico')] = threshold_epidemic
        df[_('limiar pós epidêmico')] = threshold_pos_epidemic
        df[_('limiar pré epidêmico')] = threshold_pre_epidemic

        figure = make_subplots(specs=[[{'secondary_y': True}]])

        figure.add_trace(
            go.Scatter(
                x=df['SE'],
                y=df['casos notif.'],
                name=_('Notificações'),
                marker={'color': 'rgb(33,33,33)'},
                text=df.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate=_('Semana %{text}<br>%{y:1f} Casos')
                + '<extra></extra>',
            ),
            secondary_y=True,
        )

        ks_limiar = [
            _('limiar pré epidêmico'),
            _('limiar pós epidêmico'),
            _('limiar epidêmico'),
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
                    hovertemplate=_('Semana %{text}<br>%{y:1f} Incidências')
                    + '<extra></extra>',
                ),
                secondary_y=False,
            )

        ks_alert = [
            _('alerta verde'),
            _('alerta amarelo'),
            _('alerta laranja'),
            _('alerta vermelho'),
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
                    hovertemplate=_('Semana %{text}<br>%{y:1f} Incidências')
                    + '<extra></extra>',
                ),
                secondary_y=False,
            )

        figure.update_layout(
            title=(
                _('<b>Limiares de incidência</b>:<br>')
                + ''.ljust(8)
                + _('pré epidêmico=')
                + f'{threshold_pre_epidemic:.1f}'.ljust(8)
                + _('pós epidêmico=')
                + f'{threshold_pos_epidemic:.1f}'.ljust(8)
                + _('epidêmico=')
                + f'{threshold_epidemic:.1f}'
            ),
            font=dict(family='sans-serif', size=12, color='#000'),
            xaxis=dict(
                title=_('Período (Ano/Semana)'),
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
                title=_('Incidência'),
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
            height=500,
        )

        figure.update_yaxes(
            title_text=_('Casos Notificados'),
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
        '''
        :param df:
        :param var_climate:
        :param year_week:
        :param climate_crit:
        :param climate_title:
        :return:
        '''
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

        if k == 'temp.min':
            varclim_title = 'Temperatura'
        elif k == 'umid.max':
            varclim_title = 'Umidade relativa do ar'
        else:
            raise Exception('Climate variable not found.')

        figure = go.Figure()

        figure.add_trace(
            go.Scatter(
                x=df_climate['SE'],
                y=df_climate['threshold_transmission'],
                name=_('Limiar Favorável'),
                marker={'color': 'rgb(51, 172, 255)'},
                text=df_climate.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate=_('Semana %{text} : %{y:1f}°C')
                + '<extra></extra>',
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
                hovertemplate=_('Semana %{text} : %{y:1f}°C')
                + '<extra></extra>',
            )
        )

        figure.update_layout(
            # title = '',
            xaxis=dict(
                title=_('Período (Ano/Semana)'),
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
                orientation='h',
                yanchor='bottom',
                xanchor='auto',
                y=1.01,
                x=1,
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
        '''
        :param df:
        :param var_climate:
        :param year_week:
        :param climate_crit:
        :param climate_title:
        :return:
        '''
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
                name=_('Menções em tweets'),
                marker={'color': 'rgb(0,0,255)'},
                text=df_tweet.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate=_('Semana %{text} : %{y} Tweets')
                + '<extra></extra>',
            )
        )

        figure.update_layout(
            # title='',
            xaxis=dict(
                title=_('Período (Ano/Semana)'),
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
                orientation='h',
                yanchor='bottom',
                xanchor='auto',
                y=1.01,
                x=1,
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
