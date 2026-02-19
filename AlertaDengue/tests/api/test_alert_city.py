from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from AlertaDengue.api.db import AlertCity


@pytest.fixture
def mock_engine():
    mock = MagicMock()
    conn = mock.connect.return_value.__enter__.return_value

    # Mock return value for conn.execute()
    mock_result = MagicMock()
    mock_result.keys.return_value = [
        "SE",
        "municipio_geocodigo",
        "casos",
        "data_iniSE",
        "nivel",
    ]
    mock_result.fetchall.return_value = [
        (202301, 3304557, 10, "2023-01-01", 1),
        (202302, 3304557, 20, "2023-01-08", 2),
    ]
    conn.execute.return_value = mock_result
    return mock


def test_alert_city_search_basic(mock_engine):
    df = AlertCity.search("dengue", 3304557, db_engine=mock_engine)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "SE" in df.columns
    assert "notif_accum_year" in df.columns
    assert len(df) == 2
    mock_engine.connect.assert_called_once()


def test_alert_city_search_with_weeks(mock_engine):
    df = AlertCity.search(
        "dengue",
        3304557,
        ew_start=202301,
        ew_end=202302,
        db_engine=mock_engine,
    )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    # Verify SQL parameters
    (
        args,
        kwargs,
    ) = (
        mock_engine.connect.return_value.__enter__.return_value.execute.call_args
    )
    params = kwargs.get("parameters", args[1] if len(args) > 1 else {})
    assert params["ew_start"] == 202301
    assert params["ew_end"] == 202302
    assert params["geocode"] == 3304557


def test_alert_city_search_invalid_disease():
    with pytest.raises(ValueError, match="The diseases available are"):
        AlertCity.search("invalid_disease", 3304557)


def test_alert_city_search_empty_result(mock_engine):
    conn = mock_engine.connect.return_value.__enter__.return_value
    mock_result = MagicMock()
    mock_result.keys.return_value = [
        "SE",
        "municipio_geocodigo",
        "casos",
        "data_iniSE",
        "nivel",
    ]
    mock_result.fetchall.return_value = []
    conn.execute.return_value = mock_result

    df = AlertCity.search("dengue", 3304557, db_engine=mock_engine)
    assert isinstance(df, pd.DataFrame)
    assert df.empty
