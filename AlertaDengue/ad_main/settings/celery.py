import os

DJANGO_SETTINGS_MODULE = os.environ.setdefault("DJANGO_SETTINGS_MODULE")


if DJANGO_SETTINGS_MODULE == "config.settings.dev":
    from ad_main.settings.dev import *  # noqa: F403
elif DJANGO_SETTINGS_MODULE == "config.settings.staging":
    from ad_main.settings.staging import *  # noqa: F403
else:
    from ad_main.settings.prod import *  # noqa: F403

SERVICE_NAME = "celery"
