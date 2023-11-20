import json
from datetime import date, datetime, timedelta
from pathlib import Path

from django.http import HttpRequest
from django.test import TestCase
from ninja import Router
from registry.api import PredictionIn, create_prediction
from registry.models import Author, ImplementationLanguage, Model, Prediction
from users.models import CustomUser

app_dir = Path(__file__).parent.parent

router = Router()


@router.post(
    "/create-prediction/",
    response={int: str},
    tags=["registry", "Predictions"],
)
class TestCreatePrediction(TestCase):
    def setUp(self):
        # Load Brazilian Municipalities and State names for geocode validation
        self.validation_IBGE_codes = app_dir / "data/IBGE_codes.json"
        # Load the validation Brazilian Municipalities and State names
        with open(self.validation_IBGE_codes, "r") as validation_file:
            self.validation_data = json.load(validation_file)

        # Load prediction data
        with open(app_dir / "tests/data/prediction.test.json", "r") as file:
            self.data = json.load(file)

        # Create a user and language for the model
        user, _ = CustomUser.objects.get_or_create(username="usertest")
        language = ImplementationLanguage.objects.create(language="MosqLang")

        self.model = Model.objects.create(
            author=Author.objects.get_or_create(user=user)[0],
            name="Test Model",
            implementation_language=language,
        )

    def test_validate_prediction_data(self):
        data = self.data[0]

        # Check data types
        self.assertIsInstance(data["dates"], str)
        self.assertIsInstance(data["preds"], float)
        self.assertIsInstance(data["lower"], float)
        self.assertIsInstance(data["upper"], float)
        self.assertIsInstance(data["adm_2"], int)
        self.assertIsInstance(data["adm_1"], str)
        self.assertIsInstance(data["adm_0"], str)

        # Check data values
        self.assertEqual(data["dates"], "2022-01-02")
        self.assertAlmostEqual(data["preds"], 23.4811749402)
        self.assertAlmostEqual(data["lower"], 0.0)
        self.assertAlmostEqual(data["upper"], 42.6501866267)
        self.assertEqual(data["adm_1"], "AL")
        self.assertEqual(data["adm_0"], "BR")

        # Check string field lengths
        self.assertLessEqual(len(data["dates"]), 10)
        self.assertLessEqual(len(data["adm_1"]), 2)
        self.assertLessEqual(len(data["adm_0"]), 2)

        # Check date format using datetime
        parsed_date = datetime.strptime(data["dates"], "%Y-%m-%d").date()
        self.assertIsInstance(parsed_date, date)

        # Verify if the geocode is within the range
        # for the Brazilian IBGE code
        self.assertGreaterEqual(data["adm_2"], 1100015)
        self.assertLessEqual(data["adm_2"], 5300108)

        # Check if "geocodigo" is in IBGE_code
        self.assertTrue(
            data["adm_2"]
            in [entry["geocodigo"] for entry in self.validation_data]
        )

        # Check if predict_date is after 2010 and not in the future
        self.assertGreaterEqual(parsed_date, date(2010, 1, 1))
        self.assertLessEqual(parsed_date, date.today())

    def test_create_prediction(self):
        # Create a payload for testing
        payload = PredictionIn(
            model=self.model.pk,
            description="Test description",
            ADM_level=1,
            commit="76eb927067cf54ae52da53503a14519d78a37da8",
            predict_date="2023-11-16",  # Adjust the predict_date as needed
            prediction=self.data,
        )

        request = HttpRequest()
        request.method = "POST"
        request.POST = payload.dict()

        # Call the create_prediction function and check the response
        response = create_prediction(request, payload)

        self.assertEqual(response[0], 201)

        self.assertEqual(Prediction.objects.count(), 1)
        prediction = Prediction.objects.first()
        self.assertEqual(prediction.model, self.model)
        self.assertEqual(prediction.description, "Test description")
        self.assertEqual(
            prediction.commit, "76eb927067cf54ae52da53503a14519d78a37da8"
        )

        # Check if predict_date is not in the future
        self.assertLessEqual(prediction.predict_date, date.today())

        # Check if predict_date is greater than one year
        one_year_later = datetime(2022, 11, 16) + timedelta(days=365)
        self.assertGreaterEqual(prediction.predict_date, one_year_later.date())

    def test_create_prediction_invalid_payload(self):
        # Create an invalid payload for testing
        payload = PredictionIn(
            model=self.model.pk,
            description="x" * 501,
            ADM_level=4,
            commit="76eb927067cf54ae52da53503a14519d78a37da8",
            predict_date="2023-11-08",
            prediction=self.data,
        )

        request = HttpRequest()
        request.method = "POST"
        request.POST = payload.dict()

        # Call the create_prediction function and check the response
        response = create_prediction(request, payload)

        self.assertEqual(response[0], 404)
        self.assertEqual(
            response[1],
            {
                "message": "Description too big, maximum allowed: 500.\n"
                "        Please remove 1 characters."
            },
        )
