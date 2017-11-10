from datetime import timedelta
from django import template
from time import mktime

from ..dbdata import load_series, get_series_by_UF

import json

register = template.Library()


def int_or_none(x):
    return None if x is None else int(x)


@register.inclusion_tag("series_plot.html", takes_context=True)
def alerta_series(context):
    disease = (
        'dengue' if 'disease_code' not in context else
        context['disease_code']
    )

    epiweek = context['epiweek'] if 'epiweek' in context else 0

    dados = load_series(
        context['geocodigo'], disease, epiweek
    )[context['geocodigo']]

    if dados is None:
        return {
            'nome': context['nome'],
            'dados': {},
            'start': {},
            'verde': {},
            'amarelo': {},
            'laranja': {},
            'vermelho': {},
            'disease_label': context['disease_label']
        }

    dados['dia'] = [
        int(mktime(d.timetuple())) for d in dados['dia']
    ]

    # green alert
    ga = [
        int(c) if a == 0 else None
        for a, c in zip(dados['alerta'], dados['casos'])]
    ga = [
        int_or_none(dados['casos'][n])
        if i is None and ga[n - 1] is not None else int_or_none(i)
        for n, i in enumerate(ga)]
    # yellow alert
    ya = [
        int(c) if a == 1 else None
        for a, c in zip(dados['alerta'], dados['casos'])]
    ya = [
        int_or_none(dados['casos'][n])
        if i is None and ya[n - 1] is not None else int_or_none(i)
        for n, i in enumerate(ya)]
    # orange alert
    oa = [
        int(c) if a == 2 else None
        for a, c in zip(dados['alerta'], dados['casos'])]
    oa = [
        int_or_none(dados['casos'][n])
        if i is None and oa[n - 1] is not None else int_or_none(i)
        for n, i in enumerate(oa)]
    # red alert
    ra = [
        int(c) if a == 3 else None
        for a, c in zip(dados['alerta'], dados['casos'])]
    ra = [
        int_or_none(dados['casos'][n])
        if i is None and ra[n - 1] is not None else int_or_none(i)
        for n, i in enumerate(ra)]

    forecast_models_keys = [
        k for k in dados.keys()
        if k.startswith('forecast_')
    ]

    forecast_models_title = [
        (k, k.replace('forecast_', '').replace('_cases', '').title())
        for k in forecast_models_keys
    ]

    forecast_data = {
        k: json.dumps(dados[k]) for k in forecast_models_keys
    }

    result = {
        'nome': context['nome'],
        'dados': dados,
        'start': dados['dia'][0],
        'verde': json.dumps(ga),
        'amarelo': json.dumps(ya),
        'laranja': json.dumps(oa),
        'vermelho': json.dumps(ra),
        'disease_label': context['disease_label'],
        'forecast_models': forecast_models_title
    }

    result.update(forecast_data)

    return result


@register.inclusion_tag("total_series.html", takes_context=True)
def total_series_dengue(context):
    _context = total_series(context, disease='dengue')
    _context.update({'disease_label': 'Dengue'})
    return _context


@register.inclusion_tag("total_series.html", takes_context=True)
def total_series_chik(context):
    _context = total_series(context, disease='chikungunya')
    _context.update({'disease_label': 'Chikungunya'})
    return _context


def total_series(context, disease):
    '''

    :param context:
    :param disease: dengue|chikungunya|zika
    :return:
    '''
    # gc = context['geocodigos'][0]
    series = (
        get_series_by_UF(disease) if 'case_series' not in context else
        context['case_series'][disease]
    )

    if series.empty:
        return {
            'ufs': [],
            'start': None,
            'series': {},
            'series_est': {},
            'disease': disease
        }

    ufs = list(set(series.uf.tolist()))
    # 51 weeks to get the end of the SE
    start = series.data.max() - timedelta(weeks=51)
    start = int(mktime(start.timetuple()))
    casos = {}
    casos_est = {}

    for uf in ufs:
        series_uf = series[series.uf == uf]
        datas = [
            int(mktime(d.timetuple())) * 1000
            for d in series_uf.data[-52:]
        ]
        casos[uf] = [
            list(t)
            for t in zip(
                datas,
                series_uf.casos_s[-52:].astype('int').tolist()
            )
        ]
        casos_est[uf] = [
            list(t)
            for t in zip(
                datas,
                series_uf.casos_est_s[-52:].astype('int').tolist()
            )
        ]

    return {
        'ufs': ufs,
        'start': start,
        'series': casos,
        'series_est': casos_est,
        'disease': disease
    }
