from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from datetime import date

def current_year():
    return date.today().year

def is_valid_dbf(dbf_file):
    # This is a placeholder for now. We will bring the validation functionality
    # from `load_sinan.py` to this function.
    return True

class DBF(models.Model):
    file = models.FileField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    export_date = models.DateField()
    notification_year = models.IntegerField(default=current_year)

    def clean(self):
        if self.notification_year > date.today().year:
            raise ValidationError({"notification_year": _("Notification year "
            "cannot be greater than current year")})

        if not is_valid_dbf(self.file):
            raise ValidationError({"file": _("Invalid DBF file")})

    def __str__(self):
        return "{} - {}".format(self.file, self.notification_year)
