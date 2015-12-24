from django import template
from dados.dbdata import load_series
register = template.Library()
from time import mktime


@register.inclusion_tag("series_plot.html", takes_context=True)
def alerta_series(context):
    dados = load_series(context['geocodigo'])[context['geocodigo']]
    dados['dia'] = [int(mktime(d.timetuple())) for d in dados['dia']]
    return {'nome': context['nome'],
            'dados': dados,
            'start': dados['dia'][0]
            }
