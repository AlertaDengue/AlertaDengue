from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from . import models


User = get_user_model()


class SINANForm(forms.Form):
    uploaded_by = forms.ModelChoiceField(
        queryset=User.objects.all(), widget=forms.HiddenInput()
    )
    upload_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    filename = forms.CharField(required=False, widget=forms.HiddenInput())
    export_date = forms.DateField(label=_("Data da exportação"))
    notification_year = forms.IntegerField(label=_("Ano de notificação"))
    abbreviation = forms.ChoiceField(
        choices=models.SINANUpload.UFs,
        label=_("Abrangência"),
        required=False
    )
    municipio = forms.CharField(
        label=_("Nome do município (opcional)"),
        required=False,
    )

    def clean(self):
        data = super().clean()
        try:
            uploaded_file = models.SINANChunkedUpload.objects.get(
                id=data["upload_id"], user=data["uploaded_by"]
            )
        except models.SINANChunkedUpload.DoesNotExist:
            raise ValidationError(
                _(
                    "Houve um erro durante o envio do arquivo. "
                    "Por favor, tente novamente."
                )
            )
        # This might be a performance problem for really large DBFs
        # is_valid_dbf(uploaded_file.file, cleaned_data["notification_year"])
        return data
