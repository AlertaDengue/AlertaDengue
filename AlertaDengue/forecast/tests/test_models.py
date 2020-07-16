from django.test import TestCase
from unittest import skip

# local
from forecast.models import ForecastModel


@skip
class ForecastModelTest(TestCase):
    multi_db = True

    @classmethod
    def setUpTestData(cls):
        ForecastModel.objects.create(
            name='Model1', weeks=3, commit_id='1234567', active=True
        )

    def test_select(self):
        fm = ForecastModel.objects.get(name='Model1')

        self.assertEqual(fm.weeks, 3)
