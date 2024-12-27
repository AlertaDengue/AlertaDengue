from pathlib import Path
from datetime import date

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from chunked_upload.models import BaseChunkedUpload

from dados.models import City


User = get_user_model()


def _get_upload_storage_path() -> str:
    return str(Path(settings.DBF_SINAN) / "imported")


class SINANChunkedUpload(BaseChunkedUpload):
    user = models.ForeignKey(
        User,
        related_name='sinan_chunks',
        on_delete=models.PROTECT
    )


class SINANUpload(models.Model):
    UFs = [
        (None, "Brasil"),
        ("AC", "Acre"),
        ("AL", "Alagoas"),
        ("AP", "Amapá"),
        ("AM", "Amazonas"),
        ("BA", "Bahia"),
        ("CE", "Ceará"),
        ("DF", "Distrito Federal"),
        ("ES", "Espírito Santo"),
        ("GO", "Goiás"),
        ("MA", "Maranhão"),
        ("MT", "Mato Grosso"),
        ("MS", "Mato Grosso do Sul"),
        ("MG", "Minas Gerais"),
        ("PA", "Pará"),
        ("PB", "Paraíba"),
        ("PR", "Paraná"),
        ("PE", "Pernambuco"),
        ("PI", "Piauí"),
        ("RJ", "Rio de Janeiro"),
        ("RN", "Rio Grande do Norte"),
        ("RS", "Rio Grande do Sul"),
        ("RO", "Rondônia"),
        ("RR", "Roraima"),
        ("SC", "Santa Catarina"),
        ("SP", "São Paulo"),
        ("SE", "Sergipe"),
        ("TO", "Tocantins"),
    ]

    CID10 = [
        ("A90", "Dengue"),
        ("A92.0", "Chikungunya"),
        ("A928", "Zika")
    ]

    cid10 = models.CharField(max_length=5, null=False, choices=CID10)
    uf = models.CharField(max_length=2, null=True, choices=UFs)
    year = models.IntegerField(null=False)
    upload = models.ForeignKey(
        SINANChunkedUpload,
        on_delete=models.PROTECT,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.upload.filename}"

    def validate(self):
        self._validate_year()

    def _validate_year(self):
        if self.year > date.today().year:
            raise ValidationError(
                {
                    "notification_year": _(
                        "O ano de notificação "
                        "não pode ser maior do que o ano atual"
                    )
                }
            )

    class Meta:
        app_label = "upload"


class SINANUploadHistory(models.Model):
    """
    Stores the History of SINAN inserts on "Municipio"."Notificacao". Each
    objects represent an inserted row (id) and points to SINANUpload
    """
    notificacao_id = models.BigIntegerField(null=False)
    upload = models.ForeignKey(
        SINANUpload,
        on_delete=models.PROTECT,
        related_name="notificacoes",
        null=False
    )
