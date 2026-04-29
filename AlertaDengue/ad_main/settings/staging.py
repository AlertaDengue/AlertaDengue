import os
from pathlib import Path

from ad_main.settings.prod import *  # noqa: F403,F401


def env_list(name: str, default: str = "") -> list[str]:
    return [
        item.strip()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    ]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


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

DEFAULT_ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
]

CERTBOT_DOMAINS = env_list("CERTBOT_DOMAIN")

ALLOWED_HOSTS = (
    DEFAULT_ALLOWED_HOSTS
    + env_list("ALLOWED_HOSTS")
    + [
        f"{prefix}{domain}"
        for prefix in ["www.", ""]
        for domain in CERTBOT_DOMAINS
    ]
)

# CSRF Protection
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", default=False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", default=False)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# PWA
PWA_APP_LANG = LANGUAGE_CODE
