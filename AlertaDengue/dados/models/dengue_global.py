"""Adapters for retained ``Dengue_global`` objects."""

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import READ_ONLY


class City(models.Model):
    """Read-only adapter for the retained municipality lookup table."""

    read_write_policy = READ_ONLY
    geocode = models.IntegerField(db_column="geocodigo", primary_key=True)
    name = models.CharField(db_column="nome", max_length=128)
    population = models.BigIntegerField(db_column="populacao")
    state = models.CharField(db_column="uf", max_length=20)
    regional_id = models.IntegerField(db_column="id_regional")
    regional_name = models.CharField(db_column="regional", max_length=128)
    macroregional_id = models.IntegerField(db_column="macroregional_id")
    macroregional_name = models.CharField(
        db_column="macroregional", max_length=128
    )

    class Meta:
        app_label = "dados"
        db_table = '"Dengue_global"."Municipio"'
        managed = False
        verbose_name = "city"
        verbose_name_plural = "cities"

    def __str__(self) -> str:
        return self.name

    # Compatibility aliases for the previous unmanaged adapter. New code uses
    # the normalized names above; these avoid breaking existing callers.
    @property
    def id_regional(self) -> int:
        return self.regional_id

    @property
    def regional(self) -> str:
        return self.regional_name

    @property
    def macroregional(self) -> str:
        return self.macroregional_name


class CID10(models.Model):
    """Read-only adapter for retained CID10 codes."""

    read_write_policy = READ_ONLY
    code = models.CharField(
        db_column="codigo", primary_key=True, max_length=512
    )
    name = models.CharField(db_column="nome", max_length=512)

    class Meta:
        app_label = "dados"
        db_table = '"Dengue_global"."CID10"'
        managed = False
        verbose_name = "CID10"
        verbose_name_plural = "CID10 codes"

    def __str__(self) -> str:
        return self.name


class State(models.Model):
    """Read-only adapter retained for active state-history dependencies."""

    read_write_policy = READ_ONLY
    geocode = models.IntegerField(db_column="geocodigo", primary_key=True)
    name = models.CharField(db_column="nome", max_length=128)
    abbreviation = models.CharField(db_column="uf", max_length=2)

    class Meta:
        app_label = "dados"
        db_table = '"Dengue_global"."estado"'
        managed = False


class MacroRegion(models.Model):
    """Read-only adapter required by the retained regional relationship."""

    read_write_policy = READ_ONLY
    id = models.IntegerField(primary_key=True)
    name = models.CharField(db_column="nome", max_length=128)

    class Meta:
        app_label = "dados"
        db_table = '"Dengue_global"."macroregional"'
        managed = False


class Regional(models.Model):
    """Read-only adapter for the active regional-parameter lookup."""

    read_write_policy = READ_ONLY
    id = models.IntegerField(primary_key=True)
    name = models.CharField(db_column="nome", max_length=128)
    macroregion = models.ForeignKey(
        MacroRegion,
        db_column="id_macroregional",
        on_delete=models.DO_NOTHING,
        related_name="regionals",
    )

    class Meta:
        app_label = "dados"
        db_table = '"Dengue_global"."regional"'
        managed = False


class Parameter(models.Model):
    """Read-only adapter for city/disease report parameters."""

    read_write_policy = READ_ONLY
    pk = models.CompositePrimaryKey("municipality_geocode", "cid10_code")
    municipality_geocode = models.IntegerField(db_column="municipio_geocodigo")
    cid10_code = models.CharField(db_column="cid10", max_length=16)
    baseline_variation = models.CharField(
        db_column="varcli", max_length=128, null=True
    )
    baseline_critical = models.FloatField(db_column="clicrit", null=True)
    secondary_variation = models.CharField(
        db_column="varcli2", max_length=128, null=True
    )
    secondary_critical = models.FloatField(db_column="clicrit2", null=True)
    preseason_threshold = models.FloatField(
        db_column="limiar_preseason", null=True
    )
    postseason_threshold = models.FloatField(
        db_column="limiar_posseason", null=True
    )
    epidemic_threshold = models.FloatField(
        db_column="limiar_epidemico", null=True
    )

    class Meta:
        app_label = "dados"
        db_table = '"Dengue_global"."parameters"'
        managed = False


class ParameterUF(models.Model):
    """Django-managed UF-level epidemic thresholds by disease."""

    pk = models.CompositePrimaryKey("state_code", "cid10")
    state_code = models.IntegerField(
        db_column="state_code", help_text=_("Código numérico do estado")
    )
    state_abbr = models.CharField(
        db_column="state_abbr", max_length=2, help_text=_("Sigla do estado")
    )
    state_name = models.TextField(
        db_column="state_name", help_text=_("Nome do estado")
    )
    cid10 = models.CharField(
        db_column="cid10", max_length=16, help_text=_("Código CID10 da doença")
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
        app_label = "dados"
        db_table = '"Dengue_global"."parameters_uf"'
        verbose_name = "UF parameter"
        verbose_name_plural = "UF parameters"
        indexes = [
            models.Index(
                fields=["state_code"], name="parameters_uf_idx_state_code"
            )
        ]

    def __str__(self) -> str:
        return f"{self.state_abbr} - {self.cid10}"
