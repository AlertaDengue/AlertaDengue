from sqlalchemy import create_engine
# local
from . import settings
from dados.dbdata import CID10, STATE_NAME, get_disease_suffix, MRJ_GEOCODE

import pandas as pd


db_engine = create_engine("postgresql://{}:{}@{}/{}".format(
    settings.PSQL_USER,
    settings.PSQL_PASSWORD,
    settings.PSQL_HOST,
    settings.PSQL_DB
))


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
        _diseases = ','.join(["'%s'" % cid for cid in CID10.values()])
        return (
            "REPLACE(cid10_codigo, '.', '') IN (%s)" % (
                _diseases
            ) if disease is None else
            "REPLACE(cid10_codigo, '.', '') IN ({})".format(','.join([
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

        disease_label = ' CASE '

        for cid_label, cid_id in CID10.items():
            disease_label += " WHEN cid10.codigo='{}' THEN '{}' \n".format(
                cid_id, cid_label.title()
            )

        disease_label += ' ELSE cid10.codigo END AS cid10_nome '

        sql = '''
        SELECT
            COALESCE(cid10_nome, NULL) AS category,
            count(id) AS casos
        FROM (
            SELECT
                *,
                {},
                {}
            FROM
                "Municipio"."Notificacao" AS notif
                INNER JOIN "Dengue_global"."Municipio" AS municipio
                  ON notif.municipio_geocodigo = municipio.geocodigo
                LEFT JOIN "Dengue_global"."CID10" AS cid10
                  ON REPLACE(notif.cid10_codigo, '.', '')=cid10.codigo
        ) AS tb
        WHERE {}
        GROUP BY cid10_nome;
        '''.format(disease_label, self._age_field, _dist_filters)

        with db_engine.connect() as conn:
            df_disease_dist = pd.read_sql(sql, conn)

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

    def get_age_gender_dist(self):
        """

        :param dist_filters:
        :return:
        """
        _dist_filters = self._process_filter(self.dist_filters, 'age')

        sql = '''
        SELECT
            age AS category,
            --count(age) AS casos
            COUNT(is_female) AS "Mulher",
            COUNT(is_male) AS "Homem"
        FROM (
            SELECT
                *,
                CASE WHEN cs_sexo='F' THEN 1 END AS is_female,
                CASE WHEN cs_sexo='M' THEN 1 END AS is_male,
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

    def get_epiyears(self, state_name, disease=None):
        """

        :param state_name:
        :param disease: dengue|chikungunya|zika
        :return:

        """
        disease_filter = ''

        if disease is not None:
            disease_filter = (
                " AND REPLACE(cid10_codigo, '.', '')='%s'" % CID10[disease]
            )

        sql = '''
        SELECT
          ano_notif,
          se_notif,
          COUNT(se_notif) AS casos
        FROM
          "Municipio"."Notificacao" AS notif
          INNER JOIN "Dengue_global"."Municipio" AS municipio
            ON notif.municipio_geocodigo = municipio.geocodigo
        WHERE uf='{}' {}
        GROUP BY ano_notif, se_notif
        ORDER BY ano_notif, se_notif
        '''.format(state_name, disease_filter)

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


class AlertCity:
    @staticmethod
    def search_rj(disease: str, ew_start: int, ew_end:int):
        """

        :param disease:
        :param ew_start:
        :param ew_end:
        :return:
        """
        if disease not in CID10.keys():
            raise Exception(
                'The diseases available are: %s.' % ', '.join('`%s`' % k for k in CID10.keys())
            )

        sql = '''
        SELECT *
        FROM "Municipio".alerta_mrj%s 
        WHERE se BETWEEN %s AND %s
        ''' % (get_disease_suffix(disease), ew_start, ew_end)

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn)

    @staticmethod
    def search(disease: str, geocode: int, ew_start: int, ew_end: int):
        """

        :param disease:
        :param geocode:
        :param ew_start:
        :param ew_end:
        :return:
        """
        if disease not in CID10.keys():
            raise Exception(
                'The diseases available are: %s.' % ', '.join('`%s`' % k for k in CID10.keys())
            )

        sql = '''
            SELECT *
            FROM "Municipio"."Historico_alerta%s" 
            WHERE municipio_geocodigo=%s AND "SE" BETWEEN %s AND %s
            ''' % (get_disease_suffix(disease), geocode, ew_start, ew_end)

        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn)
