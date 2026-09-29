#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --env dev|staging|prod --week YYYYWW --maps-source PATH" >&2
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

finalizer_env=""
week=""
maps_source=""
while (($#)); do
  case "$1" in
    --env|--week|--maps-source)
      (($# >= 2)) && [[ -n "$2" && "$2" != --* ]] || argument_error "Missing value for $1"
      case "$1" in
        --env) finalizer_env="$2" ;;
        --week) week="$2" ;;
        --maps-source) maps_source="$2" ;;
      esac
      shift 2
      ;;
    --help|-h) usage; exit 0 ;;
    *) argument_error "Unknown argument: $1" ;;
  esac
done

[[ -n "$finalizer_env" ]] || argument_error "Missing --env"
[[ -n "$week" ]] || argument_error "Missing --week"
[[ -n "$maps_source" ]] || argument_error "Missing --maps-source"
case "$finalizer_env" in
  dev|staging|prod) ;;
  *) argument_error "Invalid --env: $finalizer_env" ;;
esac
[[ "$week" =~ ^[0-9]{6}$ ]] || argument_error "Invalid --week: expected YYYYWW"
[[ -d "$maps_source" ]] || fail "Maps source directory does not exist: $maps_source"
maps_source="$(realpath "$maps_source")"
national_maps=(incidence_Nacional_dengue.png incidence_Nacional_chikungunya.png)
for filename in "${national_maps[@]}"; do
  [[ -f "$maps_source/country/$filename" && -s "$maps_source/country/$filename" ]] || fail "Missing or empty national map: $filename"
done
[[ -d "$maps_source/state" ]] || fail "Missing state maps directory"
state_maps="$(find "$maps_source/state" -type f -name '*.png' -print -quit)"
[[ -n "$state_maps" ]] || fail "State maps directory contains no PNG files"

cd "$(dirname "${BASH_SOURCE[0]}")/.."
repo_root="$(pwd -P)"
destination="$repo_root/AlertaDengue/static/img/incidence_maps"
[[ "$(realpath -m "$destination")" == "$destination" ]] || fail "Published maps destination escapes its intended repository path"
case "$maps_source/" in
  "$destination/"*) fail "Maps source must be outside the published maps directory" ;;
esac
case "$destination/" in
  "$maps_source/"*) fail "Published maps directory must be outside the maps source" ;;
esac

# Follow the host-side deployment convention; never print configuration values.
set -a
source .envs/.env
set +a
export ENV="$finalizer_env"

