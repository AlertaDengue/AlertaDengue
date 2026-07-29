#!/usr/bin/env bash
set -Eeuo pipefail

readonly APPROVED_SCHEMAS=(
  archive_redemet
  archive_upload
  archive_ovitrampa
  archive_alertas_regionais
  archive_cemaden
  archive_copernicus
  archive_historico_casos
  archive_mosqlimate
  archive_tweets
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'missing required command: %s\n' "$1" >&2
    exit 1
  }
}

cleanup_partial() {
  rm -f "${DUMP_PARTIAL}" "${SHA_PARTIAL}" "${TOC_PARTIAL}" \
    "${SCHEMA_SQL_PARTIAL}" "${INVENTORY_PARTIAL}" \
    "${ROW_COUNTS_PARTIAL}" "${DEPENDENCIES_PARTIAL}" \
    "${README_PARTIAL}"
}

require_cmd psql
require_cmd pg_dump
require_cmd pg_restore
require_cmd sha256sum
require_cmd df
require_cmd awk

export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-25432}"
export PGDATABASE="${PGDATABASE:-dengue}"
export PGUSER="${PGUSER:-dengueadmin}"

OUTPUT_DIR="${1:-}"
if [[ -z "${OUTPUT_DIR}" ]]; then
  printf 'usage: %s <output-dir-outside-repo>\n' "${0##*/}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"
OUTPUT_DIR="$(cd "${OUTPUT_DIR}" && pwd)"

