import os
from os.path import dirname, join

import pandas as pd
from django.conf import settings
from dotenv import load_dotenv
from sqlalchemy import create_engine

env_file = os.environ.get("ENV_FILE", ".env")
dotenv_path = join(dirname(dirname(dirname(__file__))), env_file)
load_dotenv(dotenv_path)


PSQL_URI = "postgresql://{}:{}@{}:{}/{}".format(
    settings.PSQL_USER,
    settings.PSQL_PASSWORD,
    settings.PSQL_HOST,
    settings.PSQL_PORT,
    settings.PSQL_DBF,
)
db_engine = create_engine(PSQL_URI)


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

    with db_engine.connect() as conn:
        return pd.read_sql(sql, conn)
