from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile


STANZA_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a pgBackRest config.")
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stanza", required=True)
    parser.add_argument("--repo-path", type=Path, required=True)
    parser.add_argument("--pg-user", required=True)
    parser.add_argument("--retention-full", type=int, required=True)
    parser.add_argument("--process-max", type=int, required=True)
    return parser


def validate_stanza(stanza: str) -> str:
    if not STANZA_RE.fullmatch(stanza):
        raise ValueError(f"Invalid stanza name: {stanza!r}")
    return stanza


def validate_pg_user(pg_user: str) -> str:
    if not pg_user.strip():
        raise ValueError("PostgreSQL user must not be empty.")
    return pg_user


def validate_repo_path(repo_path: Path) -> Path:
    if not repo_path.is_absolute():
        raise ValueError(f"Repository path must be absolute: {repo_path}")
    return repo_path


def render_template(
    template_text: str,
    *,
    stanza: str,
    repo_path: Path,
    pg_user: str,
    retention_full: int,
    process_max: int,
) -> str:
    rendered = template_text
    replacements = {
        "<repository path>": os.fspath(repo_path),
        "<retention count>": str(retention_full),
        "<process count>": str(process_max),
        "<stanza>": stanza,
        "<PSQL_USER>": pg_user,
    }

    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)

    return rendered.rstrip("\n") + "\n"


def atomic_write(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output_path.parent,
        delete=False,
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)

    temp_path.chmod(0o640)
    temp_path.replace(output_path)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    stanza = validate_stanza(args.stanza)
    pg_user = validate_pg_user(args.pg_user)
    repo_path = validate_repo_path(args.repo_path)

    template_text = args.template.read_text(encoding="utf-8")
    rendered = render_template(
        template_text,
        stanza=stanza,
        repo_path=repo_path,
        pg_user=pg_user,
        retention_full=args.retention_full,
        process_max=args.process_max,
    )
    atomic_write(args.output, rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
