import os

from ad_main.settings.prod import *  # noqa: F403

DEBUG = False

# we need this to console the email
# without this in staging we will get a 500 error when
# submitting the signup form for creating a new account
# because the email configuration is not set
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# need to explitly define the domains that send
# csrf_tokens otherwise all post requests will fail
CSRF_TRUSTED_ORIGINS = [
    "https://localhost",
    "https://127.0.0.1",
]

ALLOWED_HOSTS_ENV = os.getenv("ALLOWED_HOSTS", "").split(",")

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = (
    [
        "localhost",
        "www.localhost",  # needed for www redirection
        "0.0.0.0",
    ]
    + ALLOWED_HOSTS_ENV
    + [
        f"{prefix}{domain}"
        for prefix in ["www.", ""]
        for domain in os.getenv("CERTBOT_DOMAIN", "").split(",")
    ]
)
