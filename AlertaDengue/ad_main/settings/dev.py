from __future__ import annotations

from ad_main.settings.base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = INSTALLED_APPS + ["django_extensions"]

MIDDLEWARE = BASE_MIDDLEWARE + [
    "django_cprofile_middleware.middleware.ProfilerMiddleware",
]
DJANGO_CPROFILE_MIDDLEWARE_REQUIRE_STAFF = False

TEMPLATES = build_templates(debug=DEBUG)
CACHES = build_caches(debug=DEBUG)

CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 600
CACHE_MIDDLEWARE_KEY_PREFIX = "_"

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

result_backend = build_result_backend(debug=DEBUG)

PWA_APP_DEBUG_MODE = True
