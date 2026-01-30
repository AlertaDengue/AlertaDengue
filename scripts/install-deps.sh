#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-${ENV:-dev}}"
ENV_FILE="${ENV_FILE:-conda/base.yaml}"

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

if ! command -v conda >/dev/null 2>&1; then
  echo "conda not found in PATH"; exit 1
fi
eval "$(conda shell.bash hook)"

ENV_NAME="$(awk '/^name:/ {print $2; exit}' "$ENV_FILE")"
if [[ -z "${ENV_NAME:-}" ]]; then
  echo "Could not read 'name:' from $ENV_FILE"; exit 1
fi

if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  conda env update -n "$ENV_NAME" -f "$ENV_FILE" --prune
else
  conda env create -f "$ENV_FILE"
fi

conda activate "$ENV_NAME"

poetry config --local virtualenvs.create false
poetry config --local virtualenvs.in-project false

if [[ "$MODE" == "prod" ]]; then
  poetry install --no-root --only main
else
  poetry install --no-root
fi
