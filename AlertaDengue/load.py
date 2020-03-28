# coding=utf-8
from django.contrib.gis.utils.layermapping import LayerMapping
from ad_dados.models import (
    Dengue_2010,
    dengue_2010_mapping,
    Dengue_2011,
    dengue_2011_mapping,
    Dengue_2012,
    dengue_2012_mapping,
    Dengue_2013,
    dengue_2013_mapping,
    DengueConfirmados_2013,
    dengueconfirmados_2013_mapping,
)


data_dir = '/home/fccoelho/Copy/Projetos/Alerta_Dengue/'

class_dict = {
    Dengue_2010: (
        data_dir + 'Dengue2010_09_01_2014/Dengue_2010_latlon.shp',
        dengue_2010_mapping,
    ),
    Dengue_2011: (
        data_dir + 'Dengue_2011_09_01_2014/Dengue_2011_latlon.shp',
        dengue_2011_mapping,
    ),
    Dengue_2012: (
        data_dir + 'Dengue2012_09_01_2014/Dengue_2012_latlon.shp',
        dengue_2012_mapping,
    ),
    Dengue_2013: (
        data_dir + 'dengue2013_09_01_2014/Dengue_2013_latlon.shp',
        dengue_2013_mapping,
    ),
    DengueConfirmados_2013: (
        data_dir + 'dengue2013_09_01_2014/Dengue_2013_conf_latlon.shp',
        dengueconfirmados_2013_mapping,
    ),
}


def run(verbose=True):
    for k, v in class_dict.items():
        lm = LayerMapping(k, v[0], v[1], transform=False, encoding='utf8')

        lm.save(strict=True, verbose=verbose)
