"""Database helpers for epidemiological data in AlertaDengue."""

from __future__ import annotations

import json
import logging
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from functools import lru_cache
from typing import (
    Any,
    Callable,
    Final,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
)

import numpy as np
import pandas as pd
import psycopg2
from django.conf import settings
from django.core.cache import cache
from django.utils.text import slugify
from epiweeks import Week
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine, Row

# local
from .episem import episem

logger = logging.getLogger(__name__)


CID10 = {"dengue": "A90", "chikungunya": "A92.0", "zika": "A928"}
DISEASES_SHORT = ["dengue", "chik", "zika"]
DISEASES_NAME = CID10.keys()
ALERT_COLOR = {1: "verde", 2: "amarelo", 3: "laranja", 4: "vermelho"}
ALERT_CODE = dict(zip(ALERT_COLOR.values(), ALERT_COLOR.keys()))

ALL_STATE_NAMES = {
    "AC": ["Acre", [-8.77, -70.55], 6],
    "AL": ["Alagoas", [-9.71, -35.73], 6],
    "AM": ["Amazonas", [-3.07, -61.66], 6],
    "AP": ["Amapá", [1.41, -51.77], 6],
    "BA": ["Bahia", [-12.96, -38.51], 6],
    "CE": ["Ceará", [-3.71, -38.54], 6],
    "DF": ["Distrito Federal", [-15.83, -47.86], 6],
    "ES": ["Espírito Santo", [-19.19, -40.34], 6],
    "GO": ["Goiás", [-16.64, -49.31], 6],
    "MA": ["Maranhão", [-2.55, -44.3], 6],
    "MG": ["Minas Gerais", [-18.1, -44.38], 6],
    "MS": ["Mato Grosso do Sul", [-20.51, -54.54], 6],
    "MT": ["Mato Grosso", [-12.64, -55.42], 6],
    "PA": ["Pará", [-5.53, -52.29], 6],
    "PB": ["Paraíba", [-7.06, -35.55], 6],
    "PE": ["Pernambuco", [-8.28, -35.07], 6],
    "PI": ["Piauí", [-8.28, -43.68], 6],
    "PR": ["Paraná", [-24.89, -51.55], 6],
    "RJ": ["Rio de Janeiro", [-22.84, -43.15], 6],
    "RN": ["Rio Grande do Norte", [-5.22, -36.52], 6],
    "RO": ["Rondônia", [-11.22, -62.8], 6],
    "RR": ["Roraima", [1.89, -61.22], 6],
    "RS": ["Rio Grande do Sul", [-30.01, -51.22], 6],
    "SC": ["Santa Catarina", [-27.33, -49.44], 6],
    "SE": ["Sergipe", [-10.9, -37.07], 6],
    "SP": ["São Paulo", [-23.55, -46.64], 6],
    "TO": ["Tocantins", [-10.25, -48.25], 6],
}

STATE_NAME = {k: v[0] for k, v in ALL_STATE_NAMES.items()}
STATE_INITIAL = dict(zip(STATE_NAME.values(), STATE_NAME.keys()))
MAP_CENTER = {k: v[1] for k, v in ALL_STATE_NAMES.items()}
MAP_ZOOM = {k: v[2] for k, v in ALL_STATE_NAMES.items()}

with open(settings.PROJECT_ROOT / "data" / "municipalities.json", "r") as muns:
    _mun_decoded = muns.read().encode().decode("utf-8-sig")
    MUNICIPALITIES = json.loads(_mun_decoded)

DB_ENGINE = settings.DB_ENGINE

T = TypeVar("T")

HIST_UF_MATERIALIZED_VIEWS: Final[dict[str, str]] = {
    "dengue": "hist_uf_dengue_materialized_view",
    "chik": "hist_uf_chik_materialized_view",
    "chikungunya": "hist_uf_chik_materialized_view",
    "zika": "hist_uf_zika_materialized_view",
}


def _read_sql_df(
    engine: Engine,
    sql: str,
    params: dict[str, object],
) -> pd.DataFrame:
    """Execute a SQL query and return a pandas DataFrame."""
    stmt = text(sql)
    with engine.connect() as conn:
        result = conn.execute(stmt, params)
        columns = list(result.keys())
        rows: Sequence[Row] = result.fetchall()
    return pd.DataFrame(rows, columns=columns)


