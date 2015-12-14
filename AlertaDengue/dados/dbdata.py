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

