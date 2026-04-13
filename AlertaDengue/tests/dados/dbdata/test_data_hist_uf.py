"""
Contract tests for data_hist_uf().
"""

from __future__ import annotations

from dados.dbdata import data_hist_uf
from django.core.cache import cache


def test_data_hist_uf_orders_desc(hist_uf_dengue_table: None) -> None:
    """Return rows filtered by UF and ordered by SE DESC."""
    cache.clear()
    df = data_hist_uf("RJ", disease="dengue")

    assert set(df["state_abbv"].tolist()) == {"RJ"}
    assert df["SE"].tolist() == sorted(df["SE"].tolist(), reverse=True)


def test_data_hist_uf_is_cached(hist_uf_dengue_table: None) -> None:
    """Return cached results for repeated calls."""
    cache.clear()
    df1 = data_hist_uf("RJ", disease="dengue")
    df2 = data_hist_uf("RJ", disease="dengue")

    assert df2.equals(df1)


def test_data_hist_uf_empty_keeps_columns(hist_uf_dengue_table: None) -> None:
    """Keep columns even when there are no rows."""
    df = data_hist_uf("XX", disease="dengue")
    assert "casos_est" in df.columns
    assert df.empty
