from django.db import models
from django.utils.translation import ugettext_lazy as _


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


class CID10(models.Model):
    """
    geocode INT NOT NULL,
    forecast_model_id INT,
    active BOOL NOT NULL,

    """
    code = models.CharField(
        db_column='codigo', null=False, primary_key=True,
        max_length=512, help_text=_('Código do doença')
    )
    name = models.CharField(
        db_column='nome', null=False, max_length=512,
        help_text=_('Nome da doença')
    )

    class Meta:
        db_table = 'Dengue_global\".\"CID10'
        app_label = 'dados'
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name
