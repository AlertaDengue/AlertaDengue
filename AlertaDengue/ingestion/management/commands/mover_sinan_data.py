#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dbfread import DBF

UF_CODES: dict[str, int] = {
    "AC": 12,
    "AL": 27,
    "AM": 13,
    "AP": 16,
    "BA": 29,
    "CE": 23,
    "DF": 53,
    "ES": 32,
    "GO": 52,
    "MA": 21,
    "MG": 31,
    "MS": 50,
    "MT": 51,
    "PA": 15,
    "PB": 25,
    "PE": 26,
    "PI": 22,
    "PR": 41,
    "RJ": 33,
    "RN": 24,
    "RO": 11,
    "RR": 14,
    "RS": 43,
    "SC": 42,
    "SE": 28,
    "SP": 35,
    "TO": 17,
}

_CODE_TO_UF: dict[int, str] = {v: k for k, v in UF_CODES.items()}
_UF_SIGLAS: set[str] = set(UF_CODES.keys())

_CID10_FIELDS: tuple[str, ...] = (
    "ID_AGRAVO",
    "CID10",
    "CID10_CODIGO",
    "CID10CODIGO",
)
_SEM_FIELDS: tuple[str, ...] = ("SEM_NOT", "SEM_NOTIF", "SE_NOTIF", "SE_NOTIF")

_UF_FIELD_CANDIDATES: tuple[str, ...] = (
    "SG_UF_NOT",
    "SG_UF",
    "UF",
    "UF_NOT",
    "ID_UF_NOT",
    "CO_UF_NOT",
    "ID_UF",
    "CO_UF",
)

_DBF_UF_PRIMARY: tuple[str, ...] = ("SG_UF", "SG_UF_NOT", "UF")
_CSV_UF_PRIMARY: tuple[str, ...] = ("SG_UF_NOT", "SG_UF", "UF")


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute SHA-256 hex digest for a file.

    Parameters
    ----------
    path
        File path.
    chunk_size
        Chunk size for streaming reads.

    Returns
    -------
    str
        SHA-256 hex digest.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class RoutingInfo:
    """
    Normalized routing info for placing a SINAN file.

    Attributes
    ----------
    src_path
        Source file path.
    country
        Bucket code, lower-case (e.g., 'sp', 'es', 'br').
    fmt_dir
        Format directory ('csv' or 'dbf').
    cid10_norm
        Normalized CID10 string (e.g., 'A92.0', 'A90').
    disease_code
        Disease code used for enqueueing (e.g., 'A92', 'A90').
    disease_dir
        Disease directory (e.g., 'dengue', 'chik', 'unknown').
    sem_not_max
        Max SEM_NOT found (YYYYWW as int).
    year
        Year extracted from SEM_NOT (YYYY).
    week
        Week extracted from SEM_NOT (WW).
    uf
        UF folder layer (kept empty to avoid nested UF folders by default).
    encoding
        Detected/used encoding for CSV, or DBF encoding used.
    delimiter
        Detected delimiter for CSV; empty for DBF.
    """

    src_path: Path
    country: str
    fmt_dir: str
    cid10_norm: str
    disease_code: str
    disease_dir: str
    sem_not_max: int
    year: int
    week: int
    uf: str
    encoding: str
    delimiter: str


def _normalize_header(name: str) -> str:
    """
    Normalize a header/field name for robust matching.

    Parameters
    ----------
    name
        Field name.

    Returns
    -------
    str
        Normalized field name.
    """
    return name.strip().strip("\ufeff").strip().upper()


def _find_first_index(
    header: list[str], candidates: tuple[str, ...]
) -> int | None:
    """
    Find the first matching index for candidates.

    Parameters
    ----------
    header
        Normalized header list.
    candidates
        Candidate field names.

    Returns
    -------
    int | None
        Index if found; otherwise None.
    """
    cand = {_normalize_header(c) for c in candidates}
    for i, h in enumerate(header):
        if h in cand:
            return i
    return None


