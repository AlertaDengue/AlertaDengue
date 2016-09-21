from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase

from datetime import date
from io import StringIO

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

class DBFUploadViewTest(TestCase):

    def test_requires_login(self):
        response = self.client.get(reverse('dbf:upload'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
