from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase

from datetime import date
from io import StringIO
from mock import patch

from dbf.models import DBF

__all__ = ["DBFModelTest"]

class DBFModelTest(TestCase):
    fixtures = ['users']

    def test_notification_year_cant_be_greater_than_current_year(self):
        fake_file = StringIO("42")
        dbf = DBF.objects.create(
            uploaded_by=User.objects.all()[0],
            file=InMemoryUploadedFile(fake_file, 'file', 'file.dbf',
            'application/dbf', 4, 'utf-8'),
            export_date=date.today(),
            notification_year=date.today().year + 1
        )
        with self.assertRaises(ValidationError):
            dbf.clean()

    @patch('dbf.models.is_valid_dbf')
    def test_raises_error_if_dbf_is_invalid(self, mocked_validation):
        mocked_validation.return_value = False
        fake_file = StringIO("Invalid dbf")
        dbf = DBF.objects.create(
            uploaded_by=User.objects.all()[0],
            file=InMemoryUploadedFile(fake_file, 'file', 'file.dbf',
            'application/dbf', 4, 'utf-8'),
            export_date=date.today(),
            notification_year=date.today().year
        )
        with self.assertRaises(ValidationError):
            dbf.clean()
