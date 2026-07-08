#!/usr/bin/env python3

"""Run Vulture using the repository's pyproject configuration."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tomllib


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    pyproject = project_root / "pyproject.toml"
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    tool_config = config["tool"]["vulture"]

    command = ["poetry", "run", "vulture"]
    command.extend(sys.argv[1:] or tool_config.get("paths", []))

    exclude = tool_config.get("exclude", [])
    if exclude:
        command.extend(["--exclude", ",".join(exclude)])

    ignore_names = tool_config.get("ignore_names", [])
    if ignore_names:
        command.extend(["--ignore-names", ",".join(ignore_names)])

    min_confidence = tool_config.get("min_confidence")
    if min_confidence is not None:
        command.extend(["--min-confidence", str(min_confidence)])

    return subprocess.run(command, cwd=project_root, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
