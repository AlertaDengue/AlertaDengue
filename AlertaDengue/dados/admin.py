from django.contrib import admin
from dados.models import ForecastModel, ForecastCity

admin.site.register(ForecastModel)
admin.site.register(ForecastCity)
