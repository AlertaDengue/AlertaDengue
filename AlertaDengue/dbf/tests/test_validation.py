from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files import File
from django.test import TestCase
from datetime import date
# local
from ..models import DBF
from ..validation import is_valid_dbf

import datetime
import os

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

    def test_ID_MUNICIP_can_be_called_ID_MN_RESI(self):
        """
        The ID_MUNICIP collumn can also be named ID_MN_RESI
        """

        mn_resid_file = self._get_file_from_filename("id_mn_resi.dbf")
        self.assertTrue(is_valid_dbf(mn_resid_file, 2016))

    def test_can_receive_file_with_name_that_does_not_exist(self):
        """
        This is a regression test. We had an error because we were testing this
        function with data that was already saved to disk. In the upload
        process, what happens is more similiar to what is happening in this
        test: the instance exists, but was never saved to disk, so calling
        `dbf.file.path` would return a path that had no file there (because the
        save process was not complete yet).
        """
        inexistent_filename = "{}.dbf".format(datetime.datetime.now())
        with open(os.path.join(TEST_DATA_DIR, "simple.dbf"), "rb") as fp:
            # Instead of using ".objects.create()" we only instantiate the file.
            # This will trigger the error when calling dbf.clean() on an
            # unsaved instance.
            dbf = DBF(
                uploaded_by=User.objects.all()[0],
                file=File(fp, name=inexistent_filename),
                export_date=date.today(),
                notification_year=date.today().year
            )
            self.assertTrue(is_valid_dbf(dbf.file, dbf.notification_year))

    def test_dbf_with_wrong_date_datatypes_raises_ValidationError(self):
        """
        The notification year validation should be triggered even if some of
        the data is poiting to the correct year
        """

        wrong_data_type_file = self._get_file_from_filename("wrong_date_datatype.dbf")
        notification_year = 2015

        with self.assertRaises(ValidationError):
            is_valid_dbf(wrong_data_type_file, notification_year)
