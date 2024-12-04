from django.contrib.auth import get_user_model

from . import models


User = get_user_model()


class SINANForm(forms.Form):
    uploaded_by = forms.ModelChoiceField(
        queryset=User.objects.all(), widget=forms.HiddenInput()
    )
    chunked_upload_id = forms.IntegerField(
        required=False, widget=forms.HiddenInput()
    )
    filename = forms.CharField(required=False, widget=forms.HiddenInput())
    export_date = forms.DateField(label=_("Data da exportação"))
    notification_year = forms.IntegerField(label=_("Ano de notificação"))
    abbreviation = forms.ChoiceField(
        choices=models.SINANUpload.UFs, label=_("Abrangência")
    )
    municipio = forms.CharField(
        label=_("Nome do município (opcional)"), required=False
    )

    def clean(self):
        cleaned_data = super(DBFForm, self).clean()
        chunked_upload_id = cleaned_data.get("chunked_upload_id")
        user = cleaned_data.get("uploaded_by")
        # If the user tries to give the id of a chunked_upload by
        # another user, or an inexistent id, we raise a validation
        # error.
        try:
            uploaded_file = DBFChunkedUpload.objects.get(
                id=chunked_upload_id, user=user
            )
        except DBF.DoesNotExist:
            raise ValidationError(
                _(
                    "Houve um erro durante o envio do arquivo. "
                    "Por favor, tente novamente."
                )
            )
        # This might be a performance problem for really large DBFs
        # is_valid_dbf(uploaded_file.file, cleaned_data["notification_year"])
        return cleaned_data
