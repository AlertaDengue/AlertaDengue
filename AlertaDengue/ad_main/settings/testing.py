"""Settings for local/CI testing."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ad_main.settings.dev import *  # noqa: F403

DEBUG = True


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


REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = REPO_ROOT / "AlertaDengue"

_load_dotenv_if_available(REPO_ROOT)

repo_root = str(PROJECT_ROOT)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

os.environ.setdefault("PYTHONPATH", repo_root)

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")

# --- Database configuration for tests ---

# Set test names for all databases to ensure Django creates temporary databases
for db in DATABASES.values():
    if "TEST" not in db:
        db["TEST"] = {}
    if "NAME" in db and not db["NAME"].startswith("test_"):
        db["TEST"]["NAME"] = f"test_{db['NAME']}"
    elif "NAME" in db:
        db["TEST"]["NAME"] = db["NAME"]

if not PSQL_DB.startswith("test_"):
    PSQL_DB = f"test_{PSQL_DB}"
if not PSQL_DBF.startswith("test_"):
    PSQL_DBF = f"test_{PSQL_DBF}"

DB_ENGINE = get_sqla_conn(psql_db=PSQL_DB)
DB_ENGINE_FACTORY = get_sqla_conn


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
