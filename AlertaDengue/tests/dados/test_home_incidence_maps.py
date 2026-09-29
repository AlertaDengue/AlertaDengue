from unittest.mock import patch

from django.template.loader import render_to_string
from epiweeks import Week
import pytest

from dados.views import AlertaMainView


@pytest.mark.parametrize("week", ["202638", "202701"])
def test_home_uses_latest_alert_week_in_national_map_urls(week):
    with patch(
        "dados.views.get_last_SE", return_value=Week.fromstring(week)
    ) as latest:
        context = AlertaMainView().get_context_data()
    latest.assert_called_once_with()
    assert context["current_epiweek"] == week
    html = render_to_string(
        "components/home/home_uf_incidence_section.html", context
    )
    for disease in ("dengue", "chikungunya"):
        assert (
            f"/static/img/incidence_maps/country/"
            f'incidence_Nacional_{disease}.png?v={week}"'
        ) in html
