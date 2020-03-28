try:
    # to be used externally (such as notebooks science)
    from AlertaDengue.ad_main import settings
except Exception:
    from django.conf import settings


PSQL_DB = settings.PSQL_DB
PSQL_HOST = settings.PSQL_HOST
PSQL_PASSWORD = settings.PSQL_PASSWORD
PSQL_USER = settings.PSQL_USER
PSQL_PORT = settings.PSQL_PORT
QUERY_CACHE_TIMEOUT = settings.QUERY_CACHE_TIMEOUT
