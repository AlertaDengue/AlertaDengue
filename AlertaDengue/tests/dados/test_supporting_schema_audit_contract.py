"""Stable ORM contracts for the supporting-schema audit."""

import pytest

from dados.models import EpiscannerSirParams
from manager.router import DatabaseAppsRouter


def test_episcanner_adapter_contract() -> None:
    """The existing EpiScanner table remains a managed dados adapter."""
    assert EpiscannerSirParams._meta.db_table == '"episcanner"."sir_params"'
    assert EpiscannerSirParams._meta.managed is True
    assert EpiscannerSirParams._meta.get_field("id").primary_key
    assert EpiscannerSirParams._meta.get_field("geocode").column == "geocode"
    assert {
        tuple(c.fields) for c in EpiscannerSirParams._meta.constraints
    } == {("cid10", "geocode", "year")}


@pytest.mark.parametrize("operation", ["read", "write"])
def test_episcanner_routes_through_dados(operation: str) -> None:
    """The repository router selects the dados alias for this model."""
    router = DatabaseAppsRouter()
    route = (
        router.db_for_read(EpiscannerSirParams)
        if operation == "read"
        else router.db_for_write(EpiscannerSirParams)
    )
    assert route == "dados"


def test_weather_and_vegetation_have_no_django_adapters() -> None:
    """Supporting relations remain outside the ORM boundary."""
    from dados import models

    assert not hasattr(models, "Weather")
    assert not hasattr(models, "VegetationIndexMetrics")
