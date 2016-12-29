# coding: utf-8
from dados.maps import get_city_geojson, get_city_info
from dados import dbdata
from dados import models as M
from django.shortcuts import redirect
from django.views.generic.base import TemplateView, View
from django.contrib import messages
from django.http import HttpResponse
from time import mktime
from collections import defaultdict
from django.conf import settings

import random
import json
import os
import datetime
import numpy as np
import locale
import geojson

locale.setlocale(locale.LC_TIME, locale="pt_BR.UTF-8")

dados_alerta = dbdata.get_alerta_mrj()

with open(os.path.join(settings.STATICFILES_DIRS[0], 'rio_aps.geojson')) as f:
    polygons = geojson.load(f)


class AlertaMainView(TemplateView):
    template_name = 'main.html'

    def get_context_data(self, **kwargs):
        context = super(AlertaMainView, self).get_context_data(**kwargs)
        mundict = dict(dbdata.get_all_active_cities())
        municipios, geocodigos = list(mundict.values()), list(mundict.keys())
        del municipios

        # today
        today = datetime.datetime.today()
        se2 = str(today.isocalendar()[0])
        se2 += str(today.isocalendar()[1]).rjust(2, '0')

        # 7 days ago
        last_week = today - datetime.timedelta(days=0, weeks=1)
        se1 = str(last_week.isocalendar()[0])
        se1 += str(last_week.isocalendar()[1]).rjust(2, '0')

        # alerta = {}
        case_series = {}
        total = np.zeros(52, dtype=int)
        ufs = ['Rio de Janeiro', 'Paraná', 'Espírito Santo']
        sigla = {
            'Rio de Janeiro': 'RJ',
            'Paraná': 'PR',
            'Espírito Santo': 'ES'
        }

        conexao = dbdata.create_connection()

        results = dbdata.load_serie_cities(
            geocodigos, 'dengue', conexao
        )

        # series
        for gc, _case_series, in results.items():
            case_series[str(gc)] = _case_series['casos_est'][-12:]
            total += _case_series['casos_est'][-52:]

        count_cities = {}
        current_week = {}
        estimated_cases_next_week = {}
        variation_to_current_week = {}
        for uf in ufs:
            # Municípios participantes
            count_cities[uf] = dbdata.count_cities_by_state(uf, conexao)
            # Total de casos notificado e estimados na semana
            current_week[uf] = dbdata.count_cases_by_uf(
                uf, se2, conexao
            ).iloc[0].to_dict()
            # Previsão de casos para as próximas semanas
            estimated_cases_next_week[uf] = current_week[uf]['casos']
            # Variação em relação à semana anterior
            variation_to_current_week[uf] = (
                current_week[uf]['casos'] -
                dbdata.count_cases_by_uf(uf, se1, conexao).loc[0, 'casos']
            )

        context.update({
            # 'mundict': json.dumps(mundict),
            'num_mun': len(mundict),
            # 'municipios': municipios,
            'geocodigos': geocodigos,
            # 'alerta': json.dumps(alerta),
            'case_series': json.dumps(case_series),
            'total': json.dumps(total.tolist()),
            'states': ufs,
            'count_cities': count_cities,
            'current_week': current_week,
            'estimated_cases_next_week': estimated_cases_next_week,
            'variation_to_current_week': variation_to_current_week,
            'sigla': sigla
        })
        return context


def get_municipio(request):
    q = request.GET['q']
    muns = dbdata.get_city(q)
    data = json.dumps([
        {'geocodigo': g, 'nome': n, 'uf': u} for g, n, u in muns
    ])
    return HttpResponse(data, content_type='application/json')


