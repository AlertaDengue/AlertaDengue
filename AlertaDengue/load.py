import os
from django.contrib.gis.utils.layermapping import LayerMapping
from dados.models import Dengue_2010, dengue_2010_mapping, Dengue_2011, dengue_2011_mapping, Dengue_2012, \
    dengue_2012_mapping, Dengue_2013, dengue_2013_mapping, DengueConfirmados_2013, dengueconfirmados_2013_mapping

class_dict = {Dengue_2010: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/Dengue2010_09_01_2014/Dengue2010_BancoSINAN16_04_2012_v09012014.shp', dengue_2010_mapping),
              Dengue_2011: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/Dengue_2011_09_01_2014/Dengue2011_BancoSINAN14_10_2013_v09012014.shp', dengue_2011_mapping),
              Dengue_2012: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/Dengue2012_09_01_2014/Dengue2012_BancoSINAN09_09_2013_v09012014.shp', dengue_2012_mapping),
              Dengue_2013: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/dengue2013_09_01_2014/Dengue2013_BancoSINAN30_12_2013.shp', dengue_2013_mapping),
              DengueConfirmados_2013: ('/home/fccoelho/Copy/Projetos/Alerta_Dengue/dengue2013_09_01_2014/Dengue2013_CasosConfirmadosLaboratorialmente_BancoSINAN30_12_2013.shp', dengueconfirmados_2013_mapping)
            }



def run(verbose=True):
    for k, v in class_dict.items():
        lm = LayerMapping(k, v[0], v[1], transform=False, encoding='utf8')

        lm.save(strict=True, verbose=verbose)