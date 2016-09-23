from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test import TestCase

from datetime import date
from io import StringIO

from dbf.models import DBF

__all__ = ["DBFUploadViewTest"]

class DBFUploadViewTest(TestCase):
    fixtures = ['users']

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
        fake_file = StringIO("Invalid dbf")
        dbf = DBF.objects.create(
            uploaded_by=User.objects.get(username="user"),
            file=InMemoryUploadedFile(fake_file, 'file', 'file.dbf',
            'application/dbf', 4, 'utf-8'),
            export_date=date.today(),
            notification_year=date.today().year
        )
        response = self.client.get(reverse('dbf:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_uploaded', response.context)
        self.assertIn(dbf, response.context['last_uploaded'])

    def test_context_doens_not_include_files_uploaded_by_other_user(self):
        self.client.login(username="user", password="user")
        fake_file = StringIO("Invalid dbf")
        dbf = DBF.objects.create(
            uploaded_by=User.objects.get(username="admin"),
            file=InMemoryUploadedFile(fake_file, 'file', 'file.dbf',
            'application/dbf', 4, 'utf-8'),
            export_date=date.today(),
            notification_year=date.today().year
        )
        response = self.client.get(reverse('dbf:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_uploaded', response.context)
        self.assertNotIn(dbf, response.context['last_uploaded'])

    def test_redirects_to_success_url_when_form_is_valid(self):
        self.client.login(username="user", password="user")
        _file = StringIO("42")
        _file.name = "42.dbf"
        data = {
            "file": _file,
            "export_date": date.today(),
            "notification_year": date.today().year
        }
        response = self.client.post(reverse('dbf:upload'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dbf:upload_successful"))

    def test_cannot_create_file_for_other_user(self):
        self.client.login(username="user", password="user")
        self.assertEqual(len(DBF.objects.all()), 0)
        _file = StringIO("file")
        _file.name = "file.dbf"
        admin = User.objects.get(username="admin")
        data = {
            "uploaded_by": admin.id,
            "file": _file,
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
