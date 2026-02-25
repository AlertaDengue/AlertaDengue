from __future__ import annotations

import os
import sys
from pathlib import Path

from ad_main.settings.dev import *  # noqa: F403
from django.db import connections
from django.db.models.signals import pre_migrate
from django.dispatch import receiver

DEBUG = True


def _load_dotenv_if_available(project_root: Path) -> None:
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


def _base_db_name(name: str) -> str:
    return name[5:] if name.startswith("test_") else name


def _configure_test_db(db: dict[str, object]) -> None:
    name_obj = db.get("NAME")
    if not isinstance(name_obj, str) or not name_obj:
        return

    base = _base_db_name(name_obj)
    test_name = f"test_{base}"

    test_cfg = db.setdefault("TEST", {})
    if isinstance(test_cfg, dict):
        test_cfg["NAME"] = test_name


for db in DATABASES.values():  # noqa: F405
    _configure_test_db(db)

PSQL_DB = DATABASES["default"]["TEST"]["NAME"]  # noqa: F405
if "dbf" in DATABASES:  # noqa: F405
    PSQL_DBF = DATABASES["dbf"]["TEST"]["NAME"]  # noqa: F405
else:
    PSQL_DBF = PSQL_DB


@receiver(pre_migrate)
def _ensure_required_schemas(sender, using: str, **kwargs: object) -> None:
    """
    Ensure schemas/tables referenced by migrations exist in the test DB.

    This avoids failures on FK constraints pointing to Dengue_global.Municipio.
    """
    if using != "default":
        return

    with connections[using].cursor() as cur:
        cur.execute('CREATE SCHEMA IF NOT EXISTS "Dengue_global"')
        cur.execute('CREATE SCHEMA IF NOT EXISTS "test_views"')
        cur.execute(
            'CREATE TABLE IF NOT EXISTS "Dengue_global"."Municipio" '
            "(geocodigo integer PRIMARY KEY)"
        )


DB_ENGINE = get_sqla_conn(psql_db=PSQL_DB)  # noqa: F405
DB_ENGINE_FACTORY = get_sqla_conn  # noqa: F405

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "alertadengue-tests",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
