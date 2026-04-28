# api/internal/services.py

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import connection

from .schemas import NotificationQueryParams


def normalize_value(value: Any) -> Any:
    if value is None:
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


def fetch_dicts(cursor) -> list[dict[str, Any]]:
    columns = [column[0] for column in cursor.description]

    return [
        {
            column: normalize_value(value)
            for column, value in zip(columns, row, strict=True)
        }
        for row in cursor.fetchall()
    ]


def build_notification_filters(
    params: NotificationQueryParams,
) -> tuple[str, dict[str, Any]]:
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

    if not where_clauses:
        return "", sql_params

    return f"WHERE {' AND '.join(where_clauses)}", sql_params


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

    where_sql, sql_params = build_notification_filters(params)

    sql_results = f"""
        SELECT {", ".join(fields)}
        FROM "Municipio"."Notificacao"
        {where_sql}
        ORDER BY dt_notific DESC, id DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """

    sql_params["limit"] = params.limit
    sql_params["offset"] = params.offset

    with connection.cursor() as cursor:
        cursor.execute(sql_results, sql_params)
        results = fetch_dicts(cursor)

    payload: dict[str, Any] = {
        "limit": params.limit,
        "offset": params.offset,
        "results": results,
    }

    if params.include_count:
        count_params = {
            key: value
            for key, value in sql_params.items()
            if key not in {"limit", "offset"}
        }

        sql_count = f"""
            SELECT COUNT(*)
            FROM "Municipio"."Notificacao"
            {where_sql}
        """

        with connection.cursor() as cursor:
            cursor.execute(sql_count, count_params)
            count = cursor.fetchone()[0]

        payload["count"] = int(count)

    return payload