def _find_field_name(
    field_names: list[str], candidates: tuple[str, ...]
) -> str | None:
    """
    Find the actual field name matching candidates (case-insensitive).

    Parameters
    ----------
    field_names
        Field names as stored in the file.
    candidates
        Candidate field names.

    Returns
    -------
    str | None
        Matching original field name, otherwise None.
    """
    cand = {_normalize_header(c) for c in candidates}
    for name in field_names:
        if _normalize_header(name) in cand:
            return name
    return None


def _parse_sem_not(value: str) -> int | None:
    """
    Parse SEM_NOT as YYYYWW.

    Parameters
    ----------
    value
        Raw value.

    Returns
    -------
    int | None
        Parsed SEM_NOT if valid; otherwise None.
    """
    raw = value.strip()
    if not raw or not raw.isdigit() or len(raw) != 6:
        return None
    return int(raw)


def _normalize_cid10(value: str) -> str:
    """
    Normalize CID10 values.

    Parameters
    ----------
    value
        Raw CID10 / ID_AGRAVO.

    Returns
    -------
    str
        Normalized CID10.
    """
    s = value.strip().upper().replace(",", ".")
    if not s:
        return ""
    if re.fullmatch(r"[A-Z]\d{2}\d", s):
        return f"{s[:3]}.{s[3]}"
    return s


def _disease_code_from_cid10(cid10_norm: str) -> str:
    """
    Extract disease code (e.g. A92) from normalized CID10.

    Parameters
    ----------
    cid10_norm
        Normalized CID10.

    Returns
    -------
    str
        Disease code (3 chars) or empty string.
    """
    if not cid10_norm:
        return ""
    s = cid10_norm.replace(".", "")
    return s[:3] if len(s) >= 3 else s


def _disease_dir_from_code(disease_code: str) -> str:
    """
    Map disease code to disease directory.

    Parameters
    ----------
    disease_code
        Disease code (e.g. A90, A92).

    Returns
    -------
    str
        Disease directory name.
    """
    if disease_code.startswith("A90") or disease_code.startswith("A91"):
        return "dengue"
    if disease_code.startswith("A92"):
        return "chik"
    return "unknown"


def _infer_fmt_dir_from_path(path: Path) -> str | None:
    """
    Infer fmt_dir from file extension.

    Parameters
    ----------
    path
        File path.

    Returns
    -------
    str | None
        'csv' or 'dbf' when recognized; otherwise None.
    """
    ext = path.suffix.lower()
    if ext == ".csv":
        return "csv"
    if ext == ".dbf":
        return "dbf"
    return None


