#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --env dev|staging|prod --week YYYYWW" >&2
}

fail() {
  echo "[EE] $*" >&2
  exit 1
}

argument_error() {
  echo "[EE] $*" >&2
  usage
  exit 2
}

runtime_env=""
week=""
while (($#)); do
  case "$1" in
    --env|--week)
      (($# >= 2)) && [[ -n "$2" && "$2" != --* ]] || argument_error "Missing value for $1"
      case "$1" in
        --env) runtime_env="$2" ;;
        --week) week="$2" ;;
      esac
      shift 2
      ;;
    --help|-h) usage; exit 0 ;;
    *) argument_error "Unknown argument: $1" ;;
  esac
done

[[ -n "$runtime_env" ]] || argument_error "Missing --env"
[[ -n "$week" ]] || argument_error "Missing --week"
case "$runtime_env" in
  dev|staging|prod) ;;
  *) argument_error "Invalid --env: $runtime_env" ;;
esac
[[ "$week" =~ ^[0-9]{6}$ ]] || argument_error "Invalid --week: expected YYYYWW"
cd "$(dirname "${BASH_SOURCE[0]}")/.."
repo_root="$(pwd -P)"
source_static="$repo_root/AlertaDengue/static/img/incidence_maps"

# Follow the host-side deployment convention; never print configuration values.
set -a
source .envs/.env
set +a
export ENV="$runtime_env"

for command in docker sha256sum; do
  command -v "$command" >/dev/null || fail "Required command not found: $command"
done

# Match the selected .sugar.yaml profile, including its project name.
compose=(docker compose --env-file .envs/.env
  --file containers/compose-base.yaml
  --file "containers/compose-${runtime_env}.yaml")
if [[ "$runtime_env" != dev ]]; then
  compose+=(--file containers/compose-minio.yaml)
fi
compose+=(--file containers/compose-pgbackrest.yaml)
if [[ "$runtime_env" == dev ]]; then
  compose+=(--file containers/compose-nextjs.yaml)
fi
compose+=(--project-name "infodengue-${runtime_env}")

# Use the application's installed dependency without requiring host epiweeks.
"${compose[@]}" exec -T web python -c '
import sys
from epiweeks import Week
try:
    Week.fromstring(sys.argv[1])
except ValueError:
    print("[EE] Invalid --week: not a valid epidemiological week", file=sys.stderr)
    sys.exit(2)
' "$week"

national_maps=(incidence_Nacional_dengue.png incidence_Nacional_chikungunya.png)
for filename in "${national_maps[@]}"; do
  [[ -f "$source_static/country/$filename" && -s "$source_static/country/$filename" ]] || fail "Missing or empty national source map: $filename"
done

psql_query() {
  "${compose[@]}" exec -T postgres sh -c \
    'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"' \
    sh "$@"
}

phase="refresh materialized views"
trap 'echo "[EE] Runtime refresh failed during: $phase" >&2' ERR
psql_query <<'SQL'
BEGIN;
REFRESH MATERIALIZED VIEW public.hist_uf_dengue_materialized_view;
REFRESH MATERIALIZED VIEW public.hist_uf_chik_materialized_view;
REFRESH MATERIALIZED VIEW public.hist_uf_zika_materialized_view;
REFRESH MATERIALIZED VIEW public.city_count_by_uf_dengue_materialized_view;
REFRESH MATERIALIZED VIEW public.city_count_by_uf_chikungunya_materialized_view;
REFRESH MATERIALIZED VIEW public.city_count_by_uf_zika_materialized_view;
COMMIT;
SQL

phase="collectstatic"
"${compose[@]}" exec -T web python manage.py collectstatic --no-input
phase="clear Django cache"
"${compose[@]}" exec -T web python manage.py shell -c \
  'from django.core.cache import cache; cache.clear()'

phase="validate database weeks"
week_matches="$(psql_query -v "requested_week=$week" -tA <<'SQL'
SELECT
  COALESCE((SELECT MAX("SE")::integer FROM "Municipio"."Historico_alerta")
           = :'requested_week'::integer, FALSE)
  AND
  COALESCE((SELECT MAX("SE")::integer FROM public.hist_uf_dengue_materialized_view)
           = :'requested_week'::integer, FALSE);
SQL
)"
[[ "$week_matches" == t ]] || fail "Database postconditions do not match requested week $week"

phase="validate map hashes"
for filename in "${national_maps[@]}"; do
  source_hash="$(sha256sum "$source_static/country/$filename")"
  source_hash="${source_hash%% *}"
  collected_hash="$("${compose[@]}" exec -T web sha256sum "/opt/services/staticfiles/img/incidence_maps/country/$filename")"
  [[ "${collected_hash%% *}" == "$source_hash" ]] || fail "Collected map SHA256 mismatch: $filename"
done
echo "[II] Runtime refresh succeeded for $runtime_env, week $week."
