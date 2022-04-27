from copy import deepcopy

from AlertaDengue.ad_main.settings import DATABASES

DATABASES["test_default"] = deepcopy(DATABASES["default"])  # noqa: F405
DATABASES["test_default"] = {"TEST": {"MIRROR": "default"}}

DATABASES["test_dados"] = deepcopy(DATABASES["dados"])  # noqa: F405
DATABASES["test_dados"] = {"TEST": {"MIRROR": "dados"}}

DATABASES["test_infodengue"] = deepcopy(DATABASES["infodengue"])  # noqa: F405
DATABASES["test_infodengue"] = {"TEST": {"MIRROR": "infodengue"}}

DATABASES["test_forecast"] = deepcopy(DATABASES["forecast"])  # noqa: F405
DATABASES["test_forecast"] = {"TEST": {"MIRROR": "forecast"}}
