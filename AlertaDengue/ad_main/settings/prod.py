from ad_main.settings.base import *  # noqa: F401,F403

DEBUG = False

MIDDLEWARE = (
    ["django.middleware.cache.UpdateCacheMiddleware"]
    + BASE_MIDDLEWARE
    + ["django.middleware.cache.FetchFromCacheMiddleware"]
)

TEMPLATES = build_templates(debug=DEBUG)
CACHES = build_caches(debug=DEBUG)

CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 600
CACHE_MIDDLEWARE_KEY_PREFIX = "_"

result_backend = build_result_backend(debug=DEBUG)

PWA_APP_DEBUG_MODE = False
