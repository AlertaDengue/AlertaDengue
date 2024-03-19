from typing import Optional

import ibis
import ibis.expr.datatypes as dt
import pandas as pd

# local
from ad_main.settings import PSQL_DB, get_ibis_conn, get_sqla_conn
from dados.dbdata import CID10, STATE_NAME, get_disease_suffix  # noqa:F401
from sqlalchemy import text
from sqlalchemy.engine.base import Engine

DB_ENGINE = get_sqla_conn()
IBIS_CONN = get_ibis_conn()


class NotificationQueries:
    _age_field = """
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
        END AS age"""

    def __init__(
        self,
        uf,
        disease_values=None,
        age_values=None,
        gender_values=None,
        city_values=None,
        initial_date=None,
        final_date=None,
    ):
        self.uf = uf
        self.dist_filters = [
            ("uf", f"uf='{uf}'"),
            ("", self._get_disease_filter(disease_values)),
            ("", self._get_gender_filter(gender_values)),
            ("", self._get_period_filter(initial_date, final_date)),
            ("", self._get_age_filter(age_values)),
            ("cities", self._get_city_filter(city_values)),
        ]

    def _process_filter(self, data_filter, exception_key=""):
        filters = [v for k, v in data_filter if k != exception_key]
        return " AND ".join(filter(None, filters))

    def _get_gender_filter(self, gender):
        if gender is None:
            return "cs_sexo IN ('F', 'M')"
        genders = [
            "'F'" if g == "mulher" else "'M'" if g == "homem" else None
            for g in gender.lower().split(",")
        ]
        return f"cs_sexo IN ({','.join(filter(None, genders))})"

    def _get_city_filter(self, city):
        return f"municipio_geocodigo IN ({city})" if city is not None else ""

    def _get_age_filter(self, age):
        if age is None:
            return "age IS NOT NULL"
        ages = [f"'{a.replace('  ', '+ ')}'" for a in age.split(",")]
        return f"age IN ({','.join(ages)})"

    def _get_period_filter(self, initial_date=None, final_date=None):
        common_filter = """
        dt_notific >= (CURRENT_DATE - INTERVAL '1 YEAR') - CAST(CONCAT(CAST(
          EXTRACT(DOW FROM (CURRENT_DATE-INTERVAL '1 YEAR')) AS VARCHAR),'DAY'
        ) AS INTERVAL) AND
        """
        if not initial_date and not final_date:
            return common_filter + "1=1"
        date_filter = (
            f">= '{initial_date}'"
            if not final_date
            else f"<= '{final_date}'"
            if not initial_date
            else f"BETWEEN '{initial_date}' AND '{final_date}'"
        )
        return common_filter + f"dt_notific {date_filter}"

    def _get_disease_filter(self, disease):
        if disease is None:
            diseases = "','".join(CID10.values())
            return f"REPLACE(cid10_codigo, '.', '') IN ('{diseases}')"
        diseases = "','".join(
            CID10.get(d.lower(), "") for d in disease.split(",")
        )
        return f"REPLACE(cid10_codigo, '.', '') IN ('{diseases}')"

    def get_total_rows(self, db_engine: Engine = DB_ENGINE):
        """
        Retrieve the total number of rows based on specified filters.

        :param db_engine: Database engine to execute the query.
        :return: DataFrame containing the total number of rows.
        """
        filters = [
            "1=1",
            self._get_gender_filter(None),
            self._get_disease_filter(None),
            self._get_age_filter(None),
            self._get_period_filter(None, None),
        ]
        clean_filters = " uf='{}' AND ".format(self.uf) + " AND ".join(
            filter(None, filters)
        )

        sql = """
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
            """.format(
            self._age_field, clean_filters
        )

        with db_engine.connect() as conn:
            result = conn.execute(sql)
            return pd.DataFrame(result.fetchall(), columns=["casos"])

    def get_selected_rows(self, db_engine: Engine = DB_ENGINE):
        """
        Retrieve the number of selected rows based on specified filters.

        :param db_engine: Database engine to execute the query.
        :return: DataFrame containing the number of selected rows.
        """
        dist_filters = self._process_filter(self.dist_filters)

        sql = """
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
            """.format(
            self._age_field, dist_filters
        )

        with db_engine.connect() as conn:
            result = conn.execute(sql)
            return pd.DataFrame(result.fetchall(), columns=["casos"])

    def get_disease_dist(self, db_engine: Engine = DB_ENGINE) -> pd.DataFrame:
        """
        Fetches distribution of diseases.

        :param db_engine: SQLAlchemy engine to connect to the database.
        :return: DataFrame with disease distribution.
        """
        _dist_filters = self._process_filter(self.dist_filters, "disease")

        disease_label = " CASE "

        for cid_label, cid_id in CID10.items():
            disease_label += " WHEN cid10.codigo='{}' THEN '{}' \n".format(
                cid_id, cid_label.title()
            )

        disease_label += " ELSE cid10.codigo END AS cid10_nome "

        sql = """
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
        """.format(
            disease_label, self._age_field, _dist_filters
        )

        with db_engine.connect() as conn:
            result = conn.execute(sql)
            df_disease_dist = pd.DataFrame(result.fetchall())

            return df_disease_dist.set_index("category", drop=True)

    def _get_age_distribution(
        self, db_engine: Engine, gender_filter: str = ""
    ) -> pd.DataFrame:
        """
        Helper function to fetch age distribution.

        :param db_engine: SQLAlchemy engine to connect to the database.
        :param gender_filter: Filter for gender.
        :return: DataFrame with age distribution.
        """
        _dist_filters = self._process_filter(self.dist_filters, "age")

        sql = """
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
        {}
        GROUP BY age
        ORDER BY age
        """.format(
            self._age_field, _dist_filters, gender_filter
        )

        with db_engine.connect() as conn:
            result = conn.execute(sql)
            df_age_dist = pd.DataFrame(result.fetchall())

            return df_age_dist.set_index("category", drop=True)

    def get_age_dist(self, db_engine: Engine = DB_ENGINE) -> pd.DataFrame:
        """
        Fetches age distribution.

        :param db_engine: SQLAlchemy engine to connect to the database.
        :return: DataFrame with age distribution.
        """
        return self._get_age_distribution(db_engine)

    def get_age_gender_dist(
        self, db_engine: Engine = DB_ENGINE
    ) -> pd.DataFrame:
        """
        Fetches age and gender distribution.

        :param db_engine: SQLAlchemy engine to connect to the database.
        :return: DataFrame with age and gender distribution.
        """
        _dist_filters = self._process_filter(self.dist_filters, "age")

        sql = """
        SELECT
            age AS category,
            COUNT(CASE WHEN cs_sexo='F' THEN 1 END) AS "Mulher",
            COUNT(CASE WHEN cs_sexo='M' THEN 1 END) AS "Homem"
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
        """.format(
            self._age_field, _dist_filters
        )

        with db_engine.connect() as conn:
            result = conn.execute(sql)
            df_age_gender_dist = pd.DataFrame(result.fetchall())

            return df_age_gender_dist.set_index("category", drop=True)

    def get_age_male_dist(self, db_engine: Engine = DB_ENGINE) -> pd.DataFrame:
        """
        Fetches age distribution for males.

        :param db_engine: SQLAlchemy engine to connect to the database.
        :return: DataFrame with age distribution for males.
        """
        return self._get_age_distribution(db_engine, "AND cs_sexo = 'M'")

    def get_age_female_dist(
        self, db_engine: Engine = DB_ENGINE
    ) -> pd.DataFrame:
        """
        Fetches age distribution for females.

        :param db_engine: SQLAlchemy engine to connect to the database.
        :return: DataFrame with age distribution for females.
        """
        return self._get_age_distribution(db_engine, "AND cs_sexo = 'F'")

    def get_gender_dist(self, db_engine: Engine = DB_ENGINE) -> pd.DataFrame:
        """
        Fetches gender distribution.

        :param db_engine: SQLAlchemy engine to connect to the database.
        :return: DataFrame with gender distribution.
        """
        _dist_filters = self._process_filter(self.dist_filters, "gender")

        sql = """
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
        """.format(
            self._age_field, _dist_filters
        )

        with db_engine.connect() as conn:
            result = conn.execute(sql)
            df_gender_dist = pd.DataFrame(result.fetchall())

            return df_gender_dist.set_index("category", drop=True)

    def get_epiyears(
        self, state_name, disease=None, db_engine: Engine = DB_ENGINE
    ):
        parameters = {"state_name": state_name}

        disease_filter = ""
        if disease:
            disease_code = CID10.get(disease, "")
            parameters["disease_code"] = disease_code
            disease_filter = " AND disease_code = :disease_code"

        sql_text_query = """
        SELECT ano_notif, se_notif, casos
        FROM public.epiyear_summary_materialized_view
        WHERE uf = :state_name{disease_filter}
        ORDER BY ano_notif, se_notif
        """.format(
            disease_filter=disease_filter
        )

        with db_engine.connect() as conn:
            result = conn.execute(text(sql_text_query), **parameters)
            df = pd.DataFrame(
                result.fetchall(), columns=["ano_notif", "se_notif", "casos"]
            )
            return pd.crosstab(
                df["ano_notif"], df["se_notif"], df["casos"], aggfunc="sum"
            ).T

    def get_period_dist(self, db_engine: Engine = DB_ENGINE):
        _dist_filters = self._process_filter(self.dist_filters, "period")
        _dist_filters += " AND {}".format(self._get_period_filter())

        sql = """
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
        """.format(
            self._age_field, _dist_filters
        )

        with db_engine.connect() as conn:
            result = conn.execute(text(sql))
            df_alert_period = pd.DataFrame(
                result.fetchall(), columns=["dt_week", "Casos"]
            )
            df_alert_period.set_index("dt_week", inplace=True)

        sql_bounds = """
        SELECT
        (CURRENT_DATE - INTERVAL '1 YEAR') - CAST(CONCAT(CAST(
        EXTRACT(DOW FROM (CURRENT_DATE-INTERVAL '1 YEAR')) AS VARCHAR),'DAY'
        ) AS INTERVAL) AS dt_week_start,
        CURRENT_DATE - CAST(CONCAT(CAST(
            EXTRACT(DOW FROM CURRENT_DATE) AS VARCHAR), 'DAY'
        ) AS INTERVAL) AS dt_week_end
        """

        with db_engine.connect() as conn:
            result = conn.execute(text(sql_bounds))
            df_period_bounds = pd.DataFrame(
                result.fetchall(), columns=["dt_week_start", "dt_week_end"]
            )

        start_date = df_period_bounds["dt_week_start"].iloc[0]
        end_date = df_period_bounds["dt_week_end"].iloc[0]

        if start_date not in df_alert_period.index:
            df_alert_period.loc[start_date] = 0

        if end_date not in df_alert_period.index:
            df_alert_period.loc[end_date] = 0

        df_alert_period.sort_index(inplace=True)
        return df_alert_period