case "${OUTPUT_DIR}" in
  "${REPO_ROOT}"|"${REPO_ROOT}"/*)
    printf 'export directory must remain outside the git worktree: %s\n' "${OUTPUT_DIR}" >&2
    exit 1
    ;;
esac

server_major="$(psql -X -At -c 'SHOW server_version_num' | cut -c1-2)"
client_major="$(pg_dump --version | awk '{print $3}' | cut -d. -f1)"
if [[ "${server_major}" != "${client_major}" ]]; then
  printf 'client/server major version mismatch: client=%s server=%s\n' "${client_major}" "${server_major}" >&2
  exit 1
fi

avail_kb="$(df -Pk "${OUTPUT_DIR}" | awk 'NR==2 {print $4}')"
avail_inodes="$(df -Pi "${OUTPUT_DIR}" | awk 'NR==2 {print $4}')"
if (( avail_kb < 6291456 )); then
  printf 'need at least 6 GiB free in %s, found %s KiB\n' "${OUTPUT_DIR}" "${avail_kb}" >&2
  exit 1
fi
if (( avail_inodes < 2000 )); then
  printf 'need at least 2000 free inodes in %s, found %s\n' "${OUTPUT_DIR}" "${avail_inodes}" >&2
  exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
base="dengue_archive_schemas_${timestamp}"

DUMP_FINAL="${OUTPUT_DIR}/${base}.dump"
SHA_FINAL="${DUMP_FINAL}.sha256"
TOC_FINAL="${OUTPUT_DIR}/${base}.toc"
SCHEMA_SQL_FINAL="${OUTPUT_DIR}/${base}.schema.sql"
INVENTORY_FINAL="${OUTPUT_DIR}/archive_inventory_${timestamp}.tsv"
ROW_COUNTS_FINAL="${OUTPUT_DIR}/archive_row_counts_${timestamp}.tsv"
DEPENDENCIES_FINAL="${OUTPUT_DIR}/archive_dependencies_${timestamp}.tsv"
README_FINAL="${OUTPUT_DIR}/README_restore_${timestamp}.md"

DUMP_PARTIAL="${DUMP_FINAL}.partial"
SHA_PARTIAL="${SHA_FINAL}.partial"
TOC_PARTIAL="${TOC_FINAL}.partial"
SCHEMA_SQL_PARTIAL="${SCHEMA_SQL_FINAL}.partial"
INVENTORY_PARTIAL="${INVENTORY_FINAL}.partial"
ROW_COUNTS_PARTIAL="${ROW_COUNTS_FINAL}.partial"
DEPENDENCIES_PARTIAL="${DEPENDENCIES_FINAL}.partial"
README_PARTIAL="${README_FINAL}.partial"

trap cleanup_partial ERR

psql -X -v ON_ERROR_STOP=1 -f \
  "${SCRIPT_DIR}/20260729_00_audit_archive_schemas.sql" >/dev/null

psql -X -A -F $'\t' -v ON_ERROR_STOP=1 -f \
  "${SCRIPT_DIR}/20260729_01_preflight_archive_schemas_export.sql" \
  > "${INVENTORY_PARTIAL}"

psql -X -A -F $'\t' -v ON_ERROR_STOP=1 -c "
SELECT n.nspname, c.relname, c.relkind,
       (xpath('/row/count/text()', query_to_xml(format('SELECT count(*) AS count FROM %I.%I', n.nspname, c.relname), false, true, '')))[1]::text
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = ANY(ARRAY['archive_redemet','archive_upload','archive_ovitrampa','archive_alertas_regionais','archive_cemaden','archive_copernicus','archive_historico_casos','archive_mosqlimate','archive_tweets'])
  AND c.relkind IN ('r','m')
ORDER BY 1,2;" > "${ROW_COUNTS_PARTIAL}"

psql -X -A -F $'\t' -v ON_ERROR_STOP=1 -c "
SELECT obj_ns.nspname, obj.relname, obj.relkind,
       ref_ns.nspname, ref.relname, ref.relkind, d.deptype
FROM pg_depend d
JOIN pg_class obj ON obj.oid = d.objid
JOIN pg_namespace obj_ns ON obj_ns.oid = obj.relnamespace
JOIN pg_class ref ON ref.oid = d.refobjid
JOIN pg_namespace ref_ns ON ref_ns.oid = ref.relnamespace
WHERE obj_ns.nspname = ANY(ARRAY['archive_redemet','archive_upload','archive_ovitrampa','archive_alertas_regionais','archive_cemaden','archive_copernicus','archive_historico_casos','archive_mosqlimate','archive_tweets'])
   OR ref_ns.nspname = ANY(ARRAY['archive_redemet','archive_upload','archive_ovitrampa','archive_alertas_regionais','archive_cemaden','archive_copernicus','archive_historico_casos','archive_mosqlimate','archive_tweets'])
ORDER BY 1,2,4,5,7;" > "${DEPENDENCIES_PARTIAL}"

pg_dump \
  --format=custom \
  --compress=9 \
  --strict-names \
  --lock-wait-timeout=5s \
  --verbose \
  --schema=archive_redemet \
  --schema=archive_upload \
  --schema=archive_ovitrampa \
  --schema=archive_alertas_regionais \
  --schema=archive_cemaden \
  --schema=archive_copernicus \
  --schema=archive_historico_casos \
  --schema=archive_mosqlimate \
  --schema=archive_tweets \
  --file="${DUMP_PARTIAL}" \
  "${PGDATABASE}"

sha256sum "${DUMP_PARTIAL}" > "${SHA_PARTIAL}"
pg_restore -l "${DUMP_PARTIAL}" > "${TOC_PARTIAL}"
pg_restore --schema-only -f "${SCHEMA_SQL_PARTIAL}" "${DUMP_PARTIAL}"

cat > "${README_PARTIAL}" <<EOF
# Restore package ${base}

1. Verify checksum with \`sha256sum -c ${SHA_FINAL##*/}\`.
2. Inspect \`${TOC_FINAL##*/}\` to confirm only approved archive schemas are present.
3. Create minimal fixtures for:
   - \`"Dengue_global".regional(id)\`
   - \`"Dengue_global"."CID10"(codigo)\`
   - \`"Municipio"."Historico_alerta"\`
   - \`"Municipio"."Historico_alerta_chik"\`
4. Restore with:

\`\`\`bash
pg_restore --exit-on-error --verbose --dbname=<restore_db> ${DUMP_FINAL}
\`\`\`

This package intentionally retains four validated foreign keys to the active
lookup tables above and preserves the archived
\`archive_historico_casos.historico_casos\` materialized view definition.
Restoring the archived historico contents requires compatible
\`"Municipio"."Historico_alerta"\` and
\`"Municipio"."Historico_alerta_chik"\` source data so the materialized view
data step can repopulate the archive contents. Standalone restore without
those retained-source fixtures is future work.
EOF

mv "${DUMP_PARTIAL}" "${DUMP_FINAL}"
mv "${SHA_PARTIAL}" "${SHA_FINAL}"
mv "${TOC_PARTIAL}" "${TOC_FINAL}"
mv "${SCHEMA_SQL_PARTIAL}" "${SCHEMA_SQL_FINAL}"
mv "${INVENTORY_PARTIAL}" "${INVENTORY_FINAL}"
mv "${ROW_COUNTS_PARTIAL}" "${ROW_COUNTS_FINAL}"
mv "${DEPENDENCIES_PARTIAL}" "${DEPENDENCIES_FINAL}"
mv "${README_PARTIAL}" "${README_FINAL}"

trap - ERR
printf '%s\n' "${DUMP_FINAL}"
