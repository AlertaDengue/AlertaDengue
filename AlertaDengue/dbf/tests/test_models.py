import os
from django.contrib.auth.models import User
from django.core.files.base import File
from django.core.exceptions import ValidationError
from django.test import TestCase
from datetime import date
from mock import patch

# local
from django.apps import apps

DBF = apps.get_model('dbf', 'DBF')

__all__ = ["DBFModelTest"]

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data/")


class DBFModelTest(TestCase):
    fixtures = ['users']

    def test_notification_year_cant_be_greater_than_current_year(self):
        with open(os.path.join(TEST_DATA_DIR, "simple.dbf"), "rb") as fp:
            dbf = DBF.objects.create(
                uploaded_by=User.objects.all()[0],
                file=File(fp, name="simple.dbf"),
                export_date=date.today(),
                notification_year=date.today().year + 1,
                state_abbreviation='RJ',
            )
            with self.assertRaises(ValidationError):
                dbf.clean()

    @patch('dbf.models.is_valid_dbf')
    def test_raises_error_if_dbf_is_invalid(self, mocked_validation):
        mocked_validation.return_value = False
        with open(os.path.join(TEST_DATA_DIR, "invalid.dbf"), "rb") as fp:
            dbf = DBF.objects.create(
                uploaded_by=User.objects.all()[0],
                file=File(fp, name="invalid.dbf"),
                export_date=date.today(),
                notification_year=date.today().year,
                state_abbreviation='RJ',
            )
            with self.assertRaises(ValidationError):
                dbf.clean()
