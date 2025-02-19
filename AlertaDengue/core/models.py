from django.db import models


class HistoricoAlerta(models.Model):
    """
    Resultados do alerta para Dengue, conforme publicado.

    NOTE: It should run with `migrate --fake` due to previously populated table
    """
    id = models.BigAutoField(primary_key=True)
    municipio_geocodigo = models.IntegerField(null=False)
    SE = models.IntegerField(null=False)
    data_iniSE = models.DateField(null=False)
    casos_est = models.FloatField(null=True, blank=True)
    casos_est_min = models.IntegerField(null=True, blank=True)
    casos_est_max = models.IntegerField(null=True, blank=True)
    casos = models.IntegerField(null=True, blank=True)
    p_rt1 = models.FloatField(null=True, blank=True)
    p_inc100k = models.FloatField(null=True, blank=True)
    Localidade_id = models.IntegerField(null=True, blank=True)
    nivel = models.SmallIntegerField(null=True, blank=True)
    versao_modelo = models.CharField(max_length=40, null=True, blank=True)
    municipio_nome = models.CharField(max_length=128, null=True, blank=True)
    tweet = models.DecimalField(
        max_digits=5, decimal_places=0, null=True, blank=True
    )
    Rt = models.FloatField(null=True, blank=True)
    pop = models.DecimalField(
        max_digits=20, decimal_places=0, null=True, blank=True
    )
    tempmin = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    umidmax = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    receptivo = models.SmallIntegerField(null=True, blank=True)
    transmissao = models.SmallIntegerField(null=True, blank=True)
    nivel_inc = models.SmallIntegerField(null=True, blank=True)
    umidmed = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    umidmin = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tempmed = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    tempmax = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    casprov = models.IntegerField(null=True, blank=True)
    casprov_est = models.FloatField(null=True, blank=True)
    casprov_est_min = models.IntegerField(null=True, blank=True)
    casprov_est_max = models.IntegerField(null=True, blank=True)
    casconf = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = '"Municipio"."Historico_alerta"'
        indexes = [
            models.Index(fields=["data_iniSE"], name="Alerta_idx_data"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["SE", "municipio_geocodigo", "Localidade_id"],
                name="alertas_unicos"
            )
        ]


class HistoricoAlertaChik(models.Model):
    """
    Resultados do alerta para Chikungunya, conforme publicado.

    NOTE: It should run with `migrate --fake` due to previously populated table
    """
    id = models.BigIntegerField(primary_key=True)
    municipio_geocodigo = models.IntegerField(null=False)
    SE = models.IntegerField(null=False)
    data_iniSE = models.DateField(null=False)
    casos_est = models.FloatField(null=True, blank=True)
    casos_est_min = models.IntegerField(null=True, blank=True)
    casos_est_max = models.IntegerField(null=True, blank=True)
    casos = models.IntegerField(null=True, blank=True)
    p_rt1 = models.FloatField(null=True, blank=True)
    p_inc100k = models.FloatField(null=True, blank=True)
    Localidade_id = models.IntegerField(null=True, blank=True)
    nivel = models.SmallIntegerField(null=True, blank=True)
    versao_modelo = models.CharField(max_length=40, null=True, blank=True)
    municipio_nome = models.CharField(
        max_length=128, null=True, blank=True
    )
    tweet = models.DecimalField(
        max_digits=5, decimal_places=0, null=True, blank=True
    )
    Rt = models.FloatField(null=True, blank=True)
    pop = models.DecimalField(
        max_digits=15, decimal_places=5, null=True, blank=True
    )
    tempmin = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    umidmax = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    receptivo = models.SmallIntegerField(null=True, blank=True)
    transmissao = models.SmallIntegerField(null=True, blank=True)
    nivel_inc = models.SmallIntegerField(null=True, blank=True)
    umidmed = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    umidmin = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    tempmed = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    tempmax = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    casprov = models.IntegerField(null=True, blank=True)
    casprov_est = models.FloatField(null=True, blank=True)
    casprov_est_min = models.IntegerField(null=True, blank=True)
    casprov_est_max = models.IntegerField(null=True, blank=True)
    casconf = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = '"Municipio"."Historico_alerta_chik"'
        indexes = [
            models.Index(fields=["data_iniSE"], name="Alerta_chik_idx_data"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["SE", "municipio_geocodigo", "Localidade_id"],
                name="alertas_unicos_chik"
            )
        ]


class HistoricoAlertaZika(models.Model):
    """
    Resultados do alerta para Zika, conforme publicado.

    NOTE: It should run with `migrate --fake` due to previously populated table
    """
    id = models.BigIntegerField(primary_key=True)
    municipio_geocodigo = models.IntegerField(null=False)
    SE = models.IntegerField(null=False)
    data_iniSE = models.DateField(null=False)
    casos_est = models.FloatField(null=True, blank=True)
    casos_est_min = models.IntegerField(null=True, blank=True)
    casos_est_max = models.IntegerField(null=True, blank=True)
    casos = models.IntegerField(null=True, blank=True)
    p_rt1 = models.FloatField(null=True, blank=True)
    p_inc100k = models.FloatField(null=True, blank=True)
    Localidade_id = models.IntegerField(null=True, blank=True)
    nivel = models.SmallIntegerField(null=True, blank=True)
    versao_modelo = models.CharField(max_length=40, null=True, blank=True)
    municipio_nome = models.CharField(
        max_length=128, null=True, blank=True
    )
    tweet = models.DecimalField(
        max_digits=5, decimal_places=0, null=True, blank=True
    )
    Rt = models.FloatField(null=True, blank=True)
    pop = models.DecimalField(
        max_digits=15, decimal_places=5, null=True, blank=True
    )
    tempmin = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    umidmax = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    receptivo = models.SmallIntegerField(null=True, blank=True)
    transmissao = models.SmallIntegerField(null=True, blank=True)
    nivel_inc = models.SmallIntegerField(null=True, blank=True)
    umidmed = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    umidmin = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    tempmed = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    tempmax = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    casprov = models.IntegerField(null=True, blank=True)
    casprov_est = models.FloatField(null=True, blank=True)
    casprov_est_min = models.IntegerField(null=True, blank=True)
    casprov_est_max = models.IntegerField(null=True, blank=True)
    casconf = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = '"Municipio"."Historico_alerta_zika"'
        indexes = [
            models.Index(fields=["data_iniSE"], name="Alerta_zika_idx_data"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["SE", "municipio_geocodigo", "Localidade_id"],
                name="alertas_unicos_zika"
            )
        ]
