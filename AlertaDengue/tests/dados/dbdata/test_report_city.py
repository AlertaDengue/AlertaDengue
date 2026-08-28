"""
Tests for ReportCity class in dbdata.py.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db import connections
from django.test.utils import CaptureQueriesContext
import pandas as pd
import pytest
from sqlalchemy import text

from dados.dbdata import DB_ENGINE, ReportCity
from dados.services.historical_alerts import (
    build_report_city_historical_alert_queryset,
)

pytestmark = [
    pytest.mark.usefixtures("report_data_tables"),
    pytest.mark.django_db(databases={"default", "dados"}, transaction=True),
]


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def test_read_disease_data_dengue() -> None:
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


def test_read_disease_data_filter_range() -> None:
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


@pytest.mark.parametrize(
    ("disease", "table"),
    [
        ("dengue", '"Municipio"."Historico_alerta"'),
        ("chikungunya", '"Municipio"."Historico_alerta_chik"'),
        ("zika", '"Municipio"."Historico_alerta_zika"'),
    ],
)
def test_report_city_queryset_is_bounded_and_explicitly_routed(
    disease: str, table: str
) -> None:
    queryset = build_report_city_historical_alert_queryset(
        disease=disease,
        municipality_geocode=3304557,
        start_week=202201,
        end_week=202402,
    )

    assert queryset._db == "dados"
    assert queryset.model._meta.db_table == table
    assert queryset.query.order_by == ("epidemiological_week",)
    assert queryset.query.low_mark == 0
    assert queryset.query.high_mark == 200


@pytest.mark.parametrize(
    ("disease", "table"),
    [
        ("dengue", "Historico_alerta"),
        ("chikungunya", "Historico_alerta_chik"),
        ("zika", "Historico_alerta_zika"),
    ],
)
def test_read_disease_data_matches_legacy_sql_and_uses_dados(
    disease: str, table: str
) -> None:
    """The bounded ORM projection retains the legacy DataFrame contract."""
    with DB_ENGINE.begin() as connection:
        connection.execute(
            text(
                f'''INSERT INTO "Municipio"."{table}" (
                    "SE", "data_iniSE", municipio_geocodigo, casos,
                    casos_est, nivel, p_inc100k, p_rt1, tempmin, tempmed,
                    tempmax, umidmin, umidmed, umidmax
                ) VALUES
                    (202350, '2023-12-11', 3304557, 5, 7, 4, NULL, 0.5,
                     20.1, NULL, 30.1, 60.1, NULL, 80.1),
                    (202401, '2024-01-01', 9999999, 99, 99, 1, 1, 1,
                     1, 1, 1, 1, 1, 1),
                    (202000, '2020-01-01', 3304557, 1, 1, 1, 1, 1,
                     1, 1, 1, 1, 1, 1),
                    (202403, '2024-01-15', 3304557, 30, 35, 9, 12.5, 1.5,
                     21.1, 25.1, 31.1, 61.1, 70.1, 81.1),
                    (202403, '2024-01-15', 3304557, 31, 36, 3, 13.5, 1.6,
                     21.2, 25.2, 31.2, 61.2, 70.2, 81.2),
                    (202700, '2027-01-01', 3304557, 100, 100, 1, 1, 1,
                     1, 1, 1, 1, 1, 1)'''
            )
        )

    with DB_ENGINE.connect() as connection:
        result = connection.execute(
            text(
                f'''SELECT
                    "SE", casos AS "casos notif.", casos_est,
                    p_inc100k AS "incidência",
                    p_rt1 AS "pr(incid. subir)", tempmin AS "temp.min",
                    tempmed AS "temp.med", tempmax AS "temp.max",
                    umidmin AS "umid.min", umidmed AS "umid.med",
                    umidmax AS "umid.max",
                    CASE
                        WHEN nivel = 1 THEN 'verde'
                        WHEN nivel = 2 THEN 'amarelo'
                        WHEN nivel = 3 THEN 'laranja'
                        WHEN nivel = 4 THEN 'vermelho'
                        ELSE '-'
                    END AS nivel,
                    nivel AS level_code
                FROM "Municipio"."{table}"
                WHERE "SE" BETWEEN :start_week AND :end_week
                  AND municipio_geocodigo = :geocode
                ORDER BY "SE"
                LIMIT 200'''
            ),
            {"start_week": 202203, "end_week": 202403, "geocode": 3304557},
        )
        expected = pd.DataFrame(
            result.fetchall(), columns=result.keys()
        ).set_index("SE")

    with CaptureQueriesContext(connections["dados"]) as dados_queries:
        with CaptureQueriesContext(connections["default"]) as default_queries:
            actual = ReportCity.read_disease_data(disease, 3304557, 202403)

    assert actual.index.is_monotonic_increasing
    assert expected.index.is_monotonic_increasing
    assert actual.index.duplicated().any()
    pd.testing.assert_frame_equal(
        _sort_rows_within_week(actual),
        _sort_rows_within_week(expected),
        check_dtype=True,
    )
    assert len(dados_queries) == 1
    assert len(default_queries) == 0
    assert f'"Municipio"."{table}"' in dados_queries[0]["sql"]


def _sort_rows_within_week(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize only order that the legacy ``ORDER BY SE`` leaves open."""
    return (
        data.reset_index()
        .sort_values(
            by=["SE", *data.columns], kind="stable", na_position="last"
        )
        .reset_index(drop=True)
    )
