from __future__ import annotations

from typing import Any, Final

import geojson
from django.conf import settings
from sqlalchemy import text
from sqlalchemy.engine import Engine

DB_ENGINE: Final[Engine] = settings.DB_ENGINE


def get_city_geojson(
    municipio: int,
    db_engine: Engine = DB_ENGINE,
) -> dict[str, Any]:
    """Fetch a municipality GeoJSON FeatureCollection from the database.

    Parameters
    ----------
    municipio
        Municipality geocode.
    db_engine
        SQLAlchemy engine.

    Returns
    -------
    dict[str, Any]
        A GeoJSON FeatureCollection with a single Feature, enriched with
        properties (geocodigo, nome, populacao).

    Raises
    ------
    ValueError
        If the municipality is not found or has no GeoJSON.
    """
    stmt = text(
        """
        SELECT geocodigo, nome, geojson, populacao, uf
        FROM "Dengue_global"."Municipio"
        WHERE geocodigo = :geocodigo
        """
    )

    with db_engine.connect() as conn:
        row = conn.execute(stmt, {"geocodigo": municipio}).mappings().first()

    if row is None:
        raise ValueError(f"Municipio not found for geocodigo={municipio}")

    geojson_str = row.get("geojson")
    if not geojson_str:
        raise ValueError(f"Missing geojson for geocodigo={municipio}")

    feature = geojson.loads(geojson_str)
    feature["type"] = "Feature"
    feature["properties"] = {
        "geocodigo": row["geocodigo"],
        "nome": row["nome"],
        "populacao": row["populacao"],
    }

    return {
        "type": "FeatureCollection",
        "features": [feature],
    }


def get_city_info(
    geocodigo: int,
    db_engine: Engine = DB_ENGINE,
) -> dict[str, Any]:
    """Fetch municipality metadata from the database.

    Parameters
    ----------
    geocodigo
        Municipality geocode.
    db_engine
        SQLAlchemy engine.

    Returns
    -------
    dict[str, Any]
        Municipality metadata (geocodigo, nome, populacao, uf).

    Raises
    ------
    ValueError
        If the municipality is not found.
    """
    stmt = text(
        """
        SELECT geocodigo, nome, populacao, uf
        FROM "Dengue_global"."Municipio"
        WHERE geocodigo = :geocodigo
        """
    )

    with db_engine.connect() as conn:
        row = conn.execute(stmt, {"geocodigo": geocodigo}).mappings().first()

    if row is None:
        raise ValueError(f"Municipio not found for geocodigo={geocodigo}")

    return dict(row)
