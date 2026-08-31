"""Bounded ORM lookups for municipality map metadata."""

from __future__ import annotations

from typing import Any

from django.db.models import F

from dados.models import City


def get_city_info(geocode: int) -> dict[str, Any]:
    """Return scalar municipality metadata for one geocode.

    Geometry, GeoJSON, and geofile workflows remain outside this boundary.
    """
    record = (
        City.objects.using("dados")
        .filter(geocode=geocode)
        .values(
            geocodigo=F("geocode"),
            nome=F("name"),
            populacao=F("population"),
            uf=F("state"),
        )
        .first()
    )
    if record is None:
        raise ValueError(f"Municipio not found for geocodigo={geocode}")

    return dict(record)
