"""
Este módulo contem funções para interagir com o banco principal do projeto
 Alertadengue.
"""

from sqlalchemy import create_engine
from django.conf import settings
from django.core.cache import cache
from collections import defaultdict

import pandas as pd
import numpy as np

CID10 = {
    'dengue': 'A90',
    'zika': 'U06',
    'chikungunya': 'A92'
}


def get_all_active_cities():
    """
    Fetch from the database a list on names of active cities
    :return: list of tuples (geocode,name)
    """
    res = cache.get('get_all_active_cities')

    if res is None:
        conexao = create_engine(
            "postgresql://{}:{}@{}/{}".format(
                settings.PSQL_USER,
                settings.PSQL_PASSWORD,
                settings.PSQL_HOST,
                settings.PSQL_DB))
        res = conexao.execute(
            'SELECT DISTINCT municipio_geocodigo, municipio_nome FROM'
            '"Municipio"."Historico_alerta";')
        res = res.fetchall()
        cache.set('get_all_active_cities', res, settings.QUERY_CACHE_TIMEOUT)

    return res


def get_alerta_mrj():
    """
    Fetch the alert table for the city of Rio de janeiro
    :return: pandas dataframe
    """
    conexao = create_engine(
        "postgresql://{}:{}@{}/{}".format(
            settings.PSQL_USER,
            settings.PSQL_PASSWORD,
            settings.PSQL_HOST, settings.PSQL_DB))
    dados_alerta = pd.read_sql_query(
        'select * from "Municipio".alerta_mrj;', conexao, index_col='id'
    )
    return dados_alerta


def get_city(query):
    """
    Fetch city geocode, name and state from the database,
    matching the substring query
    :param query: substring of the city
    :return: list of dictionaries
    """
    conexao = create_engine(
        "postgresql://{}:{}@{}/{}".format(
            settings.PSQL_USER,
            settings.PSQL_PASSWORD,
            settings.PSQL_HOST, settings.PSQL_DB))
    sql = (
        'SELECT distinct municipio_geocodigo, nome, uf ' +
        'from "Municipio"."Historico_alerta" inner JOIN' +
        ' "Dengue_global"."Municipio" on ' +
        '"Historico_alerta".municipio_geocodigo="Municipio".geocodigo ' +
        'WHERE nome ilike(%s);'
    )

    result = conexao.execute(sql, ('%' + query + '%',))

    return result.fetchall()


def get_series_by_UF(doenca='dengue'):
    """
    Get the incidence series from the database aggregated (sum) by state
    :param UF: substring of the name of the state
    :param doenca: cid 10 code for the disease
    :return: Dataframe with the series in long format
    """
    series = cache.get('get_series_by_UF')
    if series is None:
        conexao = create_engine(
            "postgresql://{}:{}@{}/{}".format(
                settings.PSQL_USER,
                settings.PSQL_PASSWORD,
                settings.PSQL_HOST,
                settings.PSQL_DB))
        series = pd.read_sql(
            'select * from uf_total_view;', conexao, parse_dates=True)
        cache.set('get_series_by_UF', series, settings.QUERY_CACHE_TIMEOUT)

    return series


