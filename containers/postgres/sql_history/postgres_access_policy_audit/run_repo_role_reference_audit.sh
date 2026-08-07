#!/usr/bin/env bash
# Read-only repository reference audit for PostgreSQL access-policy candidates.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <development|staging|production>" >&2
  exit 64
fi

environment_label=$1
if [[ ! $environment_label =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Environment label may contain only letters, numbers, dot, underscore, and hyphen." >&2
  exit 64
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/../../../.." && pwd)
audit_root=${POSTGRES_ACCESS_AUDIT_ROOT:-/opt/services/infodengue/database_audits}
audited_utc=$(date -u +%Y%m%dT%H%M%SZ)
output_dir="${audit_root}/postgres_access_policy_${environment_label}_${audited_utc}"
mkdir -p "$output_dir"
output_file="$output_dir/repo_role_references.tsv"
printf 'searched_token\tfile_path\tline_number\tredacted_line\n' > "$output_file"

tokens=(infodenguedev analista mosqlimate_dev dengueadmin)
for token in "${tokens[@]}"; do
  while IFS= read -r file; do
    while IFS=: read -r line_number line; do
      base_name=${file##*/}
      if [[ $base_name == .env || $base_name == .env.* || $base_name == *.env || $base_name == *env.* ]]; then
        if [[ $line =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*= ]]; then
          redacted_line="${BASH_REMATCH[1]}=<matched role: ${token}>"
        else
          redacted_line="<environment-like file; matched role: ${token}>"
        fi
      elif [[ ${line,,} == *password* || ${line,,} == *pass* || ${line,,} == *secret* || ${line,,} == *token* || ${line,,} == *key* || ${line,,} == *dsn* || ${line,,} == *url* ]]; then
        redacted_line="<REDACTED credential-bearing line; token present>"
      else
        redacted_line=$line
      fi
      redacted_line=${redacted_line//$'\t'/ }
      printf '%s\t%s\t%s\t%s\n' "$token" "${file#"$repo_root"/}" "$line_number" "$redacted_line" >> "$output_file"
    done < <(rg -n -i -e "$token" -- "$file" || true)
  done < <(rg -l -i -e "$token" \
    -g '!.git/**' -g '!__pycache__/**' -g '!.mypy_cache/**' -g '!.pytest_cache/**' \
    -g '!node_modules/**' -g '!staticfiles/**' -g '!media/**' -g '!database_exports/**' -g '!database_audits/**' \
    "$repo_root" || true)
done

printf 'Repository reference audit complete: %s\n' "$output_file"
