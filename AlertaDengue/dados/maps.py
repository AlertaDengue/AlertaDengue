import psycopg2
from psycopg2.extras import DictCursor
from django.conf import settings
import geojson


conn = psycopg2.connect("dbname='{}' user='{}' host='{}' password='aldengue'".format(settings.PSQL_DB,
                                                                                     settings.PSQL_USER,
                                                                                     settings.PSQL_HOST))


def get_city_geojson(municipio):
    """
    Pega o geojson a partir do banco de dados
    :param municipio: geocódigo do municipio
    :return:
    """
    conn = psycopg2.connect("dbname='{}' user='{}' host='{}' password='aldengue'".format(settings.PSQL_DB,
                                                                                     settings.PSQL_USER,
                                                                                     settings.PSQL_HOST))
    head = r'{"type": "FeatureCollection", "features":['
    tail = ']}'
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute('select geocodigo, nome, geojson, populacao, uf from "Dengue_global"."Municipio" where geocodigo=%s', (municipio,))
    datum = cur.fetchone()
    feat = geojson.loads(datum['geojson'])

    feat['type'] = 'Feature'

    feat['properties'] = {'geocodigo': datum['geocodigo'], 'nome': datum['nome'], 'populacao': datum['populacao']}

    geoj = geojson.loads(head + geojson.dumps(feat) + tail)
    conn.close()
    return geoj

def get_city_info(geocodigo):
    """
    Pega os metadados do município da tabela Município.
    :param geocodigo: geocódigo do município.
    :return:
    """
    conn = psycopg2.connect("dbname='{}' user='{}' host='{}' password='aldengue'".format(settings.PSQL_DB,
                                                                                     settings.PSQL_USER,
                                                                                     settings.PSQL_HOST))
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute('select geocodigo, nome, populacao, uf from "Dengue_global"."Municipio" where geocodigo=%s', (geocodigo,))
    datum = cur.fetchone()
    conn.close()
    return datum

