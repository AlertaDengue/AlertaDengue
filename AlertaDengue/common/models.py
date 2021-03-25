from django.db import models


# Create your models here.
class RequestPartnerData(models.Model):
    STATUS_CHOICES = [
        (True, 'Enable'),
        (False, 'Disable'),
    ]

    geocode = models.CharField(help_text='geocodigo', max_length=7)
    name = models.CharField(help_text='nome', max_length=30)
    abbreviation = models.CharField(help_text='uf', max_length=5)
    level = models.CharField(help_text='nível de atuação', max_length=10)
    contact = models.EmailField(help_text='e-mail', max_length=50)
    status = models.BooleanField(
        null=False, choices=STATUS_CHOICES, help_text='Está ativo?'
    )

    class Meta:
        app_label = 'common'
        verbose_name_plural = "Request Partner Data"

    def __str__(self):
        return f'{self.geocode}, {self.name}'
