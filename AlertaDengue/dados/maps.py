from .dbdata import db_engine
import geojson


def get_city_geojson(municipio):
    """
    Pega o geojson a partir do banco de dados
    :param municipio: geocódigo do municipio
    :return:
    """
    with db_engine.connect() as conn:
        head = r'{"type": "FeatureCollection", "features":['
        tail = ']}'

        res = conn.execute(
            '''
            select geocodigo, nome, geojson, populacao, uf
            from "Dengue_global"."Municipio" where geocodigo=%s
            ''', (municipio,)
        )
        datum = dict(res.fetchone().items())
        feat = geojson.loads(datum['geojson'])

        feat['type'] = 'Feature'

        feat['properties'] = {'geocodigo': datum['geocodigo'],
                              'nome': datum['nome'],
                              'populacao': datum['populacao']}

        geoj = geojson.loads(head + geojson.dumps(feat) + tail)
    return geoj


def get_city_info(geocodigo):
    """
    Pega os metadados do município da tabela Município.
    :param geocodigo: geocódigo do município.
    :return:
    """
    with db_engine.connect() as conn:
        res = conn.execute(
            '''
            select geocodigo, nome, populacao, uf
            from "Dengue_global"."Municipio" where geocodigo=%s
            ''', (geocodigo,)
        )
        datum = dict(res.fetchone().items())
    return datum
