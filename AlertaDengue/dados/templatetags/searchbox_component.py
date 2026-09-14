from django import template
from django.core.cache import cache

from ad_main.typed_settings import get_query_cache_timeout
from dados.dbdata import STATE_NAME, RegionalParameters
from dados.models import City

register = template.Library()

SUPPORTED_DISEASES = frozenset({"dengue", "chikungunya", "zika"})


@register.inclusion_tag(
    "components/searchbox/searchbox.html", takes_context=True
)
def searchbox_component(context, selected_geocode=None, disease=None):
    """Render cached municipality choices with optional page-specific state."""
    cache_name = "options_cities"
    options_cities = cache.get(cache_name)

    if options_cities is None:
        options_cities = []
        for uf, state_name in STATE_NAME.items():
            for (
                geocode,
                city_name,
            ) in RegionalParameters.get_cities(state_name=state_name).items():
                options_cities.append(
                    City(geocode=geocode, name=city_name, state=uf)
                )

        cache.set(
            cache_name,
            options_cities,
            get_query_cache_timeout(),
        )

    return {
        "options_cities": options_cities,
        "selected_geocode": selected_geocode,
        "disease": disease if disease in SUPPORTED_DISEASES else None,
    }
