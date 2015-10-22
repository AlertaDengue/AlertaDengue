import psycopg2
from psycopg2.extras import DictCursor
from django.conf import settings
import geojson
from shapely.geometry import shape

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
    head = r'{"type": "FeatureCollection", "features":['
    tail = ']}'
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute('select geocodigo, nome, geojson, populacao, uf from "Dengue_global"."Municipio" where geocodigo=%s', (municipio,))
    datum = cur.fetchone()
    feat = geojson.loads(datum['geojson'])
    #shapeobj = shape(feat)
    feat['type'] = 'Feature'
    #feat['geometry']['type'] = 'Polygon'
    feat['properties'] = {'geocodigo': datum['geocodigo'], 'nome': datum['nome'], 'populacao': datum['populacao']}

    geoj = geojson.loads(head + geojson.dumps(feat) + tail)
    #print(geoj)
    return geoj

