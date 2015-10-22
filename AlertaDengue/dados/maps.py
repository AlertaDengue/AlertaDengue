import psycopg2
from django.conf import settings

# conn = psycopg2.connect("dbname='{}' user='{}' host='{}' password='aldengue'".format(settings.PSQL_DB,
#                                                                                      settings.PSQL_USER,
#                                                                                      settings.PSQL_HOST))


def get_city_geojson(municipio):
    """
    Pega o geojson a partir do banco de dados
    :param uf: sigla do estado
    :param municipio: geocódigo do municipio
    :return:
    """
    cur = conn.cursor()
    cur.execute('select geojson from "Dengue_global.Municipio" where geocodigo=%s', (municipio,))
    geoj = cur.fetchone()
    return geoj