if [[ "$finalizer_env" == prod ]]; then
  [[ -n "${INFODENGUE_WEB_ORIGIN:-}" ]] || fail "Set INFODENGUE_WEB_ORIGIN to the direct HTTP Gunicorn origin URL"
  [[ -n "${INFODENGUE_WEB_HOST:-}" ]] || fail "Set INFODENGUE_WEB_HOST to the origin Host header"
  if [[ -n "${INFODENGUE_NGINX_CONTAINER:-}" || -n "${INFODENGUE_NGINX_CACHE_PATH:-}" ]]; then
    [[ -n "${INFODENGUE_NGINX_CONTAINER:-}" && -n "${INFODENGUE_NGINX_CACHE_PATH:-}" ]] || fail "Configure both nginx container and cache path"
    [[ "$INFODENGUE_NGINX_CACHE_PATH" == /* && "$INFODENGUE_NGINX_CACHE_PATH" != / && "$INFODENGUE_NGINX_CACHE_PATH" != *//* && ! "$INFODENGUE_NGINX_CACHE_PATH" =~ (^|/)\.\.?(/|$) ]] || fail "Nginx cache path must be an absolute non-root directory"
  fi
fi
for command in docker rsync sha256sum; do
  command -v "$command" >/dev/null || fail "Required command not found: $command"
done
if [[ "$finalizer_env" == prod ]]; then
  command -v curl >/dev/null || fail "Required command not found: curl"
fi

# Match the selected .sugar.yaml profile, including its project name.
compose=(docker compose --env-file .envs/.env
  --file containers/compose-base.yaml
  --file "containers/compose-${finalizer_env}.yaml")
if [[ "$finalizer_env" != dev ]]; then
  compose+=(--file containers/compose-minio.yaml)
fi
compose+=(--file containers/compose-pgbackrest.yaml)
if [[ "$finalizer_env" == dev ]]; then
  compose+=(--file containers/compose-nextjs.yaml)
fi
compose+=(--project-name "infodengue-${finalizer_env}")

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

if [[ "$finalizer_env" == prod ]]; then
  web_binding="$("${compose[@]}" port web 8000)"
  web_port="${web_binding##*:}"
  [[ "$web_port" =~ ^[0-9]+$ ]] || fail "Cannot resolve the published web port"
  "${compose[@]}" exec -T web python -c '
import sys
from urllib.parse import urlsplit
try:
    origin = urlsplit(sys.argv[1])
    host = urlsplit("//" + sys.argv[2]).hostname
    hostname = (origin.hostname or "").lower().rstrip(".")
    public_hosts = {"info.dengue.mat.br", "www.info.dengue.mat.br", (host or "").lower().rstrip(".")}
    valid = (
        origin.scheme == "http" and hostname and hostname not in public_hosts
        and origin.port == int(sys.argv[3]) and origin.port not in (80, 443)
        and origin.username is None and origin.password is None
        and origin.path in ("", "/") and not origin.query and not origin.fragment
    )
except ValueError:
    valid = False
if not valid:
    print("[EE] INFODENGUE_WEB_ORIGIN must be a direct HTTP origin on the published web port, outside the public nginx hostname", file=sys.stderr)
    sys.exit(2)
' "$INFODENGUE_WEB_ORIGIN" "$INFODENGUE_WEB_HOST" "$web_port"
fi

psql_query() {
  "${compose[@]}" exec -T postgres sh -c \
    'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"' \
    sh "$@"
}

phase="refresh materialized views"
trap 'echo "[EE] Finalization failed during: $phase" >&2' ERR
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

phase="publish maps"
rsync -a --delete "$maps_source/" "$destination/"
phase="collectstatic"
"${compose[@]}" exec -T web python manage.py collectstatic --no-input
phase="clear Django cache"
"${compose[@]}" exec -T web python manage.py shell -c \
  'from django.core.cache import cache; cache.clear()'

nginx_skipped=0
if [[ "$finalizer_env" == prod ]]; then
  if [[ -n "${INFODENGUE_NGINX_CONTAINER:-}" ]]; then
    phase="invalidate external nginx cache"
    docker exec "$INFODENGUE_NGINX_CONTAINER" find "$INFODENGUE_NGINX_CACHE_PATH" -type f -delete
  else
    nginx_skipped=1
  fi
fi

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
  source_hash="$(sha256sum "$maps_source/country/$filename")"
  source_hash="${source_hash%% *}"
  published_hash="$(sha256sum "$destination/country/$filename")"
  [[ "${published_hash%% *}" == "$source_hash" ]] || fail "Published map SHA256 mismatch: $filename"
  collected_hash="$("${compose[@]}" exec -T web sha256sum "/opt/services/staticfiles/img/incidence_maps/country/$filename")"
  [[ "${collected_hash%% *}" == "$source_hash" ]] || fail "Collected map SHA256 mismatch: $filename"
  if [[ "$finalizer_env" == prod ]]; then
    phase="validate Gunicorn origin"
    origin_hash="$(curl --fail --silent --show-error --noproxy '*' --max-time 60 \
      --header "Host: $INFODENGUE_WEB_HOST" \
      "${INFODENGUE_WEB_ORIGIN%/}/static/img/incidence_maps/country/$filename?v=$week" | sha256sum)"
    [[ "${origin_hash%% *}" == "$source_hash" ]] || fail "Origin map SHA256 mismatch: $filename"
    phase="validate map hashes"
  fi
done
if ((nginx_skipped)); then
  echo "[II] Origin validated; external nginx cache invalidation is not configured."
fi
echo "[II] Analysis finalization succeeded for $finalizer_env, week $week."
