"""Regression tests for the searchbox_component templatetag.

Guard against the positional-argument regression introduced when the
``population`` field was added between ``name`` and ``state`` in the City
model (PR #1091).  The fix is to use keyword arguments when constructing the
temporary City presentation objects in searchbox_component.py.

References:
    https://github.com/AlertaDengue/AlertaDengue/issues/1093
"""

from pathlib import Path
import re
from unittest.mock import patch

from django.template import Context, Template
from django.template.loader import get_template
import pytest

_STATE_NAME_FIXTURE = {
    "AC": "Acre",
    "RJ": "Rio de Janeiro",
}

_CITIES_BY_STATE = {
    "Acre": {1200013: "Acrelândia"},
    "Rio de Janeiro": {3304557: "Rio de Janeiro"},
}


def _mock_get_cities(state_name=None, regional_name=None):
    """Return a minimal geocode → city-name mapping for the given state."""
    return _CITIES_BY_STATE.get(state_name, {})


@pytest.mark.django_db
class TestSearchboxComponentStateAbbreviation:
    """City objects produced by searchbox_component carry the correct state."""

    def _call(self):
        """Invoke searchbox_component with a cold cache and mocked data."""
        from django.core.cache import cache

        cache.delete("options_cities")

        with (
            patch(
                "dados.templatetags.searchbox_component.STATE_NAME",
                _STATE_NAME_FIXTURE,
            ),
            patch(
                "dados.templatetags.searchbox_component.RegionalParameters"
                ".get_cities",
                side_effect=_mock_get_cities,
            ),
        ):
            from dados.templatetags.searchbox_component import (
                searchbox_component,
            )

            result = searchbox_component(context={})

        return result["options_cities"]

    def test_state_abbreviation_is_populated(self):
        """city.state must be the UF abbreviation, not empty or a number."""
        cities = self._call()
        states = {c.state for c in cities}
        assert "AC" in states, f"Expected 'AC' in states; got {states}"
        assert "RJ" in states, f"Expected 'RJ' in states; got {states}"

    def test_multiple_states_are_handled(self):
        """Both states supplied in the fixture must appear."""
        cities = self._call()
        states = {c.state for c in cities}
        assert states == {"AC", "RJ"}

    def test_municipality_name_is_preserved(self):
        """city.name must match the name from the cities mapping."""
        cities = self._call()
        names = {c.name for c in cities}
        assert "Acrelândia" in names
        assert "Rio de Janeiro" in names

    def test_geocode_is_correct(self):
        """city.geocode must match the key from the cities mapping."""
        cities = self._call()
        geocodes = {c.geocode for c in cities}
        assert 1200013 in geocodes
        assert 3304557 in geocodes

    def test_state_is_not_numeric(self):
        """Before the fix, positional City(geocode, name, uf) would assign
        uf to ``population`` (BigIntegerField), and the template would show an
        empty string for state.  Assert state is a string UF abbreviation."""
        cities = self._call()
        for city in cities:
            assert isinstance(city.state, str), (
                f"city.state for {city.name!r} is {city.state!r}, "
                "expected a string UF abbreviation"
            )
            assert city.state in _STATE_NAME_FIXTURE, (
                f"city.state {city.state!r} is not a recognised UF"
            )

    def test_template_renders_name_dash_state(self):
        """The searchbox template must produce 'Name - UF' labels."""
        cities = self._call()

        template = Template(
            "{% for city in cities %}"
            "{{ city.name }} - {{ city.state }}|"
            "{% endfor %}"
        )
        rendered = template.render(Context({"cities": cities}))

        assert "Acrelândia - AC" in rendered, (
            f"Expected 'Acrelândia - AC' in rendered output; got: {rendered!r}"
        )
        assert "Rio de Janeiro - RJ" in rendered, (
            f"Expected 'Rio de Janeiro - RJ' in rendered; got: {rendered!r}"
        )

    @pytest.mark.parametrize("disease", ("dengue", "chikungunya", "zika"))
    def test_dashboard_context_selects_city_and_keeps_disease(self, disease):
        """Dashboard state is rendered separately from cached city choices."""
        self._call()

        from dados.templatetags.searchbox_component import searchbox_component

        context = searchbox_component(
            context={},
            selected_geocode=3304557,
            disease=disease,
        )
        rendered = get_template("components/searchbox/searchbox.html").render(
            context
        )

        assert f'data-disease="{disease}"' in rendered
        assert re.search(r'value="3304557"\s+selected', rendered)

    def test_homepage_context_uses_short_route_metadata(self):
        """The homepage has no disease state and keeps its empty selector."""
        self._call()

        from dados.templatetags.searchbox_component import searchbox_component

        rendered = get_template("components/searchbox/searchbox.html").render(
            searchbox_component(context={})
        )

        assert "data-disease" not in rendered
        assert not re.search(r"<option\b[^>]*\bselected\b", rendered)

    def test_unsupported_disease_is_not_emitted(self):
        """Only supported dashboard diseases can affect navigation metadata."""
        self._call()

        from dados.templatetags.searchbox_component import searchbox_component

        rendered = get_template("components/searchbox/searchbox.html").render(
            searchbox_component(
                context={},
                selected_geocode=3304557,
                disease="invalid",
            )
        )

        assert "data-disease" not in rendered

    def test_city_dashboard_template_uses_current_searchbox_context(self):
        """The city dashboard passes its active city and disease to the tag."""
        source = get_template("alert_base.html").template.source

        assert (
            "{% searchbox_component selected_geocode=geocode "
            "disease=disease_code %}"
        ) in source

    def test_site_searchbox_preserves_optional_disease_in_destination(self):
        """Shared Select2 navigation appends only component-provided disease."""
        source = (
            Path(__file__).parents[3] / "templates" / "base.html"
        ).read_text()

        assert 'var destination = "/alerta/" + city.id;' in source
        assert 'var disease = $searchbox.data("disease");' in source
        assert 'destination += "/" + disease;' in source

    def test_cached_choices_do_not_contain_dashboard_state(self):
        """Changing dashboard state must not change global cached choices."""
        self._call()

        from dados.templatetags.searchbox_component import searchbox_component

        dengue_context = searchbox_component(
            context={},
            selected_geocode=1200013,
            disease="dengue",
        )
        zika_context = searchbox_component(
            context={},
            selected_geocode=3304557,
            disease="zika",
        )

        assert [
            (city.geocode, city.name, city.state)
            for city in dengue_context["options_cities"]
        ] == [
            (city.geocode, city.name, city.state)
            for city in zika_context["options_cities"]
        ]
        assert dengue_context["selected_geocode"] == 1200013
        assert dengue_context["disease"] == "dengue"
        assert zika_context["selected_geocode"] == 3304557
        assert zika_context["disease"] == "zika"


