"""
Added into the first migration file:

migrations.RunSQL(
    "CREATE SCHEMA IF NOT EXISTS forecast"
),

"""
# from django.apps import apps
from django.db import models
from django.utils.translation import ugettext_lazy as _


# City = apps.get_model('dados', 'City')


class Forecast_table(models.Model):
    """
    """

    id = models.AutoField(primary_key=True)  # (serial)
    model = models.ForeignKey(
        'ForecastModel', on_delete=models.CASCADE, null=True
    )  # (foreign key to the models table)
    se = models.IntegerField(
        null=False, help_text=_('Epidemiological Week')
    )  # Epid. week when the prediction was generated
    se_predicted = models.IntegerField(
        null=False, help_text=_('Predicted Week')
    )  # (integer) Epid. week predicted

    class Meta:
        db_table = 'forecast"."forecast_predicted'
        app_label = 'forecast'

    def __str__(self):
        return self.municipio_geocodigo


class ForecastModel(models.Model):
    """
    """

    id = models.AutoField(primary_key=True)  # id (serial)
    name = models.CharField(
        max_length=128, null=False, help_text=_('Forecast Model Name')
    )
    github = models.URLField(
        max_length=100,
        help_text='URL of the the github repo',
        default='github.com',
    )  # URL of the the github
    commit_id = models.CharField(
        max_length=7, null=False, help_text=_('ID do commit (github)')
    )
    train_start = models.DateField(
        null=True, blank=True
    )  # start date of th training period
    train_end = models.DateField(
        null=True, blank=True
    )  # end date of the training period
    filename = models.FileField(
        upload_to='uploads/%Y/%m/%d/', default='trained model'
    )  # filename of the saved trained model which will be loaded

    class Meta:
        db_table = 'forecast"."forecast_model'
        app_label = 'forecast'

    def __str__(self):
        return self.name


class ForecastCity(models.Model):
    """
    city/geocode INT NOT NULL,
    forecast_model_id INT,
    active BOOL NOT NULL,

    """

    city = models.ForeignKey(
        'dados.City',
        db_column='geocode',
        null=False,
        help_text=_('Código do Município'),
        on_delete=models.DO_NOTHING,
    )
    active = models.BooleanField(
        null=False, default=True, help_text=_('Está Ativo?')
    )
    forecast_model = models.ForeignKey(
        'forecast.ForecastModel',
        db_column='forecast_model_id',
        help_text=_('Modelo de Previsão'),
        on_delete=models.DO_NOTHING,
    )

    class Meta:
        db_table = 'forecast"."forecast_city'
        app_label = 'forecast'
        verbose_name_plural = "forecast cities"
        unique_together = (('city', 'forecast_model'),)

    def __str__(self):
        return '{} - {}'.format(self.city, self.forecast_model)


class ForecastCases(models.Model):
    """
    epiweek INT NOT NULL,
    geocode INT NOT NULL,
    cid10 character varying(5) NOT NULL,
    forecast_model_id INT,
    published_date date NOT NULL,
    init_date_epiweek date NOT NULL,
    cases INT NOT NULL,

    PRIMARY KEY (
      epiweek, geocode, cid10, forecast_model_id, published_date
    ),
    FOREIGN KEY(forecast_model_id)
      REFERENCES "Municipio".forecast_model(id),
    FOREIGN KEY(geocode)
      REFERENCES "Dengue_global"."Municipio"(geocodigo),
    FOREIGN KEY(cid10) REFERENCES "Dengue_global"."CID10"(codigo)
    """

    epiweek = models.IntegerField(
        null=False, help_text=_('Semana epidemiológica')
    )
    city = models.ForeignKey(
        'dados.City',
        db_column='geocode',
        null=False,
        help_text=_('Cidade'),
        on_delete=models.DO_NOTHING,
    )
    cid10 = models.ForeignKey(
        'dados.CID10',
        db_column='cid10',
        null=False,
        help_text=_('Doença'),
        on_delete=models.DO_NOTHING,
    )
    forecast_model = models.ForeignKey(
        'forecast.ForecastModel',
        db_column='forecast_model_id',
        null=False,
        help_text=_('Modelo de Previsão'),
        on_delete=models.DO_NOTHING,
    )
    published_date = models.DateField(
        db_column='published_date',
        null=False,
        help_text=_('Data da publicação da previsão'),
    )
    init_date_epiweek = models.DateField(
        db_column='init_date_epiweek',
        null=False,
        help_text=_('Data do inicio da semana da previsão'),
    )
    cases = models.IntegerField(null=False, help_text=_('Casos Previstos'))

    class Meta:
        db_table = 'forecast"."forecast_cases'
        app_label = 'forecast'
        verbose_name_plural = "forecast"
        unique_together = (
            ('epiweek', 'city', 'cid10', 'forecast_model', 'published_date'),
        )

    def __str__(self):
        return '{} - {} - {} - {} - {}'.format(
            self.epiweek,
            self.city,
            self.cid10,
            self.forecast_model,
            self.published_date,
        )
