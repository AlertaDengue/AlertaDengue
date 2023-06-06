from dados.dbdata import STATE_NAME, RegionalParameters
from dados.models import City
from django import template

register = template.Library()


@register.inclusion_tag(
    "components/searchbox/searchbox.html", takes_context=True
)
def searchbox_component(context):
    options_cities = []
    for state_name in STATE_NAME.values():
        for (
            geocode,
            city_name,
        ) in RegionalParameters.get_cities(state_name=state_name).items():
            options_cities.append(City(geocode, city_name, state_name))

    context = {
        "options_cities": options_cities,
    }

    return context
