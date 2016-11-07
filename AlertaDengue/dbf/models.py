from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from datetime import date
from chunked_upload.models import ChunkedUpload

from dbf.validation import is_valid_dbf

def current_year():
    return date.today().year

class DBF(models.Model):
    uploaded_by = models.ForeignKey('auth.User')
    file = models.FileField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    export_date = models.DateField()
    notification_year = models.IntegerField(default=current_year)

    def clean(self):
        if self.notification_year > date.today().year:
            raise ValidationError({"notification_year": _("Notification year "
            "cannot be greater than current year")})

        if not is_valid_dbf(self.file, self.notification_year):
            raise ValidationError({"file": _("Invalid DBF file")})

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
