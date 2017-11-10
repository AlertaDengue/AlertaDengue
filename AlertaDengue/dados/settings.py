try:
    # to be used externally (such as notebooks science)
    from AlertaDengue.AlertaDengue import settings
except:
    from django.conf import settings

PSQL_DB = settings.PSQL_DB
PSQL_HOST = settings.PSQL_HOST
PSQL_PASSWORD = settings.PSQL_PASSWORD
PSQL_USER = settings.PSQL_USER
QUERY_CACHE_TIMEOUT = settings.QUERY_CACHE_TIMEOUT