class AlertCity:
    @staticmethod
    def search(
        disease: str,
        geocode: int,
        ew_start: Optional[int] = None,
        ew_end: Optional[int] = None,
    ) -> ibis.expr:
        """
        Return an ibis expression with the history for a given disease.
        Parameters
        ----------
        disease : str, {'dengue', 'chikungunya', 'zika'}
        geocode : int
        ew_start : Optional[int]
            The starting Year/Week, e.g.: 202202
        ew_end : Optional[int]
            The ending Year/Week, e.g.: 202205
        Returns
        -------
        ibis.expr.types.Expr
        """

        if disease not in CID10.keys():
            raise Exception(
                f"The diseases available are: {list(CID10.keys())}"
            )

        table_suffix = ""
        if disease != "dengue" and disease != "zika":
            table_suffix = get_disease_suffix(disease)

        # schema_city = IBIS_CONN.schema("Municipio")
        # t_hist = schema_city.table(f"Historico_alerta{table_suffix}")
        t_hist = IBIS_CONN.table(
            f"Historico_alerta{table_suffix}", PSQL_DB, "Municipio"
        )

        if ew_start and ew_end:
            t_hist_filter_bol = (
                t_hist["SE"].between(int(ew_start), int(ew_end))
            ) & (t_hist["municipio_geocodigo"] == geocode)

            t_hist_filter_expr = t_hist.filter(t_hist_filter_bol).order_by(
                ibis.desc("SE")
            )

        else:
            t_hist_filter_expr = (
                t_hist.filter(t_hist["municipio_geocodigo"] == geocode)
                .order_by(ibis.desc("SE"))
                .limit(3)
            )

        t_hist_accum_expr = t_hist_filter_expr.mutate(
            notif_accum_year=t_hist_filter_expr.casos.sum()
        )

        t_hist_accum_expr = t_hist_accum_expr.mutate(
            data_iniSE=t_hist_accum_expr.data_iniSE.cast(dt.timestamp)
        )

        # print(ibis.impala.compile(t_hist_accum_expr))

        return t_hist_accum_expr
