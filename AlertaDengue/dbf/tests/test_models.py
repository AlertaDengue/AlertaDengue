import os
import unittest
from datetime import date

# local
from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.test import TestCase
from mock import patch

DBF = apps.get_model("dbf", "DBF")

__all__ = ["DBFModelTest"]

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data/")


@unittest.skip("reason='Issue #416'")
class DBFModelTest(TestCase):
    fixtures = ["users"]

    def test_notification_year_cant_be_greater_than_current_year(self):
        with open(os.path.join(TEST_DATA_DIR, "simple.dbf"), "rb") as fp:
            dbf = DBF.objects.create(
                uploaded_by=User.objects.all()[0],
                file=File(fp, name="simple.dbf"),
                export_date=date.today(),
                notification_year=date.today().year + 1,
                abbreviation="RJ",
            )
            with self.assertRaises(ValidationError):
                dbf.clean()

    @patch("dbf.models.is_valid_dbf")
    def test_raises_error_if_dbf_is_invalid(self, mocked_validation):
        mocked_validation.return_value = False
        with open(os.path.join(TEST_DATA_DIR, "invalid.dbf"), "rb") as fp:
            dbf = DBF.objects.create(
                uploaded_by=User.objects.all()[0],
                file=File(fp, name="invalid.dbf"),
                export_date=date.today(),
                notification_year=date.today().year,
                abbreviation="RJ",
            )
            with self.assertRaises(ValidationError):
                dbf.clean()
