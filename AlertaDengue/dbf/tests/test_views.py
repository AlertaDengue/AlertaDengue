from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.files.base import File
from django.test import TestCase

from datetime import date
from io import StringIO
import os

from dbf.models import DBF

__all__ = ["DBFUploadViewTest"]

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data/")

class DBFUploadViewTest(TestCase):
    fixtures = ['users']

    def _create_dbf_from_test_data(self, uploaded_by, filename, export_date,
            notification_year):
        with open(os.path.join(TEST_DATA_DIR, filename), "rb") as fp:
            dbf = DBF.objects.create(
                uploaded_by=uploaded_by,
                file=File(fp, name=filename),
                export_date=export_date,
                notification_year=notification_year
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
        self.assertEqual(response.context['form'].Meta.model, DBF)

    def test_context_has_last_uploaded_files(self):
        self.client.login(username="user", password="user")
        dbf = self._create_dbf_from_test_data(
            uploaded_by=User.objects.get(username="user"),
            filename="simple.dbf",
            export_date=date.today(),
            notification_year=date.today().year
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
            notification_year=date.today().year
        )
        response = self.client.get(reverse('dbf:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_uploaded', response.context)
        self.assertNotIn(dbf, response.context['last_uploaded'])

    def test_redirects_to_success_url_when_form_is_valid(self):
        self.client.login(username="user", password="user")
        with open(os.path.join(TEST_DATA_DIR, "simple.dbf"), "rb") as fp:
            data = {
                "file": fp,
                "export_date": date.today(),
                "notification_year": date.today().year
            }
            response = self.client.post(reverse('dbf:upload'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dbf:upload_successful"))

    def test_cannot_create_file_for_other_user(self):
        self.client.login(username="user", password="user")
        self.assertEqual(len(DBF.objects.all()), 0)
        with open(os.path.join(TEST_DATA_DIR, "simple.dbf"), "rb") as fp:
            admin = User.objects.get(username="admin")
            data = {
                "uploaded_by": admin.id,
                "file": fp,
                "export_date": date.today(),
                "notification_year": date.today().year
            }
            response = self.client.post(reverse('dbf:upload'), data)
        # The object was created ...
        self.assertEqual(len(DBF.objects.all()), 1)
        # ... but not with the given id ...
        self.assertNotEqual(DBF.objects.all()[0].uploaded_by, admin)
        # ... it was created with the current user's id instead.
        self.assertEqual(DBF.objects.all()[0].uploaded_by.id,
                int(self.client.session['_auth_user_id']))
