import json
from time import mktime

import pandas as pd
import plotly.graph_objs as go

# local
from dados.dbdata import load_series
from django.utils.translation import gettext as _


def int_or_none(x):
    return None if x is None else int(x)


class AlertCitiesCharts:
    @classmethod
    def prepare_data(
        cls, geocode, nome, disease_label, disease="dengue", epiweek=0
    ):
        dados = load_series(geocode, disease, epiweek)[geocode]
        if dados is None:
            return {
                "nome": nome,
                "dados": {},
                "start": {},
                "verde": {},
                "amarelo": {},
                "laranja": {},
                "vermelho": {},
                "disease_label": disease_label,
            }
        dados["dia"] = [int(mktime(d.timetuple())) for d in dados["dia"]]
        # green alert
        ga = [
            int(c) if a == 0 else None
            for a, c in zip(dados["alerta"], dados["casos"])
        ]
        ga = [
            int_or_none(dados["casos"][n])
            if i is None and ga[n - 1] is not None
            else int_or_none(i)
            for n, i in enumerate(ga)
        ]
        # yellow alert
        ya = [
            int(c) if a == 1 else None
            for a, c in zip(dados["alerta"], dados["casos"])
        ]
        ya = [
            int_or_none(dados["casos"][n])
            if i is None and ya[n - 1] is not None
            else int_or_none(i)
            for n, i in enumerate(ya)
        ]
        # orange alert
        oa = [
            int(c) if a == 2 else None
            for a, c in zip(dados["alerta"], dados["casos"])
        ]
        oa = [
            int_or_none(dados["casos"][n])
            if i is None and oa[n - 1] is not None
            else int_or_none(i)
            for n, i in enumerate(oa)
        ]
        # red alert
        ra = [
            int(c) if a == 3 else None
            for a, c in zip(dados["alerta"], dados["casos"])
        ]
        ra = [
            int_or_none(dados["casos"][n])
            if i is None and ra[n - 1] is not None
            else int_or_none(i)
            for n, i in enumerate(ra)
        ]

        result = {
            "nome": nome,
            "dados": dados,
            "start": dados["dia"][0],
            "verde": json.dumps(ga),
            "amarelo": json.dumps(ya),
            "laranja": json.dumps(oa),
            "vermelho": json.dumps(ra),
            "disease_label": disease_label,
        }
        result.update(dados)
        return result

    @classmethod
    def create_alert_chart(
        cls, geocode, nome, disease_label, disease_code="dengue", epiweek=0
    ):

        result = cls.prepare_data(
            geocode, nome, disease_label, disease_code, epiweek
        )

        df_dados = pd.DataFrame(result["dados"])

        if df_dados.empty:
            raise ValueError("Data for alert chart creation is empty")

        df_verde = df_dados[df_dados.alerta == 0]
        df_verde.index = pd.to_datetime(df_verde.dia, unit="s")
        df_verde.sort_index(inplace=True)

        df_amarelo = df_dados[df_dados.alerta == 1]
        df_amarelo.index = pd.to_datetime(df_amarelo.dia, unit="s")
        df_amarelo.sort_index(inplace=True)

        df_laranja = df_dados[df_dados.alerta == 2]
        df_laranja.index = pd.to_datetime(df_laranja.dia, unit="s")
        df_laranja.sort_index(inplace=True)

        df_vermelho = df_dados[df_dados.alerta == 3]
        df_vermelho.index = pd.to_datetime(df_vermelho.dia, unit="s")
        df_vermelho.sort_index(inplace=True)

        fig = go.Figure()

        fig.add_trace(
            # Notified cases
            go.Scatter(
                x=pd.to_datetime(df_dados.dia, unit="s"),
                y=df_dados.casos,
                mode="lines",
                name=_("Casos Notificados"),
                line={"color": "#4572A7"},
                text=df_dados.SE.map(lambda v: "{}".format(str(v)[-2:])),
                hovertemplate="%(label0)s <br>%(label1)s %(week)s<br>"
                "%(cases)s %(label2)s"
                "<extra></extra>"
                % {
                    "label0": "%{x}",
                    "label1": _("SE"),
                    "week": "%{text}",
                    "cases": "%{y:1f}",
                    "label2": _("Casos"),
                },
            )
        )

        fig.add_trace(
            # Green alert
            go.Scatter(
                x=pd.to_datetime(df_verde.dia, unit="s"),
                y=df_verde.casos,
                name=_("Alerta Verde"),
                marker={"color": "#48FD48"},
                text=df_verde.SE.map(lambda v: "{}".format(str(v)[-2:])),
                hovertemplate="%(label0)s <br>%(label1)s %(week)s<br>"
                "%(cases)s %(label2)s"
                "<extra></extra>"
                % {
                    "label0": "%{x}",
                    "label1": _("SE"),
                    "week": "%{text}",
                    "cases": "%{y:1f}",
                    "label2": _("Casos"),
                },
                stackgroup="one",
                fill=None,
                line=dict(width=0),
            )
        )

        fig.add_trace(
            # Yellow alert
            go.Scatter(
                x=pd.to_datetime(df_amarelo.dia, unit="s"),
                y=df_amarelo.casos,
                name=_("Alerta Amarelo"),
                marker={"color": "#FBFC49"},
                text=df_amarelo.SE.map(lambda v: "{}".format(str(v)[-2:])),
                hovertemplate="%(label0)s <br>%(label1)s %(week)s<br>"
                "%(cases)s %(label2)s"
                "<extra></extra>"
                % {
                    "label0": "%{x}",
                    "label1": _("SE"),
                    "week": "%{text}",
                    "cases": "%{y:1f}",
                    "label2": _("Casos"),
                },
                stackgroup="one",
                line=dict(width=0),
            )
        )

        fig.add_trace(
            # Orange alert
            go.Scatter(
                x=pd.to_datetime(df_laranja.dia, unit="s"),
                y=df_laranja.casos,
                name=_("Alerta Laranja"),
                marker={"color": "#FFA858"},
                text=df_laranja.SE.map(lambda v: "{}".format(str(v)[-2:])),
                hovertemplate="%(label0)s <br>%(label1)s %(week)s<br>"
                "%(cases)s %(label2)s"
                "<extra></extra>"
                % {
                    "label0": "%{x}",
                    "label1": _("SE"),
                    "week": "%{text}",
                    "cases": "%{y:1f}",
                    "label2": _("Casos"),
                },
                stackgroup="one",
                line=dict(width=0),
            )
        )

        fig.add_trace(
            # Red alert
            go.Scatter(
                x=pd.to_datetime(df_vermelho.dia, unit="s"),
                y=df_vermelho.casos,
                name=_("Alerta Vermelho"),
                marker={"color": "#FB4949"},
                text=df_vermelho.SE.map(lambda v: "{}".format(str(v)[-2:])),
                hovertemplate="%(label0)s <br>%(label1)s %(week)s<br>"
                "%(cases)s %(label2)s"
                "<extra></extra>"
                % {
                    "label0": "%{x}",
                    "label1": _("SE"),
                    "week": "%{text}",
                    "cases": "%{y:1f}",
                    "label2": _("Casos"),
                },
                stackgroup="one",
                line=dict(width=0),
            )
        )

        fig.add_trace(
            # Estimated cases
            go.Scatter(
                x=pd.to_datetime(df_dados.dia, unit="s"),
                y=df_dados.casos_est,
                mode="lines",
                name=_("Casos Estimados"),
                line={"color": "#AA4643", "dash": "dot"},
                text=df_dados.SE.map(lambda v: "{}".format(str(v)[-2:])),
                hovertemplate="%(label0)s <br>%(label1)s %(week)s<br>"
                "%(cases)s %(label2)s"
                "<extra></extra>"
                % {
                    "label0": "%{x}",
                    "label1": _("SE"),
                    "week": "%{text}",
                    "cases": "%{y:1f}",
                    "label2": _("Casos Estimados"),
                },
            )
        )

        fig.update_layout(
            xaxis=dict(
                title=_("Mês/Ano"),
                tickangle=-15,
                showline=True,
                showgrid=True,
                showticklabels=True,
                linecolor="rgb(204, 204, 204)",
                linewidth=2,
                gridcolor="rgb(176, 196, 222)",
                rangeslider=dict(visible=False),
                type="date",
            ),
            yaxis=dict(title=_("Casos"), gridcolor="rgb(220, 220, 220)"),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=1.20,
                xanchor="left",
                # x=1,
            ),
            hoverlabel=dict(
                # bgcolor="white",
                font_size=12,
                font_family="Rockwell",
            ),
            autosize=True,
            # height=275,
            # width=310,
            margin=dict(
                autoexpand=True,
                # l=50,
                # r=20,
                t=20,
                # b=150,
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            modebar={
                "orientation": "v",
                "bgcolor": "rgba(255 ,255 ,255 ,0.7)",
            },
        )
        return fig.to_html()
