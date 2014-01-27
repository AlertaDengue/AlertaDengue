import os
from django.contrib.gis.utils.layermapping import LayerMapping
from dados.models import Dengue_2010, dengue_2010_mapping, Dengue_2011, dengue_2011_mapping, Dengue_2012, \
    dengue_2012_mapping, Dengue_2013, dengue_2013_mapping, DengueConfirmados_2013, dengueconfirmados_2013_mapping

class_dict = {Dengue_2010: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/Dengue2010_09_01_2014/Dengue_2010_latlon.shp', dengue_2010_mapping),
              Dengue_2011: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/Dengue_2011_09_01_2014/Dengue_2011_latlon.shp', dengue_2011_mapping),
              Dengue_2012: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/Dengue2012_09_01_2014/Dengue_2012_latlon.shp', dengue_2012_mapping),
              Dengue_2013: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/dengue2013_09_01_2014/Dengue_2013_latlon.shp', dengue_2013_mapping),
              DengueConfirmados_2013: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/dengue2013_09_01_2014/Dengue_2013_conf_latlon.shp', dengueconfirmados_2013_mapping)
            }



def run(verbose=True):
    for k, v in class_dict.items():
        lm = LayerMapping(k, v[0], v[1], transform=False, encoding='utf8')

        lm.save(strict=True, verbose=verbose)