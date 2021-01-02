"""
Este módulo contem funções para interagir com o banco principal do projeto
 Alertadengue.

"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Callable

from sqlalchemy import create_engine
from django.core.cache import cache
import pandas as pd
import numpy as np
import ibis
from ibis import config as cf
from ibis.sql.postgres import existing_udf

# local
from dados.episem import episem, episem2date
from ad_main import settings

with cf.config_prefix('sql'):
    cf.set_option('default_limit', None)

# rio de janeiro city geocode
MRJ_GEOCODE = 3304557

CID10 = {'dengue': 'A90', 'chikungunya': 'A920', 'zika': 'A928'}
DISEASES_SHORT = ['dengue', 'chik', 'zika']

STATE_NAME = {
    'CE': 'Ceará',
    'ES': 'Espírito Santo',
    'MG': 'Minas Gerais',
    'PR': 'Paraná',
    'RJ': 'Rio de Janeiro',
    'SP': 'São Paulo',
    'RS': 'Rio Grande do Sul',
    'MA': 'Maranhão',
}

ALL_STATE_NAMES = STATE_NAME.copy()
# TODO: add missing states here

ALERT_COLOR = {1: 'verde', 2: 'amarelo', 3: 'laranja', 4: 'vermelho'}

ALERT_CODE = dict(zip(ALERT_COLOR.values(), ALERT_COLOR.keys()))

STATE_INITIAL = dict(zip(STATE_NAME.values(), STATE_NAME.keys()))
ALL_STATE_INITIAL = dict(zip(ALL_STATE_NAMES.values(), ALL_STATE_NAMES.keys()))

PSQL_URI = "postgresql://{}:{}@{}:{}/{}".format(
    settings.PSQL_USER,
    settings.PSQL_PASSWORD,
    settings.PSQL_HOST,
    settings.PSQL_PORT,
    settings.PSQL_DB,
)

db_engine = create_engine(PSQL_URI)
con = ibis.postgres.connect(url=PSQL_URI)


# Ibis utils functions


def get_epi_week_expr() -> Callable:
    """
    Return a UDF expression for epi_week function.

    Returns
    -------
    Callable
    """
    return existing_udf('epi_week', input_types=['date'], output_type='int64')


def get_epiweek2date_expr() -> Callable:
    """
    Return a UDF expression for epiweek2date

    Returns
    -------
    Callable
    """
    return existing_udf(
        'epiweek2date', input_types=['int64'], output_type='date'
    )


# general util functions


def _nan_to_num_int_list(v):
    """

    :param v: numpy.array
    :return: list
    """
    try:
        return np.nan_to_num(v.fillna(0)).astype(int).tolist()
    except Exception:
        return np.nan_to_num(v).astype(int).tolist()


def _episem(dt):
    return episem(dt, sep='')


def get_disease_suffix(disease: str):
    """

    :param disease:
    :return:
    """
    return (
        ''
        if disease == 'dengue'
        else '_chik'
        if disease == 'chikungunya'
        else '_zika'
        if disease == 'zika'
        else ''
    )


def get_regional_names(state_name: str) -> list:
    """

    :param state_name:
    :return:
    """
    sql = '''
    SELECT DISTINCT nome_regional
    FROM "Dengue_global"."regional_saude" AS rs\
    INNER JOIN "Dengue_global"."Municipio" AS m
        ON (rs.municipio_geocodigo=m.geocodigo)
    INNER JOIN "Dengue_global"."estado" AS uf
        ON (UPPER(m.uf)=UPPER(uf.nome))
    WHERE UPPER(uf.uf) = UPPER('{}')
    '''.format(
        state_name
    )

    with db_engine.connect() as conn:
        return [v[0] for v in conn.execute(sql).fetchall()]


def get_var_climate_info(geocodes: list):
    """

    :param geocodes:
    :return:
    """
    sql = '''
    SELECT DISTINCT codigo_estacao_wu, varcli
    FROM "Dengue_global".regional_saude
    WHERE municipio_geocodigo IN ({})
    '''.format(
        ','.join(map(lambda v: "'{}'".format(v), geocodes))
    )
    with db_engine.connect() as conn:
        return conn.execute(sql).fetchone()


def get_cities(regional_name: str = None, state_name: str = None) -> dict:
    """
    Get a list of cities from available states with code and name pairs
    :return:
    """
    with db_engine.connect() as conn:
        if regional_name is not None and state_name is not None:
            sql = '''
                SELECT municipio_geocodigo, nome
                FROM \"Dengue_global\".\"Municipio\"
                INNER JOIN \"Dengue_global\".regional_saude
                ON municipio_geocodigo = geocodigo
                where uf = '%s' AND nome_regional = '%s'
            ''' % (
                state_name,
                regional_name,
            )
        else:
            if state_name is None:
                state_names = [
                    "'%s'" % state_name for state_name in STATE_NAME.values()
                ]
            else:
                state_names = ["'%s'" % state_name]

            sql = '''
            SELECT geocodigo, nome
            FROM "Dengue_global"."Municipio"
            WHERE uf IN(%s)
            ORDER BY nome
            ''' % ','.join(
                state_names
            )

        return dict(conn.execute(sql).fetchall())


def get_city_name_by_id(geocode: int):
    """

    :param geocode:
    :return:
    """
    with db_engine.connect() as conn:
        res = conn.execute(
            '''
            SELECT nome
            FROM "Dengue_global"."Municipio"
            WHERE geocodigo=%s;
        '''
            % geocode
        )
        return res.fetchone()[0]


def get_all_active_cities_state():
    """
    Fetch from the database a list on names of active cities
    :return: list of tuples (geocode,name)
    """
    res = cache.get('get_all_active_cities_state')

    if res is None:
        with db_engine.connect() as conn:
            res = conn.execute(
                '''
            SELECT DISTINCT
              hist.municipio_geocodigo,
              city.nome,
              city.uf
            FROM "Municipio"."Historico_alerta" AS hist
              INNER JOIN "Dengue_global"."Municipio" AS city
                ON (hist.municipio_geocodigo=city.geocodigo)
            '''
            )
            res = res.fetchall()
            cache.set(
                'get_all_active_cities_state',
                res,
                settings.QUERY_CACHE_TIMEOUT,
            )
    return res


def get_all_active_cities():
    """
    Fetch from the database a list on names of active cities
    :return: list of tuples (geocode,name)
    """
    res = cache.get('get_all_active_cities')

    if res is None:
        with db_engine.connect() as conn:
            res = conn.execute(
                '''
            SELECT DISTINCT
              hist.municipio_geocodigo,
              city.nome
            FROM "Municipio"."Historico_alerta" AS hist
              INNER JOIN "Dengue_global"."Municipio" AS city
                ON (hist.municipio_geocodigo=city.geocodigo)
            '''
            )
            res = res.fetchall()
            cache.set(
                'get_all_active_cities', res, settings.QUERY_CACHE_TIMEOUT
            )
    return res


def get_alerta_mrj():
    """
    Fetch the alert table for the city of Rio de janeiro
    :return: pandas dataframe
    """
    sql = 'select * from "Municipio".alerta_mrj;'
    with db_engine.connect() as conn:
        return pd.read_sql_query(sql, conn, index_col='id')


def get_alerta_mrj_chik():
    """
    Fetch the alert table for the city of Rio de janeiro
    :return: pandas dataframe
    """
    sql = 'select * from "Municipio".alerta_mrj_chik;'
    with db_engine.connect() as conexao:
        return pd.read_sql_query(sql, conexao, index_col='id')


def get_alerta_mrj_zika():
    """
    Fetch the alert table for the city of Rio de janeiro
    :return: pandas dataframe
    """
    sql = 'select * from "Municipio".alerta_mrj_zika;'
    with db_engine.connect() as conexao:
        return pd.read_sql_query(sql, conexao, index_col='id')


def get_last_alert(geo_id, disease):
    """

    :param geo_id:
    :param disease:
    :return:
    """

    table_name = 'Historico_alerta' + get_disease_suffix(disease)

    sql = '''
    SELECT nivel
    FROM "Municipio"."%s"
    WHERE municipio_geocodigo=%s
    ORDER BY "data_iniSE" DESC
    LIMIT 1
    ''' % (
        table_name,
        geo_id,
    )

    with db_engine.connect() as conn:
        return pd.read_sql_query(sql, conn)


def get_city(query):
    """
    Fetch city geocode, name and state from the database,
    matching the substring query
    :param query: substring of the city
    :return: list of dictionaries
    """
    with db_engine.connect() as conexao:
        sql = (
            ' SELECT distinct municipio_geocodigo, nome, uf'
            + ' FROM "Municipio"."Historico_alerta" AS alert'
            + '  INNER JOIN "Dengue_global"."Municipio" AS city'
            + '  ON alert.municipio_geocodigo=city.geocodigo'
            + ' WHERE nome ilike(%s);'
        )

        result = conexao.execute(sql, ('%' + query + '%',))

    return result.fetchall()


def get_series_by_UF(disease='dengue', weeks=None):
    """
    Get the incidence series from the database aggregated (sum) by state
    :param UF: substring of the name of the state
    :param disease: dengue|chikungunya|zika
    :return: Dataframe with the series in long format
    """
    cache_id = 'get_series_by_UF-{}'.format(disease)
    series = cache.get(cache_id)
    _disease = get_disease_suffix(disease)

    # TODO: this function is deprecated and will be
    # removed when plotly-dash charts are ready
    if series is None:
        with db_engine.connect() as conn:
            if weeks:
                sql = f'''
                SELECT * FROM uf_total{_disease}_view
                WHERE data >= (
                    SELECT MAX(data) AS max_date FROM uf_total{_disease}_view
                ) - INTERVAL '{weeks+2} WEEKS'
                '''
            else:
                sql = f'SELECT * FROM uf_total{_disease}_view;'

            series = pd.read_sql(sql, conn, parse_dates=['data'],)
            cache.set(cache_id, series, settings.QUERY_CACHE_TIMEOUT)

    return series


def get_n_chik_alerts():
    """

    :return: int
    """
    sql = '''
    SELECT COUNT(*) AS n_alerts
    FROM "Municipio"."Historico_alerta_chik"
    '''
    return pd.read_sql_query(sql, db_engine).loc[0, 'n_alerts']


def get_n_zika_alerts():
    """

    :return: int
    """
    sql = '''
    SELECT COUNT(*) AS n_alerts
    FROM "Municipio"."Historico_alerta_zika"
    '''
    return pd.read_sql_query(sql, db_engine).loc[0, 'n_alerts']


def load_series(cidade, disease: str = 'dengue', epiweek: int = 0):
    """
    Monta as séries do alerta para visualização no site
    :param cidade: geocodigo da cidade desejada
    :param disease: dengue|chikungunya|zika
    :param epiweek:
    :return: dictionary
    """
    cache_key = 'load_series-{}-{}'.format(cidade, disease)
    result = cache.get(cache_key)

    if result is None:
        ap = str(cidade)

        if epiweek is not None:
            dados_alerta = Forecast.load_cases(
                geocode=cidade, disease=disease, epiweek=epiweek
            )
        else:
            dados_alerta = load_cases_without_forecast(
                geocode=cidade, disease=disease
            )

        if len(dados_alerta) == 0:
            return {ap: None}

        # tweets = pd.read_sql_query('select * from "Municipio"."Tweet"
        # where "Municipio_geocodigo"={}'.format(cidade), parse_dates=True)
        series = defaultdict(lambda: defaultdict(lambda: []))
        series[ap]['dia'] = dados_alerta.data_iniSE.tolist()
        # series[ap]['tweets'] = [float(i) if not np.isnan(i) else
        # None for i in tweets.numero]
        # series[ap]['tmin'] = [float(i) if not np.isnan(i) else
        # None for i in G.get_group(ap).tmin]

        series[ap]['casos_est_min'] = _nan_to_num_int_list(
            dados_alerta.casos_est_min
        )

        series[ap]['casos_est'] = _nan_to_num_int_list(dados_alerta.casos_est)

        series[ap]['casos_est_max'] = _nan_to_num_int_list(
            dados_alerta.casos_est_max
        )

        series[ap]['casos'] = _nan_to_num_int_list(dados_alerta.casos)
        # (1,4)->(0,3)
        series[ap]['alerta'] = (
            dados_alerta.nivel.fillna(1).astype(int) - 1
        ).tolist()
        series[ap]['SE'] = (dados_alerta.SE.astype(int)).tolist()
        series[ap]['prt1'] = dados_alerta.p_rt1.astype(float).tolist()

        k_forecast = [
            k for k in dados_alerta.keys() if k.startswith('forecast_')
        ]

        if k_forecast:
            for k in k_forecast:
                series[ap][k] = dados_alerta[k].astype(float).tolist()

        series[ap] = dict(series[ap])

        result = dict(series)
        cache.set(cache_key, result, settings.QUERY_CACHE_TIMEOUT)

    return result


def load_cases_without_forecast(geocode: int, disease):
    """

    :param geocode:
    :param disease:
    :return:
    """
    with db_engine.connect() as conn:
        if geocode == MRJ_GEOCODE:  # RJ city
            table_name = 'alerta' + get_disease_suffix(disease)

            data_alert = pd.read_sql_query(
                '''
                SELECT
                   data AS "data_iniSE",
                   SUM(casos_estmin) AS casos_est_min,
                   SUM(casos_est) as casos_est,
                   SUM(casos_estmax) AS casos_est_max,
                   SUM(casos) AS casos,
                   MAX(nivel) AS nivel,
                   se AS "SE",
                   SUM(prt1) AS p_rt1
                 FROM "Municipio".{}
                 GROUP BY "data_iniSE", "SE"
                '''.format(
                    table_name
                ),
                conn,
                parse_dates=True,
            )

        else:
            table_name = 'Historico_alerta' + get_disease_suffix(disease)

            data_alert = pd.read_sql_query(
                '''
                SELECT * FROM "Municipio"."{}"
                WHERE municipio_geocodigo={} ORDER BY "data_iniSE" ASC
                '''.format(
                    table_name, geocode
                ),
                conn,
                parse_dates=True,
            )
    return data_alert


def load_serie_cities(geocodigos, doenca='dengue'):
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

    if not cidades:
        return result

    sql = (
        '''
    SELECT
        id, municipio_geocodigo, casos_est, casos,
        "data_iniSE", casos_est_min, casos_est_max,
        nivel, "SE", p_rt1
    FROM "Municipio"."Historico_alerta"
    WHERE municipio_geocodigo IN ('''
        + ('{},' * len(cidades))[:-1]
        + ''')
    ORDER BY municipio_geocodigo ASC, "data_iniSE" ASC
    '''
    ).format(*cidades)

    with db_engine.connect() as conn:
        dados_alerta = pd.read_sql_query(sql, conn, 'id', parse_dates=True)

    if len(dados_alerta) == 0:
        raise NameError("Não foi possível obter os dados do Banco")

    series = defaultdict(lambda: defaultdict(lambda: []))
    for k, v in _geocodigos.items():
        ap = str(v)
        mask = dados_alerta.municipio_geocodigo == k
        series[ap]['dia'] = dados_alerta[mask].data_iniSE.tolist()
        series[ap]['casos_est_min'] = (
            np.nan_to_num(dados_alerta[mask].casos_est_min)
            .astype(int)
            .tolist()
        )
        series[ap]['casos_est'] = (
            np.nan_to_num(dados_alerta[mask].casos_est).astype(int).tolist()
        )
        series[ap]['casos_est_max'] = (
            np.nan_to_num(dados_alerta[mask].casos_est_max)
            .astype(int)
            .tolist()
        )
        series[ap]['casos'] = (
            np.nan_to_num(dados_alerta[mask].casos).astype(int).tolist()
        )
        series[ap]['alerta'] = (
            dados_alerta[mask].nivel.astype(int) - 1
        ).tolist()  # (1,4)->(0,3)
        series[ap]['SE'] = (dados_alerta[mask].SE.astype(int)).tolist()
        series[ap]['prt1'] = dados_alerta[mask].p_rt1.astype(float).tolist()
        series[ap] = dict(series[ap])

        cache_key = 'load_series-{}-{}'.format(ap, doenca)
        cache.set(cache_key, {ap: series[ap]}, settings.QUERY_CACHE_TIMEOUT)

    return series


def get_city_alert(cidade, disease='dengue'):
    """
    Retorna vários indicadores de alerta a nível da cidade.
    :param cidade: geocódigo
    :param doenca: dengue|chikungunya|zika
    :return: tuple -> alert, SE, case_series, last_year,
        obs_case_series, min_max_est, dia, prt1
    """
    series = load_series(cidade, disease)
    series_city = series[str(cidade)]

    if series_city is None:
        return ([], None, [0], 0, [0], [0, 0], datetime.now(), 0)

    alert = series_city['alerta'][-1]
    SE = series_city['SE'][-1]
    case_series = series_city['casos_est']
    last_year = (
        series_city['casos'][-52] if len(series_city['casos']) >= 52 else None
    )

    obs_case_series = series_city['casos']
    min_max_est = (
        series_city['casos_est_min'][-1],
        series_city['casos_est_max'][-1],
    )
    dia = series_city['dia'][-1]
    prt1 = np.mean(series_city['prt1'][-3:])

    return (
        alert,
        SE,
        case_series,
        last_year,
        obs_case_series,
        min_max_est,
        dia,
        prt1,
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
    elif len(str(geocodigo)) == 6:
        return int(str(geocodigo) + str(calculate_digit(geocodigo)))
    else:
        raise ValueError('geocode does not match!')


class NotificationResume:
    @staticmethod
    def count_cities_by_uf(uf, disease='dengue'):
        """
        Returna contagem de cidades participantes por estado

        :param uf: uf a ser consultada
        :param disease: dengue|chikungunya|zika
        :return: dataframe
        """

        table_name = 'Historico_alerta' + get_disease_suffix(disease)

        sql = '''
        SELECT COALESCE(COUNT(municipio_geocodigo), 0) AS count
        FROM (
            SELECT DISTINCT municipio_geocodigo
            FROM "Municipio"."%s") AS alerta
        INNER JOIN "Dengue_global"."Municipio" AS municipio
          ON alerta.municipio_geocodigo = municipio.geocodigo
        WHERE uf='%s'
        ''' % (
            table_name,
            uf,
        )

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn).astype(int).iloc[0]['count']

    @staticmethod
    def count_cases_by_uf(uf, se):
        """
        Returna contagem de cidades participantes por estado

        :param uf: uf a ser consultada
        :param se: número do ano e semana (no ano), ex: 201503
        :return: dataframe
        """

        sql = '''
            SELECT
                COALESCE(SUM(casos), 0) AS casos,
                COALESCE(SUM(casos_est), 0) AS casos_est
            FROM
                "Municipio".historico_casos AS dengue
                INNER JOIN "Dengue_global"."Municipio" AS city
                    ON dengue.municipio_geocodigo = city.geocodigo
            WHERE uf='%s' AND "SE" = %s
            ''' % (
            uf,
            se,
        )

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn).astype(int)

    @staticmethod
    def count_cases_week_variation_by_uf(uf, se1, se2):
        """
        Returna contagem de cidades participantes por estado

        AND alerta."SE"=(select epi_week(NOW()::DATE))
        AND alerta_passado."SE"=(select epi_week(NOW()::DATE-7))

        :param uf: uf a ser consutado
        :param se1: número do ano e semana (no ano), ex: 201503
        :param se2: número do ano e semana (no ano), ex: 201503
        :return: dataframe
        """

        sql = '''
        SELECT
            COALESCE(SUM(alerta.casos)-SUM(alerta_passado.casos), 0) AS casos,
            COALESCE(SUM(alerta.casos_est)-SUM(alerta_passado.casos_est), 0)
                AS casos_est
        FROM "Municipio".historico_casos AS alerta
        INNER JOIN "Municipio".historico_casos AS alerta_passado
          ON (
            alerta.municipio_geocodigo = alerta_passado.municipio_geocodigo
            AND alerta."SE"=%s
            AND alerta_passado."SE"=%s)
        INNER JOIN "Dengue_global"."Municipio" AS municipio
          ON alerta.municipio_geocodigo = municipio.geocodigo
        WHERE uf ='%s'
        ''' % (
            se2,
            se1,
            uf,
        )

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn).astype(int)

    @staticmethod
    def tail_estimated_cases(geo_ids, n=12):
        """

        :param geo_ids: list of city geo ids
        :param n: the last n estimated cases
        :return: dict
        """

        if len(geo_ids) < 1:
            raise Exception('GEO id list should have at least 1 code.')

        sql_template = (
            '''(
        SELECT
            municipio_geocodigo, "data_iniSE", casos_est
        FROM
            "Municipio".historico_casos
        WHERE
            municipio_geocodigo={}
        ORDER BY
            "data_iniSE" DESC
        LIMIT '''
            + str(n)
            + ')'
        )

        sql = ' UNION '.join([sql_template.format(gid) for gid in geo_ids])

        if len(geo_ids) > 1:
            sql += ' ORDER BY municipio_geocodigo, "data_iniSE"'

        with db_engine.connect() as conn:
            df_case_series = pd.read_sql(sql, conn)

        return {
            k: v.casos_est.values.tolist()
            for k, v in df_case_series.groupby(by='municipio_geocodigo')
        }

    @staticmethod
    def get_cities_alert_by_state(
        state_name, disease='dengue', epi_year_week: int = None
    ):
        """
        Retorna vários indicadores de alerta a nível da cidade.

        :param state_name: State name
        :param disease: dengue|chikungunya|zika
        :param epi_year_week: int
        :return: tupla
        """

        _disease = get_disease_suffix(disease)

        sql = '''
        SELECT
            hist_alert.id,
            hist_alert.municipio_geocodigo,
            municipio.nome,
            hist_alert."data_iniSE",
            (hist_alert.nivel-1) AS level_alert
        FROM
            "Municipio"."Historico_alerta{0}" AS hist_alert
        '''

        if epi_year_week is None:
            sql += '''
            INNER JOIN (
                SELECT geocodigo, MAX("data_iniSE") AS "data_iniSE"
                FROM
                    "Municipio"."Historico_alerta{0}" AS alerta
                    INNER JOIN "Dengue_global"."Municipio" AS municipio
                        ON alerta.municipio_geocodigo = municipio.geocodigo
                WHERE uf='{1}'
                GROUP BY geocodigo
            ) AS recent_alert ON (
                recent_alert.geocodigo=hist_alert.municipio_geocodigo
                AND recent_alert."data_iniSE"=hist_alert."data_iniSE"
            )
            '''

        sql += '''
            INNER JOIN "Dengue_global"."Municipio" AS municipio ON (
                hist_alert.municipio_geocodigo = municipio.geocodigo
            )
        '''

        if epi_year_week is not None:
            sql += (
                ' WHERE hist_alert."SE" = {}'.format(epi_year_week)
                + ' AND uf=\'{1}\''
            )

        sql = sql.format(_disease, state_name)

        with db_engine.connect() as conn:
            return pd.read_sql_query(sql, conn, 'id', parse_dates=True)

    @staticmethod
    def get_4_weeks_variation(state_name, current_date):
        # for variation_4_weeks
        se_current_year_1 = _episem(current_date)
        se_current_year_2 = _episem(current_date - timedelta(days=0, weeks=3))
        se_last_year_1 = _episem(current_date - timedelta(days=0, weeks=52))
        se_last_year_2 = _episem(current_date - timedelta(days=0, weeks=55))

        sql = '''
        SELECT
            casos_corrente-casos_passado AS casos,
            casos_est_corrente-casos_est_passado AS casos_est
        FROM
            (SELECT
                COALESCE(SUM(alerta.casos), 0) AS casos_corrente,
                COALESCE(SUM(alerta.casos_est), 0) AS casos_est_corrente
            FROM "Municipio".historico_casos AS alerta
                INNER JOIN "Dengue_global"."Municipio" AS municipio
                    ON alerta.municipio_geocodigo = municipio.geocodigo
                        AND uf ='%(state_name)s'
            WHERE
                alerta."SE" <= %(se_current_year_1)s
                AND alerta."SE" >= %(se_current_year_2)s
            ) AS tb_casos
            INNER JOIN (
                SELECT
                    COALESCE(SUM(alerta.casos), 0) AS casos_passado,
                    COALESCE(SUM(alerta.casos_est), 0) AS casos_est_passado
                FROM "Municipio".historico_casos AS alerta
                    INNER JOIN "Dengue_global"."Municipio" AS municipio
                        ON alerta.municipio_geocodigo = municipio.geocodigo
                          AND uf ='%(state_name)s'
                WHERE
                    alerta."SE" <= %(se_last_year_1)s
                AND alerta."SE" >= %(se_last_year_2)s
            ) AS tb_casos_passado
                ON (1=1)
        ''' % {
            'state_name': state_name,
            'se_current_year_1': se_current_year_1,
            'se_current_year_2': se_current_year_2,
            'se_last_year_1': se_last_year_1,
            'se_last_year_2': se_last_year_2,
        }

        with db_engine.connect() as conn:
            return pd.read_sql_query(sql, conn, parse_dates=True)


class Forecast:
    @staticmethod
    def get_min_max_date(geocode: int, cid10: str) -> (str, str):
        """

        :param geocode:
        :param cid10:
        :return: tuple with min and max date (str) from the forecasts

        """
        sql = '''
        SELECT
          TO_CHAR(MIN(init_date_epiweek), 'YYYY-MM-DD') AS epiweek_min,
          TO_CHAR(MAX(init_date_epiweek), 'YYYY-MM-DD') AS epiweek_max
        FROM
          forecast.forecast_cases AS f
          INNER JOIN forecast.forecast_city AS fc
            ON (f.geocode = fc.geocode AND fc.active=TRUE)
          INNER JOIN forecast.forecast_model AS fm
            ON (fc.forecast_model_id = fm.id AND fm.active = TRUE)
        WHERE f.geocode={} AND cid10='{}'
        '''.format(
            geocode, cid10
        )

        values = pd.read_sql_query(sql, db_engine).values.flat
        return values[0], values[1]

    @staticmethod
    def load_cases(geocode: int, disease: str, epiweek: int):
        """

        :param geocode:
        :param disease:
        :param epiweek:
        :return:
        """

        # sql settings
        cid10 = CID10[disease]

        sql = '''
        SELECT DISTINCT ON (forecast_cases.forecast_model_id)
          forecast_cases.forecast_model_id,
          forecast_model.name AS forecast_model_name,
          forecast_cases.published_date
        FROM
          forecast.forecast_cases
          INNER JOIN forecast.forecast_model
            ON (
              forecast_cases.forecast_model_id =
              forecast_model.id
            )
        WHERE
          cid10 = '%s'
          AND geocode = %s
          AND epiweek = %s
        ORDER BY forecast_model_id, published_date DESC
        ''' % (
            cid10,
            geocode,
            epiweek,
        )

        with db_engine.connect() as conn:
            df_forecast_model = pd.read_sql(sql, con=conn)

        if geocode == MRJ_GEOCODE:  # RJ city
            table_name = 'alerta_mrj' + get_disease_suffix(disease)

            sql_alert = '''
            SELECT
               data AS "data_iniSE",
               SUM(casos_estmin) AS casos_est_min,
               SUM(casos_est) as casos_est,
               SUM(casos_estmax) AS casos_est_max,
               SUM(casos) AS casos,
               MAX(nivel) AS nivel,
               se AS "SE",
               SUM(prt1) AS p_rt1
            FROM "Municipio".{}
            GROUP BY "data_iniSE", "SE"
            '''.format(
                table_name
            )

        else:
            table_name = 'Historico_alerta' + get_disease_suffix(disease)

            sql_alert = '''
            SELECT * FROM "Municipio"."{}"
            WHERE municipio_geocodigo={} ORDER BY "data_iniSE" ASC
            '''.format(
                table_name, geocode
            )

        sql = """
        SELECT
            (CASE
             WHEN tb_cases."data_iniSE" IS NOT NULL
               THEN tb_cases."data_iniSE"
             %(forecast_date_ini_epiweek)s
             ELSE NULL
             END
            ) AS "data_iniSE",
            tb_cases.casos_est_min,
            tb_cases.casos_est,
            tb_cases.casos_est_max,
            tb_cases.casos,
            tb_cases.nivel,
            (CASE
             WHEN tb_cases."SE" IS NOT NULL THEN tb_cases."SE"
             %(forecast_epiweek)s
             ELSE NULL
             END
            ) AS "SE",
            tb_cases.p_rt1
            %(forecast_models_cases)s
        FROM
            (%(sql_alert)s) AS tb_cases %(forecast_models_joins)s
        ORDER BY "data_iniSE" ASC
        """

        sql_forecast_by_model = '''
        FULL OUTER JOIN (
          SELECT
            epiweek,
            init_date_epiweek,
            cases AS forecast_%(model_name)s_cases
          FROM
            forecast.forecast_cases
            INNER JOIN forecast.forecast_model
              ON (
                forecast_cases.forecast_model_id = forecast_model.id
                AND forecast_model.active=TRUE
              )
            INNER JOIN forecast.forecast_city
              ON (
                forecast_city.geocode = forecast_cases.geocode
                AND forecast_cases.forecast_model_id =
                  forecast_city.forecast_model_id
                AND forecast_city.active=TRUE
              )
          WHERE
            cid10='%(cid10)s'
            AND forecast_cases.geocode=%(geocode)s
            AND published_date='%(published_date)s'
            AND forecast_cases.forecast_model_id=%(model_id)s
        ) AS forecast%(model_id)s ON (
          tb_cases."SE" = forecast%(model_id)s.epiweek
        )
        '''

        forecast_date_ini_epiweek = ''
        forecast_models_cases = ''
        forecast_models_joins = ''
        forecast_epiweek = ''
        forecast_config = {
            'geocode': geocode,
            'cid10': cid10,
            'published_date': None,
            'model_name': None,
            'model_id': None,
        }

        for i, row in df_forecast_model.iterrows():
            forecast_config.update(
                {
                    'published_date': row.published_date,
                    'model_name': row.forecast_model_name,
                    'model_id': row.forecast_model_id,
                }
            )
            # forecast models join sql
            forecast_models_joins += sql_forecast_by_model % forecast_config

            # forecast date ini selection
            forecast_date_ini_epiweek += (
                '''
            WHEN forecast%(model_id)s.init_date_epiweek IS NOT NULL
               THEN forecast%(model_id)s.init_date_epiweek
            '''
                % forecast_config
            )

            # forecast epiweek selection
            forecast_epiweek += (
                '''
            WHEN forecast%(model_id)s.epiweek IS NOT NULL
               THEN forecast%(model_id)s.epiweek
            '''
                % forecast_config
            )

            # forecast models cases selection
            forecast_models_cases += (
                ',forecast_%(model_name)s_cases' % forecast_config
            )

        if forecast_models_cases == '':
            forecast_models_cases = ',1'

        sql = sql % {
            'forecast_models_joins': forecast_models_joins,
            'forecast_models_cases': forecast_models_cases,
            'forecast_date_ini_epiweek': forecast_date_ini_epiweek,
            'forecast_epiweek': forecast_epiweek,
            'sql_alert': sql_alert,
        }

        with db_engine.connect() as conn:
            return pd.read_sql(sql, con=conn, parse_dates=True)


class ReportCity:
    @classmethod
    def read_disease_data(
        cls,
        geocode: int,
        disease_code: str,
        station_id: str,
        year_week: int,
        var_climate: str,
        has_tweets: bool = False,
    ) -> pd.DataFrame:
        """

        :param geocode:
        :param disease_code:
        :param station_id:
        :param year_week:
        :param var_climate:
        :param has_tweets:

        :return:

        """
        k = [
            var_climate,
            'casos',
            'p_inc100k',
            'casos_est',
            'p_rt1',
            'nivel',
            'level_code',
        ]

        tweet_join = ''
        tweet_field = ''

        if has_tweets:
            k.insert(1, 'n_tweets')
            tweet_field = 'tweets.n_tweets,'

            tweet_join = '''
            LEFT JOIN (
               SELECT
                 epi_week(data_dia) AS "SE",
                 SUM(numero) as n_tweets,
                 "Municipio_geocodigo"
               FROM "Municipio"."Tweet"
               WHERE "Municipio_geocodigo" = %(geocode)s
                 AND "CID10_codigo" = '%(disease_code)s'
                 AND epi_week(data_dia) <= %(year_week)s
               GROUP BY "SE", "Municipio_geocodigo"
               ORDER BY "SE" DESC
             ) AS tweets
               ON (
                 "Municipio_geocodigo"="municipio_geocodigo"
                 AND tweets."SE"=hist."SE"
               )
            '''

        disease_table_suffix = ''

        if disease_code == CID10['chikungunya']:
            disease_table_suffix = '_chik'
        elif disease_code == CID10['zika']:
            disease_table_suffix = '_zika'

        sql = (
            (
                '''
        SELECT
           %(var_climate)s,
           hist."SE",
           '''
                + tweet_field
                + '''
           hist.casos,
           hist.p_rt1,
           hist.casos_est,
           hist.p_inc100k,
           hist.nivel AS level_code,
           (CASE
              WHEN hist.nivel=1 THEN 'verde'
              WHEN hist.nivel=2 THEN 'amarelo'
              WHEN hist.nivel=3 THEN 'laranja'
              WHEN hist.nivel=4 THEN 'vermelho'
              ELSE '-'
            END) AS nivel
        FROM
         "Municipio"."Historico_alerta%(disease_table_suffix)s" AS hist
         LEFT JOIN (
           SELECT
               epi_week(data_dia) AS epiweek,
               AVG(%(var_climate)s) AS %(var_climate)s
           FROM "Municipio"."Clima_wu"
           WHERE "Estacao_wu_estacao_id" = '%(station_id)s'
           GROUP BY epiweek
           ORDER BY epiweek
         ) AS climate_wu
           ON (hist."SE"=climate_wu.epiweek)
         '''
                + tweet_join
                + '''
        WHERE
         hist."SE" <= %(year_week)s
         AND municipio_geocodigo=%(geocode)s
        ORDER BY "SE" DESC
        '''
            )
            % {
                'year_week': year_week,
                'geocode': geocode,
                'disease_code': disease_code,
                'station_id': station_id,
                'var_climate': var_climate,
                'disease_table_suffix': disease_table_suffix,
            }
        )

        df = pd.read_sql(sql, index_col='SE', con=db_engine)[k]
        df.p_rt1 = (df.p_rt1 * 100).round(0).fillna(0)
        df.casos_est = df.casos_est.round(0).fillna(0)
        df.p_inc100k = df.p_inc100k.round(0).fillna(0)

        if df.empty:
            df['init_date_week'] = None
        else:
            df['init_date_week'] = df.index.map(episem2date)

            # merge with a range date dataframe to keep empty week on the data
            ts_date = pd.date_range(
                df['init_date_week'].min(),
                df['init_date_week'].max(),
                freq='7D',
            )
            df_date = pd.DataFrame({'init_date_week': ts_date})
            df_date.set_index(
                df.init_date_week.map(
                    lambda x: int(episem(str(x)[:10], sep=''))
                ),
                drop=True,
                inplace=True,
            )

            df.index.name = None
            df_date.index.name = None
            df = pd.merge(
                df,
                df_date,
                how='outer',
                on='init_date_week',
                left_index=True,
                right_index=True,
            )

        df.index.name = 'SE'
        df.sort_index(ascending=True, inplace=True)

        if has_tweets:
            df.n_tweets = df.n_tweets.fillna(0).round(0)

        return df.rename(
            columns={
                'umid_max': 'umid.max',
                'temp_min': 'temp.min',
                'p_inc100k': 'incidência',
                'casos': 'casos notif.',
                'n_tweets': 'tweets',
                'p_rt1': 'pr(incid. subir)',
            }
        )

    def get_station_data(self, geocode: int):
        """

        :return:
        """
        sql = (
            '''
        SELECT
          codigo_estacao_wu, varcli, ucrit, tcrit,
          limiar_preseason, limiar_posseason, limiar_epidemico
        FROM "Dengue_global".regional_saude
        WHERE municipio_geocodigo = %s
        '''
            % geocode
        )

        df = pd.read_sql(sql, con=db_engine)

        if df.empty:
            raise Exception('NO STATION FOUND')

        return df


class ReportState:
    """Report State class."""

    @classmethod
    def _get_hist_disease_expr(
        cls,
        disease: str,
        geocodes: List[int],
        year_week_start: int,
        year_week_end: int,
    ) -> ibis.expr.types.Expr:
        """
        Return an ibis expression with the history for a given disease.

        Parameters
        ----------
        disease : str, {'dengue', 'chik', 'zika'}
        geocodes : List[int]
        year_week_start : int
            The starting Year/Week, e.g.: 202002
        year_week_end : int
            The ending Year/Week, e.g.: 202005

        Returns
        -------
        ibis.expr.types.Expr
        """
        table_suffix = ''
        if disease != 'dengue':
            table_suffix = '_{}'.format(disease)

        schema_city = con.schema('Municipio')
        t_hist = schema_city.table('Historico_alerta{}'.format(table_suffix))

        case_level = (
            ibis.case()
            .when((t_hist.nivel.cast('string') == '1'), 'verde')
            .when((t_hist.nivel.cast('string') == '2'), 'amarelo')
            .when((t_hist.nivel.cast('string') == '3'), 'laranja')
            .when((t_hist.nivel.cast('string') == '4'), 'vermelho')
            .else_('-')
            .end()
        ).name(f'nivel_{disease}')

        hist_keys = [
            t_hist.SE.name(f'SE_{disease}'),
            t_hist.casos.name(f'casos_{disease}'),
            t_hist.p_rt1.name(f'p_rt1_{disease}'),
            t_hist.casos_est.name(f'casos_est_{disease}'),
            t_hist.p_inc100k.name(f'p_inc100k_{disease}'),
            t_hist.nivel.name(f'level_code_{disease}'),
            case_level,
            t_hist.municipio_geocodigo.name(f'geocode_{disease}'),
        ]

        hist_filter = (
            t_hist['SE'].between(year_week_start, year_week_end)
        ) & (t_hist['municipio_geocodigo'].isin(geocodes))

        return t_hist[hist_filter][hist_keys].sort_by(f'SE_{disease}')

    @classmethod
    def _get_twitter_expr(
        cls, geocodes_list: List[int], year_week_start: int, year_week_end: int
    ) -> ibis.expr.types.Expr:
        """
        Return a twitter expression for given parameters.

        Parameters
        ----------
        geocodes_list : List[int]
        year_week_start : int
        year_week_end : int

        Returns
        -------
        ibis.expr.types.Expr
        """
        schema_city = con.schema('Municipio')
        epi_week_fn = get_epi_week_expr()

        t_tweet = schema_city.table('Tweet')
        filter_tweet_cities = t_tweet.Municipio_geocodigo.isin(geocodes_list)
        t_tweet = t_tweet[filter_tweet_cities]
        t_tweet = t_tweet.mutate(SE_twitter=epi_week_fn(t_tweet.data_dia))

        expr_tweet = t_tweet.groupby(
            [t_tweet.SE_twitter, t_tweet.Municipio_geocodigo]
        ).aggregate(n_tweets=t_tweet.numero.sum())

        filter_tweet = t_tweet.SE_twitter.between(
            year_week_start, year_week_end
        )

        return expr_tweet[filter_tweet].sort_by(('SE_twitter', False))

    @classmethod
    def _get_climate_wu_expr(
        cls, var_climate: str, station_id: str
    ) -> ibis.expr.types.Expr:
        """
        Return an ibis expression for climate_wu for given parameters.

        Parameters
        ----------
        var_climate : str, {'umid_max', 'temp_min'}
        station_id : str

        Returns
        -------
        ibis.expr.types.Expr
        """
        epi_week_fn = get_epi_week_expr()

        schema_city = con.schema('Municipio')

        t_climate_wu = schema_city.table('Clima_wu')

        expr_filter = t_climate_wu.Estacao_wu_estacao_id == station_id
        t_climate_wu = t_climate_wu[expr_filter]
        t_climate_wu = t_climate_wu.mutate(
            epiweek_climate=epi_week_fn(t_climate_wu.data_dia)
        )

        expr_climate_wu = t_climate_wu.groupby(
            [t_climate_wu.epiweek_climate]
        ).aggregate(
            **{var_climate: t_climate_wu[var_climate].mean().name(var_climate)}
        )

        return expr_climate_wu.sort_by(t_climate_wu.epiweek_climate)

    @classmethod
    def _get_report_data(
        cls,
        geocodes_list: List[int],
        year_week_start: int,
        year_week_end: int,
        var_climate: str,
        station_id: str,
    ) -> pd.DataFrame:
        """Get Repor State Data.

        Parameters
        ----------
        geocodes_list : List[int]
        year_week_start : int
            The starting Year/Week e.g.: 202002
        year_week_end : int
            The ending Year/Week e.g.: 202005
        var_climate : str, {'umid_max', 'temp_min'}
        station_id : str

        Returns
        -------
        pd.DataFrame
        """
        hist_disease_expr = {}
        hist_prev = None
        joined_expr = None
        previous_disease = None

        for disease in DISEASES_SHORT:
            hist_expr = cls._get_hist_disease_expr(
                disease, geocodes_list, year_week_start, year_week_end,
            )
            hist_disease_expr[disease] = hist_expr

            if joined_expr is None:
                joined_expr = hist_expr
            else:
                # todo: review join approach
                hist_prev = hist_disease_expr[previous_disease]
                joined_cond = (
                    hist_prev[f'SE_{previous_disease}']
                    == hist_expr[f'SE_{disease}']
                ) & (
                    hist_prev[f'geocode_{previous_disease}']
                    == hist_expr[f'geocode_{disease}']
                )
                joined_expr = joined_expr.left_join(hist_expr, joined_cond)
            previous_disease = disease

        # twitter data
        expr_tweet = cls._get_twitter_expr(
            geocodes_list, year_week_start, year_week_end,
        )
        expr_dengue = hist_disease_expr['dengue']

        joined_expr = joined_expr.left_join(
            expr_tweet,
            (
                (expr_tweet.Municipio_geocodigo == expr_dengue.geocode_dengue)
                & (expr_tweet.SE_twitter == expr_dengue.SE_dengue)
            ),
        )

        climate_wu_expr = cls._get_climate_wu_expr(var_climate, station_id)

        joined_expr = joined_expr.left_join(
            climate_wu_expr,
            hist_disease_expr['dengue'].SE_dengue
            == climate_wu_expr.epiweek_climate,
        ).materialize()

        epiweek2date_fn = get_epiweek2date_expr()

        k = ['casos', 'p_inc100k', 'casos_est', 'p_rt1', 'nivel', 'level_code']
        proj = [
            joined_expr['{}_{}'.format(v, d)]
            for v in k
            for d in DISEASES_SHORT
        ]
        proj.extend(
            [
                joined_expr[var_climate],
                joined_expr['n_tweets'],
                joined_expr['geocode_dengue'].name('geocode'),
                joined_expr['SE_dengue'].name('SE'),
                epiweek2date_fn(joined_expr.SE_dengue).name('init_date_week'),
            ]
        )

        return joined_expr[proj].sort_by(['SE', 'geocode']).execute()

    @classmethod
    def _format_data(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format the data for plotting.

        Parameters
        ----------
        df : pd.DataFrame

        Returns
        -------
        pd.DataFrame
        """
        # make a copy
        df = df.copy()
        df.fillna(0, inplace=True)

        if not df.empty:
            dfs = []

            # merge with a range date dataframe to keep empty week on the data
            ts_date = pd.date_range(
                df['init_date_week'].min(),
                df['init_date_week'].max(),
                freq='7D',
            )
            df_date = pd.DataFrame({'init_date_week': ts_date})

            for geocode in df.geocode.unique():
                df_ = df[df.geocode == geocode].sort_values('init_date_week')

                df_date_ = df_date.set_index(
                    df_.init_date_week.map(
                        lambda x: int(episem(str(x)[:10], sep=''))
                    ),
                    drop=True,
                )

                df_.index.name = None
                df_date_.index.name = None

                df_['init_date_week'] = pd.to_datetime(
                    df_['init_date_week'], errors='coerce'
                )

                dfs.append(
                    pd.merge(df_, df_date_, how='outer', on='init_date_week',)
                )

            df = pd.concat(dfs)

        df.sort_index(ascending=True, inplace=True)

        for d in DISEASES_SHORT:
            k = 'p_rt1_{}'.format(d)
            df[k] = (df[k] * 100).fillna(0)
            k = 'casos_est_{}'.format(d)
            df[k] = df[k].fillna(0).round(0)
            k = 'p_inc100k_{}'.format(d)
            df[k] = df[k].fillna(0).round(0)

            df.rename(
                columns={
                    'p_inc100k_{}'.format(d): 'incidência {}'.format(d),
                    'casos_{}'.format(d): 'casos notif. {}'.format(d),
                    'casos_est_{}'.format(d): 'casos est. {}'.format(d),
                    'p_rt1_{}'.format(d): 'pr(incid. subir) {}'.format(d),
                },
                inplace=True,
            )

        df.n_tweets = df.n_tweets.fillna(0).round(0)

        return df.rename(
            columns={
                'umid_max': 'umid.max',
                'temp_min': 'temp.min',
                'n_tweets': 'tweets',
            }
        )

    @classmethod
    def read_disease_data(
        cls,
        cities: Dict[int, str],
        station_id: str,
        year_week: int,
        var_climate: str,
    ) -> pd.DataFrame:
        """
        Return a disease dataframe from given parameters.

        Parameters
        ----------
        cities : dict[int, str]
        station_id : str
        year_week : int
            The last Year/Week for searching reference.
        var_climate : str, {'umid_max', 'temp_min'}

        Returns
        -------
        pd.DataFrame

        """
        year_week_start = year_week - 200
        year_week_end = year_week
        geocodes_list = [v for v in cities]

        df = cls._get_report_data(
            geocodes_list=geocodes_list,
            year_week_start=year_week_start,
            year_week_end=year_week_end,
            var_climate=var_climate,
            station_id=station_id,
        )
        return cls._format_data(df)