def data_hist_uf(state_abbv: str, disease: str = "dengue") -> pd.DataFrame:
    """Load historical series by UF from a materialized view (cached)."""
    cache_name = f"data_hist_{state_abbv}_{disease}"
    res = cache.get(cache_name)
    if res is not None:
        return res

    view = HIST_UF_MATERIALIZED_VIEWS.get(disease)
    if view is None:
        raise ValueError(f"Unsupported disease: {disease!r}")

    sql = (
        f"SELECT * "
        f"FROM {view} "
        f"WHERE state_abbv = :state_abbv "
        f'ORDER BY "SE" DESC'
    )
    res = _read_sql_df(
        DB_ENGINE,
        sql,
        params={"state_abbv": state_abbv},
    )

    cache.set(cache_name, res, settings.QUERY_CACHE_TIMEOUT)
    return res


class RegionalParameters:
    """Helpers to query regional parameters via SQL."""

    SCHEMA: str = "Dengue_global"

    @classmethod
    def get_regional_names(cls, state_name: str) -> list[str]:
        """
        Return list of regional names for a given state.

        Parameters
        ----------
        state_name
            State acronym (UF), e.g. "RJ".

        Returns
        -------
        list[str]
            Regional names.
        """
        cache_name = f"regional_names_to_{state_name.replace(' ', '_')}"
        cached = cache.get(cache_name)
        if cached is not None:
            return cached

        sql = f"""
            SELECT DISTINCT r.nome
            FROM "{cls.SCHEMA}"."regional" AS r
            JOIN "{cls.SCHEMA}"."Municipio" AS m ON r.id = m.id_regional
            JOIN "{cls.SCHEMA}"."parameters" AS p ON m.geocodigo = p.municipio_geocodigo
            WHERE m.uf = :state_name
        """

        df = _read_sql_df(
            DB_ENGINE,
            sql,
            params={"state_name": state_name},
        )

        res = df["nome"].tolist()
        cache.set(cache_name, res, settings.QUERY_CACHE_TIMEOUT)
        return res

    @classmethod
    def get_var_climate_info(cls, geocodes: list[int]) -> tuple[str, str]:
        """
        Return (codigo_estacao_wu, varcli) for the first matching geocode.
        """
        if not geocodes:
            pass

        sql = f"""
            SELECT DISTINCT codigo_estacao_wu, varcli
            FROM "{cls.SCHEMA}"."parameters"
            WHERE municipio_geocodigo IN :geocodes
        """

        df = _read_sql_df(
            DB_ENGINE,
            sql,
            params={"geocodes": tuple(geocodes)},
        )

        if df.empty:
            raise IndexError("No climate info found for provided geocodes")

        row = df.to_records(index=False).tolist()[0]
        return (str(row[0]), str(row[1]))

    @classmethod
    def get_cities(
        cls,
        regional_name: str | None = None,
        state_name: str | None = None,
    ) -> dict[int, str]:
        """
        Return mapping geocode -> city name for a region or state.
        """
        cities_by_region: dict[int, str] = {}
        if state_name is None:
            return cities_by_region

        if regional_name is not None:
            cache_name = (
                f"{regional_name.replace(' ', '_')}_"
                f"{state_name.replace(' ', '_')}"
            )
            cached = cache.get(cache_name)
            if cached is not None:
                return cached

            sql = f"""
                SELECT m.geocodigo, m.nome
                FROM "{cls.SCHEMA}"."Municipio" AS m
                JOIN "{cls.SCHEMA}"."regional" AS r ON m.id_regional = r.id
                JOIN "{cls.SCHEMA}"."parameters" AS p ON m.geocodigo = p.municipio_geocodigo
                WHERE m.uf = :state_name AND r.nome = :regional_name
                ORDER BY m.nome
            """

            df = _read_sql_df(
                DB_ENGINE,
                sql,
                params={
                    "state_name": state_name,
                    "regional_name": regional_name,
                },
            )

            for row in df.itertuples(index=False):
                cities_by_region[int(row.geocodigo)] = str(row.nome)

            cache.set(
                cache_name, cities_by_region, settings.QUERY_CACHE_TIMEOUT
            )
            return cities_by_region

        cache_name = f"all_cities_from_{state_name.replace(' ', '_')}"
        cached = cache.get(cache_name)
        if cached is not None:
            return cached

        sql = f"""
            SELECT geocodigo, nome
            FROM "{cls.SCHEMA}"."Municipio"
            WHERE uf = :state_name
            ORDER BY nome
        """

        df = _read_sql_df(
            DB_ENGINE,
            sql,
            params={"state_name": state_name},
        )

        for row in df.itertuples(index=False):
            cities_by_region[int(row.geocodigo)] = str(row.nome)

        cache.set(cache_name, cities_by_region, settings.QUERY_CACHE_TIMEOUT)
        return cities_by_region

    @classmethod
    def get_station_data(cls, geocode: int, disease: str) -> tuple[Any, ...]:
        """
        Return climate thresholds for a geocode and disease.
        """
        cid10_code = CID10.get(disease, "")

        sql = f"""
            SELECT 
                cid10,
                municipio_geocodigo,
                codigo_estacao_wu,
                varcli,
                clicrit,
                varcli2,
                clicrit2,
                limiar_preseason,
                limiar_posseason,
                limiar_epidemico
            FROM "{cls.SCHEMA}"."parameters"
            WHERE cid10 = :cid10_code 
              AND municipio_geocodigo = :geocode
        """

        df = _read_sql_df(
            DB_ENGINE,
            sql,
            params={"cid10_code": cid10_code, "geocode": geocode},
        )

        return tuple(df.values)


