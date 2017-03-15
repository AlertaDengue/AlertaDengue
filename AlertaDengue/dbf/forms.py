from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from dbf.models import DBF, DBFChunkedUpload
from dbf.validation import is_valid_dbf


class DBFForm(forms.Form):
    uploaded_by = forms.ModelChoiceField(queryset=User.objects.all(), widget=forms.HiddenInput())
    chunked_upload_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    filename = forms.CharField(required=False, widget=forms.HiddenInput())
    export_date = forms.DateField(label=_("Data da exportação"))
    notification_year = forms.IntegerField(label=_("Ano de notificação"))
    state_abbreviation = forms.ChoiceField(choices=(
        (None, ''), ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'),
        ('AM', 'Amazonas'),
        ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'),
        ('ES', 'Espírito Santo'), ('GO', 'Goiás'), ('MA', 'Maranhão'),
        ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
        ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'),
        ('PR', 'Paraná'), ('PE', 'Pernambuco'), ('PI', 'Piauí'),
        ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
        ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'),
        ('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'),
        ('TO', 'Tocantins')
    ), required=False, label=_("U.F."))

    def clean(self):
        cleaned_data = super(DBFForm, self).clean()
        chunked_upload_id = cleaned_data.get('chunked_upload_id')
        user = cleaned_data.get('uploaded_by')
        # If the user tries to give the id of a chunked_upload by
        # another user, or an inexistent id, we raise a validation
        # error.
        try:
            uploaded_file = DBFChunkedUpload.objects.get(id=chunked_upload_id, user=user)
        except DBF.DoesNotExist:
            raise ValidationError(_("Houve um erro durante o envio do arquivo. "
                    "Por favor, tente novamente."))
        # This might be a performance problem for really large DBFs
        is_valid_dbf(uploaded_file.file, cleaned_data['notification_year'])
        return cleaned_data
