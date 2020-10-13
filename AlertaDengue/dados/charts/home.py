from datetime import timedelta
from time import mktime
from django.utils.translation import gettext as _

import plotly.graph_objs as go
import pandas as pd
from plotly.subplots import make_subplots

# local
from dados.dbdata import get_series_by_UF

'''
Module for plotting in the homepage charts
'''


class HomeCharts:
    colors = {
        'Ceará': 'rgb(0,0,0)',
        'Espírito Santo': 'rgb(255,0,0)',
        'Paraná': 'rgb(0,255,0)',
        'Minas Gerais': 'rgb(0,0,255)',
        'Rio de Janeiro': 'rgb(255,255,0)',
        'São Paulo': 'rgb(0,255,255)',
        'Rio Grande do Sul': 'rgb(255,150,0)',
        'Maranhão': 'rgb(255,0,255)',
    }

    @classmethod
    def total_series(cls, case_series, disease):
        '''
        :param case_series:
        :param disease: dengue|chikungunya|zika
        :return:
        '''
        # gc = context['geocodigos'][0]
        series = (
            get_series_by_UF(disease, weeks=52)
            if disease not in case_series
            else case_series[disease]
        )

        if series.empty:
            return {
                'ufs': [],
                'start': None,
                'series': {},
                'series_est': {},
                'disease': disease,
            }

        ufs = list(set(series.uf.tolist()))
        # 51 weeks to get the end of the SE
        start = series.data.max() - timedelta(weeks=51)
        start = int(mktime(start.timetuple()))
        casos = {}
        casos_est = {}
        initial_range = -52  # to get the last 52 weeks

        for uf in ufs:
            series_uf = series[series.uf == uf]
            datas = [
                int(mktime(d.timetuple())) * 1000
                for d in series_uf.data[initial_range:]
            ]
            casos[uf] = [
                list(t)
                for t in zip(datas, series_uf.casos_s[initial_range:].tolist())
            ]
            casos_est[uf] = [
                list(t)
                for t in zip(
                    datas, series_uf.casos_est_s[initial_range:].tolist()
                )
            ]

        return {
            'ufs': ufs,
            'start': start,
            'series': casos,
            'series_est': casos_est,
            'disease': disease,
        }

    @classmethod
    def _create_chart(cls, case_series, disease):
        series_est = cls.total_series(case_series, disease=disease)[
            'series_est'
        ]

        dfs = []
        for k, v in series_est.items():
            df = pd.DataFrame(v)
            df.set_index(pd.to_datetime(df[0], unit='ms'), inplace=True)
            df.drop(columns=0, inplace=True)
            df.rename(columns={1: k}, inplace=True)
            df.index.name = None
            dfs.append(df)

        df_ufs = pd.concat(dfs, sort=True)

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        for k in df_ufs:
            fig.add_trace(
                go.Scatter(
                    x=df_ufs.index,
                    y=df_ufs[k],
                    name=k,
                    marker={'color': cls.colors[k]},
                    text=df_ufs.index.strftime('%d-%b-%Y <br>{}'.format(k)),
                    hovertemplate=_(
                        '%{text} <br>' '%{y} Casos Estimados' '<extra></extra>'
                    ),
                ),
                secondary_y=True,
            )

        fig.update_layout(
            height=350,
            width=1000,
            title=go.layout.Title(
                text=_(
                    'Casos Estimados de {} ' 'nos municípios monitorados'
                ).format(disease.capitalize()),
                font=dict(family="sans-serif", size=16),
            ),
            plot_bgcolor='rgb(255, 255, 255)',
            paper_bgcolor='rgb(255, 255, 255)',
            showlegend=True,
            font=dict(family="sans-serif", size=12),
            xaxis=dict(
                # title='',
                tickangle=-20,
                nticks=len(df) // 3,
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
                # title='',
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=0,
                gridcolor='rgb(176, 196, 222)',
            ),
        )

        fig.update_yaxes(
            title_text=_('Casos'),
            secondary_y=True,
            showline=False,
            showgrid=True,
            showticklabels=True,
            linecolor='rgb(204, 204, 204)',
            linewidth=0,
            gridcolor='rgb(204, 204, 204)',
        )

        return fig.to_html()

    @classmethod
    def create_dengue_chart(cls, case_series):
        return cls._create_chart(case_series, 'dengue')

    @classmethod
    def create_chik_chart(cls, case_series):
        return cls._create_chart(case_series, 'chikungunya')

    @classmethod
    def create_zika_chart(cls, case_series):
        return cls._create_chart(case_series, 'zika')
