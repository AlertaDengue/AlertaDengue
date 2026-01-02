"""Staging settings for AlertaDengue."""

from __future__ import annotations

import os

from ad_main.settings.base import *  # noqa: F401,F403


def _bool(value: str | None, default: bool) -> bool:
    """Convert environment string flag to bool.

    Parameters
    ----------
    value : str or None
        Raw environment value.
    default : bool
        Default value if env is not set.

    Returns
    -------
    bool
        Parsed boolean value.
    """
    if value is None:
        return default
    return value.strip().lower() == "true"


DJANGO_ENV: str = "staging"
os.environ.setdefault("DJANGO_ENV", DJANGO_ENV)

DEBUG: bool = _bool(os.getenv("DEBUG"), True)

_default_hosts = "localhost,127.0.0.1"
env_hosts = os.getenv("ALLOWED_HOSTS", _default_hosts)
ALLOWED_HOSTS: list[str] = [
    h.strip() for h in env_hosts.split(",") if h.strip()
]
