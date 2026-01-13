import os

from ad_main.settings.prod import *  # noqa: F403

DEBUG = False

BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES[0]["DIRS"] = [str(BASE_DIR / "templates")]

LANGUAGE_CODE = "en-us"
MIDDLEWARE = [
    mw
    for mw in MIDDLEWARE
    if mw != "django.middleware.locale.LocaleMiddleware"
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CSRF_TRUSTED_ORIGINS = [
    "https://localhost",
    "https://127.0.0.1",
    "https://infostaging.dengue.mat.br",
]

ALLOWED_HOSTS_ENV = os.getenv("ALLOWED_HOSTS", "").split(",")

ALLOWED_HOSTS = (
    [
        "localhost",
        "www.localhost",
        "0.0.0.0",
    ]
    + ALLOWED_HOSTS_ENV
    + [
        f"{prefix}{domain}"
        for prefix in ["www.", ""]
        for domain in os.getenv("CERTBOT_DOMAIN", "").split(",")
    ]
)

PWA_APP_LANG = LANGUAGE_CODE
