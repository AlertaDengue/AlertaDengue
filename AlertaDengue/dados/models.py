from django.db import models
# from django.core.exceptions import ValidationError
# from django.utils.translation import ugettext_lazy as _
from dados.dbdata import get_city_name_by_id


class ForecastModel(models.Model):
    """
    id    SERIAL    PRIMARY    KEY,
    name    VARCHAR(128)    NOT    NULL,
    total_weeks   SMALLINT    NOT    NULL,
    commit_id    CHAR(7)    NOT    NULL,
    active    BOOL    NOT    NULL
    """
    name = models.CharField(max_length=128, null=False)
    total_weeks = models.IntegerField(null=False)
    commit_id = models.CharField(max_length=7, null=False)
    active = models.BooleanField(null=False)

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
    geoid = models.IntegerField(null=False, primary_key=True)
    active = models.BooleanField(null=False, default=True)
    forecast_model = models.ForeignKey('dados.ForecastModel')

    class Meta:
        db_table = 'Municipio\".\"forecast_city'
        verbose_name_plural = "forecast cities"
        unique_together = (('geoid', 'forecast_model'),)

    def __str__(self):
        return '{} - {}'.format(
            get_city_name_by_id(self.geoid),
            self.forecast_model
        )

