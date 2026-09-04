import pytest

from dados.models import (
    CID10,
    City,
    LegacyHistoricalAlertChikungunya,
    LegacyHistoricalAlertDengue,
    LegacyHistoricalAlertZika,
    MacroRegion,
    Notification,
    Parameter,
    ParameterUF,
    Regional,
    State,
)
from dados.models.base import READ_ONLY
from dados.services.historical_alerts import (
    get_legacy_historical_alert_model,
    get_legacy_historical_alert_table_name,
    get_supported_historical_alert_diseases,
    normalize_disease_key,
)
from manager.router import DatabaseAppsRouter


@pytest.mark.parametrize(
    ("model", "table"),
    [
        (CID10, '"Dengue_global"."CID10"'),
        (City, '"Dengue_global"."Municipio"'),
        (State, '"Dengue_global"."estado"'),
        (MacroRegion, '"Dengue_global"."macroregional"'),
        (Parameter, '"Dengue_global"."parameters"'),
        (Regional, '"Dengue_global"."regional"'),
        (Notification, '"Municipio"."Notificacao"'),
        (LegacyHistoricalAlertDengue, '"Municipio"."Historico_alerta"'),
        (
            LegacyHistoricalAlertChikungunya,
            '"Municipio"."Historico_alerta_chik"',
        ),
        (LegacyHistoricalAlertZika, '"Municipio"."Historico_alerta_zika"'),
    ],
)
def test_unmanaged_adapter_metadata(model, table):
    assert model._meta.managed is False
    assert model._meta.db_table == table


@pytest.mark.parametrize(
    "model",
    [
        LegacyHistoricalAlertDengue,
        LegacyHistoricalAlertChikungunya,
        LegacyHistoricalAlertZika,
    ],
)
def test_historical_alert_column_mappings(model):
    assert model._meta.get_field("id").primary_key
    assert (
        model._meta.get_field("epidemiological_week_start_date").column
        == "data_iniSE"
    )
    assert model._meta.get_field("epidemiological_week").column == "SE"
    assert model._meta.get_field("locality_id").column == "Localidade_id"
    assert (
        model._meta.get_field("municipality_geocode").column
        == "municipio_geocodigo"
    )
    assert model._meta.get_field("reproduction_number").column == "Rt"
    assert model._meta.get_field("population").column == "pop"
    assert model._meta.get_field("temperature_min").column == "tempmin"
    assert model._meta.get_field("temperature_mean").column == "tempmed"
    assert model._meta.get_field("temperature_max").column == "tempmax"
    assert model._meta.get_field("humidity_min").column == "umidmin"
    assert model._meta.get_field("humidity_mean").column == "umidmed"
    assert model._meta.get_field("humidity_max").column == "umidmax"
    assert model._meta.get_field("receptive").column == "receptivo"
    assert model._meta.get_field("transmission").column == "transmissao"
    assert model._meta.get_field("incidence_level").column == "nivel_inc"


@pytest.mark.parametrize(
    ("disease", "model", "table"),
    [
        (
            "dengue",
            LegacyHistoricalAlertDengue,
            '"Municipio"."Historico_alerta"',
        ),
        (
            "chik",
            LegacyHistoricalAlertChikungunya,
            '"Municipio"."Historico_alerta_chik"',
        ),
        (
            "chikungunya",
            LegacyHistoricalAlertChikungunya,
            '"Municipio"."Historico_alerta_chik"',
        ),
        (
            "zika",
            LegacyHistoricalAlertZika,
            '"Municipio"."Historico_alerta_zika"',
        ),
    ],
)
def test_historical_alert_helpers(disease, model, table):
    assert get_legacy_historical_alert_model(disease) is model
    assert get_legacy_historical_alert_table_name(disease) == table


def test_historical_alert_helper_rejects_unknown_disease():
    with pytest.raises(ValueError, match="supported values"):
        normalize_disease_key("yellow-fever")


def test_historical_alert_query_can_be_constructed():
    query = LegacyHistoricalAlertDengue.objects.filter(
        municipality_geocode=3304557,
        epidemiological_week=202601,
    ).query
    assert '"Municipio"."Historico_alerta"' in str(query)


def test_notification_key_column_mappings():
    assert Notification._meta.get_field("id").primary_key
    assert (
        Notification._meta.get_field("notification_number").column
        == "nu_notific"
    )
    assert (
        Notification._meta.get_field("notification_date").column
        == "dt_notific"
    )
    assert Notification._meta.get_field("cid10_code").column == "cid10_codigo"
    assert (
        Notification._meta.get_field("municipality_geocode").column
        == "municipio_geocodigo"
    )


def test_dengue_global_lookup_adapter_metadata():
    assert City._meta.get_field("geocode").column == "geocodigo"
    assert City._meta.get_field("population").column == "populacao"
    assert (
        City._meta.get_field("population").get_internal_type()
        == "BigIntegerField"
    )
    assert City._meta.get_field("state").column == "uf"
    assert City._meta.get_field("regional_id").column == "id_regional"
    assert Regional._meta.get_field("id").primary_key
    assert Regional._meta.get_field("macroregion").column == "id_macroregional"
    assert Parameter._meta.get_field("municipality_geocode").column == (
        "municipio_geocodigo"
    )
    assert Parameter._meta.get_field("cid10_code").column == "cid10"
    assert Parameter._meta.pk.field_names == (
        "municipality_geocode",
        "cid10_code",
    )


def test_retained_dengue_global_adapter_identity_and_routing():
    """Every retained adapter has an explicit identity and uses ``dados``."""
    router = DatabaseAppsRouter()

    assert State._meta.get_field("geocode").primary_key
    assert MacroRegion._meta.get_field("id").primary_key
    assert Regional._meta.get_field("macroregion").column == "id_macroregional"
    assert ParameterUF._meta.pk.field_names == ("state_code", "cid10")
    assert ParameterUF._meta.managed is True

    unmanaged_models = (
        CID10,
        City,
        State,
        MacroRegion,
        Parameter,
        Regional,
    )

    for model in (*unmanaged_models, ParameterUF):
        assert router.db_for_read(model) == "dados"

    assert router.db_for_write(ParameterUF) == "dados"

    for model in unmanaged_models:
        assert model.read_write_policy == READ_ONLY


def test_supported_historical_alert_diseases_are_canonical():
    assert get_supported_historical_alert_diseases() == (
        "dengue",
        "chikungunya",
        "zika",
    )
