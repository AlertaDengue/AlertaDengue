#!/usr/bin/env bash
set -euo pipefail

# cd to repo root
SCRIPT_PATH="${BASH_SOURCE:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$SCRIPT_DIR/.."

# Make uv install into the current interpreter (conda/venv)
export UV_PYTHON="$(python -c 'import sys; print(sys.executable)')"

python -m pip install uv
uv pip install -e "."
