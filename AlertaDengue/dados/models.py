from django.db import models
from django.utils.translation import ugettext_lazy as _


class ForecastModel(models.Model):
    """
    id    SERIAL    PRIMARY    KEY,
    name    VARCHAR(128)    NOT    NULL,
    total_weeks   SMALLINT    NOT    NULL,
    commit_id    CHAR(7)    NOT    NULL,
    active    BOOL    NOT    NULL
    """
    name = models.CharField(
        max_length=128, null=False,
        help_text=_('Nome do Modelo de Previsão')
    )
    weeks = models.IntegerField(
        null=False, help_text=_('Total de Semanas')
    )
    commit_id = models.CharField(
        max_length=7, null=False,
        help_text=_('ID do commit (github)')
    )
    active = models.BooleanField(
        null=False,
        help_text=_('Está ativo?')
    )

    class Meta:
        db_table = 'Municipio\".\"forecast_model'
        app_label = 'dados'

    def __str__(self):
        return self.name


class ForecastCity(models.Model):
    """
    city/geocode INT NOT NULL,
    forecast_model_id INT,
    active BOOL NOT NULL,

    """
    city = models.ForeignKey(
        'dados.City', db_column='geocode', null=False,
        help_text=_('Código do Município')
    )
    active = models.BooleanField(
        null=False, default=True, help_text=_('Está Ativo?')
    )
    forecast_model = models.ForeignKey(
        'dados.ForecastModel', help_text=_('Modelo de Previsão')
    )

    class Meta:
        db_table = 'Municipio\".\"forecast_city'
        app_label = 'dados'
        verbose_name_plural = "forecast cities"
        unique_together = (('city', 'forecast_model'),)

    def __str__(self):
        return '{} - {}'.format(self.city, self.forecast_model)


class City(models.Model):
    """
    geocode INT NOT NULL,
    forecast_model_id INT,
    active BOOL NOT NULL,

    """
    geocode = models.IntegerField(
        db_column='geocodigo', null=False, primary_key=True,
        help_text=_('Código do Município')
    )
    name = models.CharField(
        db_column='nome', null=False, max_length=128,
        help_text=_('Nome do municipio')
    )

    class Meta:
        db_table = 'Dengue_global\".\"Municipio'
        app_label = 'dados'
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name
