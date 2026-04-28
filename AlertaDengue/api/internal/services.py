# api/internal/services.py

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pandas as pd
from django.db import connection

from .schemas import NotificationQueryParams


def normalize_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, Decimal):
        if not value.is_finite():
            return None
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return value


def dataframe_to_json_records(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    dataframe = dataframe.astype(object)

    return [
        {key: normalize_value(value) for key, value in row.items()}
        for row in dataframe.to_dict(orient="records")
    ]


def list_notifications(query_params: dict[str, Any]) -> dict[str, Any]:
    params = NotificationQueryParams.model_validate(
        query_params.dict() if hasattr(query_params, "dict") else query_params
    )

    fields = [
        "id",
        "municipio_geocodigo",
        "dt_notific",
        "dt_sin_pri",
        "dt_digita",
        "se_notif",
        "ano_notif",
        "classi_fin",
        "criterio",
        "cid10_codigo",
        "id_distrit",
        "id_bairro",
        "nm_bairro",
        "nu_notific",
    ]

    where_clauses = []
    sql_params: dict[str, Any] = {}

    if params.municipio_geocodigo is not None:
        where_clauses.append("municipio_geocodigo = %(municipio_geocodigo)s")
        sql_params["municipio_geocodigo"] = params.municipio_geocodigo

    if params.cid10:
        where_clauses.append("cid10_codigo = %(cid10)s")
        sql_params["cid10"] = params.cid10

    if params.year is not None:
        where_clauses.append("ano_notif = %(year)s")
        sql_params["year"] = params.year

    if params.epiweek_start is not None:
        where_clauses.append("se_notif >= %(epiweek_start)s")
        sql_params["epiweek_start"] = params.epiweek_start

    if params.epiweek_end is not None:
        where_clauses.append("se_notif <= %(epiweek_end)s")
        sql_params["epiweek_end"] = params.epiweek_end

    if params.date_start:
        where_clauses.append("dt_notific >= %(date_start)s")
        sql_params["date_start"] = params.date_start

    if params.date_end:
        where_clauses.append("dt_notific <= %(date_end)s")
        sql_params["date_end"] = params.date_end

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sql_results = f"""
        SELECT {", ".join(fields)}
        FROM "Municipio"."Notificacao"
        {where_sql}
        ORDER BY dt_notific DESC, id DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """

    sql_params["limit"] = params.limit
    sql_params["offset"] = params.offset

    results_df = pd.read_sql_query(
        sql_results,
        connection,
        params=sql_params,
    )

    payload = {
        "limit": params.limit,
        "offset": params.offset,
        "results": dataframe_to_json_records(results_df),
    }

    if params.include_count:
        sql_count = f"""
            SELECT COUNT(*)
            FROM "Municipio"."Notificacao"
            {where_sql}
        """

        count_params = {
            key: value
            for key, value in sql_params.items()
            if key not in {"limit", "offset"}
        }

        with connection.cursor() as cursor:
            cursor.execute(sql_count, count_params)
            count = cursor.fetchone()[0]

        payload["count"] = int(count)

    return payload
