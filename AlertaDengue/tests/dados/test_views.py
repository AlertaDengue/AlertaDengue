"""
Tests for ``get_var_params`` logic used in ``ReportCityView``.

The function is nested inside ``ReportCityView.get_context_data``,
so we replicate its logic here and exercise all branches:
valid keys, empty keys, unknown string keys, and non-string keys (e.g. NaN).
"""
from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from django.utils.translation import gettext as _


def _get_var_params(
    params: tuple[Any, ...] | list[Any] | None,
    logger: logging.Logger | None = None,
) -> tuple[dict[str, list[Any]], list[str]]:
    """Replicate the ``get_var_params`` helper from ``ReportCityView``.

    Parameters
    ----------
    params :
        Tuple/list returned by ``RegionalParameters.get_station_data``.
        Index 3 = first climate key, 4 = first value,
        5 = second key, 6 = second value.
    logger :
        Optional logger for warning messages on invalid keys.

    Returns
    -------
    var_climate :
        Map of normalised keys (e.g. ``"temp.min"``) to label lists.
    varcli_keys :
        Ordered list of accepted normalised key names.
    """
    if not params:
        return {}, []

    varcli_dict: dict[str, list[Any]] = {
        "temp.min": [_("°C temperatura mínima")],
        "temp.med": [_("°C temperatura média")],
        "temp.max": [_("°C temperatura máxima")],
        "umid.min": [_("% umidade mínima do ar")],
        "umid.med": [_("% umidade média do ar")],
        "umid.max": [_("% umidade máxima do ar")],
    }

    var_climate: dict[str, list[Any]] = {}
    varcli_pair: dict[str, Any] = {}

    def _add_param(raw_key: Any, raw_value: Any) -> None:
        if not raw_key:
            return

        if not isinstance(raw_key, str):
            if logger is not None:
                logger.warning(
                    "Ignoring invalid varclimate key %r in get_var_params. "
                    "params=%r",
                    raw_key,
                    params,
                )
            return

        normalized_key = raw_key.replace("_", ".")

        if normalized_key not in varcli_dict:
            if logger is not None:
                logger.warning(
                    "Ignoring invalid varclimate key %r in get_var_params. "
                    "params=%r",
                    raw_key,
                    params,
                )
            return

        varcli_pair[raw_key] = raw_value
        varcli_dict[normalized_key].append(raw_value)

    _add_param(params[3], params[4])
    _add_param(params[5], params[6])

    varcli_keys = [key.replace("_", ".") for key in varcli_pair.keys()]
    for key in varcli_keys:
        var_climate[key] = varcli_dict.get(key)

    return var_climate, varcli_keys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_params(
    key1: Any = None,
    value1: Any = None,
    key2: Any = None,
    value2: Any = None,
) -> list[Any]:
    """Build a params list matching the shape expected by ``_get_var_params``."""
    return [None, None, None, key1, value1, key2, value2, 0, 0, 0]


class TestGetVarParamsValidInput:
    """Tests for valid climate key extraction."""

    def test_single_valid_key(self) -> None:
        """A single valid climate key is returned normalised."""
        params = _make_params(key1="temp_min", value1="20")
        result, keys = _get_var_params(params)

        assert keys == ["temp.min"]
        assert "temp.min" in result

    def test_two_valid_keys(self) -> None:
        """Two valid climate keys are both returned."""
        params = _make_params(
            key1="temp_min", value1="20", key2="umid_med", value2="60"
        )
        result, keys = _get_var_params(params)

        assert set(keys) == {"temp.min", "umid.med"}
        assert len(result) == 2

    def test_key_normalisation(self) -> None:
        """Underscores in keys are replaced by dots."""
        params = _make_params(
            key1="temp_max", value1="30", key2="umid_max", value2="80"
        )
        _, keys = _get_var_params(params)

        assert "temp.max" in keys
        assert "umid.max" in keys


class TestGetVarParamsEmptyInput:
    """Tests for empty or missing input."""

    def test_none_params_returns_empty(self) -> None:
        """Passing ``None`` returns empty dict and list."""
        result, keys = _get_var_params(None)

        assert result == {}
        assert keys == []

    def test_empty_params_returns_empty(self) -> None:
        """Passing an empty list returns empty dict and list."""
        result, keys = _get_var_params([])

        assert result == {}
        assert keys == []

    def test_none_key_is_skipped(self) -> None:
        """A ``None`` key is silently skipped."""
        params = _make_params(key2="temp_min", value2="20")
        result, keys = _get_var_params(params)

        assert keys == ["temp.min"]

    def test_empty_string_key_is_skipped(self) -> None:
        """An empty string key is silently skipped."""
        params = _make_params(
            key1="", value1="20", key2="temp_min", value2="20"
        )
        result, keys = _get_var_params(params)

        assert keys == ["temp.min"]


class TestGetVarParamsInvalidInput:
    """Tests for invalid climate keys."""

    def test_unknown_string_key_triggers_warning(self) -> None:
        """A string key not in varcli_dict logs a warning and is skipped."""
        mock_logger = MagicMock(spec=logging.Logger)

        params = _make_params(
            key1="unknown_var", value1="20", key2="temp_min", value2="20"
        )
        result, keys = _get_var_params(params, logger=mock_logger)

        assert mock_logger.warning.call_count == 1
        assert "unknown.var" not in keys
        assert "temp.min" in keys

    def test_nan_key_triggers_warning(self) -> None:
        """A NaN (float) key logs a warning and is skipped."""
        mock_logger = MagicMock(spec=logging.Logger)

        params = _make_params(
            key1=float("nan"), value1="20", key2="temp_min", value2="20"
        )
        result, keys = _get_var_params(params, logger=mock_logger)

        assert mock_logger.warning.call_count == 1
        assert "temp.min" in keys

    def test_both_keys_invalid_returns_empty(self) -> None:
        """When both keys are invalid the result is empty."""
        mock_logger = MagicMock(spec=logging.Logger)

        params = _make_params(
            key1="invalid1", value1="20", key2="invalid2", value2="30"
        )
        result, keys = _get_var_params(params, logger=mock_logger)

        assert keys == []
        assert result == {}
        assert mock_logger.warning.call_count == 2

    def test_both_nan_keys_triggers_two_warnings(self) -> None:
        """Two NaN keys produce two warnings and empty result."""
        mock_logger = MagicMock(spec=logging.Logger)

        params = _make_params(
            key1=float("nan"), value1="20", key2=float("nan"), value2="30"
        )
        result, keys = _get_var_params(params, logger=mock_logger)

        assert mock_logger.warning.call_count == 2
        assert keys == []
        assert result == {}
