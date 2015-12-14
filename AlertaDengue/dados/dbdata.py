"""
Este módulo contem funções para interagir com o banco principal do projeto
 Alertadengue.
"""

import psycopg2
from sqlalchemy import create_engine
from django.conf import settings
import pandas as pd
import numpy as np
from collections import defaultdict
import datetime
from time import mktime
settings.configure()


conexao = create_engine("postgresql://{}:{}@{}/{}".format('dengueadmin', 'aldengue', 'localhost', 'dengue'))




def load_series(cidade, doenca='dengue'):
    """
    Monta as séries do alerta para visualização no site
    :param cidade: geocodigo da cidade desejada
    :param doenca: dengue|chik|zika
    :return: dictionary
    """
    dados_alerta = pd.read_sql_query('select * from "Municipio"."Historico_alerta" where municipio_geocodigo={}'.format(cidade), conexao, 'id', parse_dates=True)

    # tweets = pd.read_sql_query('select * from "Municipio"."Tweet" where "Municipio_geocodigo"={}'.format(cidade), parse_dates=True)
    series = defaultdict(lambda: defaultdict(lambda: []))
    ap = 'global'
    series[ap]['dia'] = dados_alerta.data_iniSE.tolist()
    # series[ap]['tweets'] = [float(i) if not np.isnan(i) else None for i in tweets.numero]
    # series[ap]['tmin'] = [float(i) if not np.isnan(i) else None for i in G.get_group(ap).tmin]
    series[ap]['casos_est_min'] = dados_alerta.casos_est_min.astype(int).tolist()
    series[ap]['casos_est'] = dados_alerta.casos_est.astype(int).tolist()
    series[ap]['casos_est_max'] = dados_alerta.casos_est_max.astype(int).tolist()
    series[ap]['casos'] = dados_alerta.casos.astype(int).tolist()
    series[ap]['alerta'] = (dados_alerta.nivel.astype(int)-1).tolist()
    # print(series['dia'])
    return series

def get_city_alert(cidade, doenca='dengue'):
    """
    Retorna vários indicadores de alerta a nível da cidade.
    :param cidade: geocódigo
    :param doenca: dengue|chik|zika
    :return: tupla
    """
    series = load_series(cidade, doenca)
    alert = series['global']['alerta'][-1]
    current = series['global']['casos_est'][-1]
    case_series = series['global']['casos_est']
    obs_case_series = series['global']['casos']
    last_year = series['global']['casos'][-52]
    min_max_est = (series['global']['casos_est_min'][-1], series['global']['casos_est_max'][-1])
    return alert, current, case_series, last_year, obs_case_series, min_max_est
