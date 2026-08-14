"""Small response-payload helpers for public REST API endpoints."""

from typing import Any


def build_success_response(
    data: Any = None,
    *,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable public success payload."""
    payload = {"data": data}
    if meta is not None:
        payload["meta"] = meta
    return payload


def build_error_response(
    detail: str,
    *,
    code: str | None = None,
) -> dict[str, str]:
    """Build a stable public error payload."""
    payload = {"detail": detail}
    if code is not None:
        payload["code"] = code
    return payload