def load_series(cidade, doenca='dengue', conexao=None):
    """
    Monta as séries do alerta para visualização no site
    :param cidade: geocodigo da cidade desejada
    :param doenca: dengue|chik|zika
    :return: dictionary
    """
    cache_key = 'load_series-{}-{}'.format(cidade, doenca)
    result = cache.get(cache_key)
    if result is None:
        if conexao is None:
            conexao = create_engine(
                "postgresql://{}:{}@{}/{}".format(
                    settings.PSQL_USER,
                    settings.PSQL_PASSWORD,
                    settings.PSQL_HOST,
                    settings.PSQL_DB))

        ap = str(cidade)
        cidade = add_dv(int(str(cidade)[:-1]))

        dados_alerta = pd.read_sql_query((
            'select * from "Municipio"."Historico_alerta" ' +
            'where municipio_geocodigo={} ORDER BY "data_iniSE" ASC'
        ).format(cidade), conexao, 'id', parse_dates=True)

        if len(dados_alerta) == 0:
            raise NameError((
                "Não foi possível obter os dados " +
                "do Banco para cidade {}"
            ).format(cidade))

        series = defaultdict(lambda: defaultdict(lambda: []))
        series[ap]['dia'] = dados_alerta.data_iniSE.tolist()
        series[ap]['casos_est_min'] = np.nan_to_num(
            dados_alerta.casos_est_min).astype(int).tolist()
        series[ap]['casos_est'] = np.nan_to_num(dados_alerta.casos_est).astype(
            int).tolist()
        series[ap]['casos_est_max'] = np.nan_to_num(
            dados_alerta.casos_est_max).astype(int).tolist()
        series[ap]['casos'] = np.nan_to_num(dados_alerta.casos).astype(
            int).tolist()
        series[ap]['alerta'] = (
            dados_alerta.nivel.astype(int) - 1
        ).tolist()  # (1,4)->(0,3)
        series[ap]['SE'] = (dados_alerta.SE.astype(int)).tolist()
        series[ap]['prt1'] = dados_alerta.p_rt1.astype(float).tolist()
        series[ap] = dict(series[ap])
        # conexao.close()
        result = dict(series)

        cache.set(cache_key, result, settings.QUERY_CACHE_TIMEOUT)

    return result


def load_serie_cities(geocodigos, doenca='dengue', conexao=None):
    """
    Monta as séries do alerta para visualização no site
    :param cidade: geocodigo da cidade desejada
    :param doenca: dengue|chik|zika
    :return: dictionary
    """
    result = {}
    _geocodigos = {}
    aps = []
    cidades = []

    for cidade in geocodigos:
        cache_key = 'load_series-{}-{}'.format(cidade, doenca)
        _result = cache.get(cache_key)
        ap = str(cidade)
        aps.append(ap)

        if _result is not None:
            result.update(_result)
        else:
            cidades.append(add_dv(int(ap[:-1])))
            _geocodigos[cidades[-1]] = cidade

    sql = ('''
    SELECT
        id, municipio_geocodigo, casos_est, casos,
        "data_iniSE", casos_est_min, casos_est_max,
        nivel, "SE", p_rt1
    FROM "Municipio"."Historico_alerta"
    WHERE municipio_geocodigo IN (''' + ('{},'*len(cidades))[:-1] + ''')
    ORDER BY municipio_geocodigo ASC, "data_iniSE" ASC
    ''').format(*cidades)

    dados_alerta = pd.read_sql_query(
        sql, conexao, 'id', parse_dates=True
    )

    if len(dados_alerta) == 0:
        raise NameError(
            "Não foi possível obter os dados do Banco"
        )

    series = defaultdict(lambda: defaultdict(lambda: []))
    for k, v in _geocodigos.items():
        ap = str(ap)
        mask = dados_alerta.municipio_geocodigo == k
        series[ap]['dia'] = dados_alerta[mask].data_iniSE.tolist()
        series[ap]['casos_est_min'] = np.nan_to_num(
            dados_alerta[mask].casos_est_min).astype(int).tolist()
        series[ap]['casos_est'] = np.nan_to_num(
            dados_alerta[mask].casos_est
        ).astype(int).tolist()
        series[ap]['casos_est_max'] = np.nan_to_num(
            dados_alerta[mask].casos_est_max).astype(int).tolist()
        series[ap]['casos'] = np.nan_to_num(
            dados_alerta[mask].casos
        ).astype(int).tolist()
        series[ap]['alerta'] = (
            dados_alerta[mask].nivel.astype(int) - 1
        ).tolist()  # (1,4)->(0,3)
        series[ap]['SE'] = (dados_alerta[mask].SE.astype(int)).tolist()
        series[ap]['prt1'] = dados_alerta[mask].p_rt1.astype(float).tolist()
        series[ap] = dict(series[ap])
    result = dict(series)

    cache.set(cache_key, result, settings.QUERY_CACHE_TIMEOUT)

    return series


