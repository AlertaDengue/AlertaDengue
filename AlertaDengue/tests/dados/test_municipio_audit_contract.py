"""Regression checks for the audited Municipio adapter contract."""

import pytest

from dados.models import (
    LegacyHistoricalAlertChikungunya,
    LegacyHistoricalAlertDengue,
    LegacyHistoricalAlertZika,
    Notification,
)
from dados.models.base import (
    READ_WRITE_APPLICATION,
    READ_WRITE_EXTERNAL,
)
from manager.router import DatabaseAppsRouter


@pytest.mark.parametrize(
    ("model", "table"),
    [
        (Notification, '"Municipio"."Notificacao"'),
        (
            LegacyHistoricalAlertDengue,
            '"Municipio"."Historico_alerta"',
        ),
        (
            LegacyHistoricalAlertChikungunya,
            '"Municipio"."Historico_alerta_chik"',
        ),
        (LegacyHistoricalAlertZika, '"Municipio"."Historico_alerta_zika"'),
    ],
)
def test_audited_municipio_adapter_contract(model, table):
    """Retained adapters have explicit identity, table, policy, and routing."""
    router = DatabaseAppsRouter()

    assert model._meta.db_table == table
    assert model._meta.managed is False
    assert model._meta.get_field("id").primary_key
    assert model.read_write_policy in {
        READ_WRITE_APPLICATION,
        READ_WRITE_EXTERNAL,
    }
    assert router.db_for_read(model) == "dados"
    assert router.db_for_write(model) == "dados"


@pytest.mark.parametrize(
    "model",
    [
        LegacyHistoricalAlertDengue,
        LegacyHistoricalAlertChikungunya,
        LegacyHistoricalAlertZika,
    ],
)
def test_audited_historical_adapters_do_not_represent_archived_tweet(model):
    """The ORM projection remains valid before or after physical migration."""
    columns = {field.column for field in model._meta.concrete_fields}

    assert "tweet" not in columns
    assert "id" in columns
    assert "municipio_geocodigo" in columns
    assert "SE" in columns
