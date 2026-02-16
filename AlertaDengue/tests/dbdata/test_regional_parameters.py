"""
Tests for RegionalParameters class in dbdata.py.
"""
from __future__ import annotations

import pandas as pd
import pytest
from dados.dbdata import RegionalParameters
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


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
