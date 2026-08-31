"""PostgreSQL compatibility tests for municipality map metadata."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

from django.core.cache import cache
from django.db import connections
from django.test.utils import CaptureQueriesContext
from epiweeks import Week
import pandas as pd
import pytest
from sqlalchemy import text

from dados import maps
from dados.views import AlertaMunicipioPageView

pytestmark = pytest.mark.django_db(
    databases={"default", "dados"}, transaction=True
)


@pytest.fixture()
def municipality_map_table() -> Iterator[None]:
    """Provision the independent physical contract used by map lookups."""
    with connections["dados"].cursor() as cursor:
        cursor.execute('CREATE SCHEMA IF NOT EXISTS "Dengue_global"')
        cursor.execute('DROP TABLE IF EXISTS "Dengue_global"."Municipio"')
        cursor.execute(
            """
            CREATE TABLE "Dengue_global"."Municipio" (
                geocodigo INTEGER PRIMARY KEY,
                nome VARCHAR(128) NOT NULL,
                geojson TEXT NOT NULL,
                populacao BIGINT NOT NULL,
                uf VARCHAR(20) NOT NULL,
                id_regional INTEGER,
                regional VARCHAR(128),
                macroregional_id INTEGER,
                macroregional VARCHAR(128)
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO "Dengue_global"."Municipio"
                (geocodigo, nome, geojson, populacao, uf)
            VALUES
                (3304557, 'Rio de Janeiro', '{"type": "Feature"}',
                 6748000, 'Rio de Janeiro'),
                (3303302, 'Niterói', '{"type": "Feature"}',
                 515317, 'Rio de Janeiro')
            """
        )

    yield

    with connections["dados"].cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS "Dengue_global"."Municipio"')
    maps.DB_ENGINE.dispose()


@pytest.fixture(autouse=True)
def clear_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.mark.usefixtures("municipality_map_table")
def test_get_city_info_matches_legacy_sql_contract() -> None:
    """The ORM projection preserves the legacy scalar metadata response."""
    with maps.DB_ENGINE.connect() as connection:
        legacy = (
            connection.execute(
                text(
                    """
                SELECT geocodigo, nome, populacao, uf
                FROM "Dengue_global"."Municipio"
                WHERE geocodigo = :geocodigo
                """
                ),
                {"geocodigo": 3304557},
            )
            .mappings()
            .one()
        )

    with CaptureQueriesContext(connections["dados"]) as dados_queries:
        with CaptureQueriesContext(connections["default"]) as default_queries:
            actual = maps.get_city_info(3304557)

    assert actual == dict(legacy)
    assert list(actual) == ["geocodigo", "nome", "populacao", "uf"]
    assert isinstance(actual["geocodigo"], int)
    assert isinstance(actual["nome"], str)
    assert isinstance(actual["populacao"], int)
    assert isinstance(actual["uf"], str)
    assert len(dados_queries) == 1
    assert len(default_queries) == 0


@pytest.mark.usefixtures("municipality_map_table")
def test_get_city_info_rejects_unknown_geocode() -> None:
    with pytest.raises(
        ValueError, match="Municipio not found for geocodigo=999"
    ):
        maps.get_city_info(999)


@pytest.mark.usefixtures("municipality_map_table")
def test_get_city_geojson_passes_with_its_independent_fixture() -> None:
    feature_collection = maps.get_city_geojson(3304557)

    assert feature_collection["type"] == "FeatureCollection"
    assert feature_collection["features"][0]["properties"] == {
        "geocodigo": 3304557,
        "nome": "Rio de Janeiro",
        "populacao": 6748000,
    }


def _configure_city_page_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    get_city_info_mock: MagicMock,
) -> None:
    monkeypatch.setattr(
        "dados.views.ReportState.get_regional_by_state",
        lambda _state: pd.DataFrame(
            [{"municipio_geocodigo": 3304557, "id_regional": 1}]
        ),
    )
    monkeypatch.setattr("dados.views.get_last_SE", lambda: Week(2024, 1))
    monkeypatch.setattr("dados.views.get_city_info", get_city_info_mock)
    monkeypatch.setattr(
        "dados.views.get_city_alert",
        lambda *_args: ({}, None, [10], [1], 2023, [8], (1, 2), None, 0.5),
    )
    monkeypatch.setattr(
        "dados.views.AlertCitiesCharts.create_alert_chart",
        lambda *_args: "chart",
    )


def test_city_page_cache_miss_preserves_city_info_key_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    city_info = {
        "geocodigo": 3304557,
        "nome": "Rio de Janeiro",
        "populacao": 6748000,
        "uf": "Rio de Janeiro",
    }
    get_city_info_mock = MagicMock(return_value=city_info)
    view_cache = MagicMock()
    view_cache.get.return_value = None
    _configure_city_page_dependencies(monkeypatch, get_city_info_mock)
    monkeypatch.setattr("dados.views.cache", view_cache)

    view = AlertaMunicipioPageView()
    view.kwargs = {"geocodigo": "3304557", "disease": "dengue"}
    context = view.get_context_data(**view.kwargs)

    assert context["nome"] == "Rio de Janeiro"
    assert context["populacao"] == 6748000
    assert context["state"] == "RJ"
    assert context["geojson_urls"] == ["/static/geojson/3304557.json"]
    get_city_info_mock.assert_called_once_with(3304557)
    view_cache.get.assert_called_once_with("city_info:3304557")
    view_cache.set.assert_called_once_with(
        "city_info:3304557", city_info, 60 * 60 * 24
    )


def test_city_page_cache_hit_does_not_query_city_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    city_info = {
        "geocodigo": 3304557,
        "nome": "Rio de Janeiro",
        "populacao": 6748000,
        "uf": "Rio de Janeiro",
    }
    get_city_info_mock = MagicMock()
    view_cache = MagicMock()
    view_cache.get.return_value = city_info
    _configure_city_page_dependencies(monkeypatch, get_city_info_mock)
    monkeypatch.setattr("dados.views.cache", view_cache)

    view = AlertaMunicipioPageView()
    view.kwargs = {"geocodigo": "3304557", "disease": "dengue"}
    with CaptureQueriesContext(connections["dados"]) as dados_queries:
        with CaptureQueriesContext(connections["default"]) as default_queries:
            context = view.get_context_data(**view.kwargs)

    assert context["nome"] == "Rio de Janeiro"
    get_city_info_mock.assert_not_called()
    view_cache.set.assert_not_called()
    assert len(dados_queries) == 0
    assert len(default_queries) == 0