class AlertaPageView(TemplateView):
    template_name = 'alerta.html'

    def get_context_data(self, **kwargs):
        context = super(AlertaPageView, self).get_context_data(**kwargs)
        alert, current, case_series, last_year, observed_cases, min_max_est = \
            get_alert()
        casos_ap = {
            float(ap.split('AP')[-1]):
                int(current[current.aps == ap]['casos_est'])
            for ap in alert.keys()
        }
        alerta = {
            float(k.split('AP')[-1]): int(v) - 1
            for k, v in alert.items()
        }
        semana = str(current.se.iat[-1])[-2:]
        segunda = current.data.iat[-1]
        city_info = get_city_info("3304557")
        total_series = sum(
            np.array(list(case_series.values())), np.zeros(12, int)
        )
        total_observed_series = sum(
            np.array(list(observed_cases.values())), np.zeros(12, int)
        )
        bairros_mrj = {
            1.0: 'AP 1: Centro e adjacências',
            2.1: 'AP 2.1: Zona Sul',
            2.2: 'AP 2.2: Tijuca e adjacências',
            3.1: 'AP 3.1: Bonsucesso e adjacências',
            3.2: 'AP 3.2: Meier e adjacências',
            3.3: 'AP 3.3: Madureira e adjacências',
            4.0: 'AP 4: Barra, Recreio e Jacarepaguá',
            5.1: 'AP 5.1: Bangu e adjacências',
            5.2: 'AP 5.2: Campo Grande e adjacências',
            5.3: 'AP 5.3: Santa Cruz e adjacências'
        }
        context.update({
            'geocodigo': "3304557",
            'nome': "Rio de Janeiro",
            'populacao': city_info['populacao'],
            'incidencia': (
                              total_observed_series[-1] / city_info['populacao']
                          ) * 100000,  # casos/100000
            'casos_por_ap': json.dumps(casos_ap),
            'alerta': alerta,
            'novos_casos': sum(casos_ap.values()),
            'bairros': bairros_mrj,
            'min_est': sum(i[0] for i in min_max_est.values()),
            'max_est': sum(i[1] for i in min_max_est.values()),
            'series_casos': case_series,
            'SE': int(semana),
            'data1': segunda.strftime("%d de %B de %Y"),
            'data2': (
                segunda + datetime.timedelta(6)
            ).strftime("%d de %B de %Y"),
            'last_year': last_year,
            'look_back': len(total_series),
            'total_series': ', '.join(map(str, total_series)),
            'total_observed': total_observed_series[-1],
            'total_observed_series': ', '.join(map(str, total_observed_series)),
        })
        return context


class AlertaPageViewMunicipio(TemplateView):
    template_name = 'alerta_municipio.html'

    def dispatch(self, request, *args, **kwargs):
        super(AlertaPageViewMunicipio, self) \
            .get_context_data(**kwargs)
        municipio_gc = kwargs['geocodigo']

        if int(municipio_gc) == 3304557:  # Rio de Janeiro
            return redirect('mrj', permanent=True)

        return super(AlertaPageViewMunicipio, self) \
            .dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AlertaPageViewMunicipio, self) \
            .get_context_data(**kwargs)
        municipio_gc = context['geocodigo']
        city_info = get_city_info(municipio_gc)
        (
            alert, SE, case_series, last_year,
            observed_cases, min_max_est, dia, prt1
        ) = dbdata.get_city_alert(municipio_gc)
        casos_ap = {municipio_gc: int(case_series[-1])}
        bairros = {municipio_gc: city_info['nome']}
        total_series = case_series[-12:]
        total_observed_series = observed_cases[-12:]
        context.update({
            'nome': city_info['nome'],
            'populacao': city_info['populacao'],
            'incidencia': (
                case_series[-1] / city_info['populacao']
            ) * 100000,  # casos/100000
            'casos_por_ap': json.dumps(casos_ap),
            'alerta': {municipio_gc: alert},
            'prt1': prt1 * 100,
            'novos_casos': case_series[-1],
            'bairros': bairros,
            'min_est': min_max_est[0],
            'max_est': min_max_est[1],
            'series_casos': {municipio_gc: case_series[-12:]},
            'SE': SE,
            'data1': dia.strftime("%d de %B de %Y"),
            'data2': (dia + datetime.timedelta(6)).strftime("%d de %B de %Y"),
            'last_year': last_year,
            'look_back': len(total_series),
            'total_series': ', '.join(map(str, total_series)),
            'total_observed': total_observed_series[-1],
            'total_observed_series': ', '.join(map(str, total_observed_series)),
            'geocodigo': municipio_gc,
        })
        return context


class AlertaGeoJSONView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(geojson.dumps(polygons))


class CityMapView(View):
    def get(self, request, geocodigo):
        mapa = get_city_geojson(int(geocodigo))
        return HttpResponse(geojson.dumps(mapa))


class DetailsPageView(TemplateView):
    template_name = 'details.html'

    def get_context_data(self, **kwargs):
        context = super(DetailsPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request, 'O site do projeto Alerta Dengue está em construção.')
        series = load_series()
        aps = list(series.keys())
        aps.sort()
        ga = {}
        ya = {}
        oa = {}
        ra = {}
        for k, v in series.items():
            ga[k] = [1 if a == 0 else None for a in v['alerta']]
            ya[k] = [1 if a == 1 else None for a in v['alerta']]
            oa[k] = [1 if a == 2 else None for a in v['alerta']]
            ra[k] = [1 if a == 3 else None for a in v['alerta']]

        context.update({
            'APS': aps,
            'green_alert': json.dumps(ga),
            'yellow_alert': json.dumps(ya),
            'casos': json.dumps(series),
            'red_alert': json.dumps(ra),
            'orange_alert': json.dumps(oa),
            'xvalues': series['AP1']['dia'],
        })
        return context


class MapaDengueView(TemplateView):
    template_name = 'mapadengue.html'

    def get_context_data(self, **kwargs):
        context = super(MapaDengueView, self).get_context_data(**kwargs)
        return context


