from sqlalchemy import create_engine

import pytest
from AlertaDengue.ad_main import settings


PSQL_URI = "postgresql://{}:{}@{}:{}/{}".format(
    settings.PSQL_USER,
    settings.PSQL_PASSWORD,
    settings.PSQL_HOST,
    settings.PSQL_PORT,
    'postgres',
)


def run_sql(sql):
    conn = create_engine(PSQL_URI)
    conn.execution_options(isolation_level="AUTOCOMMIT").execute(sql)


@pytest.fixture(scope='module')
def django_db_setup():

    db_name = settings.DATABASES['infodengue']['NAME']
    run_sql('DROP DATABASE IF EXISTS {}'.format(db_name))
    run_sql(
        "CREATE DATABASE {} WITH OWNER dengueadmin ENCODING 'utf-8'".format(
            db_name
        )
    )
