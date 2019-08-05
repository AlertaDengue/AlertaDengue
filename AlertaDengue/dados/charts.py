import altair as alt
import pandas as pd


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
        """
        k = 'incidência'

        df['alerta verde'] = df[df.level_code == 1][k]
        df['alerta amarelo'] = df[df.level_code == 2][k]
        df['alerta laranja'] = df[df.level_code == 3][k]
        df['alerta vermelho'] = df[df.level_code == 4][k]

        df['limiar epidêmico'] = threshold_epidemic
        df['limiar pós epidêmico'] = threshold_pos_epidemic
        df['limiar pré epidêmico'] = threshold_pre_epidemic


        figure_bar = df.iplot(
            asFigure=True,
            kind='bar',
            x=['SE'],
            y=[
                'alerta verde',
                'alerta amarelo',
                'alerta laranja',
                'alerta vermelho',
            ],
            legend=True,
            showlegend=True,
            yTitle='Incidência',
            xTitle='Período (Ano/Semana)',
            color=[
                'rgb(0,255,0)',
                'rgb(255,255,0)',
                'rgb(255,150,0)',
                'rgb(255,0,0)',
            ],
            hoverinfo='x+y+name',
        )

        figure_threshold = df.iplot(
            asFigure=True,
            x=['SE'],
            y=[
                'limiar pré epidêmico',
                'limiar pós epidêmico',
                'limiar epidêmico',
            ],
            legend=False,
            showlegend=False,
            color=['rgb(0,255,0)', 'rgb(255,150,0)', 'rgb(255,0,0)'],
            hoverinfo='none',
        )

        figure_line = df.iplot(
            asFigure=True,
            x=['SE'],
            y=['casos notif.'],
            legend=False,
            showlegend=False,
            secondary_y=['casos notif.'],
            secondary_y_title='Casos',
            hoverinfo='x+y+name',
            color=['rgb(33,33,33)'],
        )

        figure_line['layout']['legend'].update(
            x=-0.27,
            y=0.5,
            traceorder='normal',
            font=dict(family='sans-serif', size=12, color='#000'),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1,
            orientation='l',
        )

        figure_line['layout']['yaxis1'].update(title='Incidência')

        figure_line['layout'].update(
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
            showlegend=True,
        )

        figure_threshold.data.extend(figure_bar.data)
        figure_line.data.extend(figure_threshold.data)

        figure_line['layout']['yaxis2'].update(
            showgrid=False, range=[0, df['casos notif.'].max()]
        )

        figure_line['layout']['xaxis1'].update(
            tickangle=-60, nticks=len(df) // 4, title='Período (Ano/Semana)'
        )

        for trace in figure_line['data']:
            if trace['name'] == 'casos notif.':
                trace['visible'] = 'legendonly'

        return _plot_html(
            figure_or_data=figure_line,
            config={},
            validate=True,
            default_width='100%',
            default_height=500,
            global_requirejs='',
        )[0]
        """
        df_casos = df.rename(columns={"casos notif.": "casosnotif"})

        # Legendas
        df_casos.insert(1, 'labelIncidencia', 'incidência')
        df_casos.insert(2, 'labelCasos', 'Casos')

        base = alt.Chart(df_casos).encode(
            alt.X('SE:T', axis=alt.Axis(title='Período (Ano/Semana)'))
        )
        bar = (
            base.mark_bar()
            .encode(
                alt.Y('incidência:Q', axis=alt.Axis(title='Incidência')),
                alt.Color('labelIncidencia', legend=alt.Legend(title='')),
            )
            .interactive()
        )

        line = (
            base.mark_line(color="#ffd100", strokeWidth=5)
            .encode(
                alt.Y('casosnotif:Q', axis=alt.Axis(title='Casos')),
                alt.Color('labelCasos', legend=alt.Legend(title='')),
            )
            .interactive()
        )

        return (
            (bar + line)
            .resolve_scale(y='independent')
            .configure_legend(orient='bottom')
            .configure_axis(labelColor='black')
            .properties(width=1050)
        )

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
        """
        figure = df_climate.iplot(
            asFigure=True,
            x=['SE'],
            y=[k, 'Limiar favorável transmissão'],
            showlegend=True,
            yTitle=climate_title,
            xTitle='Período (Ano/Semana)',
        )

        figure['layout']['xaxis1'].update(
            tickangle=-60, nticks=len(df_climate) // 4
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

        return _plot_html(
            figure_or_data=figure,
            config={},
            validate=True,
            default_width='100%',
            default_height=500,
            global_requirejs='',
        )[0]
        """

        df_climate_chart = df_climate.rename(
            columns={
                "temp.min": "temp_min",
                "Limiar favorável transmissão": "limiar_transmissao",
            }
        )

        return (
            alt.Chart(df_climate_chart)
            .mark_trail(strokeWidth=2, color='orange')
            .encode(
                alt.X('SE:T', axis=alt.Axis(title='Período (Ano/Semana)')),
                alt.Y('temp_min:Q', axis=alt.Axis(title='Temperatura')),
            )
            .properties(width=1050)
        )

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

        """
        figure = df_tweet.iplot(
            x=['SE'],
            y=['menções'],
            asFigure=True,
            showlegend=True,
            xTitle='Período (Ano/Semana)',
        )
        figure['layout']['xaxis1'].update(
            tickangle=-60, nticks=len(df_tweet) // 4
        )
        figure['layout']['yaxis1'].update(title='Tweets')

        figure['layout']['legend'].update(
            x=-0.1,
            y=1.2,
            traceorder='normal',
            font=dict(family='sans-serif', size=12, color='#000'),
            bgcolor='#FFFFFF',
            bordercolor='#E2E2E2',
            borderwidth=1,
        )

        return _plot_html(
            figure_or_data=figure,
            config={},
            validate=True,
            default_width='100%',
            default_height=500,
            global_requirejs='',
        )[0]
        """
        return (
            alt.Chart(df_tweet)
            .mark_trail(strokeWidth=2, color='orange')
            .encode(
                alt.X('SE:T', axis=alt.Axis(title='Período (Ano/Semana)')),
                alt.Y('tweets:Q', axis=alt.Axis(title='Tweets')),
            )
            .properties(width=1050)
        )


