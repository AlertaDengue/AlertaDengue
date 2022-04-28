from django.test import TestCase

# local
from forecast.models import ForecastModel

# from forecast.models import ForecastCity


class ForecastModelTest(TestCase):
    multi_db = True
    databases = ["forecast"]

    @classmethod
    def setUpTestData(cls):
        ForecastModel.objects.create(
            name="Model1",
            github="http://github.com",
            commit_id="1234567",
            train_start="2021-04-22",
            train_end="2021-04-22",
            filename="Trained model",
            active=True,
        ),

    def test_select(self):
        fm = ForecastModel.objects.get(name="Model1")
        self.assertEqual(fm.filename, "Trained model")
