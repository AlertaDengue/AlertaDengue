from django.db import models
from django.utils.translation import ugettext_lazy as _
#local
from .dbdata import get_city_name_by_id


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

    def __str__(self):
        return self.name


class ForecastCity(models.Model):
    """
    geoid INT NOT NULL,
    forecast_model_id INT,
    active BOOL NOT NULL,

    """
    geocode = models.IntegerField(
        null=False, help_text=_('Código do Município')
    )
    active = models.BooleanField(
        null=False, default=True, help_text=_('Está Ativo?')
    )
    forecast_model = models.ForeignKey(
        'dados.ForecastModel', help_text=_('Modelo de Previsão')
    )

    class Meta:
        db_table = 'Municipio\".\"forecast_city'
        verbose_name_plural = "forecast cities"
        unique_together = (('geocode', 'forecast_model'),)

    def __str__(self):
        return '{} - {}'.format(
            get_city_name_by_id(self.geocode),
            self.forecast_model
        )

