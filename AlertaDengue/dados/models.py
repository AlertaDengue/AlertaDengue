from django.db import models
from django.utils.translation import ugettext_lazy as _


class City(models.Model):
    """
    geocode INT NOT NULL,
    forecast_model_id INT,
    active BOOL NOT NULL,

    """

    geocode = models.IntegerField(
        db_column='geocodigo',
        null=False,
        primary_key=True,
        help_text=_('Código do Município'),
    )
    name = models.CharField(
        db_column='nome',
        null=False,
        max_length=128,
        help_text=_('Nome do municipio'),
    )
    state = models.CharField(
        db_column='uf',
        null=False,
        max_length=20,
        help_text=_('Nome do estado'),
    )

    class Meta:
        db_table = 'Dengue_global\".\"Municipio'
        app_label = 'dados'
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name


class CID10(models.Model):
    """
    geocode INT NOT NULL,
    forecast_model_id INT,
    active BOOL NOT NULL,

    """

    code = models.CharField(
        db_column='codigo',
        null=False,
        primary_key=True,
        max_length=512,
        help_text=_('Código do doença'),
    )
    name = models.CharField(
        db_column='nome',
        null=False,
        max_length=512,
        help_text=_('Nome da doença'),
    )

    class Meta:
        db_table = 'Dengue_global\".\"CID10'
        app_label = 'dados'
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name


class RegionalHealth(models.Model):
    """
    codigo_estacao_wu
    varcli
    ucrit
    tcrit
    limiar_preseason
    limiar_posseason
    limiar_epidemico

    """

    id = models.IntegerField(
        db_column='id',
        null=False,
        primary_key=True,
        help_text=_('Código da Regional Saúde'),
    )
    codigo_estacao_wu = models.CharField(
        db_column='codigo_estacao_wu',
        null=False,
        max_length=16,
        help_text=_('Código da Estação WU'),
    )
    varcli = models.CharField(
        db_column='varcli',
        null=False,
        max_length=10,
        help_text=_('Variável climática'),
    )
    ucrit = models.FloatField(
        db_column='ucrit', null=False, help_text=_('Umidade Crítica')
    )
    tcrit = models.FloatField(
        db_column='tcrit', null=False, help_text=_('Temperatura Crítica')
    )
    limiar_preseason = models.FloatField(
        db_column='limiar_preseason',
        null=False,
        help_text=_('Limiar pré-epidêmica'),
    )
    limiar_posseason = models.FloatField(
        db_column='limiar_posseason',
        null=False,
        help_text=_('Limiar pós-epidêmica'),
    )
    limiar_epidemico = models.FloatField(
        db_column='limiar_epidemico',
        null=False,
        help_text=_('Limiar epidêmico'),
    )
    municipio_geocodigo = models.FloatField(
        db_column='municipio_geocodigo',
        null=False,
        unique=True,
        help_text=_('Código do municipio'),
    )

    class Meta:
        db_table = 'Dengue_global\".\"regional_saude'
        app_label = 'dados'
        verbose_name_plural = "regionais_saude"

    def __str__(self):
        return self.name
