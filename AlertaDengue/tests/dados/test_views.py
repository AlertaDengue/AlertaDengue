"""Tests for city-report view helpers."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from dados.dbdata import ReportParameters
from dados.views import get_var_params


def make_parameters(
    varcli: Any = None,
    clicrit: Any = None,
    varcli2: Any = None,
    clicrit2: Any = None,
) -> ReportParameters:
    """Build report parameters using the production result type."""
    return ReportParameters(
        cid10="A90",
        municipio_geocodigo=3304557,
        varcli=varcli,
        clicrit=clicrit,
        varcli2=varcli2,
        clicrit2=clicrit2,
        limiar_preseason=100,
        limiar_posseason=80,
        limiar_epidemico=300,
    )


def test_get_var_params_returns_empty_for_missing_parameters() -> None:
    assert get_var_params(None) == ({}, [])


def test_get_var_params_normalizes_valid_keys() -> None:
    parameters = make_parameters("temp_min", 22, "umid_med", 60)

    variables, keys = get_var_params(parameters)

    assert keys == ["temp.min", "umid.med"]
    assert variables["temp.min"][1] == 22
    assert variables["umid.med"][1] == 60


@pytest.mark.parametrize("invalid_key", [None, "", float("nan"), "NA"])
def test_get_var_params_skips_invalid_keys(invalid_key: Any) -> None:
    parameters = make_parameters(invalid_key, 10, "temp_max", 30)

    variables, keys = get_var_params(parameters)

    assert keys == ["temp.max"]
    assert list(variables) == ["temp.max"]


def test_get_var_params_logs_unknown_keys(
    caplog: pytest.LogCaptureFixture,
) -> None:
    parameters = make_parameters("unknown_var", 10)

    with caplog.at_level(logging.WARNING, logger="dados.views"):
        variables, keys = get_var_params(parameters)

    assert variables == {}
    assert keys == []
    assert "Skipping invalid varclimate key 'unknown_var'" in caplog.text


def test_report_parameters_are_immutable() -> None:
    parameters = make_parameters("temp_min", 22)

    with pytest.raises(AttributeError):
        parameters.varcli = "temp_max"  # type: ignore[misc]
