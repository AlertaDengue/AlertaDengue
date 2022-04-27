"""
Código antigos usados para comparar novas implementações
"""

import pandas as pd
from ad_main import settings
from dados.episem import episem
from sqlalchemy import create_engine

PSQL_URI = "postgresql://{}:{}@{}:{}/{}".format(
    settings.PSQL_USER,
    settings.PSQL_PASSWORD,
    settings.PSQL_HOST,
    settings.PSQL_PORT,
    settings.PSQL_DB,
)

db_engine = create_engine(PSQL_URI)


class OldReportState:
    diseases = ["dengue", "chik", "zika"]

    @classmethod
    def _read_disease_data(
        cls, cities: dict, station_id: str, year_week: int, var_climate: str
    ) -> pd.DataFrame:
        """
        :param cities:
        :param station_id:
        :param year_week:
        :param var_climate:
        :return:
        """

        k = ["casos", "p_inc100k", "casos_est", "p_rt1", "nivel", "level_code"]

        k = ["{}_{}".format(v, d) for v in k for d in cls.diseases]

        k.append(var_climate)
        k.append("n_tweets")
        k.append("geocode_dengue AS geocode")
        k.append('"SE_dengue" AS "SE"')
        k.append('epiweek2date("SE_dengue") AS init_date_week')

        general_param = {
            "year_week_start": year_week - 100,
            "year_week_end": year_week,
            "geocodes": ",".join(map(lambda v: "'{}'".format(v), cities)),
            "var_climate": var_climate,
            "station_id": station_id,
        }

        sql = ""
        previous_disease = ""
        for disease in cls.diseases:
            _param = dict(general_param)
            _param["disease"] = disease

            table_suffix = ""
            if disease != "dengue":
                table_suffix = "_{}".format(disease)

            _param["table_suffix"] = table_suffix

            sql_ = (
                """
            (SELECT
               hist."SE" AS "SE_%(disease)s",
               hist.casos AS casos_%(disease)s,
               hist.p_rt1 AS p_rt1_%(disease)s,
               hist.casos_est AS casos_est_%(disease)s,
               hist.p_inc100k AS p_inc100k_%(disease)s,
               hist.nivel AS level_code_%(disease)s,
               (CASE
                  WHEN hist.nivel=1 THEN 'verde'
                  WHEN hist.nivel=2 THEN 'amarelo'
                  WHEN hist.nivel=3 THEN 'laranja'
                  WHEN hist.nivel=4 THEN 'vermelho'
                  ELSE '-'
                END) AS nivel_%(disease)s,
                hist.municipio_geocodigo AS geocode_%(disease)s
            FROM
             "Municipio"."Historico_alerta%(table_suffix)s" AS hist
            WHERE
             hist."SE" BETWEEN %(year_week_start)s AND %(year_week_end)s
             AND hist.municipio_geocodigo IN (%(geocodes)s)
            ORDER BY "SE_%(disease)s" DESC
            ) AS %(disease)s
            """
                % _param
            )

            if not sql:
                sql = sql_
            else:
                sql += """
                    LEFT JOIN {0}
                    ON (
                      {1}."SE_{1}" = {2}."SE_{2}"
                      AND {1}.geocode_{1} = {2}.geocode_{2}
                    )
                """.format(
                    sql_, previous_disease, disease
                )
            previous_disease = disease

        tweet_join = (
            """
        LEFT JOIN (
           SELECT
             epi_week(data_dia) AS "SE_twitter",
             SUM(numero) as n_tweets,
             "Municipio_geocodigo"
           FROM "Municipio"."Tweet"
           WHERE
             "Municipio_geocodigo" IN (%(geocodes)s)
             AND epi_week(data_dia)
               BETWEEN %(year_week_start)s AND %(year_week_end)s
           GROUP BY "SE_twitter", "Municipio_geocodigo"
           ORDER BY "SE_twitter" DESC
        ) AS tweets
           ON (
             "Municipio_geocodigo"=dengue."geocode_dengue"
             AND tweets."SE_twitter"=dengue."SE_dengue"
           )
        """
            % general_param
        )

        climate_join = (
            """
        LEFT JOIN (
          SELECT
             epi_week(data_dia) AS epiweek_climate,
             AVG(%(var_climate)s) AS %(var_climate)s
          FROM "Municipio"."Clima_wu"
          WHERE "Estacao_wu_estacao_id" = '%(station_id)s'
          GROUP BY epiweek_climate
          ORDER BY epiweek_climate
        ) AS climate_wu
           ON (dengue."SE_dengue"=climate_wu.epiweek_climate)
        """
            % general_param
        )

        sql += climate_join + tweet_join

        sql = " SELECT {} FROM ({}) AS data".format(",".join(k), sql)

        df = pd.read_sql(sql, index_col="SE", con=db_engine)

        if not df.empty:
            dfs = []

            # merge with a range date dataframe to keep empty week on the data
            ts_date = pd.date_range(
                df["init_date_week"].min(),
                df["init_date_week"].max(),
                freq="7D",
            )
            df_date = pd.DataFrame({"init_date_week": ts_date})

            for geocode in df.geocode.unique():
                df_ = df[df.geocode == geocode].sort_values("init_date_week")

                df_date_ = df_date.set_index(
                    df_.init_date_week.map(
                        lambda x: int(episem(str(x)[:10], sep=""))
                    ),
                    drop=True,
                )

                df_.index.name = "SE"
                df_date_.index.name = None

                df_["init_date_week"] = pd.to_datetime(
                    df_["init_date_week"], errors="coerce"
                )
                # TODO: these parameters is not valid in the future releases.
                dfs.append(
                    pd.merge(
                        df_,
                        df_date_,
                        how="outer",
                        left_index=True,
                        right_index=True,
                    )
                )

            df = pd.concat(dfs)

        df.sort_index(ascending=True, inplace=True)

        for d in cls.diseases:
            k = "p_rt1_{}".format(d)
            df[k] = (df[k] * 100).fillna(0)
            k = "casos_est_{}".format(d)
            df[k] = df[k].fillna(0).round(0)
            k = "p_inc100k_{}".format(d)
            df[k] = df[k].fillna(0).round(0)

            df.rename(
                columns={
                    "p_inc100k_{}".format(d): "incidência {}".format(d),
                    "casos_{}".format(d): "casos notif. {}".format(d),
                    "casos_est_{}".format(d): "casos est. {}".format(d),
                    "p_rt1_{}".format(d): "pr(incid. subir) {}".format(d),
                },
                inplace=True,
            )

        df.n_tweets = df.n_tweets.fillna(0).round(0)

        return df.rename(
            columns={
                "umid_max": "umid.max",
                "temp_min": "temp.min",
                "n_tweets": "tweets",
            }
        )
