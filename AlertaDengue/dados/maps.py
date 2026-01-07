import geojson

# local
from django.conf import settings

DB_ENGINE = settings.DB_ENGINE


def get_city_geojson(municipio):
    """
    Pega o geojson a partir do banco de dados
    :param municipio: geocódigo do municipio
    :return:
    """

    with DB_ENGINE.connect() as conn:
        head = r'{"type": "FeatureCollection", "features":['
        tail = "]}"

        res = conn.execute(
            f"""
            SELECT geocodigo, nome, geojson, populacao, uf
            FROM "Dengue_global"."Municipio"
            WHERE geocodigo={municipio}
            """
        )
        datum = dict(res.fetchone().items())
        feat = geojson.loads(datum["geojson"])

        feat["type"] = "Feature"

        feat["properties"] = {
            "geocodigo": datum["geocodigo"],
            "nome": datum["nome"],
            "populacao": datum["populacao"],
        }

        geoj = geojson.loads(head + geojson.dumps(feat) + tail)

    return geoj


def get_city_info(geocodigo):
    """
    Pega os metadados do município da tabela Município.
    :param geocodigo: geocódigo do município.
    :return:
    """

    with DB_ENGINE.connect() as conn:
        res = conn.execute(
            f"""
            SELECT geocodigo, nome, populacao, uf
            FROM "Dengue_global"."Municipio"
            WHERE geocodigo={geocodigo}
            """
        )
        datum = dict(res.fetchone().items())

    return datum
