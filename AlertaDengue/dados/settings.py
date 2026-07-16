from typing import cast

from django.conf import settings as django_settings

try:
    # to be used externally (such as notebooks science)
    from AlertaDengue.ad_main.settings.base import (
        PSQL_DB,
        PSQL_HOST,
        PSQL_PASSWORD,
        PSQL_PORT,
        PSQL_USER,
        QUERY_CACHE_TIMEOUT,
    )
except Exception:
    PSQL_DB = cast(str, getattr(django_settings, "PSQL_DB"))
    PSQL_HOST = cast(str, getattr(django_settings, "PSQL_HOST"))
    PSQL_PASSWORD = cast(str, getattr(django_settings, "PSQL_PASSWORD"))
    PSQL_USER = cast(str, getattr(django_settings, "PSQL_USER"))
    PSQL_PORT = cast(int, getattr(django_settings, "PSQL_PORT"))
    QUERY_CACHE_TIMEOUT = cast(
        int,
        getattr(django_settings, "QUERY_CACHE_TIMEOUT"),
    )
