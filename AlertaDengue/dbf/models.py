from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from datetime import date
from chunked_upload.models import ChunkedUpload

from .validation import is_valid_dbf


def current_year():
    return date.today().year


class DBF(models.Model):
    STATE_ABBREVIATION_CHOICES = (
        (None, ''),
        ('AC', 'Acre'),
        ('AL', 'Alagoas'),
        ('AP', 'Amapá'),
        ('AM', 'Amazonas'),
        ('BA', 'Bahia'),
        ('CE', 'Ceará'),
        ('DF', 'Distrito Federal'),
        ('ES', 'Espírito Santo'),
        ('GO', 'Goiás'),
        ('MA', 'Maranhão'),
        ('MT', 'Mato Grosso'),
        ('MS', 'Mato Grosso do Sul'),
        ('MG', 'Minas Gerais'),
        ('PA', 'Pará'),
        ('PB', 'Paraíba'),
        ('PR', 'Paraná'),
        ('PE', 'Pernambuco'),
        ('PI', 'Piauí'),
        ('RJ', 'Rio de Janeiro'),
        ('RN', 'Rio Grande do Norte'),
        ('RS', 'Rio Grande do Sul'),
        ('RO', 'Rondônia'),
        ('RR', 'Roraima'),
        ('SC', 'Santa Catarina'),
        ('SP', 'São Paulo'),
        ('SE', 'Sergipe'),
        ('TO', 'Tocantins')
    )

    uploaded_by = models.ForeignKey('auth.User')
    file = models.FileField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    export_date = models.DateField()
    notification_year = models.IntegerField(default=current_year)
    state_abbreviation = models.CharField(
        max_length=2, null=True, choices=STATE_ABBREVIATION_CHOICES
    )
    municipio = models.CharField(max_length=255, blank=True, default="")

    def clean(self):
        if self.notification_year > date.today().year:
            raise ValidationError({"notification_year": _("O ano de notificação "
                        "não pode ser maior do que o ano atual")})

        if not is_valid_dbf(self.file, self.notification_year):
            raise ValidationError({"file": _("Arquivo DBF inválido")})

    def __str__(self):
        return "{} - {}".format(self.file, self.notification_year)


class DBFChunkedUpload(ChunkedUpload):
    """
    For now we need to create our own subclass of ChunkedUpload
    because the chunked_upload package does not provide migrations.
    As soon as
    https://github.com/juliomalegria/django-chunked-upload/pull/21 is
    merged, we can remove this.
    """
    pass