def get_city_alert(cidade, doenca='dengue'):
    """
    Retorna vários indicadores de alerta a nível da cidade.
    :param cidade: geocódigo
    :param doenca: dengue|chik|zika
    :return: tupla
    """
    series = load_series(cidade, doenca)
    alert = series[str(cidade)]['alerta'][-1]
    SE = series[str(cidade)]['SE'][-1]
    case_series = series[str(cidade)]['casos_est']
    obs_case_series = series[str(cidade)]['casos']
    last_year = series[str(cidade)]['casos'][-52]
    min_max_est = (
        series[str(cidade)]['casos_est_min'][-1],
        series[str(cidade)]['casos_est_max'][-1])
    dia = series[str(cidade)]['dia'][-1]
    prt1 = np.mean(series[str(cidade)]['prt1'][-3:])

    return (
        alert, SE, case_series, last_year,
        obs_case_series, min_max_est, dia, prt1
    )


def calculate_digit(dig):
    """
    Calcula o digito verificador do geocódigo de município
    :param dig: geocódigo com 6 dígitos
    :return: dígito verificador
    """
    peso = [1, 2, 1, 2, 1, 2, 0]
    soma = 0
    dig = str(dig)

    for i in range(6):
        valor = int(dig[i]) * peso[i]
        soma += sum([int(d) for d in str(valor)]) if valor > 9 else valor

    dv = 0 if soma % 10 == 0 else (10 - (soma % 10))
    return dv


def add_dv(geocodigo):
    """
    Retorna o geocóodigo do município adicionando o digito verificador,
    se necessário.
    :param geocodigo: geocóodigo com 6 ou 7 dígitos
    """
    if len(str(geocodigo)) == 7:
        return geocodigo
    else:
        return int(str(geocodigo) + str(calculate_digit(geocodigo)))


def create_connection():
    """
    Retorna um sqlalchemy engine com a conexão com o banco.

    :return: sqlalchemy engine

    """
    return create_engine(
        "postgresql://{}:{}@{}/{}".format(
            settings.PSQL_USER,
            settings.PSQL_PASSWORD,
            settings.PSQL_HOST,
            settings.PSQL_DB))


def count_cities_by_state(uf, connection):
    """
    Returna contagem de cidades participantes por estado

    :param uf: nome do estado
    :param connection: sqlalchemy engine
    :return: dataframe
    """

    sql = '''
    SELECT COALESCE(COUNT(municipio_geocodigo), 0) AS count
    FROM (
        SELECT DISTINCT municipio_geocodigo
        FROM "Municipio"."Historico_alerta") AS alerta
    INNER JOIN "Dengue_global"."Municipio" AS municipio
      ON alerta.municipio_geocodigo = municipio.geocodigo
    WHERE uf='%s'
    ''' % uf

    return int(pd.read_sql(sql, connection)['count'])


def count_cases_by_uf(uf, se, connection):
    """
    Returna contagem de cidades participantes por estado

    :param uf: nome do estado
    :param se: número do ano e semana (no ano), ex: 201503
    :param connection: sqlalchemy engine
    :return: dataframe
    """
    sql = '''
    SELECT
        COALESCE(SUM(casos), 0) AS casos,
        COALESCE(SUM(casos_est), 0) AS casos_est
    FROM "Municipio"."Historico_alerta" AS alerta
    INNER JOIN "Dengue_global"."Municipio" AS municipio
      ON alerta.municipio_geocodigo = municipio.geocodigo
    WHERE uf='%s' AND "SE" = '%s'
    ''' % (uf, se)

    return pd.read_sql(sql, connection).astype(int)