class MapaMosquitoView(TemplateView):
    template_name = 'mapamosquito.html'

    def get_context_data(self, **kwargs):
        context = super(MapaMosquitoView, self).get_context_data(**kwargs)
        return context


class HistoricoView(TemplateView):
    template_name = 'historico.html'

    def get_context_data(self, **kwargs):
        context = super(HistoricoView, self).get_context_data(**kwargs)
        series = load_series()
        aps = list(series.keys())
        aps.sort()
        context.update({
            'APS': aps,
            'xvalues': series['AP1']['dia'],
            'dados': json.dumps(series)
        })
        return context


class AboutPageView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super(AboutPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request, 'O site do projeto Alerta Dengue está em construção.')
        return context


class ContactPageView(TemplateView):
    template_name = 'contact.html'

    def get_context_data(self, **kwargs):
        context = super(ContactPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request, 'O site do projeto Alerta Dengue está em construção.')
        return context


class JoininPageView(TemplateView):
    template_name = 'joinin.html'

    def get_context_data(self, **kwargs):
        context = super(JoininPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request, 'O site do projeto Alerta Dengue está em construção.')
        return context


class SinanCasesView(View):
    def get(self, request, year, sample):
        sample = int(sample)
        try:
            assert int(year) in [2010, 2011, 2012, 2013]
        except AssertionError:
            messages.error(
                self.request,
                'O projeto conté dados apenas dos anos 2010 a 2013.'
            )

        sample = 1 if sample == 0 else sample / 100.
        cases = "{\"type\":\"FeatureCollection\", \"features\":["
        if int(year) == 2010:
            dados = M.Dengue_2010.objects.geojson()
        elif int(year) == 2011:
            dados = M.Dengue_2011.objects.geojson()
        elif int(year) == 2012:
            dados = M.Dengue_2012.objects.geojson()
        elif int(year) == 2013:
            dados = M.Dengue_2013.objects.geojson()
        else:
            dados = []

        if len(dados) < 5500:
            sample = 1
        for c in random.sample(list(dados), int(len(dados) * sample)):
            cases += (
                "{\"type\":\"Feature\",\"geometry\":" + c.geojson +
                ", \"properties\":{\"data\":\"" + c.dt_notific.isoformat() +
                "\"}},"
            )
        cases = cases[:-1] + "]}"
        # json.loads(cases)
        return HttpResponse(cases, content_type="application/json")


def get_alert():
    """
    Read the data and return the alert status of all APs.
    returns a tuple with the following elements:
    - alert: dictionary with the alert status per AP
    - current: tuple with all variables from the last SE
    - case_series: dictionary with 12-weeks case series per AP
    - last_year: integer representing the total number of cases 52 weeks ago.
    :rtype : tuple
    """
    df = dados_alerta
    df.fillna(0, inplace=True)
    last_SE = df.se.max()  # Last epidemiological week
    # year = datetime.date.today().year  # Current year
    # current epidemiological week
    # SE = int(str(last_SE).split(str(year))[-1])
    current = df[df['se'] == last_SE]  # Current status
    G = df.groupby("aps")
    group_names = G.groups.keys()
    alert = defaultdict(lambda: 0)
    case_series = {}
    obs_case_series = {}
    min_max_est = {}

    for ap in group_names:
        adf = G.get_group(ap)  # .tail()  # only calculates on the series tail
        case_series[str(float(ap.split('AP')[-1]))] = [
            int(v) for v in adf.casos_est.iloc[-12:].values
        ]
        obs_case_series[str(float(ap.split('AP')[-1]))] = [
            int(v) for v in adf.casos.iloc[-12:].values
        ]
        alert[ap] = adf.nivel.iloc[-1]
        last_year = int(adf.casos.iloc[-52])
        min_max_est[ap] = (adf.casos_estmin.iloc[-1], adf.casos_estmax.iloc[-1])
    return alert, current, case_series, last_year, obs_case_series, min_max_est


def load_series():
    """
    Monta as séries para visualização no site
    """
    series = defaultdict(lambda: defaultdict(lambda: []))
    G = dados_alerta.groupby("aps")
    for ap in G.groups.keys():
        series[ap]['dia'] = [
            int(mktime(datetime.datetime.strptime(d, "%Y-%m-%d").timetuple()))
            if isinstance(d, str) else None
            for d in G.get_group(ap).data
        ]
        series[ap]['tweets'] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).tweets
        ]
        series[ap]['tmin'] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).tmin
        ]
        series[ap]['casos_est'] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).casos_est
        ]
        series[ap]['casos'] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).casos
        ]
        series[ap]['alerta'] = [
            c - 1 if not np.isnan(c) else None
            for c in G.get_group(ap).cor
        ]
    return series

#
# def get_global_series(col, group):
#     series = group[col].groups.items()
#     ssum = None
#     for g, ser in group[col].items():
#         if ssum is None:
#             ssum = np.array(ser)
#         else:
#             ssum += np.array(ser)
