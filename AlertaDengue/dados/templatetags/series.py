from django import template
from dados.dbdata import load_series
register = template.Library()
from time import mktime
import json


@register.inclusion_tag("series_plot.html", takes_context=True)
def alerta_series(context):
    dados = load_series(context['geocodigo'])[context['geocodigo']]
    dados['dia'] = [int(mktime(d.timetuple())) for d in dados['dia']]

    ga = [int(c) if a == 0 else None for a, c in zip(dados['alerta'], dados['casos'])]
    ya = [int(c) if a == 1 else None for a, c in zip(dados['alerta'], dados['casos'])]
    oa = [int(c) if a == 2 else None for a, c in zip(dados['alerta'], dados['casos'])]
    ra = [int(c) if a == 3 else None for a, c in zip(dados['alerta'], dados['casos'])]
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
    return {}
