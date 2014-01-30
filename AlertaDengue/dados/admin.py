from django.contrib.gis import admin
from dados.models import Dengue_2010, Dengue_2011, Dengue_2012, Dengue_2013, DengueConfirmados_2013

for mod in [Dengue_2010, Dengue_2011, Dengue_2012, Dengue_2013, DengueConfirmados_2013]:
    admin.site.register(mod, admin.GeoModelAdmin)
x=10
media_reputacao=10
reputacao_mais_baixa=2
(x > ((media_reputacao - reputacao_mais_baixa)/2. + reputacao_mais_baixa) or x > (reputacao_mais_alta - (reputacao_mais_alta - media_reputacao)/2.))
