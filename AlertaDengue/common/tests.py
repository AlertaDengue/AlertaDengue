import unittest
from django.test import Client


@unittest.skip(reason="dbdemo is not updated")
class LoginTest(unittest.TestCase):
    """
    Tests login the django admin interface
    """

    def setUp(self):
        # Every test needs a client.
        self.client = Client()
        self.client.login(username='user', password='user')

    def test_requires_login(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
