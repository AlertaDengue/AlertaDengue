"""Read-only Django ORM lookups for retained ``Dengue_global`` objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.cache import cache
from django.db.models import Exists, OuterRef

from ad_main.typed_settings import get_query_cache_timeout
from dados.models import City, Parameter, Regional

CID10_CODES = {"dengue": "A90", "chikungunya": "A92.0", "zika": "A928"}


@dataclass(frozen=True, slots=True)
class ReportParameters:
    """Disease-specific parameters used by city reports."""

    cid10: str
    municipio_geocodigo: int
    varcli: Any
    clicrit: Any
    varcli2: Any
    clicrit2: Any
    limiar_preseason: Any
    limiar_posseason: Any
    limiar_epidemico: Any


def get_regional_names(state_name: str) -> list[str]:
    """Return parameterized regional names for a state.

    Parameters
    ----------
    state_name
        State name used by the retained municipality table.
    """
    cache_name = f"regional_names_to_{state_name.replace(' ', '_')}"
    cached = cache.get(cache_name)
    if cached is not None:
        return cached

    parameterized_cities = Parameter.objects.filter(
        municipality_geocode=OuterRef("geocode")
    )
    regional_ids = (
        City.objects.filter(state=state_name)
        .filter(Exists(parameterized_cities))
        .values("regional_id")
    )
    names = list(
        Regional.objects.filter(id__in=regional_ids)
        .order_by("name")
        .values_list("name", flat=True)
    )
    cache.set(cache_name, names, get_query_cache_timeout())
    return names


def get_cities(
    regional_name: str | None = None,
    state_name: str | None = None,
) -> dict[int, str]:
    """Return a name-ordered mapping of municipality geocodes to names."""
    if state_name is None:
        return {}

    if regional_name is None:
        cache_name = f"all_cities_from_{state_name.replace(' ', '_')}"
        queryset = City.objects.filter(state=state_name)
    else:
        cache_name = (
            f"{regional_name.replace(' ', '_')}_{state_name.replace(' ', '_')}"
        )
        parameterized_cities = Parameter.objects.filter(
            municipality_geocode=OuterRef("geocode")
        )
        regional_ids = Regional.objects.filter(name=regional_name).values("id")
        queryset = City.objects.filter(
            state=state_name, regional_id__in=regional_ids
        ).filter(Exists(parameterized_cities))

    cached = cache.get(cache_name)
    if cached is not None:
        return cached

    cities = {
        int(geocode): str(name)
        for geocode, name in queryset.order_by("name").values_list(
            "geocode", "name"
        )
    }
    cache.set(cache_name, cities, get_query_cache_timeout())
    return cities


def get_report_parameters(
    municipality_geocode: int, disease: str
) -> ReportParameters | None:
    """Return one city/disease parameter record using both key components.

    Parameters
    ----------
    municipality_geocode
        IBGE municipality geocode.
    disease
        Supported normalized disease name.
    """
    cid10_code = CID10_CODES.get(disease)
    if cid10_code is None:
        return None

    record = (
        Parameter.objects.filter(
            municipality_geocode=municipality_geocode,
            cid10_code=cid10_code,
        )
        .values(
            "cid10_code",
            "municipality_geocode",
            "baseline_variation",
            "baseline_critical",
            "secondary_variation",
            "secondary_critical",
            "preseason_threshold",
            "postseason_threshold",
            "epidemic_threshold",
        )
        .first()
    )
    if record is None:
        return None

    return ReportParameters(
        cid10=str(record["cid10_code"]),
        municipio_geocodigo=int(record["municipality_geocode"]),
        varcli=record["baseline_variation"],
        clicrit=record["baseline_critical"],
        varcli2=record["secondary_variation"],
        clicrit2=record["secondary_critical"],
        limiar_preseason=record["preseason_threshold"],
        limiar_posseason=record["postseason_threshold"],
        limiar_epidemico=record["epidemic_threshold"],
    )


def get_regional_municipalities(state_name: str) -> list[dict[str, Any]]:
    """Return stable regional-report rows for a state.

    The serialized rows let the legacy report adapter retain its DataFrame
    output without caching a lazy queryset.
    """
    return list(
        City.objects.filter(state=state_name)
        .order_by("geocode")
        .values(
            "regional_id",
            "regional_name",
            "geocode",
            "name",
        )
    )
