#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dbfread import DBF


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 hex digest for a file."""
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
    Normalized routing info for placing an InfoDengue file.

    Attributes
    ----------
    src_path
        Source file path.
    country
        Country code, lower-case (e.g., 'br', 'es').
    fmt_dir
        Format directory ('csv' or 'dbf').
    cid10_norm
        Normalized CID10 string (e.g., 'A92.0', 'A90').
    disease_dir
        Disease directory (e.g., 'dengue', 'chik', 'unknown').
    sem_not_max
        Max SEM_NOT found (YYYYWW as int).
    year
        Year extracted from SEM_NOT (YYYY).
    uf
        UF code (optional, when include_uf is enabled).
    encoding
        Detected/used encoding for CSV, or DBF encoding used.
    delimiter
        Detected delimiter for CSV; empty for DBF.
    """

    src_path: Path
    country: str
    fmt_dir: str
    cid10_norm: str
    disease_dir: str
    sem_not_max: int
    year: int
    uf: str
    encoding: str
    delimiter: str


_CID10_FIELDS = ("ID_AGRAVO", "CID10", "CID10_CODIGO", "CID10CODIGO")
_SEM_FIELDS = ("SEM_NOT", "SEM_NOTIF", "SE_NOTIF", "SE_NOTIF")
_UF_FIELDS = ("SG_UF_NOT", "SG_UF", "UF")


def _normalize_header(name: str) -> str:
    """
    Normalize a header field name for robust matching.

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

    Examples
    --------
    - 'A920' -> 'A92.0'
    - 'A92.0' -> 'A92.0'
    - 'A90' -> 'A90'

    Parameters
    ----------
    value
        Raw CID10 / ID_AGRAVO.

    Returns
    -------
    str
        Normalized CID10.
    """
    s = value.strip().upper()
    s = s.replace(",", ".")
    if not s:
        return ""
    if re.fullmatch(r"[A-Z]\d{2}\d", s):
        return f"{s[:3]}.{s[3]}"
    return s


def _disease_dir_from_cid10(cid10_norm: str) -> str:
    """
    Map CID10 to disease directory.

    Parameters
    ----------
    cid10_norm
        Normalized CID10.

    Returns
    -------
    str
        Disease directory name.
    """
    if cid10_norm.startswith("A90"):
        return "dengue"
    if cid10_norm.startswith("A92"):
        return "chik"
    return "unknown"


def _infer_country_from_path(path: Path) -> str | None:
    """
    Infer country code from any path component.

    Parameters
    ----------
    path
        Path to inspect.

    Returns
    -------
    str | None
        Country code if found, else None.
    """
    for part in (path.name, *[p.name for p in path.parents]):
        m = re.search(r"(^|[_\-.])(br|es)([_\-.]|$)", part.lower())
        if m:
            return m.group(2)
    for p in path.parts:
        if p.lower() in {"br", "es"}:
            return p.lower()
    return None


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
        'csv' or 'dbf' when recognized, else None.
    """
    ext = path.suffix.lower()
    if ext == ".csv":
        return "csv"
    if ext == ".dbf":
        return "dbf"
    return None


def _find_first_index(
    header: list[str],
    candidates: tuple[str, ...],
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
        Index if found, else None.
    """
    cand = {_normalize_header(c) for c in candidates}
    for i, h in enumerate(header):
        if h in cand:
            return i
    return None


