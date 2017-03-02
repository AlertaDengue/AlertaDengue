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


db_engine = create_engine("postgresql://{}:{}@{}/{}".format(
    settings.PSQL_USER,
    settings.PSQL_PASSWORD,
    settings.PSQL_HOST,
    settings.PSQL_DB
))

def get_all_active_cities():
    """
    Fetch from the database a list on names of active cities
    :return: list of tuples (geocode,name)
    """
    res = cache.get('get_all_active_cities')

    if res is None:
        with db_engine.connect() as conexao:
            res = conexao.execute('SELECT DISTINCT municipio_geocodigo, municipio_nome FROM'
                '"Municipio"."Historico_alerta";')
            res = res.fetchall()
            cache.set('get_all_active_cities', res, settings.QUERY_CACHE_TIMEOUT)
    return res


def get_alerta_mrj():
    """
    Fetch the alert table for the city of Rio de janeiro
    :return: pandas dataframe
    """
    with db_engine.connect() as conexao:
        dados_alerta = pd.read_sql_query('select * from "Municipio".alerta_mrj;', conexao, index_col='id')
    return dados_alerta


def get_city(query):
    """
    Fetch city geocode, name and state from the database,
    matching the substring query
    :param query: substring of the city
    :return: list of dictionaries
    """
    with db_engine.connect() as conexao:
        sql = 'SELECT distinct municipio_geocodigo, nome, uf from "Municipio"."Historico_alerta" inner JOIN' \
              ' "Dengue_global"."Municipio" on "Historico_alerta".municipio_geocodigo="Municipio".geocodigo ' \
              'WHERE nome ilike(%s);'

        result = conexao.execute(sql, ('%'+query+'%',))

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
        with db_engine.connect() as conexao:
            series = pd.read_sql('select * from uf_total_view;', conexao, parse_dates=True)
            cache.set('get_series_by_UF', series, settings.QUERY_CACHE_TIMEOUT)

    return series


def load_series(cidade, doenca='dengue', conn=None):
    """
    Monta as séries do alerta para visualização no site
    :param cidade: geocodigo da cidade desejada
    :param doenca: dengue|chik|zika
    :return: dictionary
    """
    cache_key = 'load_series-{}-{}'.format(cidade, doenca)
    result = cache.get(cache_key)
    if result is None:
        with db_engine.connect() as conexao:
            ap = str(cidade)
            cidade = add_dv(int(str(cidade)[:-1]))
            dados_alerta = pd.read_sql_query('select * from "Municipio"."Historico_alerta" where municipio_geocodigo={} ORDER BY "data_iniSE" ASC'.format(cidade), conexao, 'id', parse_dates=True)
            if len(dados_alerta) == 0:
                raise NameError("Não foi possível obter os dados do Banco para cidade {}".format(cidade))

            # tweets = pd.read_sql_query('select * from "Municipio"."Tweet" where "Municipio_geocodigo"={}'.format(cidade), parse_dates=True)
            series = defaultdict(lambda: defaultdict(lambda: []))
            series[ap]['dia'] = dados_alerta.data_iniSE.tolist()
            # series[ap]['tweets'] = [float(i) if not np.isnan(i) else None for i in tweets.numero]
            # series[ap]['tmin'] = [float(i) if not np.isnan(i) else None for i in G.get_group(ap).tmin]
            series[ap]['casos_est_min'] = np.nan_to_num(dados_alerta.casos_est_min).astype(int).tolist()
            series[ap]['casos_est'] = np.nan_to_num(dados_alerta.casos_est).astype(int).tolist()
            series[ap]['casos_est_max'] = np.nan_to_num(dados_alerta.casos_est_max).astype(int).tolist()
            series[ap]['casos'] = np.nan_to_num(dados_alerta.casos).astype(int).tolist()
            series[ap]['alerta'] = (dados_alerta.nivel.astype(int)-1).tolist()  # (1,4)->(0,3)
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

    if not cidades:
        return result

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
        ap = str(v)
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

        cache_key = 'load_series-{}-{}'.format(ap, doenca)
        cache.set(cache_key, {ap: series[ap]}, settings.QUERY_CACHE_TIMEOUT)

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


