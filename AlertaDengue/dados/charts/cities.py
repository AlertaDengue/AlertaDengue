from copy import deepcopy
from typing import Any

import pandas as pd
import plotly.graph_objs as go
from django.utils.translation import gettext as _
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
    ) -> go.Figure:
        """
        Creates an incidence chart based on the given DataFrame and thresholds.

        Parameters
        ----------
        df (pd.DataFrame): The DataFrame containing the data for the chart.
        year_week (int): The year and week number for the chart.
        threshold_pre_epidemic (float): The threshold for pre-epidemic level.
        threshold_pos_epidemic (float): The threshold for post-epidemic level.
        threshold_epidemic (float): The threshold for epidemic level.

        Returns
        -------
            str: The HTML representation of the chart.
        """

        df = df.reset_index()[
            ["SE", "incidência", "casos notif.", "casos_est", "level_code"]
        ]

        df["SE"] = df.SE.map(lambda v: "%s/%s" % (str(v)[:4], str(v)[-2:]))

        k = "casos notif."

        df[_("alerta verde")] = df[df.level_code == 1][k]
        df[_("alerta amarelo")] = df[df.level_code == 2][k]
        df[_("alerta laranja")] = df[df.level_code == 3][k]
        df[_("alerta vermelho")] = df[df.level_code == 4][k]

        df[_("limiar epidêmico")] = threshold_epidemic
        df[_("limiar pós epidêmico")] = threshold_pos_epidemic
        df[_("limiar pré epidêmico")] = threshold_pre_epidemic

        # Helper for unified hover
        level_map = {
            1: _("Verde"),
            2: _("Amarelo"),
            3: _("Laranja"),
            4: _("Vermelho"),
        }
        df["nivel_nome"] = df["level_code"].map(level_map)

        figure = make_subplots(specs=[[{"secondary_y": True}]])

        figure.add_trace(
            go.Scatter(
                x=df["SE"],
                y=df["casos notif."],
                name=_("Notificações"),
                mode="lines",
                line={"color": "#3A4750", "width": 2.5},
                customdata=df[["nivel_nome", "incidência", "casos_est"]],
                hovertemplate="<b>SE</b>: %{x}<br>"
                "<b>Alerta</b>: %{customdata[0]}<br>"
                "<b>Notificações</b>: %{y:.0f}<br>"
                "<b>Incidência</b>: %{customdata[1]:.1f}<br>"
                "<b>Estimados</b>: %{customdata[2]:.0f}<extra></extra>",
                hoverlabel=dict(namelength=0),
            ),
            secondary_y=True,
        )

        figure.add_trace(
            go.Scatter(
                x=df["SE"],
                y=df["casos_est"],
                name=_("Estimados (Nowcast)"),
                mode="lines",
                line={"color": "#4169e1", "dash": "dot", "width": 3.5},
                hoverinfo="skip",
            ),
            secondary_y=True,
        )

        ks_limiar = [
            _("limiar pré epidêmico"),
            _("limiar pós epidêmico"),
            _("limiar epidêmico"),
        ]

        colors = ["rgb(0,255,0)", "rgb(255,150,0)", "rgb(255,0,0)"]

        for k, c in zip(ks_limiar, colors):
            figure.add_trace(
                go.Scatter(
                    x=df["SE"],
                    y=df[k],
                    name=k.title(),
                    marker={"color": c},
                    hoverinfo="skip",
                ),
                secondary_y=False,
            )

        ks_alert = [
            _("alerta verde"),
            _("alerta amarelo"),
            _("alerta laranja"),
            _("alerta vermelho"),
        ]

        colors = [
            "rgb(0,255,0)",
            "rgb(255,255,0)",
            "rgb(255,150,0)",
            "rgb(255,0,0)",
        ]

        for k, c in zip(ks_alert, colors):
            figure.add_trace(
                go.Bar(
                    x=df["SE"],
                    y=df[k],
                    marker={"color": c},
                    name=k.title(),
                    width=0.8,
                    text=None,
                    hoverinfo="skip",
                ),
                secondary_y=True,
            )

        figure.update_layout(
            hovermode="closest",
            hoverlabel=dict(
                bgcolor="rgba(240, 240, 240, 0.9)",
                font_size=12,
                font_family="Arial, sans-serif",
            ),
            title=(
                _("Limiares de incidência")
                + ":"
                + "<br>"
                + "".ljust(8)
                + _("pré epidêmico")
                + "="
                + f"{threshold_pre_epidemic:.1f}".ljust(8)
                + _("pós epidêmico")
                + "="
                + f"{threshold_pos_epidemic:.1f}".ljust(8)
                + _("epidêmico")
                + "="
                + f"{threshold_epidemic:.1f}"
            ),
            font=dict(family="sans-serif", size=12, color="#000"),
            xaxis=dict(
                title=_("Período (Ano/Semana)"),
                tickangle=-60,
                nticks=len(df) // 4,
                showline=False,
                showgrid=True,
                showticklabels=True,
                linecolor="rgb(204, 204, 204)",
                linewidth=0,
                gridcolor="rgb(176, 196, 222)",
                ticks="outside",
                tickfont=dict(
                    family="Arial", size=12, color="rgb(82, 82, 82)"
                ),
                showspikes=False,
                hoverformat=" ",
            ),
            yaxis=dict(
                title=_("Incidência"),
                showline=False,
                showgrid=True,
                showticklabels=True,
                linecolor="rgb(204, 204, 204)",
                linewidth=0,
                gridcolor="rgb(176, 196, 222)",
            ),
            showlegend=True,
            legend=dict(
                traceorder="normal",
                font=dict(family="sans-serif", size=12, color="#000"),
                bgcolor="#FFFFFF",
                bordercolor="#E2E2E2",
                borderwidth=1,
            ),
            plot_bgcolor="rgb(255, 255, 255)",
            paper_bgcolor="rgb(245, 246, 249)",
            width=1100,
            height=500,
            barmode="overlay",
            bargap=0,
        )

        figure.update_yaxes(
            title_text=_("Casos"),
            secondary_y=True,
            showline=False,
            showgrid=True,
            showticklabels=True,
            linecolor="rgb(204, 204, 204)",
            linewidth=0,
            gridcolor="rgb(204, 204, 204)",
        )

        return figure.to_html()

    @classmethod
    def create_climate_chart(
        cls,
        df: pd.DataFrame,
        var_climate: dict[str, list[Any]],
    ) -> str:
        """
        :param df:
        :param var_climate:
        :return:
        """

        varcli_keys = list(var_climate.keys())
        varcli_values = list(var_climate.values())

        if not varcli_keys:
            return ""

        def get_series_label(index: int) -> str:
            return str(varcli_values[index][0])

        df_climate = deepcopy(df[["SE", *varcli_keys]])
        for column in varcli_keys:
            df_climate[column] = pd.to_numeric(
                df_climate[column], errors="coerce"
            )

        df_climate["SE"] = df_climate.SE.map(
            lambda v: "%s/%s" % (str(v)[:4], str(v)[-2:])
        )

        df_climate[f"threshold_{varcli_keys[0]}"] = var_climate[
            varcli_keys[0]
        ][1]

        figure = make_subplots(specs=[[{"secondary_y": True}]])
        # Temperature
        figure.add_trace(
            go.Scatter(
                x=df_climate["SE"],
                y=df_climate[varcli_keys[0]],
                name=get_series_label(0),
                mode="lines",
                line={"color": "rgb(255, 204, 153)", "width": 3},
                customdata=df_climate[varcli_keys[1]]
                if len(varcli_keys) == 2
                else [None] * len(df_climate),
                hovertemplate="SE: %{x}<br>"
                + f"<b>{get_series_label(0)}</b>: %{{y:.1f}}<br>"
                + (
                    f"<b>{get_series_label(1)}</b>: %{{customdata:.1f}}"
                    if len(varcli_keys) == 2
                    else ""
                )
                + "<extra></extra>",
                hoverlabel=dict(namelength=0),
            ),
            secondary_y=False,
        )
        # Temperature treshold
        figure.add_trace(
            go.Scatter(
                x=df_climate["SE"],
                y=df_climate[f"threshold_{varcli_keys[0]}"],
                name=("{} {}{}").format(
                    _("Limiar favorável"),
                    varcli_values[0][1],
                    varcli_values[0][0][0:2],
                ),
                mode="lines",
                line={"color": "rgb(255,150,0)", "width": 2},
                hoverinfo="skip",
            ),
            secondary_y=False,
        )

        if len(varcli_keys) == 2:

            df_climate[f"threshold_{varcli_keys[1]}"] = var_climate[
                varcli_keys[1]
            ][1]
            # Humidity
            figure.add_trace(
                go.Scatter(
                    x=df_climate["SE"],
                    y=df_climate[varcli_keys[1]],
                    name=get_series_label(1),
                    mode="lines",
                    line={"color": "rgb(173, 216, 230)", "width": 3},
                    hoverinfo="skip",
                ),
                secondary_y=True,
            )
            # Humidity treshold
            figure.add_trace(
                go.Scatter(
                    x=df_climate["SE"],
                    y=df_climate[f"threshold_{varcli_keys[1]}"],
                    name=("{} {}{}").format(
                        _("Limiar favorável"),
                        varcli_values[1][1],
                        varcli_values[1][0][0:2],
                    ),
                    mode="lines",
                    line={"color": "rgb(51, 172, 255)", "width": 2},
                    hoverinfo="skip",
                ),
                secondary_y=True,
            )

            figure.update_yaxes(
                title_text=f"{varcli_values[1][0]}", secondary_y=True
            )

        figure.update_layout(
            hovermode="closest",
            hoverlabel=dict(
                bgcolor="rgba(240, 240, 240, 0.9)",
                font_size=12,
                font_family="Arial, sans-serif",
            ),
            title=_("Condições climáticas para transmissão"),
            xaxis=dict(
                title=_("Período (Ano/Semana)"),
                tickangle=-60,
                nticks=len(df_climate) // 4,
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor="rgb(204, 204, 204)",
                linewidth=0,
                gridcolor="rgb(176, 196, 222)",
                showspikes=False,
                hoverformat=" ",
            ),
            yaxis=dict(
                title=f"{varcli_values[0][0]}",
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor="rgb(204, 204, 204)",
                linewidth=0,
                gridcolor="rgb(176, 196, 222)",
            ),
            showlegend=True,
            autosize=True,
            margin=dict(l=70, r=40, t=80, b=100),
            legend=dict(
                orientation="h",
                yanchor="middle",
                xanchor="right",
                y=1.10,
                x=0.94,
                font=dict(family="sans-serif", size=12, color="#000"),
                bgcolor="#FFFFFF",
                bordercolor="#E2E2E2",
                borderwidth=1,
            ),
            plot_bgcolor="rgb(255, 255, 255)",
            paper_bgcolor="rgb(245, 246, 249)",
            height=520,
        )

        return figure.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={"responsive": True},
        )
