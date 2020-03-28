import os
from django.contrib.auth.models import User
from django.core.files.base import File
from django.test import TestCase
import pytest

from django.urls import reverse

from datetime import date

# local
from AlertaDengue.dbf.models import DBF, DBFChunkedUpload
from AlertaDengue.dbf.forms import DBFForm


__all__ = ["DBFUploadViewTest"]


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data/")


class DBFUploadViewTest(TestCase):
    databases = ['infodengue', 'default']
    fixtures = ['AlertaDengue/dbf/fixtures/users.json']

    @pytest.fixture()
    @pytest.mark.django_db(transaction=True)
    def _create_dbf_from_test_data(
        self, uploaded_by, filename, export_date, notification_year
    ):
        with open(os.path.join(TEST_DATA_DIR, filename), "rb") as fp:
            dbf = DBF.objects.create(
                uploaded_by=uploaded_by,
                file=File(fp, name=filename),
                export_date=export_date,
                notification_year=notification_year,
            )
        return dbf

    def test_requires_login(self):
        response = self.client.get(reverse('dbf:upload'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_shows_form_when_logged_in(self):
        self.client.login(username="user", password="user")
        response = self.client.get(reverse('dbf:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], DBFForm)

    def test_context_has_last_uploaded_files(self):
        self.client.login(username="user", password="user")
        dbf = self._create_dbf_from_test_data(
            uploaded_by=User.objects.get(username="user"),
            filename="simple.dbf",
            export_date=date.today(),
            notification_year=date.today().year,
        )
        response = self.client.get(reverse('dbf:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_uploaded', response.context)
        self.assertIn(dbf, response.context['last_uploaded'])

    def test_context_does_not_include_files_uploaded_by_other_user(self):
        self.client.login(username="user", password="user")
        dbf = self._create_dbf_from_test_data(
            uploaded_by=User.objects.get(username="admin"),
            filename="simple.dbf",
            export_date=date.today(),
            notification_year=date.today().year,
        )
        response = self.client.get(reverse('dbf:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_uploaded', response.context)
        self.assertNotIn(dbf, response.context['last_uploaded'])

    def test_redirects_to_success_url_when_form_is_valid(self):
        self.client.login(username="user", password="user")
        with open(os.path.join(TEST_DATA_DIR, "simple.dbf"), "rb") as fp:
            DBFChunkedUpload.objects.create(
                id=1,
                file=File(fp, name='cool_file'),
                filename="cool_file",
                user=User.objects.get(username="user"),
            )
            fp.seek(0)
            data = {
                "file": fp,
                "export_date": date.today(),
                "notification_year": date.today().year,
                "chunked_upload_id": 1,
                "state_abbreviation": "RJ",
            }
            response = self.client.post(reverse('dbf:upload'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dbf:upload_successful"))

    def test_cannot_create_file_for_other_user(self):
        self.client.login(username="user", password="user")
        self.assertEqual(len(DBF.objects.all()), 0)
        regular_user = User.objects.get(username="user")
        admin = User.objects.get(username="admin")

        with open(os.path.join(TEST_DATA_DIR, "simple.dbf"), "rb") as fp:
            DBFChunkedUpload.objects.create(
                id=1,
                file=File(fp, name='cool_file'),
                filename="cool_file",
                user=regular_user,
            )
            fp.seek(0)
            data = {
                "uploaded_by": admin.id,
                "file": fp,
                "export_date": date.today(),
                "notification_year": date.today().year,
                "chunked_upload_id": 1,
                "state_abbreviation": "RJ",
            }
            self.client.post(reverse('dbf:upload'), data)

        admin = User.objects.get(username="admin")
        # The object was created ...
        self.assertEqual(len(DBF.objects.all()), 1)
        # ... but not with the given id ...
        self.assertNotEqual(DBF.objects.all()[0].uploaded_by, admin)
        # ... it was created with the current user's id instead.
        self.assertEqual(
            DBF.objects.all()[0].uploaded_by.id,
            int(self.client.session['_auth_user_id']),
        )
