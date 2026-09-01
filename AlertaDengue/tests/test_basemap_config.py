"""Tests for CARTO basemap tile URL building and configuration."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core import checks
from django.template.loader import render_to_string
from leaflet.templatetags.leaflet_tags import leaflet_map
import pytest

from ad_main.settings.base import (
    CARTO_ATTRIBUTION,
    build_basemap_tile_url,
    check_carto_basemap_api_key,
)
from ad_main.typed_settings import get_carto_basemap_api_key


def test_build_basemap_tile_url_with_configured_key() -> None:
    """Configured key returns an HTTPS URL containing the key query parameter."""
    url = build_basemap_tile_url("test-carto-key-123")

    assert url.startswith("https://")
    assert "basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png" in url
    assert url == (
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
        "?key=test-carto-key-123"
    )


def test_build_basemap_tile_url_strips_whitespace() -> None:
    """Whitespace surrounding the API key is trimmed."""
    url = build_basemap_tile_url("   test-key-with-spaces \n\t")

    assert url == (
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
        "?key=test-key-with-spaces"
    )


@pytest.mark.parametrize("missing_key", [None, "", "   ", "\t\n"])
def test_build_basemap_tile_url_without_key(missing_key: str | None) -> None:
    """Missing or empty key returns HTTPS URL without a key parameter."""
    url = build_basemap_tile_url(missing_key)

    assert url.startswith("https://")
    assert url == "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
    assert "?key=" not in url


def test_system_check_passes_when_key_configured(
    settings: Any,
) -> None:
    """System check returns no warnings when CARTO_BASEMAP_API_KEY is set."""
    settings.CARTO_BASEMAP_API_KEY = "test-api-key"

    warnings = check_carto_basemap_api_key()

    assert warnings == []


@pytest.mark.parametrize("empty_key", [None, "", "   "])
def test_system_check_warns_when_key_missing(
    settings: Any,
    empty_key: str | None,
) -> None:
    """System check returns ad_main.W001 warning when CARTO_BASEMAP_API_KEY is missing."""
    settings.CARTO_BASEMAP_API_KEY = empty_key

    warnings = check_carto_basemap_api_key()

    assert len(warnings) == 1
    warning = warnings[0]
    assert isinstance(warning, checks.Warning)
    assert warning.id == "ad_main.W001"
    assert "CARTO_BASEMAP_API_KEY" in warning.msg
    assert "CARTO_BASEMAP_API_KEY" in (warning.hint or "")


def test_get_carto_basemap_api_key_helper(settings: Any) -> None:
    """Typed settings helper retrieves CARTO_BASEMAP_API_KEY from settings."""
    settings.CARTO_BASEMAP_API_KEY = "my-test-key"
    assert get_carto_basemap_api_key() == "my-test-key"

    settings.CARTO_BASEMAP_API_KEY = None
    assert get_carto_basemap_api_key() is None


def test_leaflet_config_defaults_and_attribution() -> None:
    """LEAFLET_CONFIG preserves map behavior and includes required attribution."""
    leaflet_cfg = settings.LEAFLET_CONFIG

    assert leaflet_cfg["DEFAULT_CENTER"] == (-22.907, -43.431)
    assert leaflet_cfg["DEFAULT_ZOOM"] == 8
    assert leaflet_cfg["MAXIMUM_ZOOM"] == 13
    assert leaflet_cfg["MINIMAP"] is False
    assert leaflet_cfg["RESET_VIEW"] is False
    assert "info.dengue.mat.br" in leaflet_cfg["ATTRIBUTION_PREFIX"]

    # Attribution contains OpenStreetMap and CARTO credits
    assert "OpenStreetMap" in CARTO_ATTRIBUTION
    assert "CARTO" in CARTO_ATTRIBUTION
    assert "https://www.openstreetmap.org/copyright" in CARTO_ATTRIBUTION
    assert "https://carto.com/attributions" in CARTO_ATTRIBUTION

    # Tiles configuration structure
    tiles = leaflet_cfg["TILES"]
    assert isinstance(tiles, list)
    assert len(tiles) == 1
    label, url, attr = tiles[0]
    assert label == "CARTO Positron"
    assert url.startswith("https://")
    assert attr == CARTO_ATTRIBUTION


def test_leaflet_map_tag_renders_configured_tile_layer() -> None:
    """leaflet_map template tag outputs JSON containing configured tile layer."""
    rendered = leaflet_map("main")

    assert rendered["name"] == "main"
    assert "djoptions" in rendered
    assert "CARTO Positron" in rendered["djoptions"]
    assert "https://" in rendered["djoptions"]
    assert "OpenStreetMap" in rendered["djoptions"]
    assert "CARTO" in rendered["djoptions"]


def test_alert_map_template_renders_successfully() -> None:
    """Municipality/state alert map template renders without error."""
    context = {
        "map_center": [-22.9, -43.4],
        "map_zoom": 8,
        "mun_dict": "{}",
        "alerts_level": "{}",
        "case_series": "{}",
        "geo_ids": "[]",
        "SE": 1,
    }
    rendered_html = render_to_string("alert_state/map.html", context)

    assert 'id="main"' in rendered_html
    assert "leaflet-container-default" in rendered_html
    assert "main_map_init" in rendered_html
