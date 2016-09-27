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
                notification_year=date.today().year,
            )
        return dbf.file

    def test_valid_dbf_returns_true(self):
        valid_file = self._get_file_from_filename("simple.dbf")
        self.assertTrue(is_valid_dbf(valid_file, 2016))

    def test_invalid_dbf_raises_ValidationError(self):
        """If the file is not in dbf format, we should raise an error."""

        invalid_file = self._get_file_from_filename("invalid.dbf")
        with self.assertRaises(ValidationError):
            is_valid_dbf(invalid_file, 2016)

    def test_dbf_without_an_expected_column_raises_ValidationError(self):
        """
        If the file does not have all columns we expect in a SINAN file, we
        should raise an error.
        """

        missing_column_file = self._get_file_from_filename("missing_nu_ano.dbf")
        with self.assertRaises(ValidationError):
            is_valid_dbf(missing_column_file, 2016)

    def test_dbf_with_records_from_year_other_than_the_one_specified_raises_ValidationError(self):
        """
        If the file has records pointing to an year other than the one
        specified we should also raise a ValidationError.
        """

        missing_column_file = self._get_file_from_filename("simple.dbf")
        notification_year = 2015

        with self.assertRaises(ValidationError):
            is_valid_dbf(missing_column_file, notification_year)

    def test_dbf_with_mixed_notification_years_raises_ValidationError(self):
        """
        The notification year validation should be triggered even if some of
        the data is poiting to the correct year
        """

        missing_column_file = self._get_file_from_filename("mixed_notification_years.dbf")
        notification_year = 2015

        with self.assertRaises(ValidationError):
            is_valid_dbf(missing_column_file, notification_year)