# General util functions
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
    return episem(dt, sep="")


def normalize_str(string: str) -> str:
    """
    São Tomé -> sao tome
    """
    non_ascii = (
        unicodedata.normalize("NFKD", string)
        .encode("ascii", "ignore")
        .decode()
    )
    string = non_ascii.lower()
    return string


def get_disease_suffix(
    disease: Literal["dengue", "zika", "chikungunya"],
    empty_for_dengue: bool = True,
):
    """
    :param disease:
    :return:
    """
    return (
        ("" if empty_for_dengue else "_dengue")
        if disease == "dengue"
        else "_chik"
        if disease == "chikungunya"
        else "_zika"
        if disease == "zika"
        else ""
    )


# TODO: check if this works and is necessary

'''
def get_city_name_by_id(geocode: int, db_engine: Engine) -> str:
    """
    Get the name of a city by its geocode.

    Parameters
    ----------
    geocode : int
        The geocode of the city.
    db_engine : Engine
        The database engine to use for the query.

    Returns
    -------
    str
        The name of the city.
    """

    with db_engine.connect() as conn:
        res = conn.execute(
            f"""
            SELECT nome
            FROM "Dengue_global"."Municipio"
            WHERE geocodigo={geocode};
        """
        )
        return res.fetchone()[0]

'''


def get_all_active_cities_state(
    db_engine: Engine = DB_ENGINE,
) -> list[tuple[int, object, str, str]]:
    """Return active cities with state info from recent alert history.

    Parameters
    ----------
    db_engine
        SQLAlchemy engine.

    Returns
    -------
    list[tuple[int, object, str, str]]
        Rows as returned by the query:
        (municipio_geocodigo, data_iniSE, nome, uf)
    """
    cache_key = "get_all_active_cities_state"
    cached = cache.get(cache_key)
    if cached is not None:
        return list(cached)

    stmt = text(
        """
        SELECT DISTINCT
            hist.municipio_geocodigo,
            hist."data_iniSE",
            city.nome,
            city.uf
        FROM "Municipio"."Historico_alerta" AS hist
        INNER JOIN "Dengue_global"."Municipio" AS city
            ON hist.municipio_geocodigo = city.geocodigo
        WHERE hist."data_iniSE" >= (
            SELECT MAX(h2."data_iniSE") - interval '52 weeks'
            FROM "Municipio"."Historico_alerta" AS h2
        )
        ORDER BY hist."data_iniSE";
        """
    )

    with db_engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()

    cache.set(cache_key, rows, settings.QUERY_CACHE_TIMEOUT)
    return list(rows)


def get_last_alert(geo_id, disease, db_engine: Engine = DB_ENGINE):
    """
    Get the last alert level for a specific municipality and disease.

    Parameters
    ----------
    geo_id : str
        The geocode of the municipality.
    disease : str
        The name of the disease.
    db_engine : sqlalchemy.engine.Engine, optional
        The database engine, defaults to DB_ENGINE.

    Returns
    -------
    pandas.DataFrame
        The last alert level for the specified municipality and disease.
    """

    table_name = "Historico_alerta" + get_disease_suffix(disease)

    sql = f"""
    SELECT nivel
    FROM "Municipio"."{table_name}"
    WHERE municipio_geocodigo={geo_id}
    ORDER BY "data_iniSE" DESC
    LIMIT 1
    """

    return pd.read_sql_query(sql, db_engine.raw_connection())


