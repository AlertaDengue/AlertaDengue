# from django.conf import settings
from django.test import TestCase

try:
    from django.urls import reverse  # django 2
except ModuleNotFoundError:
    # django old version
    from django.core.urlresolvers import reverse


class TestAlertaPageView(TestCase):
    def test_about(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)

    def test_contact(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)

    def test_joinin(self):
        response = self.client.get(reverse('joinin'))
        self.assertEqual(response.status_code, 200)

    def test_partners(self):
        response = self.client.get(reverse('partners'))
        self.assertEqual(response.status_code, 200)

    def test_data_public_services(self):
        response = self.client.get(reverse('data_public_services'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse('data_public_services', kwargs={'service': 'maps'})
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse('data_public_services', kwargs={'service': 'api'})
        )
        self.assertEqual(response.status_code, 200)

    def test_data_public_services_type(self):
        response = self.client.get(
            reverse(
                'data_public_services_type',
                kwargs={
                    'service': 'maps',
                    'service_type': 'doc'
                })
        )
        self.assertEqual(response.status_code, 200)
