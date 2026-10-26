"""State weekly bulletin PDF discovery and URL construction.

Bulletin PDFs follow the naming convention published by the bulletin pipeline:

    <BASE_URL>/Estados/{UF}/Estado/E{UF}-{YEAR}/E{UF}-{YEARWEEK}.pdf

Example:
    https://info.dengue.mat.br/relatorios/Estados/RJ/Estado/ERJ-2026/ERJ-202640.pdf

The base URL is read from the ``STATE_BULLETINS_BASE_URL`` Django setting and
defaults to the known production base.  No files are assumed to exist locally;
availability is checked via HTTP HEAD on demand. There is no local publication
index, so the selector offers the most recent 260 epidemiological weeks; the
availability check, not the selector, determines whether a PDF was published.

This module never makes HTTP requests during page rendering. The
``StateBulletinPdfView`` validates inputs server-side and redirects only after
confirming that the selected PDF is available.
"""

from __future__ import annotations

from email.message import Message
from enum import Enum
import hashlib
import logging
import re
import socket
from typing import IO, NamedTuple
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from epiweeks import Week

logger = logging.getLogger(__name__)

VALID_UF_CODES: frozenset[str] = frozenset(
    [
        "AC",
        "AL",
        "AM",
        "AP",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MG",
        "MS",
        "MT",
        "PA",
        "PB",
        "PE",
        "PI",
        "PR",
        "RJ",
        "RN",
        "RO",
        "RR",
        "RS",
        "SC",
        "SE",
        "SP",
        "TO",
    ]
)

_DEFAULT_BULLETINS_BASE_URL = "https://info.dengue.mat.br/relatorios/Estados"
_BULLETINS_ORIGIN = ("https", "info.dengue.mat.br", 443)


def get_bulletins_base_url() -> str:
    """Return a validated HTTPS path for the official bulletin origin.

    Reads ``STATE_BULLETINS_BASE_URL`` from Django settings and falls back to
    the official publication path if the setting is absent or blank. The
    hostname is intentionally fixed because bulletins are served from the
    official publication origin in every deployment environment.
    """
    url: str = getattr(
        settings, "STATE_BULLETINS_BASE_URL", _DEFAULT_BULLETINS_BASE_URL
    )
    if not url or not url.strip():
        url = _DEFAULT_BULLETINS_BASE_URL

    try:
        parsed = urllib.parse.urlsplit(url.strip())
        port = parsed.port or 443
    except ValueError as exc:
        raise ImproperlyConfigured(
            "STATE_BULLETINS_BASE_URL must be a valid HTTPS URL."
        ) from exc

    decoded_path = urllib.parse.unquote(parsed.path)
    path_parts = decoded_path.split("/")
    if (
        parsed.scheme != "https"
        or parsed.hostname != _BULLETINS_ORIGIN[1]
        or port != _BULLETINS_ORIGIN[2]
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
        or any(part in {".", ".."} for part in path_parts)
        or "\\" in decoded_path
        or any(ord(char) < 32 for char in decoded_path)
    ):
        raise ImproperlyConfigured(
            "STATE_BULLETINS_BASE_URL must use the official HTTPS origin "
            "info.dengue.mat.br."
        )

    return urllib.parse.urlunsplit(
        ("https", _BULLETINS_ORIGIN[1], parsed.path.rstrip("/"), "", "")
    )


class EpiWeekInfo(NamedTuple):
    year: int
    week: int


def current_epiweek() -> EpiWeekInfo:
    """Return the current CDC (Sunday-start) epidemiological week and year."""
    import datetime

    today = datetime.date.today()
    w = Week.fromdate(today, system="CDC")
    return EpiWeekInfo(year=w.year, week=w.week)


def epiweek_options(n_weeks: int = 52) -> list[EpiWeekInfo]:
    """Return the last *n_weeks* epiweek infos, most-recent first.

    Uses :class:`epiweeks.Week` arithmetic to correctly handle year
    boundaries and 52/53-week years.
    """
    import datetime

    today = datetime.date.today()
    current = Week.fromdate(today, system="CDC")

    result: list[EpiWeekInfo] = []
    w = current
    for _ in range(n_weeks):
        result.append(EpiWeekInfo(year=w.year, week=w.week))
        w -= 1  # epiweeks.Week supports subtraction by integer
    return result


def week_label(info: EpiWeekInfo) -> str:
    """Human-readable label for an epiweek, e.g. ``'SE 40/2026'``."""
    return f"SE {info.week:02d}/{info.year}"


# Pattern accepted as a valid UF code (strict: uppercase letters only, 2 chars)
_UF_RE = re.compile(r"^[A-Z]{2}$")

# Pattern accepted as a valid year-week string: exactly 6 digits
_YEARWEEK_RE = re.compile(r"^\d{6}$")


def build_bulletin_url(uf: str, year: int, week: int) -> str:
    """Construct the canonical bulletin PDF URL for *uf* and epiweek.

    Parameters
    ----------
    uf:
        Two-letter Brazilian state code (e.g. ``'RJ'``).
    year:
        Epidemiological year (e.g. ``2026``).
    week:
        Epidemiological week number (1-53).

    Returns
    -------
    str
        Fully-qualified HTTPS URL.

    Raises
    ------
    ValueError
        If *uf*, *year*, or *week* are invalid.
    """
    uf = uf.upper().strip()
    if not _UF_RE.match(uf) or uf not in VALID_UF_CODES:
        raise ValueError(f"Invalid or unsupported UF code: {uf!r}")
    if not (1900 <= year <= 2100):
        raise ValueError(f"Year out of range: {year!r}")
    try:
        Week(year, week, system="CDC")
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Invalid epidemiological week: {year}SE{week:02d}"
        ) from exc

    base = get_bulletins_base_url()
    # Each path component is percent-encoded individually; UF is always ASCII.
    uf_enc = urllib.parse.quote(uf, safe="")
    year_str = str(year)
    week_str = f"{week:02d}"
    year_week = f"{year}{week_str}"

    path = (
        f"{base}/{uf_enc}/Estado/"
        f"E{uf_enc}-{year_str}/"
        f"E{uf_enc}-{year_week}.pdf"
    )
    return path


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent availability checks from following HTTP redirects."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> urllib.request.Request | None:
        del req, fp, code, msg, headers, newurl
        return None