def get_last_SE(
    disease: str = "dengue", db_engine: Engine = DB_ENGINE
) -> Week:
    """Return the most recent epidemiological week for a disease.

    Parameters
    ----------
    disease
        Disease key (e.g. "dengue", "chikungunya", "zika").
    db_engine
        SQLAlchemy engine.

    Returns
    -------
    epiweeks.Week
        Most recent epidemiological week.

    Raises
    ------
    ValueError
        If the table has no rows.
    """
    table_name = f"Historico_alerta{get_disease_suffix(disease)}"
    stmt = text(
        f"""
        SELECT "SE"
        FROM "Municipio"."{table_name}"
        ORDER BY "data_iniSE" DESC
        LIMIT 1
        """
    )

    with db_engine.connect() as conn:
        row = conn.execute(stmt).first()

    if row is None:
        raise ValueError(f"No rows found for disease={disease!r}")

    return Week.fromstring(str(row[0]))


def load_cases_without_forecast(
    geocode: int,
    disease: str = "dengue",
    db_engine: Engine = DB_ENGINE,
) -> pd.DataFrame:
    """
    Load historical alert series without using forecast tables.

    Parameters
    ----------
    geocode
        Municipality geocode.
    disease
        Disease key.
    db_engine
        SQLAlchemy engine.

    Returns
    -------
    pandas.DataFrame
        Alert time series.
    """
    table_name = "Historico_alerta" + get_disease_suffix(disease)

    stmt = text(
        f"""
        SELECT *
        FROM "Municipio"."{table_name}"
        WHERE municipio_geocodigo = :geocode
        ORDER BY "data_iniSE" ASC
        """
    )

    with db_engine.connect() as conn:
        result = conn.execute(stmt, {"geocode": geocode})
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def load_series(
    cidade: int,
    disease: str = "dengue",
    epiweek: int | None = 0,
    db_engine: Engine = DB_ENGINE,
) -> dict:
    """
    Load alert series for visualization.

    Parameters
    ----------
    cidade
        Municipality geocode.
    disease
        Disease key.
    epiweek
        Epidemiological week. Use ``None`` or ``0`` to disable forecast.
    db_engine
        SQLAlchemy engine.

    Returns
    -------
    dict
        Mapping keyed by BOTH ``str(cidade)`` and ``cidade`` (int), for
        compatibility across callers.
    """
    cache_key = "load_series-{}-{}".format(cidade, disease)
    cached = cache.get(cache_key)

    key_str = str(cidade)
    key_int = int(cidade)

    if cached is not None:
        if key_int in cached:
            return cached
        if key_str in cached:
            result = dict(cached)
            result[key_int] = result[key_str]
            return result
        return cached

    use_forecast = isinstance(epiweek, int) and epiweek > 0

    if use_forecast:
        dados_alerta = Forecast.load_cases(
            geocode=cidade,
            disease=disease,
            epiweek=epiweek,
            db_engine=db_engine,
        )
    else:
        dados_alerta = load_cases_without_forecast(
            geocode=cidade,
            disease=disease,
            db_engine=db_engine,
        )

    if len(dados_alerta) == 0:
        result = {key_str: None}
        cache.set(cache_key, result, settings.QUERY_CACHE_TIMEOUT)
        return {key_str: None, key_int: None}

    series = defaultdict(lambda: defaultdict(list))

    series[key_str]["dia"] = dados_alerta.data_iniSE.tolist()
    series[key_str]["nivel"] = dados_alerta.nivel.tolist()
    series[key_str]["casos_est_min"] = _nan_to_num_int_list(
        dados_alerta.casos_est_min
    )
    series[key_str]["casos_est"] = _nan_to_num_int_list(dados_alerta.casos_est)
    series[key_str]["casos_est_max"] = _nan_to_num_int_list(
        dados_alerta.casos_est_max
    )
    series[key_str]["casos"] = _nan_to_num_int_list(dados_alerta.casos)

    series[key_str]["alerta"] = (
        dados_alerta.nivel.fillna(1).astype(int) - 1
    ).tolist()
    series[key_str]["SE"] = dados_alerta.SE.astype(int).tolist()
    series[key_str]["prt1"] = dados_alerta.p_rt1.astype(float).tolist()

    for k in [k for k in dados_alerta.keys() if k.startswith("forecast_")]:
        series[key_str][k] = dados_alerta[k].astype(float).tolist()

    payload = {key_str: dict(series[key_str])}
    cache.set(cache_key, payload, settings.QUERY_CACHE_TIMEOUT)

    result = dict(payload)
    result[key_int] = result[key_str]
    return result


