"""Django-owned models in the ``episcanner`` schema."""

from django.db import models

from .dengue_global import City


class EpiscannerSirParams(models.Model):
    """Existing managed application model; ownership is intentionally unchanged."""

    cid10 = models.CharField(max_length=10)
    geocode = models.ForeignKey(
        City,
        to_field="geocode",
        db_column="geocode",
        on_delete=models.DO_NOTHING,
    )
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
    t_ini = models.IntegerField(null=True, blank=True)
    t_end = models.IntegerField(null=True, blank=True)

    class Meta:
        app_label = "dados"
        db_table = '"episcanner"."sir_params"'
        constraints = [
            models.UniqueConstraint(
                fields=["cid10", "geocode", "year"],
                name="uq_sir_params_cid10_geocode_year",
            )
        ]
