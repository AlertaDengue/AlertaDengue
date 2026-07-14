from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class City(models.Model):
    """Read-only mapping for cities."""

    geocode = models.IntegerField(
        db_column="geocodigo",
        primary_key=True,
        help_text=_("Código do Município"),
    )
    name = models.CharField(
        db_column="nome",
        max_length=128,
        help_text=_("Nome do município"),
    )
    state = models.CharField(
        db_column="uf",
        max_length=20,
        help_text=_("Nome do estado"),
    )
    id_regional = models.IntegerField(
        db_column="id_regional",
        help_text=_("Geocódigo da Regional de Saúde"),
    )
    regional = models.CharField(
        db_column="regional",
        max_length=128,
        help_text=_("Nome da Regional de Saúde"),
    )
    macroregional_id = models.IntegerField(
        db_column="macroregional_id",
        help_text=_("Geocódigo da Macroregional de Saúde"),
    )
    macroregional = models.CharField(
        db_column="macroregional",
        max_length=128,
        help_text=_("Nome da Macroregional de Saúde"),
    )

    class Meta:
        db_table = '"Dengue_global"."Municipio"'
        app_label = "dados"
        managed = False
        verbose_name = "city"
        verbose_name_plural = "cities"

    def __str__(self) -> str:
        """Return the city name."""
        return self.name


class CID10(models.Model):
    """Read-only mapping for CID10 codes."""

    code = models.CharField(
        db_column="codigo",
        primary_key=True,
        max_length=512,
        help_text=_("Código da doença"),
    )
    name = models.CharField(
        db_column="nome",
        max_length=512,
        help_text=_("Nome da doença"),
    )

    class Meta:
        db_table = '"Dengue_global"."CID10"'
        app_label = "dados"
        managed = False
        verbose_name = "CID10"
        verbose_name_plural = "CID10 codes"

    def __str__(self) -> str:
        """Return the disease name."""
        return self.name


class ParameterUF(models.Model):
    """UF-level epidemic thresholds by disease."""

    pk = models.CompositePrimaryKey("state_code", "cid10")

    state_code = models.IntegerField(
        db_column="state_code",
        help_text=_("Código numérico do estado"),
    )
    state_abbr = models.CharField(
        db_column="state_abbr",
        max_length=2,
        help_text=_("Sigla do estado"),
    )
    state_name = models.TextField(
        db_column="state_name",
        help_text=_("Nome do estado"),
    )
    cid10 = models.CharField(
        db_column="cid10",
        max_length=16,
        help_text=_("Código CID10 da doença"),
    )
    limiar_preseason = models.FloatField(
        db_column="limiar_preseason",
        null=True,
        blank=True,
        help_text=_("Limiar de pré-sazonalidade"),
    )
    limiar_posseason = models.FloatField(
        db_column="limiar_posseason",
        null=True,
        blank=True,
        help_text=_("Limiar de pós-sazonalidade"),
    )
    limiar_epidemico = models.FloatField(
        db_column="limiar_epidemico",
        null=True,
        blank=True,
        help_text=_("Limiar epidêmico"),
    )

    class Meta:
        db_table = '"Dengue_global"."parameters_uf"'
        app_label = "dados"
        verbose_name = "UF parameter"
        verbose_name_plural = "UF parameters"
        indexes = [
            models.Index(
                fields=["state_code"],
                name="parameters_uf_idx_state_code",
            )
        ]

    def __str__(self) -> str:
        """Return a readable UF/disease identifier."""
        return f"{self.state_abbr} - {self.cid10}"


class EpiscannerSirParams(models.Model):
    cid10 = models.CharField(max_length=10)
    geocode = models.BigIntegerField()
    year = models.IntegerField()
    ep_ini = models.CharField(max_length=20, null=True, blank=True)
    ep_pw = models.CharField(max_length=20)
    ep_end = models.CharField(max_length=20, null=True, blank=True)
    ep_dur = models.IntegerField(null=True, blank=True)
    peak_week = models.FloatField()
    beta = models.FloatField()
    gamma = models.FloatField()
    r0 = models.FloatField()
    total_cases = models.FloatField()
    alpha = models.FloatField()
    sum_res = models.FloatField()

    class Meta:
        db_table = "episcanner.sir_params"
        constraints = [
            models.UniqueConstraint(
                fields=["cid10", "geocode", "year"],
                name="uq_sir_params_cid10_geocode_year",
            ),
        ]