def test_short_city_route_still_redirects_to_dengue(client):
    """The existing short municipality route remains backward compatible."""
    response = client.get("/alerta/3304557")

    assert response.status_code == 302
    assert response["Location"] == "/alerta/3304557/dengue"


def test_city_dashboard_layout_uses_dynamic_summary_context():
    """The dashboard keeps its navigation contract in the refined layout."""
    source = get_template("alert_base.html").template.source

    assert "{% searchbox_component selected_geocode=geocode " in source
    assert "disease=disease_code %}" in source
    assert "Dados atualizados até a SE {{ week }}/{{ year }}" in source
    assert "Dados consolidados" not in source
    assert source.index("city-dashboard-controls") < source.index(
        "city-dashboard-summary"
    )
    assert "Incidência estimada na SE {{ week }}" in source
    assert "dados:report_city" in source
    assert "dados:alerta_uf" in source
    assert "Casos de {{ disease }} em {{ municipality }}" in source
    assert "{{ chart_alert | safe }}" in source


@pytest.mark.parametrize("disease", ("dengue", "chikungunya", "zika"))
def test_city_dashboard_disease_controls_keep_active_state(disease):
    """Each supported disease remains represented by an accessible control."""
    source = get_template("alert_base.html").template.source

    assert f'disease_code == "{disease}"' in source
    assert f"./{disease}" in source
