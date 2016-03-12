from django import template
from dados.dbdata import load_series
register = template.Library()
from time import mktime
import json


@register.inclusion_tag("series_plot.html", takes_context=True)
def alerta_series(context):
    dados = load_series(context['geocodigo'])[context['geocodigo']]
    dados['dia'] = [int(mktime(d.timetuple())) for d in dados['dia']]
    int_or_none  = lambda x: None if x is None else int(x)

    ga = [int(c) if a == 0 else None for a, c in zip(dados['alerta'], dados['casos'])]
    ga = [int_or_none(dados['casos'][n]) if i is None and ga[n-1] is not None else int_or_none(i) for n, i in enumerate(ga)]
    ya = [int(c) if a == 1 else None for a, c in zip(dados['alerta'], dados['casos'])]
    ya = [int_or_none(dados['casos'][n]) if i is None and ya[n-1] is not None else int_or_none(i) for n, i in enumerate(ya)]
    oa = [int(c) if a == 2 else None for a, c in zip(dados['alerta'], dados['casos'])]
    oa = [int_or_none(dados['casos'][n]) if i is None and oa[n-1] is not None else int_or_none(i) for n, i in enumerate(oa)]
    ra = [int(c) if a == 3 else None for a, c in zip(dados['alerta'], dados['casos'])]
    ra = [int_or_none(dados['casos'][n]) if i is None and ra[n-1] is not None else int_or_none(i) for n, i in enumerate(ra)]
    return {'nome': context['nome'],
            'dados': dados,
            'start': dados['dia'][0],
            'verde': json.dumps(ga),
            'amarelo': json.dumps(ya),
            'laranja': json.dumps(oa),
            'vermelho': json.dumps(ra),
            }


@register.inclusion_tag("total_series.html", takes_context=True)
def total_series(context):
    gc = context['geocodigos'][0]
    dados = load_series(gc)
    dias = dados[str(gc)]['dia'][-52:]

    tempo = [int(mktime(d.timetuple())) for d in dias]
    print(dias)
    print(tempo)
    return {
        'tempo': tempo,
        'start': tempo[0],
        'total': context['total']
    }