class BulletinAvailability(Enum):
    """Result of checking a bulletin's published availability."""

    AVAILABLE = "available"
    MISSING = "missing"
    UPSTREAM_ERROR = "upstream_error"
    TIMEOUT = "timeout"
    REDIRECT_REJECTED = "redirect_rejected"
    HEAD_UNSUPPORTED = "head_unsupported"


def _status_from_http_error(status: int) -> BulletinAvailability:
    if status in (404, 410):
        return BulletinAvailability.MISSING
    if 300 <= status < 400:
        return BulletinAvailability.REDIRECT_REJECTED
    return BulletinAvailability.UPSTREAM_ERROR


def _request_bulletin(
    url: str,
    method: str,
    headers: dict[str, str] | None = None,
) -> BulletinAvailability:
    request = urllib.request.Request(url, headers=headers or {}, method=method)
    opener = urllib.request.build_opener(_NoRedirectHandler)
    try:
        with opener.open(request, timeout=5) as response:
            if 200 <= response.status < 300:
                if method == "GET":
                    response.read(1)
                return BulletinAvailability.AVAILABLE
            return BulletinAvailability.UPSTREAM_ERROR
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        if status in (405, 501):
            return BulletinAvailability.HEAD_UNSUPPORTED
        return _status_from_http_error(status)
    except (socket.timeout, TimeoutError) as exc:
        logger.warning("Bulletin availability check timed out: %s", exc)
        return BulletinAvailability.TIMEOUT
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            logger.warning("Bulletin availability check timed out: %s", exc)
            return BulletinAvailability.TIMEOUT
        logger.warning("Bulletin availability check failed: %s", exc)
        return BulletinAvailability.UPSTREAM_ERROR
    except OSError as exc:
        logger.warning("Bulletin availability check failed: %s", exc)
        return BulletinAvailability.UPSTREAM_ERROR


def _validate_bulletin_origin(url: str) -> None:
    """Reject checks outside the validated official HTTPS origin."""
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port or 443
    except ValueError as exc:
        raise ValueError("Invalid bulletin URL.") from exc

    if (
        parsed.scheme != "https"
        or parsed.hostname != _BULLETINS_ORIGIN[1]
        or port != _BULLETINS_ORIGIN[2]
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path.lower().endswith(".pdf")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Bulletin checks are restricted to the official HTTPS origin."
        )


def is_bulletin_available(url: str) -> BulletinAvailability:
    """Check a constructed bulletin URL with bounded, cached HTTP requests.

    Confirmed available and missing results are cached briefly. Transient
    upstream errors, timeouts, and rejected redirects are not cached.
    """
    _validate_bulletin_origin(url)
    cache_key = (
        "state-bulletin-availability:"
        + hashlib.sha256(url.encode("utf-8")).hexdigest()
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return BulletinAvailability(cached)

    result = _request_bulletin(url, "HEAD")
    if result is BulletinAvailability.HEAD_UNSUPPORTED:
        result = _request_bulletin(
            url,
            "GET",
            headers={"Range": "bytes=0-0"},
        )

    if result in (
        BulletinAvailability.AVAILABLE,
        BulletinAvailability.MISSING,
    ):
        cache.set(
            cache_key,
            result.value,
            timeout=900 if result is BulletinAvailability.AVAILABLE else 300,
        )
    return result


def validate_uf(uf: str | None) -> str:
    """Return the normalised UF or raise ``ValueError``.

    Parameters
    ----------
    uf:
        Raw user input.

    Returns
    -------
    str
        Validated, uppercased two-letter UF code.

    Raises
    ------
    ValueError
        If *uf* is blank, too long, or not in :data:`VALID_UF_CODES`.
    """
    if not uf or not uf.strip():
        raise ValueError("Selecione uma Unidade Federativa.")
    cleaned = uf.strip().upper()
    # Guard against path traversal: must be exactly 2 uppercase ASCII letters
    if not _UF_RE.match(cleaned) or cleaned not in VALID_UF_CODES:
        raise ValueError(f"UF inválida: {uf!r}")
    return cleaned


def validate_year_week(raw: str | None) -> tuple[int, int]:
    """Parse and validate a ``YYYYWW`` string.

    Parameters
    ----------
    raw:
        Raw user input, expected as a 6-digit string (e.g. ``'202640'``).

    Returns
    -------
    tuple[int, int]
        Validated ``(year, week)`` pair.

    Raises
    ------
    ValueError
        If *raw* is blank, not exactly 6 digits, or the week is out of range
        for the given year according to the CDC epiweek system.
    """
    if not raw or not raw.strip():
        raise ValueError("Selecione uma semana epidemiológica.")
    cleaned = raw.strip()
    if not _YEARWEEK_RE.match(cleaned):
        raise ValueError(
            f"Formato de semana inválido: esperado YYYYSS, recebido {raw!r}"
        )
    year = int(cleaned[:4])
    week = int(cleaned[4:])

    # Validate using epiweeks - this handles 52/53-week years correctly
    try:
        Week(year, week, system="CDC")
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Semana epidemiológica inválida: {year}SE{week:02d}. {exc}"
        ) from exc

    return year, week
