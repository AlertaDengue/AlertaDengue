"""Regression tests for the searchbox_component templatetag.

Guard against the positional-argument regression introduced when the
``population`` field was added between ``name`` and ``state`` in the City
model (PR #1091).  The fix is to use keyword arguments when constructing the
temporary City presentation objects in searchbox_component.py.

References:
    https://github.com/AlertaDengue/AlertaDengue/issues/1093
"""

from unittest.mock import patch

from django.template import Context, Template
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