def get_city_alert(cidade, disease="dengue"):
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

    alert = series_city["alerta"][-1]
    SE = series_city["SE"][-1]
    case_series = series_city["casos_est"]
    nivel = series_city["nivel"]
    last_year = (
        series_city["casos"][-52] if len(series_city["casos"]) >= 52 else None
    )

    obs_case_series = series_city["casos"]
    min_max_est = (
        series_city["casos_est_min"][-1],
        series_city["casos_est_max"][-1],
    )
    dia = series_city["dia"][-1]
    prt1 = np.mean(series_city["prt1"][-3:])

    return (
        alert,
        SE,
        case_series,
        nivel,
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


@np.vectorize
def add_dv(geocodigo):
    """
    Retorna o geocóodigo do município adicionando o digito verificador,
    se necessário.
    :param geocodigo: geocóodigo com 6 ou 7 dígitos
    """

    miscalculated_geocodes = {
        "2201911": 2201919,
        "2201986": 2201988,
        "2202257": 2202251,
        "2611531": 2611533,
        "3117835": 3117836,
        "3152139": 3152131,
        "4305876": 4305871,
        "5203963": 5203962,
        "5203930": 5203939,
    }

    if len(str(geocodigo)) == 7:
        return geocodigo

    if len(str(geocodigo)) == 6:
        geocode = int(str(geocodigo) + str(calculate_digit(geocodigo)))
        if str(geocode) in miscalculated_geocodes:
            return miscalculated_geocodes[str(geocode)]
        return geocode

    raise ValueError("geocode does not match!")


def get_epiyears(
    state_name: str,
    disease: Optional[str] = None,
    db_engine: Engine = DB_ENGINE,
) -> List[Tuple]:
    """
    Retrieve epidemiological years data from the database.

    Parameters:
    state_name (str): Name of the state.
    disease (Optional[str]): Disease name, defaults to None.
    db_engine (Engine): Database engine, defaults to DB_ENGINE.

    Returns:
    List[Tuple]: List of tuples containing the retrieved data.
    """
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
        result = conn.execute(text(sql_text_query), parameters)
        data = [tuple(row) for row in result.fetchall()]
    return data


class NotificationResume:
    @staticmethod
    def count_cities_by_uf(
        uf: str,
        disease: str = "dengue",
        db_engine: Engine = DB_ENGINE,
    ) -> int:
        """Return number of cities for a UF and disease from a materialized view.

        Parameters
        ----------
        uf
            UF (e.g. "RJ").
        disease
            Disease key (e.g. "dengue").
        db_engine
            SQLAlchemy engine.

        Returns
        -------
        int
            City count (0 if missing / error).
        """
        view_name = f"public.city_count_by_uf_{disease}_materialized_view"
        stmt = text(
            f"""
            SELECT city_count
            FROM {view_name}
            WHERE uf = :uf
            """
        )

        try:
            with db_engine.connect() as conn:
                row = conn.execute(stmt, {"uf": uf}).fetchone()
            return int(row[0]) if row else 0
        except Exception:
            logger.exception(
                "count_cities_by_uf failed (uf=%s, disease=%s)", uf, disease
            )
            return 0

    @staticmethod
    def get_cities_alert_by_state(
        state_name: str,
        disease: str = "dengue",
        db_engine: Engine = DB_ENGINE,
        epi_year_week: int | None = None,
    ) -> pd.DataFrame:
        """Return city-level alert indicators for a given state and disease.

        Parameters
        ----------
        state_name
            State name (UF).
        disease
            One of: dengue, chikungunya, zika.
        db_engine
            SQLAlchemy engine.
        epi_year_week
            If provided, filters by epidemiological year-week.

        Returns
        -------
        pandas.DataFrame
            Columns: municipio_geocodigo, nome, data_iniSE, level_alert
            with id as index.
        """
        _disease = get_disease_suffix(disease)
        cache_key = (
            f"cities_alert_{slugify(state_name, allow_unicode=True)}_{disease}"
        )
        cities_alert = cache.get(cache_key)

        if cities_alert is not None:
            logger.info("Cache found for key: %s", cache_key)
            return cities_alert

        logger.info("Cache NOT found for key: %s", cache_key)

        hist_table = f'"Municipio"."Historico_alerta{_disease}"'

        sql_parts: list[str] = [
            f"""
            SELECT
                hist_alert.id,
                hist_alert.municipio_geocodigo,
                municipio.nome,
                hist_alert."data_iniSE",
                (hist_alert.nivel - 1) AS level_alert
            FROM {hist_table} AS hist_alert
            INNER JOIN "Dengue_global"."Municipio" AS municipio
                ON hist_alert.municipio_geocodigo = municipio.geocodigo
            """
        ]

        params: dict[str, Any] = {"uf": state_name}

        if epi_year_week is None:
            sql_parts.append(
                f"""
                INNER JOIN (
                    SELECT
                        alerta.municipio_geocodigo AS geocodigo,
                        MAX(alerta."data_iniSE") AS "data_iniSE"
                    FROM {hist_table} AS alerta
                    INNER JOIN "Dengue_global"."Municipio" AS mun2
                        ON alerta.municipio_geocodigo = mun2.geocodigo
                    WHERE mun2.uf = :uf
                    GROUP BY alerta.municipio_geocodigo
                ) AS recent_alert
                    ON recent_alert.geocodigo = hist_alert.municipio_geocodigo
                   AND recent_alert."data_iniSE" = hist_alert."data_iniSE"
                WHERE municipio.uf = :uf
                """
            )
        else:
            sql_parts.append(
                """
                WHERE hist_alert."SE" = :epi_year_week
                  AND municipio.uf = :uf
                """
            )
            params["epi_year_week"] = epi_year_week

        sql = "\n".join(sql_parts)

        with db_engine.connect() as conn:
            result = conn.execute(text(sql), params)
            rows = result.mappings().all()

        cities_alert = pd.DataFrame.from_records(rows)
        cities_alert = cities_alert.reindex(
            columns=[
                "id",
                "municipio_geocodigo",
                "nome",
                "data_iniSE",
                "level_alert",
            ]
        )

        if not cities_alert.empty:
            cities_alert["data_iniSE"] = pd.to_datetime(
                cities_alert["data_iniSE"],
                errors="coerce",
            )
            cities_alert = cities_alert.set_index("id")

        cache.set(cache_key, cities_alert, settings.QUERY_CACHE_TIMEOUT)
        logger.info("Cache set for key: %s", cache_key)

        return cities_alert

    @staticmethod
    def tail_estimated_cases(
        geo_ids: list[int],
        n: int = 12,
        db_engine: Engine = DB_ENGINE,
    ) -> pd.DataFrame:
        """Fetch the last `n` estimated cases rows per municipality.

        Parameters
        ----------
        geo_ids
            Municipality geocodes.
        n
            Number of weeks to fetch per municipality.
        db_engine
            SQLAlchemy engine.

        Returns
        -------
        pandas.DataFrame
            Columns: municipio_geocodigo, data_iniSE, casos_est
        """
        if not geo_ids:
            return pd.DataFrame(
                columns=["municipio_geocodigo", "data_iniSE", "casos_est"]
            )

        stmt = text(
            """
            SELECT municipio_geocodigo, "data_iniSE", casos_est
            FROM (
                SELECT
                    municipio_geocodigo,
                    "data_iniSE",
                    casos_est,
                    row_number() OVER (
                        PARTITION BY municipio_geocodigo
                        ORDER BY "data_iniSE" DESC
                    ) AS rn
                FROM "Municipio".historico_casos
                WHERE municipio_geocodigo IN :geo_ids
            ) t
            WHERE rn <= :n
            ORDER BY municipio_geocodigo, "data_iniSE"
            """
        ).bindparams(bindparam("geo_ids", expanding=True))

        with db_engine.connect() as conn:
            result = conn.execute(stmt, {"geo_ids": geo_ids, "n": n})
            rows = result.fetchall()

        df = pd.DataFrame(rows, columns=result.keys())
        if not df.empty:
            df["data_iniSE"] = pd.to_datetime(
                df["data_iniSE"], errors="coerce"
            )
        return df


class Forecast:
    @staticmethod
    def get_min_max_date(
        geocode: int,
        cid10: str,
        db_engine: Engine = DB_ENGINE,
    ) -> tuple[str | None, str | None]:
        """
        Retrieve the minimum and maximum forecast epiweek dates.

        If the `forecast.*` tables have no matching rows (or are empty), this
        returns (None, None) so callers can disable forecast logic cleanly.

        Parameters
        ----------
        geocode
            Municipality geocode.
        cid10
            Disease code (CID10).
        db_engine
            SQLAlchemy engine.

        Returns
        -------
        tuple[str | None, str | None]
            Minimum and maximum dates as 'YYYY-MM-DD' strings, or (None, None)
            when there is no forecast data.
        """
        stmt = text(
            """
            SELECT
                TO_CHAR(MIN(f.init_date_epiweek), 'YYYY-MM-DD') AS epiweek_min,
                TO_CHAR(MAX(f.init_date_epiweek), 'YYYY-MM-DD') AS epiweek_max
            FROM forecast.forecast_cases AS f
            INNER JOIN forecast.forecast_city AS fc
                ON f.geocode = fc.geocode AND fc.active = TRUE
            INNER JOIN forecast.forecast_model AS fm
                ON fc.forecast_model_id = fm.id AND fm.active = TRUE
            WHERE f.geocode = :geocode
              AND f.cid10 = :cid10
            """
        )

        with db_engine.connect() as connection:
            row = connection.execute(
                stmt,
                {"geocode": geocode, "cid10": cid10},
            ).fetchone()

        if row is None or row[0] is None or row[1] is None:
            return None, None

        return str(row[0]), str(row[1])

    @staticmethod
    def load_cases(
        geocode: int,
        disease: str,
        epiweek: int,
        db_engine: Engine = DB_ENGINE,
    ) -> pd.DataFrame:
        """
        Load alert series and (when available) attach forecast model columns.

        Parameters
        ----------
        geocode
            Municipality geocode.
        disease
            Disease key.
        epiweek
            Epidemiological week.
        db_engine
            SQLAlchemy engine.

        Returns
        -------
        pandas.DataFrame
            Alert + optional forecast columns.
        """
        cid10 = CID10[disease]

        stmt_models = text(
            """
            SELECT DISTINCT ON (fcases.forecast_model_id)
                fcases.forecast_model_id,
                fmodel.name AS forecast_model_name,
                fcases.published_date
            FROM forecast.forecast_cases AS fcases
            INNER JOIN forecast.forecast_model AS fmodel
                ON (fcases.forecast_model_id = fmodel.id)
            WHERE fcases.cid10 = :cid10
              AND fcases.geocode = :geocode
              AND fcases.epiweek = :epiweek
            ORDER BY fcases.forecast_model_id, fcases.published_date DESC
            """
        )

        with db_engine.connect() as conn:
            result = conn.execute(
                stmt_models,
                {"cid10": cid10, "geocode": geocode, "epiweek": epiweek},
            )
            df_forecast_model = pd.DataFrame(
                result.fetchall(),
                columns=result.keys(),
            )

        table_name = "Historico_alerta" + get_disease_suffix(disease)

        sql_alert = """
        SELECT * FROM "Municipio"."{}"
        WHERE municipio_geocodigo={} ORDER BY "data_iniSE" ASC
        """.format(
            table_name,
            geocode,
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

        sql_forecast_by_model = """
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
        """

        forecast_date_ini_epiweek = ""
        forecast_models_cases = ""
        forecast_models_joins = ""
        forecast_epiweek = ""

        forecast_config: dict[str, object] = {
            "geocode": geocode,
            "cid10": cid10,
            "published_date": None,
            "model_name": None,
            "model_id": None,
        }

        for _, row in df_forecast_model.iterrows():
            forecast_config.update(
                {
                    "published_date": row.published_date,
                    "model_name": row.forecast_model_name,
                    "model_id": row.forecast_model_id,
                }
            )

            forecast_models_joins += sql_forecast_by_model % forecast_config

            forecast_date_ini_epiweek += (
                """
            WHEN forecast%(model_id)s.init_date_epiweek IS NOT NULL
               THEN forecast%(model_id)s.init_date_epiweek
            """
                % forecast_config
            )

            forecast_epiweek += (
                """
            WHEN forecast%(model_id)s.epiweek IS NOT NULL
               THEN forecast%(model_id)s.epiweek
            """
                % forecast_config
            )

            forecast_models_cases += (
                ",forecast_%(model_name)s_cases" % forecast_config
            )

        if forecast_models_cases == "":
            forecast_models_cases = ",1"

        sql = sql % {
            "forecast_models_joins": forecast_models_joins,
            "forecast_models_cases": forecast_models_cases,
            "forecast_date_ini_epiweek": forecast_date_ini_epiweek,
            "forecast_epiweek": forecast_epiweek,
            "sql_alert": sql_alert,
        }

        with db_engine.connect() as conn:
            result = conn.execute(text(sql))
            return pd.DataFrame(result.fetchall(), columns=result.keys())


class ReportCity:
    @classmethod
    def read_disease_data(
        cls,
        disease: str,
        geocode: int,
        year_week: int,
    ) -> pd.DataFrame:
        """
        Return a DataFrame with the history for a given disease/city.
        """
        if disease not in CID10:
            raise ValueError(f"Unsupported disease: {disease!r}")

        table_suffix = ""
        if disease != "dengue":
            table_suffix = get_disease_suffix(disease)

        table_name = f"Historico_alerta{table_suffix}"

        ew_end = year_week
        ew_start = ew_end - 200

        # Note: SE is typically an integer YYYYWW. Subtracting 200 from it directly
        # (e.g. 202401 - 200 = 202201) works roughly but isn't chemically pure date math.
        # However, preserving the logic from original code: `ew_start = ew_end - 200`

        sql = f"""
            SELECT 
                "SE" AS "SE",
                casos AS "casos notif.",
                casos_est AS "casos_est",
                p_inc100k AS "incidência",
                p_rt1 AS "pr(incid. subir)",
                tempmin AS "temp.min",
                tempmed AS "temp.med",
                tempmax AS "temp.max",
                umidmin AS "umid.min",
                umidmed AS "umid.med",
                umidmax AS "umid.max",
                CASE 
                    WHEN nivel = 1 THEN 'verde'
                    WHEN nivel = 2 THEN 'amarelo'
                    WHEN nivel = 3 THEN 'laranja'
                    WHEN nivel = 4 THEN 'vermelho'
                    ELSE '-' 
                END AS nivel,
                nivel AS level_code
            FROM "Municipio"."{table_name}"
            WHERE 
                "SE" BETWEEN :ew_start AND :ew_end
                AND municipio_geocodigo = :geocode
            ORDER BY "SE"
            LIMIT 200
        """

        df = _read_sql_df(
            DB_ENGINE,
            sql,
            params={
                "ew_start": ew_start,
                "ew_end": ew_end,
                "geocode": geocode,
            },
        )
        return df.set_index("SE")


class ReportState:
    @classmethod
    def get_regional_by_state(cls, state: str) -> pd.DataFrame:
        """
        Import CSV file with the municipalities of regional health by state.
        Parameters
        ----------
            state: State abbreviation.
        Returns:
            df: df with the municipalities of the regionals filtered by state.
        """
        # TODO: Export CSV to JSON file: see #

        cache_name = "regional_by_state_" + "_" + str(state)
        res = cache.get(cache_name)

        if res is None:
            uf_name = ALL_STATE_NAMES[state][0]

            sql = f"""
                SELECT 
                    m.id_regional AS id_regional,
                    m.regional AS nome_regional,
                    m.geocodigo AS municipio_geocodigo,
                    m.nome AS municipio_nome
                FROM "Dengue_global"."Municipio" AS m
                WHERE m.uf = :uf_name
            """

            df = _read_sql_df(
                DB_ENGINE,
                sql,
                params={"uf_name": uf_name},
            )

            res = df
            cache.set(
                cache_name,
                res,
                settings.QUERY_CACHE_TIMEOUT,
            )

        return res

    @classmethod
    def create_report_state_data(
        cls,
        geocodes: list[int],
        disease: str,
        year_week: int,
    ) -> pd.DataFrame:
        """
        Return history for multiple cities for a given disease/state report.
        """
        if disease not in CID10:
            raise ValueError(f"Unsupported disease: {disease!r}")

        table_suffix = ""
        if disease != "dengue":
            table_suffix = get_disease_suffix(disease)

        table_name = f"Historico_alerta{table_suffix}"

        ew_start = year_week - 20

        # We need to construct the IN clause for geocodes.
        if not geocodes:
            return pd.DataFrame(
                columns=[
                    "SE",
                    "casos_est",
                    "casos",
                    "nivel",
                    "municipio_geocodigo",
                    "municipio_nome",
                ]
            )

        # Use parameterized query with tuple for IN clause

        sql = f"""
            SELECT
                h."SE",
                h.casos_est,
                h.casos,
                h.nivel,
                h.municipio_geocodigo,
                m.nome AS municipio_nome
            FROM "Municipio"."{table_name}" AS h
            JOIN "Dengue_global"."Municipio" AS m ON h.municipio_geocodigo = m.geocodigo
            WHERE 
                h."SE" BETWEEN :ew_start AND :ew_end
                AND h.municipio_geocodigo IN :geocodes
            ORDER BY h."SE"
        """

        df = _read_sql_df(
            DB_ENGINE,
            sql,
            params={
                "ew_start": ew_start,
                "ew_end": year_week,
                "geocodes": tuple(geocodes),
            },
        )
        return df
