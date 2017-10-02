from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from bootstrap3.renderers import FormRenderer

from .models import DBF, DBFChunkedUpload
from .validation import is_valid_dbf


class DBFForm(forms.Form):
    uploaded_by = forms.ModelChoiceField(
        queryset=User.objects.all(), widget=forms.HiddenInput()
    )
    chunked_upload_id = forms.IntegerField(
        required=False, widget=forms.HiddenInput()
    )
    filename = forms.CharField(required=False, widget=forms.HiddenInput())
    export_date = forms.DateField(label=_("Data da exportação"))
    notification_year = forms.IntegerField(label=_("Ano de notificação"))
    state_abbreviation = forms.ChoiceField(
        choices=DBF.STATE_ABBREVIATION_CHOICES, label=_("U.F.")
    )
    municipio = forms.CharField(
        label=_("Nome do município (opcional)"),  required=False
    )

    def clean(self):
        cleaned_data = super(DBFForm, self).clean()
        chunked_upload_id = cleaned_data.get('chunked_upload_id')
        user = cleaned_data.get('uploaded_by')
        # If the user tries to give the id of a chunked_upload by
        # another user, or an inexistent id, we raise a validation
        # error.
        try:
            uploaded_file = DBFChunkedUpload.objects.get(
                id=chunked_upload_id, user=user
            )
        except DBF.DoesNotExist:
            raise ValidationError(
                _("Houve um erro durante o envio do arquivo. "
                  "Por favor, tente novamente."))
        # This might be a performance problem for really large DBFs
        is_valid_dbf(uploaded_file.file, cleaned_data['notification_year'])
        return cleaned_data


class FormRendererWithHiddenFieldErrors(FormRenderer):

    def get_fields_errors(self):
        form_errors = []
        for field in self.form:
            if field.errors:
                form_errors += field.errors
        return form_errors
