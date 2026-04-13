"""
Tests for ReportState class in dbdata.py.
"""
from __future__ import annotations

import pandas as pd
import pytest
from dados.dbdata import ReportState
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def test_get_regional_by_state(report_data_tables: None) -> None:
    """Test get_regional_by_state returns correct DataFrame."""
    # Fixture: 3304557 (Rio), id_regional=1, 'Metropolitana I', UF='RJ'

    df = ReportState.get_regional_by_state("RJ")

    assert not df.empty
    assert len(df) == 1

    # Expected columns: nome_regional, municipio_geocodigo, municipio_nome
    # Note: original implementation used 'id_regional' too, and renamed cols.
    # We should match the return structure.
    # Expected: id_regional, nome_regional, municipio_geocodigo, municipio_nome

    row = df.iloc[0]
    assert row["nome_regional"] == "Metropolitana I"
    assert row["municipio_geocodigo"] == 3304557
    assert row["municipio_nome"] == "Rio de Janeiro"
    assert row["id_regional"] == 1


def test_create_report_state_data(report_data_tables: None) -> None:
    """Test create_report_state_data returns history for multiple cities."""
    # Data inserted: Rio (3304557) with SE 202401, 202402

    df = ReportState.create_report_state_data(
        geocodes=[3304557], disease="dengue", year_week=202402
    )

    assert not df.empty
    assert len(df) == 2  # Assuming both weeks fall in range [end-20, end]

    # Columns: SE, casos_est, casos, nivel, municipio_geocodigo, municipio_nome
    expected_cols = [
        "SE",
        "casos_est",
        "casos",
        "nivel",
        "municipio_geocodigo",
        "municipio_nome",
    ]
    for col in expected_cols:
        assert col in df.columns

    # Check join with municipio table for names
    assert df["municipio_nome"].iloc[0] == "Rio de Janeiro"


def test_create_report_state_data_multiple_cities(
    report_data_tables: None,
) -> None:
    """Test filtering by multiple geocodes works correctly."""
    # Assuming fixture has only Rio. Let's rely on fixture having Rio.
    # If we query Rio + nonexistent, should return Rio only.

    df = ReportState.create_report_state_data(
        geocodes=[3304557, 9999999], disease="dengue", year_week=202402
    )

    assert len(df) == 2  # Only Rio rows
    assert all(df["municipio_geocodigo"] == 3304557)
