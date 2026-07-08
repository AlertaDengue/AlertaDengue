#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

cd frontend

if [[ "$#" -eq 0 ]]; then
  exec npm exec prettier --     --check     src     eslint.config.mjs     next.config.mjs     postcss.config.mjs     tsconfig.json     package.json
fi

files=()
for file in "$@"; do
  files+=("${file#frontend/}")
done

exec npm exec prettier -- --check "${files[@]}"
