from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files import File
from django.test import TestCase

from datetime import date
import os

from dbf.models import DBF
from dbf.validation import is_valid_dbf


__all__ = ["DBFValidationTest"]

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data/")

class DBFValidationTest(TestCase):
    fixtures = ['users']

    def _get_file_from_filename(self, filename):
        with open(os.path.join(TEST_DATA_DIR, filename), "rb") as fp:
            dbf = DBF.objects.create(
                uploaded_by=User.objects.all()[0],
                file=File(fp, name=filename),
                export_date=date.today(),
                notification_year=date.today().year + 1
            )
        return dbf.file

    def test_valid_dbf_returns_true(self):
        valid_file = self._get_file_from_filename("simple.dbf")
        self.assertTrue(is_valid_dbf(valid_file))

    def test_invalid_dbf_raises_ValidationError(self):
        """If the file is not in dbf format, we should raise an error."""

        invalid_file = self._get_file_from_filename("invalid.dbf")
        with self.assertRaises(ValidationError):
            is_valid_dbf(invalid_file)

    def test_dbf_without_an_expected_column_raises_ValidationError(self):
        """
        If the file does not have all columns we expect in a SINAN file, we
        should raise an error.
        """

        missing_column_file = self._get_file_from_filename("missing_nu_ano.dbf")
        with self.assertRaises(ValidationError):
            is_valid_dbf(missing_column_file)