def _decode_dbf_value(value: Any, encoding: str) -> str:
    """
    Decode DBF raw values to string.

    Parameters
    ----------
    value
        Raw value, possibly bytes.
    encoding
        Encoding.

    Returns
    -------
    str
        Decoded string.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(encoding, errors="replace").strip()
    return str(value).strip()


def _csv_field_limit() -> None:
    """
    Increase CSV field size limit for very large text fields.
    """
    try:
        csv.field_size_limit(10_000_000)
    except OverflowError:
        csv.field_size_limit(sys.maxsize)


def _read_text_sample(path: Path, encoding: str, size: int = 16384) -> str:
    """
    Read a small text sample for delimiter/header detection.

    Parameters
    ----------
    path
        File path.
    encoding
        Text encoding.
    size
        Maximum number of characters.

    Returns
    -------
    str
        Text sample.
    """
    with path.open("r", encoding=encoding, errors="replace", newline="") as f:
        return f.read(size)


def _header_from_sample(sample: str, delimiter: str) -> list[str] | None:
    """
    Parse header from a sample using a delimiter.

    Parameters
    ----------
    sample
        Text sample.
    delimiter
        CSV delimiter.

    Returns
    -------
    list[str] | None
        Header fields if any.
    """
    reader = csv.reader(io.StringIO(sample), delimiter=delimiter)
    return next(reader, None)


def _choose_csv_delimiter_and_header(
    csv_path: Path, encoding: str
) -> tuple[str, list[str]]:
    """
    Choose a CSV delimiter by validating CID10 and SEM_NOT presence.

    Parameters
    ----------
    csv_path
        CSV path.
    encoding
        Text encoding.

    Returns
    -------
    tuple[str, list[str]]
        (delimiter, header)

    Raises
    ------
    ValueError
        If a delimiter with required fields cannot be determined.
    """
    sample = _read_text_sample(csv_path, encoding=encoding)
    candidates = [";", ",", "\t", "|"]

    try:
        sniff = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        if sniff.delimiter:
            if sniff.delimiter in candidates:
                candidates.remove(sniff.delimiter)
            candidates.insert(0, sniff.delimiter)
    except csv.Error:
        pass

    best_errors: list[str] = []
    for d in candidates:
        header = _header_from_sample(sample, delimiter=d)
        if not header:
            best_errors.append(f"delimiter={d!r}: header vazio")
            continue

        norm = [_normalize_header(h) for h in header]
        cid_idx = _find_first_index(norm, _CID10_FIELDS)
        sem_idx = _find_first_index(norm, _SEM_FIELDS)

        if cid_idx is None or sem_idx is None:
            best_errors.append(
                f"delimiter={d!r}: faltam campos "
                f"CID10={cid_idx is not None} SEM={sem_idx is not None}"
            )
            continue

        return d, header

    raise ValueError(
        "Não foi possível determinar delimiter com header válido: "
        + "; ".join(best_errors[:6])
    )


def _iter_csv_rows(
    path: Path, *, encoding: str, delimiter: str
) -> Iterator[list[str]]:
    """
    Iterate CSV rows as lists.

    Parameters
    ----------
    path
        CSV path.
    encoding
        Encoding to use.
    delimiter
        Delimiter.

    Yields
    ------
    list[str]
        CSV row fields.
    """
    with path.open("r", encoding=encoding, errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            yield row


def _uf_priority(primary: tuple[str, ...]) -> tuple[str, ...]:
    """
    Build a full UF candidate priority list.

    Parameters
    ----------
    primary
        Primary candidate order.

    Returns
    -------
    tuple[str, ...]
        Primary candidates followed by remaining candidates.
    """
    rest = tuple(c for c in _UF_FIELD_CANDIDATES if c not in primary)
    return primary + rest


_DBF_UF_FIELDS = _uf_priority(_DBF_UF_PRIMARY)
_CSV_UF_FIELDS = _uf_priority(_CSV_UF_PRIMARY)


def _uf_sigla_from_raw(raw: str) -> tuple[str | None, bool]:
    """
    Normalize a UF raw value into a UF sigla.

    Parameters
    ----------
    raw
        Raw UF value (e.g. "SP", "35", "BR", "").

    Returns
    -------
    tuple[str | None, bool]
        (sigla, unknown). sigla None means blank/BR. unknown means non-empty
        that cannot be mapped.
    """
    s = raw.strip().upper()
    if not s:
        return None, False
    if s == "BR":
        return None, False
    if s in _UF_SIGLAS:
        return s, False
    if s.isdigit():
        sigla = _CODE_TO_UF.get(int(s))
        return (sigla, False) if sigla else (None, True)
    return None, True


def _select_bucket_from_candidates(
    *,
    siglas_by_field: dict[str, set[str]],
    unknown_by_field: dict[str, bool],
    priority: tuple[str, ...],
) -> str:
    """
    Select a bucket based on UF candidates (content-based).

    The first candidate (by `priority`) that yields exactly one valid UF sigla
    and no unknown values wins. Otherwise, falls back to BR.

    Parameters
    ----------
    siglas_by_field
        Mapping candidate -> set of UF siglas found.
    unknown_by_field
        Mapping candidate -> whether unknown UF-like values were found.
    priority
        Candidate evaluation order.

    Returns
    -------
    str
        Bucket label (UF sigla like "SP" or "BR").
    """
    for cand in priority:
        if cand not in siglas_by_field:
            continue
        if unknown_by_field.get(cand, False):
            continue
        siglas = siglas_by_field[cand]
        if len(siglas) == 1:
            return next(iter(siglas))
    return "BR"


def _extract_csv_routing_info(
    csv_path: Path,
    *,
    encoding: str | None,
    try_encodings: list[str],
    country_override: str | None,
) -> RoutingInfo:
    """
    Extract routing info from a CSV by scanning SEM_NOT max.

    Parameters
    ----------
    csv_path
        CSV file path.
    encoding
        Preferred encoding; when None, try `try_encodings`.
    try_encodings
        Encodings to try if `encoding` is None or fails.
    country_override
        Optional bucket override.

    Returns
    -------
    RoutingInfo
        Routing info.

    Raises
    ------
    ValueError
        When required fields are missing.
    """
    encodings: list[str] = []
    if encoding:
        encodings.append(encoding)
    encodings.extend([e for e in try_encodings if e not in encodings])

    errors: list[str] = []
    for enc in encodings:
        try:
            delimiter, header = _choose_csv_delimiter_and_header(
                csv_path,
                encoding=enc,
            )
            norm_header = [_normalize_header(h) for h in header]
            cid_idx = _find_first_index(norm_header, _CID10_FIELDS)
            sem_idx = _find_first_index(norm_header, _SEM_FIELDS)

            if cid_idx is None or sem_idx is None:
                raise ValueError("Header inválido (CID10/SEM_NOT ausentes)")

            uf_idxs: dict[str, int] = {}
            for cand in _CSV_UF_FIELDS:
                idx = _find_first_index(norm_header, (cand,))
                if idx is not None:
                    uf_idxs[cand] = idx

            rows = _iter_csv_rows(csv_path, encoding=enc, delimiter=delimiter)
            _ = next(rows, None)

            cid10_norm = ""
            sem_max: int | None = None

            siglas_by_field: dict[str, set[str]] = {c: set() for c in uf_idxs}
            unknown_by_field: dict[str, bool] = {c: False for c in uf_idxs}

            for row in rows:
                if cid_idx < len(row):
                    c = _normalize_cid10(row[cid_idx])
                    if c:
                        if not cid10_norm:
                            cid10_norm = c
                        elif cid10_norm != c:
                            raise ValueError(
                                "CSV com CID10 múltiplos: "
                                f"{cid10_norm!r} vs {c!r}"
                            )

                if sem_idx < len(row):
                    sem = _parse_sem_not(row[sem_idx])
                    if sem is not None:
                        sem_max = sem if sem_max is None else max(sem_max, sem)

                for cand, idx in uf_idxs.items():
                    if idx >= len(row):
                        continue
                    sigla, unknown = _uf_sigla_from_raw(row[idx])
                    unknown_by_field[cand] = unknown_by_field[cand] or unknown
                    if sigla is not None:
                        siglas_by_field[cand].add(sigla)

            if not cid10_norm:
                raise ValueError("CSV sem CID10/ID_AGRAVO")
            if sem_max is None:
                raise ValueError("CSV sem SEM_NOT válido")

            bucket = _select_bucket_from_candidates(
                siglas_by_field=siglas_by_field,
                unknown_by_field=unknown_by_field,
                priority=_CSV_UF_FIELDS,
            )
            country = country_override or bucket.lower()

            disease_code = _disease_code_from_cid10(cid10_norm)
            disease_dir = _disease_dir_from_code(disease_code)
            year = sem_max // 100
            week = sem_max % 100

            return RoutingInfo(
                src_path=csv_path,
                country=country,
                fmt_dir="csv",
                cid10_norm=cid10_norm,
                disease_code=disease_code,
                disease_dir=disease_dir,
                sem_not_max=sem_max,
                year=year,
                week=week,
                uf="",
                encoding=enc,
                delimiter=delimiter,
            )
        except Exception as exc:
            errors.append(f"{enc}: {type(exc).__name__}: {exc}")

    raise ValueError(
        "Falha ao ler CSV "
        f"{csv_path} com encodings {encodings}: " + " | ".join(errors[:4])
    )


def _extract_dbf_routing_info(
    dbf_path: Path,
    *,
    encoding: str,
    country_override: str | None,
) -> RoutingInfo:
    """
    Extract routing info from a DBF by scanning SEM_NOT max.

    Parameters
    ----------
    dbf_path
        DBF file path.
    encoding
        DBF encoding to use.
    country_override
        Optional bucket override.

    Returns
    -------
    RoutingInfo
        Routing info.

    Raises
    ------
    ValueError
        When required fields are missing.
    """
    try:
        table = DBF(str(dbf_path), encoding=encoding, load=False, raw=True)
    except Exception as exc:
        raise ValueError(f"DBF inválido: {exc}") from exc

    field_names = list(table.field_names)
    cid_field = _find_field_name(field_names, _CID10_FIELDS)
    sem_field = _find_field_name(field_names, _SEM_FIELDS)

    if cid_field is None:
        raise ValueError(f"DBF sem CID10/ID_AGRAVO: {dbf_path}")
    if sem_field is None:
        raise ValueError(f"DBF sem SEM_NOT: {dbf_path}")

    uf_fields: dict[str, str] = {}
    for cand in _DBF_UF_FIELDS:
        fname = _find_field_name(field_names, (cand,))
        if fname is not None:
            uf_fields[cand] = fname

    cid10_norm = ""
    sem_max: int | None = None
    seen_any = False

    siglas_by_field: dict[str, set[str]] = {c: set() for c in uf_fields}
    unknown_by_field: dict[str, bool] = {c: False for c in uf_fields}

    for rec in table:
        seen_any = True

        c_raw = _decode_dbf_value(rec.get(cid_field), encoding)
        c = _normalize_cid10(c_raw)
        if c:
            if not cid10_norm:
                cid10_norm = c
            elif cid10_norm != c:
                raise ValueError(
                    "DBF com CID10 múltiplos: "
                    f"{cid10_norm!r} vs {c!r} em {dbf_path}"
                )

        s_raw = _decode_dbf_value(rec.get(sem_field), encoding)
        sem = _parse_sem_not(s_raw)
        if sem is not None:
            sem_max = sem if sem_max is None else max(sem_max, sem)

        for cand, fname in uf_fields.items():
            u_raw = _decode_dbf_value(rec.get(fname), encoding)
            sigla, unknown = _uf_sigla_from_raw(u_raw)
            unknown_by_field[cand] = unknown_by_field[cand] or unknown
            if sigla is not None:
                siglas_by_field[cand].add(sigla)

    if not seen_any:
        raise ValueError(f"DBF sem registros: {dbf_path}")
    if not cid10_norm:
        raise ValueError(f"DBF sem CID10/ID_AGRAVO: {dbf_path}")
    if sem_max is None:
        raise ValueError(f"DBF sem SEM_NOT válido: {dbf_path}")

    bucket = _select_bucket_from_candidates(
        siglas_by_field=siglas_by_field,
        unknown_by_field=unknown_by_field,
        priority=_DBF_UF_FIELDS,
    )
    country = country_override or bucket.lower()

    disease_code = _disease_code_from_cid10(cid10_norm)
    disease_dir = _disease_dir_from_code(disease_code)
    year = sem_max // 100
    week = sem_max % 100

    return RoutingInfo(
        src_path=dbf_path,
        country=country,
        fmt_dir="dbf",
        cid10_norm=cid10_norm,
        disease_code=disease_code,
        disease_dir=disease_dir,
        sem_not_max=sem_max,
        year=year,
        week=week,
        uf="",
        encoding=encoding,
        delimiter="",
    )


def _build_filename(info: RoutingInfo) -> str:
    """
    Build canonical filename.

    Parameters
    ----------
    info
        Routing info.

    Returns
    -------
    str
        Canonical filename.
    """
    ext = info.src_path.suffix.lower()
    if info.disease_dir == "dengue":
        prefix = "DenInfodengue"
    elif info.disease_dir == "chik":
        prefix = "ChikInfodengue"
    else:
        prefix = "Infodengue"

    sem = f"{info.sem_not_max:06d}"
    label = info.country.upper()
    return f"{prefix}_{label}_{sem}{ext}"


def _rel_dest_path(info: RoutingInfo, *, include_uf: bool) -> Path:
    """
    Build destination relative path.

    Parameters
    ----------
    info
        Routing info.
    include_uf
        Kept for CLI compatibility. UF folder layer is not used by default.

    Returns
    -------
    Path
        Relative destination path.
    """
    sem = f"{info.sem_not_max:06d}"
    name = _build_filename(info)
    parts: list[str] = [info.country.lower(), info.fmt_dir, info.disease_dir]
    if include_uf and info.uf:
        parts.append(info.uf)
    parts.extend([str(info.year), sem])
    return Path(*parts) / name


def _strip_numeric_suffix(stem: str) -> str:
    """
    Strip trailing _NN suffix from a filename stem.

    Parameters
    ----------
    stem
        Filename stem.

    Returns
    -------
    str
        Stem without trailing numeric suffix.
    """
    return re.sub(r"_(\d{2})$", "", stem)


def _base_roots(base: Path) -> list[Path]:
    """
    Compute base roots to check for existence.

    Parameters
    ----------
    base
        Base directory.

    Returns
    -------
    list[Path]
        Roots to check.
    """
    roots = [base]
    if base.name.lower() in {"br", "es"}:
        roots.append(base.parent)
    return roots


def _exists_in_any_base(rel_path: Path, bases: list[Path]) -> Path | None:
    """
    Check if a relative path exists under any base root.

    Parameters
    ----------
    rel_path
        Relative path.
    bases
        Base roots.

    Returns
    -------
    Path | None
        Full path to the first existing file found, or None.
    """
    for b in bases:
        p = b / rel_path
        if p.exists():
            return p
    return None


def _resolve_collision(
    rel_path: Path,
    *,
    src_path: Path,
    imported_roots: list[Path],
    uploaded_roots: list[Path],
    reserved: set[Path],
    on_exists: str,
) -> Path | None:
    """
    Resolve destination collisions across imported + uploaded + in-run reserved.

    Parameters
    ----------
    rel_path
        Proposed destination relative path.
    src_path
        Source file.
    imported_roots
        Roots for imported existence checks.
    uploaded_roots
        Roots for uploaded existence checks.
    reserved
        Relative paths already reserved in this run.
    on_exists
        Collision policy: version, skip, error.

    Returns
    -------
    Path | None
        Final relative path, or None to signal skip.
    """
    bases = imported_roots + uploaded_roots
    src_hash: str | None = None

    def _hash_src() -> str:
        nonlocal src_hash
        if src_hash is None:
            src_hash = _sha256_file(src_path)
        return src_hash

    def _is_same(existing: Path) -> bool:
        return _sha256_file(existing) == _hash_src()

    occupied = rel_path in reserved
    existing_full = _exists_in_any_base(rel_path, bases)
    if existing_full is not None:
        if _is_same(existing_full):
            return None
        occupied = True

    if not occupied:
        return rel_path

    if on_exists == "skip":
        return None
    if on_exists == "error":
        raise FileExistsError(str(rel_path))

    parent = rel_path.parent
    base_stem = _strip_numeric_suffix(rel_path.stem)
    suffix = rel_path.suffix

    for n in range(1, 1000):
        candidate = parent / f"{base_stem}_{n:02d}{suffix}"
        if candidate in reserved:
            continue
        existing_full = _exists_in_any_base(candidate, bases)
        if existing_full is not None:
            if _is_same(existing_full):
                return None
            continue
        return candidate

    raise FileExistsError(f"Sem slot livre para versionamento: {rel_path}")


def _expand_inputs(paths: list[Path]) -> list[Path]:
    """
    Expand file/dir inputs into a flat list of CSV/DBF files.

    Parameters
    ----------
    paths
        Input paths (files or directories).

    Returns
    -------
    list[Path]
        Sorted list of files found.
    """
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            for ext in ("*.csv", "*.CSV", "*.dbf", "*.DBF"):
                files.extend(sorted(p.rglob(ext)))
        else:
            files.append(p)

    unique = sorted({f.resolve() for f in files if f.exists()})
    return unique


def move_to_canonical(
    src: Path,
    *,
    imported_base: Path,
    uploaded_base: Path,
    reserved_relpaths: set[Path],
    dry_run: bool,
    include_uf: bool,
    country: str | None,
    fmt_dir: str | None,
    csv_encoding: str | None,
    try_csv_encodings: list[str],
    dbf_encoding: str,
    on_exists: str,
) -> tuple[bool, Path | None, RoutingInfo | None, str | None]:
    """
    Move one file to canonical imported path.

    Parameters
    ----------
    src
        Source file.
    imported_base
        Imported base directory.
    uploaded_base
        Uploaded base directory for collision checks.
    reserved_relpaths
        Reserved relative paths within the current run.
    dry_run
        Whether to skip the actual move.
    include_uf
        CLI compatibility; UF folder layer is disabled by default.
    country
        Bucket override (lowercase).
    fmt_dir
        Optional override for fmt dir.
    csv_encoding
        Optional preferred CSV encoding.
    try_csv_encodings
        Encodings to try for CSV.
    dbf_encoding
        Encoding for DBF decoding.
    on_exists
        Collision policy: version, skip, error.

    Returns
    -------
    tuple[bool, Path | None, RoutingInfo | None, str | None]
        (ok, dest, info, err). If err starts with "SKIP", it's a skip.
    """
    fmt = fmt_dir or _infer_fmt_dir_from_path(src)
    if fmt not in {"csv", "dbf"}:
        return False, None, None, f"Formato não suportado: {src}"

    imported_roots = _base_roots(imported_base)
    uploaded_roots = _base_roots(uploaded_base)

    try:
        if fmt == "dbf":
            info = _extract_dbf_routing_info(
                src,
                encoding=dbf_encoding,
                country_override=country,
            )
        else:
            info = _extract_csv_routing_info(
                src,
                encoding=csv_encoding,
                try_encodings=try_csv_encodings,
                country_override=country,
            )

        rel = _rel_dest_path(info, include_uf=include_uf)
        rel_final = _resolve_collision(
            rel,
            src_path=src,
            imported_roots=imported_roots,
            uploaded_roots=uploaded_roots,
            reserved=reserved_relpaths,
            on_exists=on_exists,
        )
        if rel_final is None:
            return False, None, info, "SKIP (already exists)"

        reserved_relpaths.add(rel_final)
        dest = imported_base / rel_final

        if dry_run:
            return True, dest, info, None

        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise FileExistsError(f"Destino já existe: {dest}")

        shutil.move(str(src), str(dest))
        return True, dest, info, None
    except Exception as exc:
        return False, None, None, f"{type(exc).__name__}: {exc}"


def _build_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.

    Returns
    -------
    argparse.ArgumentParser
        Parser.
    """
    p = argparse.ArgumentParser(
        prog="mover_sinan_data.py",
        description=(
            "Move CSV/DBF to canonical imported path using CID10 + max SEM_NOT "
            "and content-based UF bucketing."
        ),
    )
    p.add_argument("paths", nargs="+", help="Files and/or directories.")
    p.add_argument(
        "--imported-base",
        default="/Storage/infodengue_data/sftp2/sinan/raw_data/imported",
        help="Destination base directory for canonical placement.",
    )
    p.add_argument(
        "--uploaded-base",
        default="/Storage/infodengue_data/sftp2/sinan/raw_data/uploaded",
        help="Extra base directory used for collision checks.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not move files; only print planned actions.",
    )
    p.add_argument(
        "--include-uf",
        action="store_true",
        help="CLI compatibility. UF folder layer is disabled by default.",
    )
    p.add_argument(
        "--country",
        default=None,
        help="Override bucket (e.g. br, es, sp). If omitted, derived from data.",
    )
    p.add_argument(
        "--fmt-dir",
        default=None,
        choices=["csv", "dbf"],
        help="Override format dir. If omitted, inferred from extension.",
    )
    p.add_argument(
        "--csv-encoding",
        default=None,
        help="Preferred CSV encoding (e.g. iso-8859-1).",
    )
    p.add_argument(
        "--try-csv-encodings",
        default="iso-8859-1,cp1252,utf-8,utf-8-sig,latin-1",
        help="Comma-separated CSV encodings to try.",
    )
    p.add_argument(
        "--dbf-encoding",
        default="iso-8859-1",
        help="DBF encoding to use.",
    )
    p.add_argument(
        "--on-exists",
        default="version",
        choices=["version", "skip", "error"],
        help="Collision policy (default: version).",
    )
    p.add_argument(
        "--manifest",
        default=None,
        help="Write a JSON manifest of moved files to this path.",
    )
    return p


