try:
    # to be used externally (such as notebooks science)
    from AlertaDengue.AlertaDengue import settings
except:
    from django.conf import settings

PSQL_USER = settings.PSQL_USER
PSQL_PASSWORD = settings.PSQL_PASSWORD
PSQL_HOST = settings.PSQL_HOST
PSQL_DB = settings.PSQL_DB
