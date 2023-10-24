from django.db import models


class HistoricoAlerta(models.Model):
    """
    "Municipio"."Historico_alerta"
    """
    data_iniSE = models.DateField(null=False, db_column="data_iniSE")
    SE = models.IntegerField(null=False, db_column="SE")
    casos_est = models.FloatField(db_column="casos_est")
    casos_est_min = models.IntegerField(db_column="casos_est_min")
    casos_est_max = models.IntegerField(db_column="casos_est_max")
    casos = models.IntegerField(db_column="casos")
    municipio_geocodigo = models.IntegerField(
        null=False, db_column="municipio_geocodigo"
    )
    p_rt1 = models.FloatField(db_column="p_rt1")
    p_inc100k = models.FloatField(db_column="p_inc100k")
    Localidade_id = models.IntegerField(db_column="Localidade_id")
    nivel = models.SmallIntegerField(db_column="nivel")
    id = models.BigAutoField(primary_key=True, db_column="id")
    versao_modelo = models.CharField(max_length=40, db_column="versao_modelo")
    municipio_nome = models.CharField(
        max_length=128, db_column="municipio_nome")
    tweet = models.DecimalField(
        max_digits=5, decimal_places=0, null=True, default=None, db_column="tweet"
    )
    Rt = models.FloatField(null=True, default=None, db_column="Rt")
    pop = models.DecimalField(max_digits=10, decimal_places=0, db_column="pop")
    tempmin = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="tempmin")
    umidmax = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="umidmax")
    receptivo = models.SmallIntegerField(db_column="receptivo")
    transmissao = models.SmallIntegerField(db_column="transmissao")
    nivel_inc = models.SmallIntegerField(db_column="nivel_inc")
    umidmed = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="umidmed")
    umidmin = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="umidmin")
    tempmed = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="tempmed")
    tempmax = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="tempmax")
    casprov = models.IntegerField(db_column="casprov")
    casprov_est = models.FloatField(db_column="casprov_est")
    casprov_est_min = models.IntegerField(db_column="casprov_est_min")
    casprov_est_max = models.IntegerField(db_column="casprov_est_max")
    casconf = models.IntegerField(db_column="casconf")

    class Meta:
        db_table = '"Municipio"."Historico_alerta"'


class HistoricoAlertaChik(models.Model):
    """
    "Municipio"."Historico_alerta_chik"
    """
    data_iniSE = models.DateField(null=False, db_column="data_iniSE")
    SE = models.IntegerField(null=False, db_column="SE")
    casos_est = models.FloatField(db_column="casos_est")
    casos_est_min = models.IntegerField(db_column="casos_est_min")
    casos_est_max = models.IntegerField(db_column="casos_est_max")
    casos = models.IntegerField(db_column="casos")
    municipio_geocodigo = models.IntegerField(
        null=False, db_column="municipio_geocodigo"
    )
    p_rt1 = models.FloatField(db_column="p_rt1")
    p_inc100k = models.FloatField(db_column="p_inc100k")
    Localidade_id = models.IntegerField(db_column="Localidade_id")
    nivel = models.SmallIntegerField(db_column="nivel")
    id = models.BigAutoField(primary_key=True, db_column="id")
    versao_modelo = models.CharField(max_length=40, db_column="versao_modelo")
    municipio_nome = models.CharField(
        max_length=128, db_column="municipio_nome")
    tweet = models.DecimalField(
        max_digits=5, decimal_places=0, null=True, default=None, db_column="tweet"
    )
    Rt = models.FloatField(null=True, default=None, db_column="Rt")
    pop = models.DecimalField(max_digits=10, decimal_places=0, db_column="pop")
    tempmin = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="tempmin")
    umidmax = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="umidmax")
    receptivo = models.SmallIntegerField(db_column="receptivo")
    transmissao = models.SmallIntegerField(db_column="transmissao")
    nivel_inc = models.SmallIntegerField(db_column="nivel_inc")
    umidmed = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="umidmed")
    umidmin = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="umidmin")
    tempmed = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="tempmed")
    tempmax = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="tempmax")
    casprov = models.IntegerField(db_column="casprov")
    casprov_est = models.FloatField(db_column="casprov_est")
    casprov_est_min = models.IntegerField(db_column="casprov_est_min")
    casprov_est_max = models.IntegerField(db_column="casprov_est_max")
    casconf = models.IntegerField(db_column="casconf")

    class Meta:
        db_table = '"Municipio"."Historico_alerta_chik"'


class HistoricoAlertaZika(models.Model):
    """
    "Municipio"."Historico_alerta_zika"
    """
    data_iniSE = models.DateField(null=False, db_column="data_iniSE")
    SE = models.IntegerField(null=False, db_column="SE")
    casos_est = models.FloatField(db_column="casos_est")
    casos_est_min = models.IntegerField(db_column="casos_est_min")
    casos_est_max = models.IntegerField(db_column="casos_est_max")
    casos = models.IntegerField(db_column="casos")
    municipio_geocodigo = models.IntegerField(
        null=False, db_column="municipio_geocodigo"
    )
    p_rt1 = models.FloatField(db_column="p_rt1")
    p_inc100k = models.FloatField(db_column="p_inc100k")
    Localidade_id = models.IntegerField(db_column="Localidade_id")
    nivel = models.SmallIntegerField(db_column="nivel")
    id = models.BigAutoField(primary_key=True, db_column="id")
    versao_modelo = models.CharField(max_length=40, db_column="versao_modelo")
    municipio_nome = models.CharField(
        max_length=128, db_column="municipio_nome")
    tweet = models.DecimalField(
        max_digits=5, decimal_places=0, null=True, default=None, db_column="tweet"
    )
    Rt = models.FloatField(null=True, default=None, db_column="Rt")
    pop = models.DecimalField(max_digits=10, decimal_places=0, db_column="pop")
    tempmin = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="tempmin")
    umidmax = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="umidmax")
    receptivo = models.SmallIntegerField(db_column="receptivo")
    transmissao = models.SmallIntegerField(db_column="transmissao")
    nivel_inc = models.SmallIntegerField(db_column="nivel_inc")
    umidmed = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="umidmed")
    umidmin = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="umidmin")
    tempmed = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="tempmed")
    tempmax = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="tempmax")
    casprov = models.IntegerField(db_column="casprov")
    casprov_est = models.FloatField(db_column="casprov_est")
    casprov_est_min = models.IntegerField(db_column="casprov_est_min")
    casprov_est_max = models.IntegerField(db_column="casprov_est_max")
    casconf = models.IntegerField(db_column="casconf")

    class Meta:
        db_table = '"Municipio"."Historico_alerta_zika"'
