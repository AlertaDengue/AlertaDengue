"""Settings for local/CI testing."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_dotenv_if_available(project_root: Path) -> None:
    """Load .env files if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    envs_env = project_root / ".envs" / ".env"
    if envs_env.exists():
        load_dotenv(envs_env)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

_load_dotenv_if_available(PROJECT_ROOT)

repo_root = str(PROJECT_ROOT)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

os.environ.setdefault("PYTHONPATH", repo_root)

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")

from ad_main.settings.dev import *  # noqa: F403,E402

DEBUG = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "alertadengue-tests",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