def _find_field_name(
    field_names: list[str],
    candidates: tuple[str, ...],
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
        Matching original field name, else None.
    """
    cand = {_normalize_header(c) for c in candidates}
    for name in field_names:
        if _normalize_header(name) in cand:
            return name
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
        try:
            return value.decode(encoding, errors="ignore").strip()
        except Exception:
            return value.decode("ascii", errors="ignore").strip()
    return str(value).strip()


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
        Max number of characters to read.

    Returns
    -------
    str
        Sample.
    """
    # with path.open("r", encoding=encoding, newline="") as f:
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
    csv_path: Path,
    encoding: str,
    include_uf: bool,
) -> tuple[str, list[str]]:
    """
    Choose a CSV delimiter by validating required fields in the header.

    Parameters
    ----------
    csv_path
        CSV path.
    encoding
        Text encoding.
    include_uf
        Whether UF is required (it is not required even if enabled).

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
        if sniff.delimiter and sniff.delimiter not in candidates:
            candidates.insert(0, sniff.delimiter)
        elif sniff.delimiter:
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
        uf_idx = _find_first_index(norm, _UF_FIELDS) if include_uf else None

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
    path: Path,
    *,
    encoding: str,
    delimiter: str,
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


def _extract_csv_routing_info(
    csv_path: Path,
    *,
    include_uf: bool,
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
    include_uf
        Whether to include UF in routing.
    encoding
        Preferred encoding; when None, try `try_encodings`.
    try_encodings
        Encodings to try if `encoding` is None or fails.
    country_override
        Optional country override.

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
                include_uf=include_uf,
            )
            norm_header = [_normalize_header(h) for h in header]
            cid_idx = _find_first_index(norm_header, _CID10_FIELDS)
            sem_idx = _find_first_index(norm_header, _SEM_FIELDS)
            uf_idx = (
                _find_first_index(norm_header, _UF_FIELDS)
                if include_uf
                else None
            )

            if cid_idx is None or sem_idx is None:
                raise ValueError("Header inválido (CID10/SEM_NOT ausentes)")

            rows = _iter_csv_rows(csv_path, encoding=enc, delimiter=delimiter)
            _ = next(rows, None)

            cid10_norm = ""
            sem_max: int | None = None
            uf = ""

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

                if include_uf and uf_idx is not None and not uf:
                    if uf_idx < len(row):
                        uf = row[uf_idx].strip().upper()

            if not cid10_norm:
                raise ValueError("CSV sem CID10/ID_AGRAVO")
            if sem_max is None:
                raise ValueError("CSV sem SEM_NOT válido")

            country = (
                country_override or _infer_country_from_path(csv_path) or "br"
            )
            disease_dir = _disease_dir_from_cid10(cid10_norm)
            year = int(str(sem_max)[:4])

            return RoutingInfo(
                src_path=csv_path,
                country=country,
                fmt_dir="csv",
                cid10_norm=cid10_norm,
                disease_dir=disease_dir,
                sem_not_max=sem_max,
                year=year,
                uf=uf,
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
    include_uf: bool,
    encoding: str,
    country_override: str | None,
) -> RoutingInfo:
    """
    Extract routing info from a DBF by scanning SEM_NOT max.

    Parameters
    ----------
    dbf_path
        DBF file path.
    include_uf
        Whether to include UF in routing.
    encoding
        DBF encoding to use.
    country_override
        Optional country override.

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
    uf_field = (
        _find_field_name(field_names, _UF_FIELDS) if include_uf else None
    )

    if cid_field is None:
        raise ValueError(f"DBF sem CID10/ID_AGRAVO: {dbf_path}")
    if sem_field is None:
        raise ValueError(f"DBF sem SEM_NOT: {dbf_path}")

    cid10_norm = ""
    sem_max: int | None = None
    uf = ""
    seen_any = False

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

        if include_uf and uf_field and not uf:
            u_raw = _decode_dbf_value(rec.get(uf_field), encoding)
            uf = u_raw.upper()

    if not seen_any:
        raise ValueError(f"DBF sem registros: {dbf_path}")
    if not cid10_norm:
        raise ValueError(f"DBF sem CID10/ID_AGRAVO: {dbf_path}")
    if sem_max is None:
        raise ValueError(f"DBF sem SEM_NOT válido: {dbf_path}")

    country = country_override or _infer_country_from_path(dbf_path) or "br"
    disease_dir = _disease_dir_from_cid10(cid10_norm)
    year = int(str(sem_max)[:4])

    return RoutingInfo(
        src_path=dbf_path,
        country=country,
        fmt_dir="dbf",
        cid10_norm=cid10_norm,
        disease_dir=disease_dir,
        sem_not_max=sem_max,
        year=year,
        uf=uf,
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
    if info.country.lower() == "br":
        return f"{prefix}_{sem}{ext}"
    cc = info.country.upper()
    return f"{prefix}_{cc}_{sem}{ext}"


def _rel_dest_path(info: RoutingInfo, *, include_uf: bool) -> Path:
    """
    Build destination relative path.

    Parameters
    ----------
    info
        Routing info.
    include_uf
        Whether UF should be included.

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
    Check if a relative path exists under any of the base roots.

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

    If an identical file (by checksum) already exists at rel_path or any of its
    versioned versions, we return None to signal it should be skipped.
    """
    src_hash = _sha256_file(src_path)

    def _get_match(target_rel: Path) -> bool:
        """Check if target_rel matches src by checksum or reservation."""
        if target_rel in reserved:
            return True  # If reserved, we don't have its hash yet, assume collision

        existing_full = _exists_in_any_base(
            target_rel, imported_roots + uploaded_roots
        )
        if not existing_full:
            return False

        # If it exists, check checksum
        return _sha256_file(existing_full) == src_hash

    # 1. Check canonical path
    if _exists_in_any_base(rel_path, imported_roots + uploaded_roots):
        if _get_match(rel_path):
            return None  # ALREADY_EXISTS (same checksum)
    elif rel_path not in reserved:
        return rel_path

    if on_exists == "skip":
        return None
    if on_exists == "error":
        raise FileExistsError(str(rel_path))

    # 2. Check versioned paths
    parent = rel_path.parent
    base_stem = _strip_numeric_suffix(rel_path.stem)
    suffix = rel_path.suffix

    for n in range(1, 1000):
        candidate = parent / f"{base_stem}_{n:02d}{suffix}"
        if _exists_in_any_base(candidate, imported_roots + uploaded_roots):
            if _get_match(candidate):
                return None  # ALREADY_EXISTS (same checksum)
        elif candidate not in reserved:
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
    """Move one file to canonical imported path."""
    fmt = fmt_dir or _infer_fmt_dir_from_path(src)
    if fmt not in {"csv", "dbf"}:
        return False, None, None, f"Formato não suportado: {src}"

    imported_roots = _base_roots(imported_base)
    uploaded_roots = _base_roots(uploaded_base)

    try:
        if fmt == "dbf":
            info = _extract_dbf_routing_info(
                src,
                include_uf=include_uf,
                encoding=dbf_encoding,
                country_override=country,
            )
        else:
            info = _extract_csv_routing_info(
                src,
                include_uf=include_uf,
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
            return False, None, info, "SKIP (já existe)"

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
        prog="infodengue_move.py",
        description=(
            "Move CSV/DBF to canonical imported path using CID10 + max SEM_NOT."
        ),
    )
    p.add_argument("paths", nargs="+", help="Files and/or directories.")
    p.add_argument(
        "--imported-base",
        default="/Storage/infodengue_data/sftp2/alertadengue/imported",
        help="Destination base directory for canonical placement.",
    )
    p.add_argument(
        "--uploaded-base",
        default="/Storage/infodengue_data/sftp2/alertadengue/uploaded",
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
        help="Include UF folder layer when UF is present.",
    )
    p.add_argument(
        "--country",
        default=None,
        help="Override country (e.g. br, es). If omitted, inferred.",
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
        default="iso-8859-1,cp1252,utf-8,utf-8-sig",
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

    try:
        csv.field_size_limit(10**7)
    except OverflowError:
        csv.field_size_limit(sys.maxsize)

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

    for src in files:
        processed += 1
        ok, dest, info, err = move_to_canonical(
            src,
            imported_base=imported_base,
            uploaded_base=uploaded_base,
            reserved_relpaths=reserved_relpaths,
            dry_run=bool(args.dry_run),
            include_uf=bool(args.include_uf),
            country=args.country.lower() if args.country else None,
            fmt_dir=args.fmt_dir,
            csv_encoding=args.csv_encoding,
            try_csv_encodings=try_encodings,
            dbf_encoding=args.dbf_encoding,
            on_exists=args.on_exists,
        )

        if ok and dest is not None and err is None:
            moved += 1
            prefix = "DRY-RUN" if args.dry_run else "OK"
            print(f"{prefix}: {src} -> {dest}")
            if info is not None:
                manifest_entries.append(
                    {
                        "dest": str(dest),
                        "country": info.country,
                        "disease": info.cid10_norm,
                        "disease_dir": info.disease_dir,
                        "year": info.year,
                        "week": info.sem_not_max % 100,
                        "sem_not_max": info.sem_not_max,
                        "uf": info.uf,
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
            key=lambda e: (e["country"] != "es", e["sem_not_max"]),
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
