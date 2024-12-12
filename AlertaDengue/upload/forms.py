from datetime import date

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
    cid10 = forms.ChoiceField(
        choices=models.SINANUpload.CID10,
        label=_("CID10"),
        initial=models.SINANUpload.CID10[0][0],
    )
    notification_year = forms.IntegerField(
        label=_("Ano de notificação"),
        initial=date.today().year
    )
    uf = forms.ChoiceField(
        choices=models.SINANUpload.UFs,
        label=_("Abrangência"),
        required=False,
        initial=None
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
