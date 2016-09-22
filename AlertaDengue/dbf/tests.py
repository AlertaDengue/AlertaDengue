from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase

from datetime import date
from io import StringIO
from mock import patch

from dbf.models import DBF

class DBFModelTest(TestCase):

    def test_notification_year_cant_be_greater_than_current_year(self):
        fake_file = StringIO("42")
        dbf = DBF.objects.create(
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
            file=InMemoryUploadedFile(fake_file, 'file', 'file.dbf',
            'application/dbf', 4, 'utf-8'),
            export_date=date.today(),
            notification_year=date.today().year
        )
        with self.assertRaises(ValidationError):
            dbf.clean()


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
