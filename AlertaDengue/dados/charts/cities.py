from copy import deepcopy
from time import mktime
import json
from django.utils.translation import gettext as _

import plotly.graph_objs as go
import pandas as pd
from plotly.subplots import make_subplots

# local
from dados.dbdata import load_series


def int_or_none(x):
    return None if x is None else int(x)


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
            plot_bgcolor='rgb(255, 255, 255)',
            paper_bgcolor='rgb(245, 246, 249)',
            width=1100,
            height=500,
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
                hoverformat=".1f",
            ),
            showlegend=True,
            plot_bgcolor='rgb(255, 255, 255)',
            paper_bgcolor='rgb(245, 246, 249)',
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
            plot_bgcolor='rgb(255, 255, 255)',
            paper_bgcolor='rgb(245, 246, 249)',
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

        # TODO: check this code

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
                name='Tweets',
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
                name='Casos notificados',
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
            title='Menções na mídia social',
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
        figure.update_yaxes(title_text="<b>Menções</b>", secondary_y=False)
        figure.update_yaxes(title_text="<b>Casos</b>", secondary_y=True)

        return figure.to_html()


class CityCharts:
    @classmethod
    def prepare_data(
        cls, geocode, nome, disease_label, disease='dengue', epiweek=0
    ):
        dados = load_series(geocode, disease, epiweek)[geocode]
        if dados is None:
            return {
                'nome': nome,
                'dados': {},
                'start': {},
                'verde': {},
                'amarelo': {},
                'laranja': {},
                'vermelho': {},
                'disease_label': disease_label,
            }
        dados['dia'] = [int(mktime(d.timetuple())) for d in dados['dia']]
        # green alert
        ga = [
            int(c) if a == 0 else None
            for a, c in zip(dados['alerta'], dados['casos'])
        ]
        ga = [
            int_or_none(dados['casos'][n])
            if i is None and ga[n - 1] is not None
            else int_or_none(i)
            for n, i in enumerate(ga)
        ]
        # yellow alert
        ya = [
            int(c) if a == 1 else None
            for a, c in zip(dados['alerta'], dados['casos'])
        ]
        ya = [
            int_or_none(dados['casos'][n])
            if i is None and ya[n - 1] is not None
            else int_or_none(i)
            for n, i in enumerate(ya)
        ]
        # orange alert
        oa = [
            int(c) if a == 2 else None
            for a, c in zip(dados['alerta'], dados['casos'])
        ]
        oa = [
            int_or_none(dados['casos'][n])
            if i is None and oa[n - 1] is not None
            else int_or_none(i)
            for n, i in enumerate(oa)
        ]
        # red alert
        ra = [
            int(c) if a == 3 else None
            for a, c in zip(dados['alerta'], dados['casos'])
        ]
        ra = [
            int_or_none(dados['casos'][n])
            if i is None and ra[n - 1] is not None
            else int_or_none(i)
            for n, i in enumerate(ra)
        ]

        result = {
            'nome': nome,
            'dados': dados,
            'start': dados['dia'][0],
            'verde': json.dumps(ga),
            'amarelo': json.dumps(ya),
            'laranja': json.dumps(oa),
            'vermelho': json.dumps(ra),
            'disease_label': disease_label,
        }
        result.update(dados)
        return result

    @classmethod
    def create_alert_chart(
        cls, geocode, nome, disease_label, disease_code='dengue', epiweek=0
    ):

        result = cls.prepare_data(
            geocode, nome, disease_label, disease_code, epiweek
        )

        df_dados = pd.DataFrame(result['dados'])

        if df_dados.empty:
            raise ValueError('Data for alert chart creation is empty')

        df_verde = df_dados[df_dados.alerta == 0]
        df_verde.index = pd.to_datetime(df_verde.dia, unit='s')
        df_verde.sort_index(inplace=True)

        df_amarelo = df_dados[df_dados.alerta == 1]
        df_amarelo.index = pd.to_datetime(df_amarelo.dia, unit='s')
        df_amarelo.sort_index(inplace=True)

        df_laranja = df_dados[df_dados.alerta == 2]
        df_laranja.index = pd.to_datetime(df_laranja.dia, unit='s')
        df_laranja.sort_index(inplace=True)

        df_vermelho = df_dados[df_dados.alerta == 3]
        df_vermelho.index = pd.to_datetime(df_vermelho.dia, unit='s')
        df_vermelho.sort_index(inplace=True)

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(df_dados.dia, unit='s'),
                y=df_dados.casos,
                mode='lines',
                name=_('Casos Notificados de ') + disease_label,
                line={'color': '#4572A7'},
                text=df_dados.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hovertemplate=_(
                    '%{x} <br>'
                    'Semana: %{text} <br>'
                    '%{y} Casos Estimados'
                    '<extra></extra>'
                ),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(df_verde.dia, unit='s'),
                y=df_verde.casos,
                name=_('Alerta Verde de ') + disease_label,
                marker={'color': '#48FD48'},
                text=df_verde.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hovertemplate=_(
                    '%{x} <br>'
                    'Semana: %{text} <br>'
                    '%{y} Casos Estimados'
                    '<extra></extra>'
                ),
                stackgroup='one',
                fill=None,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(df_amarelo.dia, unit='s'),
                y=df_amarelo.casos,
                name=_('Alerta Amarelo de ') + disease_label,
                marker={'color': '#FBFC49'},
                text=df_amarelo.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hovertemplate=_(
                    '%{x} <br>'
                    'Semana: %{text} <br>'
                    '%{y} Casos Estimados'
                    '<extra></extra>'
                ),
                stackgroup='one',
                line=dict(width=0),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(df_laranja.dia, unit='s'),
                y=df_laranja.casos,
                name=_('Alerta Laranja de ') + disease_label,
                marker={'color': '#FFA858'},
                text=df_laranja.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hovertemplate=_(
                    '%{x} <br>'
                    'Semana: %{text} <br>'
                    '%{y} Casos Estimados'
                    '<extra></extra>'
                ),
                stackgroup='one',
                line=dict(width=0),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(df_vermelho.dia, unit='s'),
                y=df_vermelho.casos,
                name=_('Alerta Vermelho de ') + disease_label,
                marker={'color': '#FB4949'},
                text=df_vermelho.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hovertemplate=_(
                    '%{x} <br>'
                    'Semana: %{text} <br>'
                    '%{y} Casos Estimados'
                    '<extra></extra>'
                ),
                stackgroup='one',
                line=dict(width=0),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(df_dados.dia, unit='s'),
                y=df_dados.casos_est,
                mode='lines',
                name=_('Casos Estimados de ') + disease_label,
                line={'color': '#AA4643', 'dash': 'dot'},
                text=df_dados.SE.map(lambda v: '{}'.format(str(v)[-2:])),
                hovertemplate=_(
                    '%{x} <br>' 'Semana: %{text} <br>' '%{y} Casos Estimados'
                ),
            )
        )

        fig.update_layout(
            xaxis=go.layout.XAxis(
                rangeselector=dict(buttons=list([dict(step="all")])),
                rangeslider=dict(visible=True),
                type="date",
            ),
            yaxis=dict(title=_('Casos'), gridcolor='rgb(220, 220, 220)'),
            plot_bgcolor='rgb(255, 255, 255)',
        )
        return fig.to_html()
