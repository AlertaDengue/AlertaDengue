import pandas as pd

# local
from django.conf import settings

DB_ENGINE = settings.DB_ENGINE_FACTORY(settings.PSQL_DBF)


def is_partner_active():
    """
    :param: name, contact, email
        where status is True
    :return: pandas dataframe
    """
    sql = """
      SELECT name, contact, email FROM dbf_sendtoPartner
      WHERE status = 'True'
      ORDER BY name
    """

    with DB_ENGINE.connect() as conn:
        data = conn.execute(sql).fetchall()
        return pd.DataFrame(data)
