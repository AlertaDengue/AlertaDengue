import os

from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ad_main.settings")
os.environ.setdefault("NUMEXPR_MAX_THREADS", "16")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "16")

REDIS_PORT = os.environ.get("REDIS_PORT")
ENV = "dev" if settings.DEBUG else "prod"

broker_url = f"redis://infodengue-{ENV}-redis:6379/0"
result_backend = f"redis://infodengue-{ENV}-redis:6379/0"
broker_connection_retry_on_startup = True
