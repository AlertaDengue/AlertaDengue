from django import forms

from dbf.models import DBF


class DBFForm(forms.ModelForm):
    class Meta:
        model = DBF
        widgets = {"uploaded_by": forms.HiddenInput()}
        fields = ["uploaded_by", "file", "export_date", "notification_year"]
