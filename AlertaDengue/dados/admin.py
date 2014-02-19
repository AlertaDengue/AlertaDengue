# coding=utf-8
from django.contrib.gis import admin
from dados.models import Dengue_2010, Dengue_2011, Dengue_2012, Dengue_2013, DengueConfirmados_2013

for mod in [Dengue_2010, Dengue_2011, Dengue_2012, Dengue_2013, DengueConfirmados_2013]:
    admin.site.register(mod, admin.GeoModelAdmin)

