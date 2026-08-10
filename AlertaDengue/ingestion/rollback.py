"""Targeted, audited rollback support for completed SINAN ingestion runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from django.db import connection, transaction
from django.utils import timezone

from ingestion.models import (
    RollbackStatus,
    Run,
    RunRollback,
    RunStatus,
    SinanStage,
)
from ingestion.sinan_specs import SINAN_DEST_COLUMNS

NATURAL_KEY = (
    "nu_notific",
    "dt_notific",
    "cid10_codigo",
    "municipio_geocodigo",
)
STAGE_TABLE = '"ingestion"."sinan_stage"'
NOTIFICACAO_TABLE = '"Municipio"."Notificacao"'


class RollbackValidationError(ValueError):
    """Raised when a rollback request cannot be executed safely."""


@dataclass(frozen=True)
class RollbackPreview:
    """Classification counts for a proposed rollback."""

    current_run_id: str
    restore_run_id: str
    new_only: int
    old_only: int
    changed: int
    unchanged: int


@dataclass(frozen=True)
class RollbackResult:
    """Persisted outcome counts for a completed rollback."""

    rollback_id: int
    preview: RollbackPreview
    deleted: int
    restored: int


def find_previous_completed_run(run: Run) -> Run:
    """Return the immediately preceding completed run in the same scope."""
    previous = (
        Run.objects.filter(
            status=RunStatus.COMPLETED,
            uf=run.uf,
            disease=run.disease,
            created_at__lt=run.created_at,
        )
        .order_by("-created_at")
        .first()
    )
    if previous is None:
        raise RollbackValidationError("No previous completed run was found.")
    return previous


def _classification_sql() -> str:
    values = ", ".join(f"c.{column}" for column in SINAN_DEST_COLUMNS)
    restored_values = ", ".join(f"r.{column}" for column in SINAN_DEST_COLUMNS)
    return f"""
        WITH current_rows AS (
            SELECT * FROM {STAGE_TABLE} WHERE run_id = %s
        ),
        restore_rows AS (
            SELECT * FROM {STAGE_TABLE} WHERE run_id = %s
        ),
        compared AS (
            SELECT
                c.id AS current_id,
                r.id AS restore_id,
                ({values}) IS DISTINCT FROM ({restored_values}) AS changed
            FROM current_rows c
            LEFT JOIN restore_rows r
              ON c.nu_notific IS NOT DISTINCT FROM r.nu_notific
             AND c.dt_notific IS NOT DISTINCT FROM r.dt_notific
             AND c.cid10_codigo IS NOT DISTINCT FROM r.cid10_codigo
             AND c.municipio_geocodigo IS NOT DISTINCT FROM r.municipio_geocodigo
            UNION ALL
            SELECT
                NULL AS current_id,
                r.id AS restore_id,
                FALSE AS changed
            FROM restore_rows r
            LEFT JOIN current_rows c
              ON c.nu_notific IS NOT DISTINCT FROM r.nu_notific
             AND c.dt_notific IS NOT DISTINCT FROM r.dt_notific
             AND c.cid10_codigo IS NOT DISTINCT FROM r.cid10_codigo
             AND c.municipio_geocodigo IS NOT DISTINCT FROM r.municipio_geocodigo
            WHERE c.id IS NULL
        )
        SELECT
            COUNT(*) FILTER (WHERE restore_id IS NULL),
            COUNT(*) FILTER (WHERE current_id IS NULL),
            COUNT(*) FILTER (
                WHERE current_id IS NOT NULL
                  AND restore_id IS NOT NULL
                  AND changed
            ),
            COUNT(*) FILTER (
                WHERE current_id IS NOT NULL
                  AND restore_id IS NOT NULL
                  AND NOT changed
            )
        FROM compared
    """


def _preview(current_run: Run, restore_run: Run) -> RollbackPreview:
    with connection.cursor() as cursor:
        cursor.execute(
            _classification_sql(),
            [str(current_run.pk), str(restore_run.pk)],
        )
        new_only, old_only, changed, unchanged = cursor.fetchone()
    return RollbackPreview(
        current_run_id=str(current_run.pk),
        restore_run_id=str(restore_run.pk),
        new_only=int(new_only or 0),
        old_only=int(old_only or 0),
        changed=int(changed or 0),
        unchanged=int(unchanged or 0),
    )


def _validate(current_run: Run, restore_run: Run) -> None:
    if current_run.pk == restore_run.pk:
        raise RollbackValidationError(
            "The current and restore runs must be different."
        )
    if current_run.status != RunStatus.COMPLETED:
        raise RollbackValidationError("The current run is not completed.")
    if restore_run.status != RunStatus.COMPLETED:
        raise RollbackValidationError("The restore run is not completed.")
    if current_run.uf != restore_run.uf:
        raise RollbackValidationError("Runs must have the same UF.")
    if current_run.disease != restore_run.disease:
        raise RollbackValidationError("Runs must have the same disease.")
    if restore_run.created_at >= current_run.created_at:
        raise RollbackValidationError(
            "The restore run must precede the current run."
        )
    latest = (
        Run.objects.filter(
            status=RunStatus.COMPLETED,
            uf=current_run.uf,
            disease=current_run.disease,
        )
        .order_by("-created_at")
        .first()
    )
    if latest is None or latest.pk != current_run.pk:
        raise RollbackValidationError(
            "Only the latest completed run for this UF and disease can be "
            "rolled back."
        )
    if not SinanStage.objects.filter(run=current_run).exists():
        raise RollbackValidationError("The current run has no staging rows.")
    if not SinanStage.objects.filter(run=restore_run).exists():
        raise RollbackValidationError("The restore run has no staging rows.")
    for field_name in NATURAL_KEY:
        if SinanStage.objects.filter(
            run__in=[current_run, restore_run],
            **{f"{field_name}__isnull": True},
        ).exists():
            raise RollbackValidationError(
                "Rollback requires non-null values for every natural-key "
                "field."
            )
    if RunRollback.objects.filter(
        current_run=current_run,
        status=RollbackStatus.COMPLETED,
    ).exists():
        raise RollbackValidationError(
            "The current run was already rolled back."
        )


def preview_rollback(current_run: Run, restore_run: Run) -> RollbackPreview:
    """Validate and classify stage rows without changing final-table data."""
    _validate(current_run, restore_run)
    return _preview(current_run, restore_run)


def _execute_changes(current_run: Run, restore_run: Run) -> tuple[int, int]:
    key_match = " AND ".join(
        f'n."{key}" IS NOT DISTINCT FROM c."{key}"' for key in NATURAL_KEY
    )
    stage_match = " AND ".join(
        f'c."{key}" IS NOT DISTINCT FROM r."{key}"' for key in NATURAL_KEY
    )
    update_columns = [column for column in SINAN_DEST_COLUMNS]
    assignments = ", ".join(
        f'"{column}" = r."{column}"' for column in update_columns
    )
    current_values = ", ".join(
        f'c."{column}"' for column in SINAN_DEST_COLUMNS
    )
    final_differs = " OR ".join(
        f'n."{column}"::text IS DISTINCT FROM c."{column}"::text'
        for column in SINAN_DEST_COLUMNS
    )
    delete_sql = f"""
        DELETE FROM {NOTIFICACAO_TABLE} n
        USING {STAGE_TABLE} c
        WHERE c.run_id = %s
          AND {key_match}
          AND NOT EXISTS (
              SELECT 1 FROM {STAGE_TABLE} r
              WHERE r.run_id = %s AND {stage_match}
          )
        RETURNING n.nu_notific
    """
    update_sql = f"""
        UPDATE {NOTIFICACAO_TABLE} n
        SET {assignments}
        FROM {STAGE_TABLE} c
        JOIN {STAGE_TABLE} r ON {stage_match} AND r.run_id = %s
        WHERE c.run_id = %s
          AND {key_match}
          AND ({", ".join(f'c."{col}"' for col in SINAN_DEST_COLUMNS)})
              IS DISTINCT FROM
              ({", ".join(f'r."{col}"' for col in SINAN_DEST_COLUMNS)})
        RETURNING n.nu_notific
    """
    lock_sql = f"""
        SELECT n.nu_notific
        FROM {NOTIFICACAO_TABLE} n
        JOIN {STAGE_TABLE} c ON {key_match}
        WHERE c.run_id = %s
        FOR UPDATE
    """
    drift_sql = f"""
        SELECT c.nu_notific
        FROM {STAGE_TABLE} c
        LEFT JOIN {NOTIFICACAO_TABLE} n ON {key_match}
        LEFT JOIN {STAGE_TABLE} r
          ON {stage_match} AND r.run_id = %s
        WHERE c.run_id = %s
          AND (
              r.id IS NULL
              OR ({current_values}) IS DISTINCT FROM
                 ({", ".join(f'r."{column}"' for column in SINAN_DEST_COLUMNS)})
          )
          AND (
              n.nu_notific IS NULL
              OR ({final_differs})
          )
        LIMIT 1
    """
    with connection.cursor() as cursor:
        cursor.execute(lock_sql, [str(current_run.pk)])
        cursor.execute(drift_sql, [str(restore_run.pk), str(current_run.pk)])
        if cursor.fetchone() is not None:
            raise RollbackValidationError(
                "Final rows no longer match the current run; rollback was "
                "aborted to avoid overwriting newer data."
            )
        cursor.execute(delete_sql, [str(current_run.pk), str(restore_run.pk)])
        deleted = len(cursor.fetchall())
        cursor.execute(update_sql, [str(restore_run.pk), str(current_run.pk)])
        restored = len(cursor.fetchall())
    return deleted, restored


def execute_rollback(current_run: Run, restore_run: Run) -> RollbackResult:
    """Restore changed rows and remove new rows in an audited transaction."""
    with transaction.atomic():
        current_run = Run.objects.select_for_update().get(pk=current_run.pk)
        restore_run = Run.objects.select_for_update().get(pk=restore_run.pk)
        _validate(current_run, restore_run)
        preview = _preview(current_run, restore_run)
        audit = RunRollback.objects.create(
            current_run=current_run,
            restore_run=restore_run,
            started_at=timezone.now(),
            rows_new_only=preview.new_only,
            rows_old_only=preview.old_only,
            rows_changed=preview.changed,
            rows_unchanged=preview.unchanged,
            metadata={"preview": asdict(preview)},
        )
    try:
        with transaction.atomic():
            current_run = Run.objects.select_for_update().get(
                pk=current_run.pk
            )
            restore_run = Run.objects.select_for_update().get(
                pk=restore_run.pk
            )
            _validate(current_run, restore_run)
            deleted, restored = _execute_changes(current_run, restore_run)
            audit.status = RollbackStatus.COMPLETED
            audit.finished_at = timezone.now()
            audit.rows_deleted = deleted
            audit.rows_restored = restored
            audit.save()
            return RollbackResult(audit.pk, preview, deleted, restored)
    except Exception as exc:
        RunRollback.objects.filter(pk=audit.pk).update(
            status=RollbackStatus.FAILED,
            finished_at=timezone.now(),
            errors=[{"code": exc.__class__.__name__, "message": str(exc)}],
        )
        raise
