"""
Tests for RegionalParameters class in dbdata.py.

Covers the composite PK (municipio_geocodigo, cid10) parameters table
and verifies that disease-specific filtering returns correct thresholds.
"""
from __future__ import annotations

import pandas as pd
import pytest
from dados.dbdata import RegionalParameters
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


# ---------------------------------------------------------------------------
# Existing tests (updated for composite PK fixture data)
# ---------------------------------------------------------------------------


def test_get_regional_names(regional_parameters_tables: None) -> None:
    """Test get_regional_names returns correct list of active names."""
    names = RegionalParameters.get_regional_names("RJ")
    assert "Metropolitana I" in names
    assert "Metropolitana II" in names
    assert len(names) == 2


def test_get_var_climate_info(regional_parameters_tables: None) -> None:
    """Test get_var_climate_info returns correct tuple for geocode."""
    # 3304557 is Rio de Janeiro
    station, varcli = RegionalParameters.get_var_climate_info([3304557])
    assert station == "83743"
    assert varcli == "p_rt1"


def test_get_cities_by_state(regional_parameters_tables: None) -> None:
    """Test get_cities returns all cities in state when no region specified."""
    cities = RegionalParameters.get_cities(state_name="RJ")
    assert 3304557 in cities
    assert cities[3304557] == "Rio de Janeiro"
    assert 3303302 in cities
    assert cities[3303302] == "Niterói"


def test_get_cities_by_region(regional_parameters_tables: None) -> None:
    """Test get_cities returns cities only in specified region."""
    cities = RegionalParameters.get_cities(
        regional_name="Metropolitana I", state_name="RJ"
    )
    assert 3304557 in cities  # Rio is in Metro I
    assert 3303302 not in cities  # Niteroi is in Metro II (in our mock data)


def test_get_station_data(regional_parameters_tables: None) -> None:
    """Test get_station_data returns correct threshold values."""
    data = RegionalParameters.get_station_data(3304557, "dengue")
    # Expected tuple struct: (cid10, geocode, station, varcli, clicrit, varcli2, clicrit2, pre, pos, epid)
    assert len(data) > 0
    row = data[0]
    assert row[1] == 3304557
    assert row[2] == "83743"
    # Verify thresholds
    assert row[7] == 100  # pre
    assert row[9] == 300  # epid


# ---------------------------------------------------------------------------
# Disease-filter tests for composite PK
# ---------------------------------------------------------------------------


class TestDiseaseFilterParameters:
    """Tests verifying that the parameters table correctly filters by
    disease (cid10) after migration to composite PK."""

    def test_dengue_thresholds_differ_from_chik(
        self, regional_parameters_tables: None
    ) -> None:
        """Dengue and chik must return different thresholds for the
        same municipality (Rio, geocode=3304557)."""
        dengue = RegionalParameters.get_station_data(3304557, "dengue")
        chik = RegionalParameters.get_station_data(3304557, "chikungunya")

        assert len(dengue) > 0 and len(chik) > 0

        # cid10 column (index 0) should differ
        assert dengue[0][0] == "A90"
        assert chik[0][0] == "A92.0"

        # Thresholds: dengue(100,80,300) vs chik(25,20,75)
        dengue_pre, dengue_pos, dengue_epid = (
            dengue[0][7],
            dengue[0][8],
            dengue[0][9],
        )
        chik_pre, chik_pos, chik_epid = chik[0][7], chik[0][8], chik[0][9]

        assert dengue_pre != chik_pre
        assert dengue_epid != chik_epid
        assert dengue_pre == 100
        assert chik_pre == 25

    def test_chik_thresholds_for_niteroi(
        self, regional_parameters_tables: None
    ) -> None:
        """Verify chikungunya thresholds for Niterói (geocode=3303302)."""
        chik = RegionalParameters.get_station_data(3303302, "chikungunya")

        assert len(chik) > 0
        row = chik[0]
        assert row[0] == "A92.0"
        assert row[1] == 3303302
        assert row[7] == 50  # limiar_preseason
        assert row[8] == 40  # limiar_posseason
        assert row[9] == 150  # limiar_epidemico

    def test_dengue_thresholds_for_niteroi(
        self, regional_parameters_tables: None
    ) -> None:
        """Verify dengue thresholds for Niterói (geocode=3303302)."""
        dengue = RegionalParameters.get_station_data(3303302, "dengue")

        assert len(dengue) > 0
        row = dengue[0]
        assert row[0] == "A90"
        assert row[1] == 3303302
        assert row[7] == 90  # limiar_preseason
        assert row[8] == 70  # limiar_posseason
        assert row[9] == 250  # limiar_epidemico

    def test_station_data_returns_single_row_per_disease(
        self, regional_parameters_tables: None
    ) -> None:
        """get_station_data should return exactly 1 row per
        geocode+disease query, not multiple."""
        dengue = RegionalParameters.get_station_data(3304557, "dengue")
        chik = RegionalParameters.get_station_data(3304557, "chikungunya")

        assert (
            len(dengue) == 1
        ), f"Expected 1 dengue row for Rio, got {len(dengue)}"
        assert len(chik) == 1, f"Expected 1 chik row for Rio, got {len(chik)}"

    def test_nonexistent_disease_returns_empty(
        self, regional_parameters_tables: None
    ) -> None:
        """Querying a disease with no matching cid10 should return empty."""
        # "zika" maps to CID10 "A928" — not present in our fixture data
        zika = RegionalParameters.get_station_data(3304557, "zika")
        assert len(zika) == 0

    def test_regional_names_not_duplicated_with_multi_cid10(
        self, regional_parameters_tables: None
    ) -> None:
        """get_regional_names should return distinct names even when
        each municipality has multiple cid10 rows in parameters."""
        names = RegionalParameters.get_regional_names("RJ")

        # Should still be exactly 2 (Metro I, Metro II) — not 4
        assert len(names) == 2

    def test_cities_not_duplicated_with_multi_cid10(
        self, regional_parameters_tables: None
    ) -> None:
        """get_cities should return each municipality once even when
        there are multiple cid10 rows per municipality."""
        cities = RegionalParameters.get_cities(state_name="RJ")

        # Should still be exactly 2 cities — not 4
        assert len(cities) == 2
        assert 3304557 in cities
        assert 3303302 in cities

    def test_var_climate_info_consistent_across_diseases(
        self, regional_parameters_tables: None
    ) -> None:
        """get_var_climate_info returns weather station info that is the
        same regardless of which cid10 row is picked."""
        station, varcli = RegionalParameters.get_var_climate_info([3304557])
        assert station == "83743"
        assert varcli == "p_rt1"

        station2, varcli2 = RegionalParameters.get_var_climate_info([3303302])
        assert station2 == "83000"
        assert varcli2 == "p_rt1"