def get_cities_alert_by_state(state_name, doenca='dengue', conn=None):
    """
    Retorna vários indicadores de alerta a nível da cidade.
    :param cidade: geocódigo
    :param doenca: dengue|chik|zika
    :return: tupla
    """
    alert = pd.read_sql_query('''
    SELECT
        hist_alert.id,
        hist_alert.municipio_geocodigo,
        municipio.nome,
        hist_alert."data_iniSE",
        (hist_alert.nivel-1) AS level_alert
    FROM
        "Municipio"."Historico_alerta" AS hist_alert
        INNER JOIN (
            SELECT geocodigo, MAX("data_iniSE") AS "data_iniSE"
            FROM
                "Municipio"."Historico_alerta" AS alerta
                INNER JOIN "Dengue_global"."Municipio" AS municipio
                    ON alerta.municipio_geocodigo = municipio.geocodigo
            WHERE uf='{}'
            GROUP BY geocodigo
        ) AS recent_alert ON (
            recent_alert.geocodigo=hist_alert.municipio_geocodigo
            AND recent_alert."data_iniSE"=hist_alert."data_iniSE"
        ) INNER JOIN "Dengue_global"."Municipio" AS municipio ON (
            hist_alert.municipio_geocodigo = municipio.geocodigo
        )
    '''.format(state_name), conn, 'id', parse_dates=True)

    return alert


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


