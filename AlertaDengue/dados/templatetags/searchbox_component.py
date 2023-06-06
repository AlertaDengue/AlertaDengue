from dados.dbdata import STATE_NAME, RegionalParameters
from dados.models import City
from django import template
from django.conf import settings
from django.core.cache import cache

register = template.Library()


@register.inclusion_tag(
    "components/searchbox/searchbox.html", takes_context=True
)
def searchbox_component(context):
    cache_name = "options_cities"
    res = cache.get(cache_name)

    if res:
        context = {
            "options_cities": res,
        }
        return context

    options_cities = []
    for state_name in STATE_NAME.values():
        for (
            geocode,
            city_name,
        ) in RegionalParameters.get_cities(state_name=state_name).items():
            options_cities.append(City(geocode, city_name, state_name))

    cache.set(
        cache_name,
        options_cities,
        settings.QUERY_CACHE_TIMEOUT,
    )

    context = {
        "options_cities": options_cities,
    }

    return context