def main() -> int:
    """
    CLI entrypoint.

    Returns
    -------
    int
        Exit code.
    """
    args = _build_parser().parse_args()
    _csv_field_limit()

    imported_base = Path(args.imported_base).resolve()
    uploaded_base = Path(args.uploaded_base).resolve()

    inputs = [Path(p).resolve() for p in args.paths]
    files = _expand_inputs(inputs)

    processed = 0
    moved = 0
    skipped = 0
    failed = 0

    try_encodings = [
        e.strip() for e in str(args.try_csv_encodings).split(",") if e.strip()
    ]
    reserved_relpaths: set[Path] = set()
    manifest_entries: list[dict[str, Any]] = []

    country_override = args.country.lower() if args.country else None

    for src in files:
        processed += 1
        ok, dest, info, err = move_to_canonical(
            src,
            imported_base=imported_base,
            uploaded_base=uploaded_base,
            reserved_relpaths=reserved_relpaths,
            dry_run=bool(args.dry_run),
            include_uf=bool(args.include_uf),
            country=country_override,
            fmt_dir=args.fmt_dir,
            csv_encoding=args.csv_encoding,
            try_csv_encodings=try_encodings,
            dbf_encoding=args.dbf_encoding,
            on_exists=args.on_exists,
        )

        if ok and dest is not None and err is None and info is not None:
            moved += 1
            prefix = "DRY-RUN" if args.dry_run else "OK"
            print(f"{prefix}: {src} -> {dest}")
            manifest_entries.append(
                {
                    "dest": str(dest),
                    "country": info.country.lower(),
                    "disease": info.disease_code,
                    "disease_dir": info.disease_dir,
                    "year": info.year,
                    "week": info.week,
                    "sem_not_max": info.sem_not_max,
                    "uf": info.country.upper(),
                    "fmt": info.fmt_dir,
                }
            )
        elif err and err.startswith("SKIP"):
            skipped += 1
            print(f"SKIP: {src} ({err})")
        else:
            failed += 1
            print(f"FAIL: {src} ({err})")

    if args.manifest and manifest_entries:
        manifest_entries.sort(
            key=lambda e: (
                e["country"] == "br",
                e["country"],
                e["sem_not_max"],
            ),
        )
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest_entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"MANIFEST: {manifest_path} ({len(manifest_entries)} entries)")

    print(
        "SUMMARY: "
        f"processed={processed} moved={moved} skipped={skipped} "
        f"failed={failed}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
