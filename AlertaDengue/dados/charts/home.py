from datetime import timedelta
from time import mktime
import json
from django.utils.translation import gettext as _

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from django_plotly_dash import DjangoDash

import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots
import numpy as np
import dash_core_components as dcc
import plotly.express as px


# local
from .dbdata import get_series_by_UF, load_series, sql_home_charts


def home_chart1():
    animals = ['giraffes', 'orangutans', 'monkeys']

    fig = go.Figure(
        data=[
            go.Bar(name='SF Zoo', x=animals, y=[20, 14, 23]),
            go.Bar(name='LA Zoo', x=animals, y=[12, 18, 29]),
        ]
    )
    # Change the bar mode
    fig.update_layout(
        barmode='group',
        autosize=False,
        width=295,
        height=145,
        margin=dict(l=50, r=50, b=10, t=10, pad=4),
        paper_bgcolor="LightSteelBlue",
        legend=dict(
            x=0,
            y=1.0,
            bgcolor='rgba(255, 255, 255, 0)',
            bordercolor='rgba(255, 255, 255, 0)',
        ),
    )

    graph = fig.to_html(full_html=False, default_height=270, default_width=350)
    return graph


def home_chart2():
    # Stack chart
    animals = ['giraffes', 'orangutans', 'monkeys']

    fig2 = go.Figure(
        data=[
            go.Bar(name='SF Zoo', x=animals, y=[20, 14, 23]),
            go.Bar(name='LA Zoo', x=animals, y=[12, 18, 29]),
        ]
    )
    # Change the bar mode
    fig2.update_layout(
        barmode='stack',
        autosize=False,
        width=275,
        height=145,
        margin=dict(l=50, r=50, b=10, t=10, pad=4),
        paper_bgcolor="LightSteelBlue",
        legend=dict(
            x=0,
            y=1.0,
            bgcolor='rgba(255, 255, 255, 0)',
            bordercolor='rgba(255, 255, 255, 0)',
        ),
    )

    graph2 = fig2.to_html(
        full_html=False, default_height=270, default_width=350
    )
    return graph2


def home_chart3():
    # Chart line
    x = np.arange(10)

    fig3 = go.Figure(data=go.Scatter(x=x, y=x ** 2))
    fig3.update_layout(
        barmode='stack',
        autosize=False,
        width=275,
        height=145,
        margin=dict(l=50, r=50, b=10, t=10, pad=4),
        paper_bgcolor="LightSteelBlue",
        legend=dict(
            x=0,
            y=1.0,
            bgcolor='rgba(255, 255, 255, 0)',
            bordercolor='rgba(255, 255, 255, 0)',
        ),
    )

    graph3 = fig3.to_html(
        full_html=False, default_height=270, default_width=350
    )
    return graph3


def home_chart4():
    # Scatter
    N = 1000
    t = np.linspace(0, 10, 100)
    y = np.sin(t)

    fig4 = go.Figure(data=go.Scatter(x=t, y=y, mode='markers'))
    fig4.update_layout(
        barmode='stack',
        autosize=False,
        width=275,
        height=145,
        margin=dict(l=50, r=50, b=10, t=10, pad=4),
        paper_bgcolor="LightSteelBlue",
        legend=dict(
            x=0,
            y=1.0,
            bgcolor='rgba(255, 255, 255, 0)',
            bordercolor='rgba(255, 255, 255, 0)',
        ),
    )

    graph4 = fig4.to_html(
        full_html=False, default_height=270, default_width=350
    )
    return graph4


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = DjangoDash('SimpleExample', external_stylesheets=external_stylesheets)

app.layout = html.Div(
    [
        html.H1('Square Root Slider Graph'),
        dcc.Graph(
            id='slider-graph',
            animate=True,
            style={"backgroundColor": "#1a2d46", 'color': '#ffffff'},
        ),
        dcc.Slider(
            id='slider-updatemode',
            marks={i: '{}'.format(i) for i in range(20)},
            max=20,
            value=2,
            step=1,
            updatemode='drag',
        ),
    ]
)


@app.callback(
    Output('slider-graph', 'figure'), [Input('slider-updatemode', 'value')]
)
def display_value(value):

    x = []
    for i in range(value):
        x.append(i)

    y = []
    for i in range(value):
        y.append(i * i)

    graph = go.Scatter(x=x, y=y, name='Manipulate Graph')
    layout = go.Layout(
        paper_bgcolor='#27293d',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(range=[min(x), max(x)]),
        yaxis=dict(range=[min(y), max(y)]),
        font=dict(color='white'),
    )
    return {'data': [graph], 'layout': layout}


def home_chart_bar():
    df = sql_home_charts()

    df_home = df[['SE', 'casos_est', 'casos', 'nome', 'uf', 'Rt']]

    filter_se = df_home.SE > 202015

    select_uf = df_home['uf'].map(lambda x: x.startswith('Ceará'))

    df_uf = df_home[select_uf][filter_se].sort_values('uf')
    df_ufs = df_uf.groupby('SE').sum()

    # import pdb; pdb.set_trace()
    colors = {
        'A': px.colors.qualitative.Light24[2],
        'B': px.colors.qualitative.Pastel2[1],
    }

    fig = go.Figure(
        data=[
            go.Bar(
                name='Casos estatísticos',
                x=df_ufs.index.map(
                    lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
                ),
                y=df_ufs.casos_est,
                text=df_ufs.index.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate="Semana %{text}<br>Incidência=%{y:1f}",
                marker={'color': colors['B']}
                #         marker_color=
            ),
            go.Scatter(
                name='Casos',
                x=df_ufs.index.map(
                    lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
                ),
                y=df_ufs.casos,
                text=df_ufs.index.map(lambda v: '{}'.format(str(v)[-2:])),
                hoverinfo='text',
                hovertemplate="Semana %{text}<br>Incidência=%{y:1f}",
                marker={'color': colors['A']}
                #         marker_color=
            ),
        ]
    )
    # Change the bar mode
    fig.update_layout(
        xaxis=dict(
            title='Período (Ano/Semana)',
            tickangle=-60,
            nticks=4,
            showline=False,
            showgrid=True,
            showticklabels=True,
            linecolor='rgb(204, 204, 204)',
            linewidth=0,
            gridcolor='rgb(176, 196, 222)',
            ticks='outside',
            tickfont=dict(family='Arial', size=12, color='rgb(82, 82, 82)'),
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
        autosize=False,
        width=575,
        height=245,
        margin=dict(l=50, r=50, b=10, t=30, pad=4),
    )
    fig.update_layout(title=df_uf.uf.iloc[0])

    graph = fig.to_html(full_html=False, default_height=270, default_width=350)
    return graph