class ReportStateCharts:
    @classmethod
    def create_tweet_chart(cls, df: pd.DataFrame, year_week, disease: str):
        """
        :param df:
        :param year_week:
        :param disease:
        :return:
        """
        k_cases = 'casos notif. {}'.format(disease)
        df = df.rename(columns={k_cases: k_cases.replace('.', '')})
        k_cases = k_cases.replace('.', '')

        df.index.name = 'SE'
        df_tweet = df.reset_index()[['SE', 'tweets', k_cases]]

        df_tweet = df_tweet[df_tweet.SE >= year_week - 200]

        df_grp = (
            df_tweet.groupby(df.index)[['tweets', k_cases]].sum().reset_index()
        )

        df_grp['SE'] = df_grp.SE.map(
            lambda v: '%s/%s' % (str(v)[:4], str(v)[-2:])
        )

        # Legendas
        df_grp.insert(1, 'Tweets', 'Tweets')
        df_grp.insert(2, 'Casos', 'Casos')

        se = alt.Chart(df_grp).encode(
            alt.X('SE:T', axis=alt.Axis(title='Período (Ano/Semana)'))
        )

        tweets = (
            se.mark_line(strokeWidth=2, color='blue')
            .encode(
                alt.Y('tweets:Q', axis=alt.Axis(title='Tweets')),
                alt.Color('Tweets', legend=alt.Legend(title='')),
            )
            .interactive()
        )

        casos = (
            se.mark_trail(strokeWidth=2, color='orange')
            .encode(
                alt.Y(k_cases + ':Q', axis=alt.Axis(title='Casos')),
                alt.Color('Casos', legend=alt.Legend(title='')),
            )
            .interactive()
        )

        return (
            (tweets + casos)
            .resolve_scale(y='independent')
            .configure_legend(orient='bottom')
            .configure_axis(labelColor='black')
            .properties(width=1050)
        )
