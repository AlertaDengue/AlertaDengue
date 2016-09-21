from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from datetime import date

def current_year():
    return date.today().year

class DBF(models.Model):
    file = models.FileField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    export_date = models.DateField()
    notification_year = models.IntegerField(default=current_year)

    def clean(self):
        if self.notification_year > date.today().year:
            raise ValidationError({"notification_year": _("Notification year "
            "cannot be greater than current year")})

    def __str__(self):
        return "{} - {}".format(self.file, self.notification_year)
