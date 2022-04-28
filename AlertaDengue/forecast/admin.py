from django.contrib import admin

from .models import ForecastCity, ForecastModel

admin.site.register(ForecastModel)
admin.site.register(ForecastCity)
