"""
Tests for ReportCity class in dbdata.py.
"""
from __future__ import annotations

import pandas as pd
import pytest
from dados.dbdata import ReportCity
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def test_read_disease_data_dengue(report_data_tables: None) -> None:
    """Test read_disease_data returns correct DataFrame for dengue."""
    # 3304557 is Rio de Janeiro
    # Data inserted in fixture: SE 202401, 202402
    df = ReportCity.read_disease_data(
        disease="dengue", geocode=3304557, year_week=202402
    )

    assert not df.empty
    assert len(df) == 2
    # Check index
    assert 202401 in df.index
    assert 202402 in df.index

    # Check columns
    expected_cols = [
        "casos notif.",
        "casos_est",
        "incidência",
        "pr(incid. subir)",
        "temp.min",
        "temp.med",
        "temp.max",
        "umid.min",
        "umid.med",
        "umid.max",
        "nivel",
        "level_code",
    ]
    for col in expected_cols:
        assert col in df.columns

    # Check specific values
    row1 = df.loc[202401]
    assert row1["casos notif."] == 10
    assert row1["casos_est"] == 15
    assert row1["level_code"] == 2
    assert row1["nivel"] == "amarelo"


def test_read_disease_data_invalid_disease() -> None:
    """Test read_disease_data raises ValueError for invalid disease."""
    with pytest.raises(ValueError, match="Unsupported disease"):
        ReportCity.read_disease_data(
            disease="invalid", geocode=3304557, year_week=202402
        )


def test_read_disease_data_filter_range(report_data_tables: None) -> None:
    """Test read_disease_data filters by SE range (last 200 weeks)."""
    # Fixture has 202401, 202402.
    # If we ask for 202401, it should return that and anything up to 200 weeks prior.
    # Since our mock data is small, it should return just 202401 if we exclude 202402 by range?
    # actually logic is between (end-200, end).

    df = ReportCity.read_disease_data(
        disease="dengue", geocode=3304557, year_week=202401
    )

    assert 202401 in df.index
    assert 202402 not in df.index  # 202402 > 202401