def count_cities_by_uf(uf, connection):
    """
    Returna contagem de cidades participantes por estado

    :param uf: uf a ser consultada
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

    return pd.read_sql(sql, connection).astype(int).iloc[0]['count']


def count_cases_by_uf(uf, se, connection):
    """
    Returna contagem de cidades participantes por estado

    :param uf: uf a ser consultada
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
        WHERE uf='%s' AND "SE" = %s
        ''' % (uf, se)

    return pd.read_sql(sql, connection).astype(int)


def count_cases_week_variation_by_uf(uf, se1, se2, connection):
    """
    Returna contagem de cidades participantes por estado

    :param uf: uf a ser consutado
    :param se: número do ano e semana (no ano), ex: 201503
    :param connection: sqlalchemy engine
    :return: dataframe
    """

    sql = '''
    SELECT
        COALESCE(SUM(alerta.casos)-SUM(alerta_passado.casos), 0) AS casos,
        COALESCE(SUM(alerta.casos_est)-SUM(alerta_passado.casos_est), 0)
            AS casos_est
    FROM "Municipio"."Historico_alerta" AS alerta
    INNER JOIN "Municipio"."Historico_alerta" AS alerta_passado
      ON (
        alerta.municipio_geocodigo = alerta_passado.municipio_geocodigo
        AND alerta."SE"=%s
        AND alerta_passado."SE"=%s)
    INNER JOIN "Dengue_global"."Municipio" AS municipio
      ON alerta.municipio_geocodigo = municipio.geocodigo
    WHERE uf ='%s'
    ''' % (se2, se1, uf)

    return pd.read_sql(sql, connection).astype(int)


def tail_estimated_cases(geo_ids, n=12, conn=None):
    """

    :param geo_ids: list of city geo ids
    :param n: the last n estimated cases
    :param conn: connection
    :return: dict
    """

    sql_template = '''(
    SELECT municipio_geocodigo, "data_iniSE", casos_est, id
    FROM "Municipio"."Historico_alerta"
    WHERE municipio_geocodigo={}
    ORDER BY "data_iniSE" DESC
    LIMIT ''' + str(n) + ')'

    sql = ' UNION '.join([
        sql_template.format(gid) for gid in geo_ids
    ]) + ' ORDER BY municipio_geocodigo, "data_iniSE"'

    df_case_series = pd.read_sql(sql, conn, 'id')

    return {
        k: v.casos_est.values.tolist()
        for k, v in df_case_series.groupby(by='municipio_geocodigo')
    }


class NotificationQueries:
    _age_field = '''
        CASE
        WHEN nu_idade_n <= 4004 THEN '00-04 anos'
        WHEN nu_idade_n BETWEEN 4005 AND 4009 THEN '05-09 anos'
        WHEN nu_idade_n BETWEEN 4010 AND 4019 THEN '10-19 anos'
        WHEN nu_idade_n BETWEEN 4020 AND 4029 THEN '20-29 anos'
        WHEN nu_idade_n BETWEEN 4030 AND 4039 THEN '30-39 anos'
        WHEN nu_idade_n BETWEEN 4040 AND 4049 THEN '40-49 anos'
        WHEN nu_idade_n BETWEEN 4050 AND 4059 THEN '50-59 anos'
        WHEN nu_idade_n >=4060 THEN '60+ anos'
        ELSE NULL
        END AS age'''
    dist_filters = None

    def __init__(
        self, uf, disease_values, age_values, gender_values,
        city_values, initial_date, final_date
    ):
        """

        :param conn:
        """
        self.uf = uf

        self.dist_filters = [
            ('uf', "uf='%s'" % uf),
            ('', self._get_disease_filter(None)),  # min filter
            ('', self._get_gender_filter(None)),  # min filter
            ('', self._get_period_filter(None)),  # min filter
            ('', self._get_age_filter(None)),  # min filter
            ('disease', self._get_disease_filter(disease_values)),
            ('gender', self._get_gender_filter(gender_values)),
            ('age', self._get_age_filter(age_values)),
            ('cities', self._get_city_filter(city_values)),
            ('period', self._get_period_filter(
                initial_date, final_date
            )),
        ]

    def _process_filter(self, data_filter, exception_key=''):
        """

        :param data_filter:
        :param exception_key:
        :return:
        """
        _f = [v for k, v in data_filter if not k == exception_key]
        return ' AND '.join(filter(lambda x: x, _f))

    def _get_gender_filter(self, gender):
        """

        :param gender:
        :return:
        """
        return (
            "cs_sexo IN ('F', 'M')" if gender is None else
            "cs_sexo IN ({})".format(','.join([
                "'F'" if _gender == 'mulher' else
                "'M'" if _gender == 'homem' else
                None for _gender in gender.lower().split(',')
            ]))
        )

    def _get_city_filter(self, city):
        """

        :param city:
        :return:
        """
        return (
            '' if city is None else
            'municipio_geocodigo IN(%s)' % city
        )

    def _get_age_filter(self, age):
        """

        :param age:
        :return:
        """

        if age is None:
            return 'age IS NOT NULL'

        _age = [
            "'{}'".format(_age.replace('  ', '+ '))
            for _age in age.split(',')
        ]
        return "age IN ({})".format(','.join(_age))

    def _get_period_filter(self, initial_date=None, final_date=None):
        """

        :param initial_date:
        :param final_date:
        :return:
        """
        common_filter = '''
        dt_notific >= (CURRENT_DATE - INTERVAL '1 YEAR') - CAST(CONCAT(CAST(
          EXTRACT(DOW FROM (CURRENT_DATE-INTERVAL '1 YEAR')) AS VARCHAR),'DAY'
        ) AS INTERVAL) AND
        '''
        return common_filter + (
            '1=1' if not initial_date and not final_date else
            'dt_notific {} '.format(
                ">= '{}'".format(initial_date) if not final_date else
                "<= '{}'".format(final_date) if not initial_date else
                " BETWEEN '{}' AND '{}'".format(initial_date, final_date)
            )
        )

    def _get_disease_filter(self, disease):
        """

        :param disease:
        :return:
        """
        return (
            'cid10_codigo IS NOT NULL' if disease is None else
            'cid10_codigo IN ({})'.format(','.join([
                "'{}'".format(CID10[cid.lower()])
                for cid in disease.split(',')
            ]))
        )

    def get_total_rows(self):
        """

        :param uf:
        :return:
        """
        _filt = filter(
            lambda x: x, [
                '1=1',
                self._get_gender_filter(None),
                self._get_disease_filter(None),
                self._get_age_filter(None),
                self._get_period_filter(None, None)
            ]
        )

        clean_filters = " uf='{}' AND ".format(self.uf) + ' AND '.join(_filt)

        sql = '''
            SELECT
                count(id) AS casos
            FROM (
                SELECT
                    *,
                    {}
                FROM
                    "Municipio"."Notificacao" AS notif
                    INNER JOIN "Dengue_global"."Municipio" AS municipio
                      ON notif.municipio_geocodigo = municipio.geocodigo
            ) AS tb
            WHERE {}
            '''.format(self._age_field, clean_filters)

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn, 'casos')

    def get_selected_rows(self):
        """

        :return:
        """
        _dist_filters = self._process_filter(self.dist_filters)

        sql = '''
            SELECT
                count(id) AS casos
            FROM (
                SELECT
                    *,
                    {}
                FROM
                    "Municipio"."Notificacao" AS notif
                    INNER JOIN "Dengue_global"."Municipio" AS municipio
                      ON notif.municipio_geocodigo = municipio.geocodigo
            ) AS tb
            WHERE {}
            '''.format(self._age_field, _dist_filters)

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn, 'casos')

    def get_disease_dist(self):
        """

        :return:
        """
        _dist_filters = self._process_filter(self.dist_filters, 'disease')

        sql = '''
        SELECT
            COALESCE(cid10_nome, NULL) AS category,
            count(id) AS casos
        FROM (
            SELECT
                *,
                cid10.nome AS cid10_nome,
                {}
            FROM
                "Municipio"."Notificacao" AS notif
                INNER JOIN "Dengue_global"."Municipio" AS municipio
                  ON notif.municipio_geocodigo = municipio.geocodigo
                LEFT JOIN "Dengue_global"."CID10" AS cid10
                  ON notif.cid10_codigo=cid10.codigo
        ) AS tb
        WHERE {}
        GROUP BY cid10_nome;
        '''.format(self._age_field, _dist_filters)

        with db_engine.connect() as conn:
            df_disease_dist = pd.read_sql(sql, conn)

        df_disease_dist.category = (
            df_disease_dist.category.replace(
                'Dengue [dengue clássico]', 'Dengue'
            )
        )

        return df_disease_dist.set_index('category', drop=True)

    def get_age_dist(self):
        """

        :param dist_filters:
        :return:
        """
        _dist_filters = self._process_filter(self.dist_filters, 'age')

        sql = '''
        SELECT
            age AS category,
            count(age) AS casos
        FROM (
            SELECT
                *,
                {}
            FROM
                "Municipio"."Notificacao" AS notif
                INNER JOIN "Dengue_global"."Municipio" AS municipio
                  ON notif.municipio_geocodigo = municipio.geocodigo
        ) AS tb
        WHERE {}
        GROUP BY age
        ORDER BY age
        '''.format(self._age_field, _dist_filters)

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn, 'category')

    def get_age_male_dist(self):
        """

        :param dist_filters:
        :return:
        """
        _dist_filters = self._process_filter(self.dist_filters, 'age')

        sql = '''
        SELECT
            age AS category,
            count(age) AS casos
        FROM (
            SELECT
                *,
                {}
            FROM
                "Municipio"."Notificacao" AS notif
                INNER JOIN "Dengue_global"."Municipio" AS municipio
                  ON notif.municipio_geocodigo = municipio.geocodigo
        ) AS tb
        WHERE {} AND cs_sexo = 'M'
        GROUP BY age
        ORDER BY age
        '''.format(self._age_field, _dist_filters)

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn, 'category')

    def get_age_female_dist(self):
        """

        :param dist_filters:
        :return:
        """
        _dist_filters = self._process_filter(self.dist_filters, 'age')

        sql = '''
        SELECT
            age AS category,
            count(age) AS casos
        FROM (
            SELECT
                *,
                {}
            FROM
                "Municipio"."Notificacao" AS notif
                INNER JOIN "Dengue_global"."Municipio" AS municipio
                  ON notif.municipio_geocodigo = municipio.geocodigo
        ) AS tb
        WHERE {} AND cs_sexo = 'F'
        GROUP BY age
        ORDER BY age
        '''.format(self._age_field, _dist_filters)

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn, 'category')

    def get_gender_dist(self):
        _dist_filters = self._process_filter(self.dist_filters, 'gender')

        sql = '''
        SELECT
            (CASE COALESCE(cs_sexo, NULL)
             WHEN 'M' THEN 'Homem'
             WHEN 'F' THEN 'Mulher'
             ELSE NULL
             END
            ) AS category,
            COUNT(id) AS casos
        FROM (
            SELECT *,
                {}
            FROM
                "Municipio"."Notificacao" AS notif
                INNER JOIN "Dengue_global"."Municipio" AS municipio
                  ON notif.municipio_geocodigo = municipio.geocodigo
        ) AS tb
        WHERE {} AND cs_sexo IN ('F', 'M')
        GROUP BY cs_sexo;
        '''.format(self._age_field, _dist_filters)

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn, 'category')

    def get_epiyears(self, state_name):
        sql = '''
        SELECT
          ano_notif,
          se_notif,
          COUNT(se_notif) AS casos
        FROM
          "Municipio"."Notificacao" AS notif
          INNER JOIN "Dengue_global"."Municipio" AS municipio
            ON notif.municipio_geocodigo = municipio.geocodigo
        WHERE uf='{}'
        GROUP BY ano_notif, se_notif
        ORDER BY ano_notif, se_notif
        '''.format(state_name)

        with db_engine.connect() as conn:
            df = pd.read_sql(sql, conn)

        return pd.crosstab(
            df['ano_notif'], df['se_notif'], df['casos'], aggfunc=sum
        ).T


    def get_period_dist(self):
        _dist_filters = self._process_filter(self.dist_filters, 'period')
        _dist_filters += ' AND {}'.format(self._get_period_filter())

        sql = '''
        SELECT
            dt_week,
            count(dt_week) AS Casos
        FROM (
            SELECT *,
                dt_notific - CAST(
                    CONCAT(CAST(EXTRACT(DOW FROM dt_notific) AS VARCHAR), 'DAY'
                ) AS INTERVAL) AS dt_week,
                {}
            FROM
                "Municipio"."Notificacao" AS notif
                INNER JOIN "Dengue_global"."Municipio" AS municipio
                    ON notif.municipio_geocodigo = municipio.geocodigo
        ) AS tb
        WHERE {}
        GROUP BY dt_week
        ORDER BY dt_week
        '''.format(self._age_field, _dist_filters)

        with db_engine.connect() as conn:
            df_alert_period = pd.read_sql(sql, conn, index_col='dt_week')

        df_alert_period.index.rename('category', inplace=True)

        sql = '''
        SELECT
          (CURRENT_DATE - INTERVAL '1 YEAR') - CAST(CONCAT(CAST(
           EXTRACT(DOW FROM (CURRENT_DATE-INTERVAL '1 YEAR')) AS VARCHAR),'DAY'
          ) AS INTERVAL) AS dt_week_start,
          CURRENT_DATE - CAST(CONCAT(CAST(
            EXTRACT(DOW FROM CURRENT_DATE) AS VARCHAR), 'DAY'
          ) AS INTERVAL) AS dt_week_end
        '''

        with db_engine.connect() as conn:
            df_period_bounds = pd.read_sql(sql, conn)

        if not df_period_bounds.dt_week_start[0] in df_alert_period.index:
            df = pd.DataFrame({
                'category': [df_period_bounds.dt_week_start[0]],
                'casos': [0]
            })

            df = df.set_index('category')

            df_alert_period = pd.concat([
                df, df_alert_period
            ])

        if not df_period_bounds.dt_week_end[0] in df_alert_period.index:
            df = pd.DataFrame({
                'category': [df_period_bounds.dt_week_end[0]],
                'casos': [0]
            })

            df = df.set_index('category')

            df_alert_period = pd.concat([
                df_alert_period, df
            ])

        return df_alert_period
