"""
Tests for RegionalParameters class in dbdata.py.

Covers the composite PK (municipio_geocodigo, cid10) parameters table
and verifies that disease-specific filtering returns correct thresholds.
"""

from __future__ import annotations

from django.core.cache import cache
import pytest

from dados.dbdata import RegionalParameters

pytestmark = pytest.mark.usefixtures("regional_parameters_tables")


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def test_get_regional_names() -> None:
    """Test get_regional_names returns correct list of active names."""
    names = RegionalParameters.get_regional_names("RJ")
    assert "Metropolitana I" in names
    assert "Metropolitana II" in names
    assert len(names) == 2


def test_get_cities_by_state() -> None:
    """Test get_cities returns all cities in state when no region specified."""
    cities = RegionalParameters.get_cities(state_name="RJ")
    assert 3304557 in cities
    assert cities[3304557] == "Rio de Janeiro"
    assert 3303302 in cities
    assert cities[3303302] == "Niterói"


def test_get_cities_by_region() -> None:
    """Test get_cities returns cities only in specified region."""
    cities = RegionalParameters.get_cities(
        regional_name="Metropolitana I", state_name="RJ"
    )
    assert 3304557 in cities  # Rio is in Metro I
    assert 3303302 not in cities  # Niteroi is in Metro II (in our mock data)


def test_get_report_parameters() -> None:
    """Test get_report_parameters returns climate and disease thresholds."""
    params = RegionalParameters.get_report_parameters(3304557, "dengue")

    assert params is not None
    assert params.municipio_geocodigo == 3304557
    assert params.varcli == "p_rt1"
    assert params.varcli2 == "temp_min"
    assert params.limiar_preseason == 100
    assert params.limiar_epidemico == 300


class TestDiseaseFilterParameters:
    """Verify disease-specific parameter selection."""

    def test_disease_thresholds_differ(self) -> None:
        dengue = RegionalParameters.get_report_parameters(3304557, "dengue")
        chik = RegionalParameters.get_report_parameters(3304557, "chikungunya")

        assert dengue is not None
        assert chik is not None
        assert dengue.cid10 == "A90"
        assert chik.cid10 == "A92.0"
        assert dengue.limiar_preseason == 100
        assert chik.limiar_preseason == 25
        assert dengue.limiar_epidemico == 300
        assert chik.limiar_epidemico == 75

    def test_niteroi_thresholds(self) -> None:
        params = RegionalParameters.get_report_parameters(
            3303302, "chikungunya"
        )

        assert params is not None
        assert params.cid10 == "A92.0"
        assert params.municipio_geocodigo == 3303302
        assert params.limiar_preseason == 50
        assert params.limiar_posseason == 40
        assert params.limiar_epidemico == 150

    def test_nonexistent_disease_returns_none(self) -> None:
        assert (
            RegionalParameters.get_report_parameters(3304557, "zika") is None
        )

    def test_regional_names_not_duplicated(self) -> None:
        assert len(RegionalParameters.get_regional_names("RJ")) == 2

    def test_cities_not_duplicated(self) -> None:
        cities = RegionalParameters.get_cities(state_name="RJ")

        assert len(cities) == 2
        assert 3304557 in cities
        assert 3303302 in cities
