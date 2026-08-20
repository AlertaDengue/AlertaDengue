"""Adapters for retained ``Municipio`` objects."""

from django.db import models

from .base import READ_WRITE_APPLICATION, READ_WRITE_EXTERNAL


class LegacyHistoricalAlertBase(models.Model):
    """Shared verified columns of the three separate legacy alert tables."""

    read_write_policy = READ_WRITE_EXTERNAL
    id = models.BigAutoField(primary_key=True)
    epidemiological_week_start_date = models.DateField(db_column="data_iniSE")
    epidemiological_week = models.IntegerField(db_column="SE")
    estimated_cases = models.FloatField(db_column="casos_est", null=True)
    estimated_cases_min = models.IntegerField(
        db_column="casos_est_min", null=True
    )
    estimated_cases_max = models.IntegerField(
        db_column="casos_est_max", null=True
    )
    cases = models.IntegerField(db_column="casos", null=True)
    rt1_probability = models.FloatField(db_column="p_rt1", null=True)
    incidence_100k_probability = models.FloatField(
        db_column="p_inc100k", null=True
    )
    locality_id = models.IntegerField(db_column="Localidade_id", null=True)
    alert_level = models.SmallIntegerField(db_column="nivel", null=True)
    model_version = models.CharField(
        db_column="versao_modelo", max_length=40, null=True
    )
    reproduction_number = models.FloatField(db_column="Rt", null=True)
    population = models.IntegerField(db_column="pop", null=True)
    temperature_min = models.FloatField(db_column="tempmin", null=True)
    temperature_mean = models.FloatField(db_column="tempmed", null=True)
    temperature_max = models.FloatField(db_column="tempmax", null=True)
    humidity_min = models.FloatField(db_column="umidmin", null=True)
    humidity_mean = models.FloatField(db_column="umidmed", null=True)
    humidity_max = models.FloatField(db_column="umidmax", null=True)
    receptive = models.SmallIntegerField(db_column="receptivo", null=True)
    transmission = models.SmallIntegerField(db_column="transmissao", null=True)
    incidence_level = models.SmallIntegerField(
        db_column="nivel_inc", null=True
    )
    municipality_name = models.CharField(
        db_column="municipio_nome", max_length=128, null=True
    )
    municipality_geocode = models.IntegerField(db_column="municipio_geocodigo")
    probable_cases = models.IntegerField(db_column="casprov", null=True)
    estimated_probable_cases = models.FloatField(
        db_column="casprov_est", null=True
    )
    estimated_probable_cases_min = models.IntegerField(
        db_column="casprov_est_min", null=True
    )
    estimated_probable_cases_max = models.IntegerField(
        db_column="casprov_est_max", null=True
    )
    confirmed_cases = models.IntegerField(db_column="casconf", null=True)

    class Meta:
        abstract = True


class LegacyHistoricalAlertDengue(LegacyHistoricalAlertBase):
    """External adapter for ``Municipio.Historico_alerta``; never merged."""

    class Meta:
        app_label = "dados"
        db_table = '"Municipio"."Historico_alerta"'
        managed = False


class LegacyHistoricalAlertChikungunya(LegacyHistoricalAlertBase):
    """External adapter for ``Municipio.Historico_alerta_chik``; never merged."""

    class Meta:
        app_label = "dados"
        db_table = '"Municipio"."Historico_alerta_chik"'
        managed = False


class LegacyHistoricalAlertZika(LegacyHistoricalAlertBase):
    """External adapter for ``Municipio.Historico_alerta_zika``; never merged."""

    class Meta:
        app_label = "dados"
        db_table = '"Municipio"."Historico_alerta_zika"'
        managed = False


class Notification(models.Model):
    """Application-write adapter; ingestion remains the raw-SQL owner."""

    read_write_policy = READ_WRITE_APPLICATION
    id = models.BigAutoField(primary_key=True)
    notification_date = models.DateField(db_column="dt_notific", null=True)
    notification_week = models.IntegerField(db_column="se_notif", null=True)
    notification_year = models.IntegerField(db_column="ano_notif", null=True)
    symptom_onset_date = models.DateField(db_column="dt_sin_pri", null=True)
    symptom_onset_week = models.IntegerField(db_column="se_sin_pri", null=True)
    entry_date = models.DateField(db_column="dt_digita", null=True)
    municipality_geocode = models.IntegerField(db_column="municipio_geocodigo")
    notification_number = models.CharField(
        db_column="nu_notific", max_length=64
    )
    cid10_code = models.CharField(db_column="cid10_codigo", max_length=16)
    birth_date = models.DateField(db_column="dt_nasc", null=True)
    sex = models.CharField(db_column="cs_sexo", max_length=1, null=True)
    age_code = models.CharField(
        db_column="nu_idade_n", max_length=8, null=True
    )
    final_classification = models.CharField(
        db_column="classi_fin", max_length=8, null=True
    )
    criteria = models.CharField(db_column="criterio", max_length=8, null=True)
    district_id = models.CharField(
        db_column="id_distrit", max_length=16, null=True
    )
    neighborhood_id = models.CharField(
        db_column="id_bairro", max_length=16, null=True
    )
    neighborhood_name = models.CharField(
        db_column="nm_bairro", max_length=128, null=True
    )

    class Meta:
        app_label = "dados"
        db_table = '"Municipio"."Notificacao"'
        managed = False
