from __future__ import annotations

from datetime import timedelta
import uuid

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory
from django.utils import timezone
import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from ingestion.models import (
    RollbackStatus,
    Run,
    RunRollback,
    RunStatus,
    SinanStage,
)
from ingestion.rollback import (
    RollbackValidationError,
    execute_rollback,
    find_previous_completed_run,
    preview_rollback,
)
from ingestion.sinan_specs import SINAN_DEST_COLUMNS


@pytest.fixture()
def db_engine() -> Engine:
    """Return the SQLAlchemy engine configured by Django settings."""
    return getattr(settings, "DB_ENGINE")


@pytest.fixture()
def municipio_notificacao_table(db_engine: Engine) -> None:
    """Create the minimal final table used by SINAN merge and rollback."""
    key_types = {
        "nu_notific": "INTEGER",
        "dt_notific": "DATE",
        "cid10_codigo": "TEXT",
        "municipio_geocodigo": "INTEGER",
    }
    columns = ", ".join(
        f'"{column}" {key_types.get(column, "TEXT")}'
        for column in SINAN_DEST_COLUMNS
    )
    with db_engine.begin() as conn:
        conn.execute(
            text(
                f"""CREATE SCHEMA IF NOT EXISTS "Municipio";
                DROP TABLE IF EXISTS "Municipio"."Notificacao" CASCADE;
                CREATE TABLE "Municipio"."Notificacao" (
                    {columns},
                    CONSTRAINT casos_unicos UNIQUE (
                        nu_notific, dt_notific, cid10_codigo,
                        municipio_geocodigo
                    )
                );"""
            )
        )


def _run(
    *, status: str = RunStatus.COMPLETED, disease: str = "A90", uf: str = "RJ"
) -> Run:
    run = Run.objects.create(
        status=status,
        uf=uf,
        disease=disease,
        source_format="csv",
        delivery_year=2026,
        delivery_week=10,
        source_path=f"test/{timezone.now().timestamp()}",
        filename="test.csv",
        sha256=f"{Run.objects.count():064d}",
        size_bytes=1,
    )
    return run


def _stage(
    run: Run,
    notification: int,
    sex: str | None = "M",
    notification_date: str | None = "2025-01-01",
) -> None:
    SinanStage.objects.create(
        run=run,
        chunk_id=0,
        source_rownum=notification,
        nu_notific=notification,
        dt_notific=notification_date,
        cid10_codigo="A90",
        municipio_geocodigo=3304557,
        cs_sexo=sex,
    )


def _stage_many(
    run: Run,
    notifications: range,
    changed_notifications: set[int] | None = None,
) -> None:
    """Create a deterministic retained-stage snapshot in one database query."""
    changed_notifications = changed_notifications or set()
    SinanStage.objects.bulk_create(
        [
            SinanStage(
                run=run,
                chunk_id=0,
                source_rownum=notification,
                nu_notific=notification,
                dt_notific="2025-01-01",
                cid10_codigo="A90",
                municipio_geocodigo=3304557,
                cs_sexo="F" if notification in changed_notifications else "M",
            )
            for notification in notifications
        ]
    )


def _insert_final(
    db_engine: Engine,
    notification: int,
    sex: str = "M",
    notification_date: str | None = "2025-01-01",
    disease: str = "A90",
    geocode: int = 3304557,
) -> None:
    with db_engine.begin() as conn:
        conn.execute(
            text(
                """INSERT INTO "Municipio"."Notificacao" (
                    nu_notific, dt_notific, cid10_codigo,
                    municipio_geocodigo, cs_sexo
                ) VALUES (
                    :notification, :notification_date, :disease, :geocode, :sex
                )"""
            ),
            {
                "notification": notification,
                "notification_date": notification_date,
                "disease": disease,
                "geocode": geocode,
                "sex": sex,
            },
        )


def _ordered_runs() -> tuple[Run, Run]:
    disease = f"rollback-{uuid.uuid4().hex[:7]}"
    restore = _run(disease=disease)
    current = _run(disease=disease)
    now = timezone.now()
    Run.objects.filter(pk=restore.pk).update(
        created_at=now - timedelta(hours=1)
    )
    Run.objects.filter(pk=current.pk).update(created_at=now)
    restore.refresh_from_db()
    current.refresh_from_db()
    return restore, current


@pytest.mark.django_db(transaction=True)
def test_find_previous_completed_run_filters_scope_and_status() -> None:
    restore, current = _ordered_runs()
    _run(status=RunStatus.FAILED, disease=current.disease, uf=current.uf)
    _run(disease="B00", uf=current.uf)
    _run(uf="SP")

    assert find_previous_completed_run(current) == restore


@pytest.mark.django_db(transaction=True)
def test_find_previous_completed_run_errors_without_previous_run() -> None:
    run = _run(disease=f"rollback-{uuid.uuid4().hex[:7]}")
    Run.objects.filter(pk=run.pk).update(
        created_at=timezone.now() - timedelta(days=36500)
    )
    run.refresh_from_db()

    with pytest.raises(RollbackValidationError, match="No previous"):
        find_previous_completed_run(run)


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("municipio_notificacao_table")
def test_preview_and_execute_target_only_classified_rows(
    db_engine: Engine,
) -> None:
    restore, current = _ordered_runs()
    _stage(restore, 1, "M")
    _stage(restore, 2, "F")
    _stage(restore, 3, "M")
    _stage(current, 1, "M")
    _stage(current, 3, "F")
    _stage(current, 4, "F")
    for notification, sex in ((1, "M"), (2, "F"), (3, "F"), (4, "F")):
        _insert_final(db_engine, notification, sex)
    _insert_final(db_engine, 99, "F", disease="B00")
    _insert_final(db_engine, 100, "F", geocode=3303302)

    preview = preview_rollback(current, restore)

    assert (
        preview.new_only,
        preview.old_only,
        preview.changed,
        preview.unchanged,
    ) == (
        1,
        1,
        1,
        1,
    )
    common = preview.changed + preview.unchanged
    assert preview.new_only + common == 3
    assert preview.old_only + common == 3
    result = execute_rollback(current, restore)

    assert (result.deleted, result.restored) == (1, 1)
    with db_engine.begin() as conn:
        rows = conn.execute(
            text(
                """SELECT nu_notific, cs_sexo
                FROM "Municipio"."Notificacao"
                ORDER BY nu_notific"""
            )
        ).all()
    assert rows == [(1, "M"), (2, "F"), (3, "M"), (99, "F"), (100, "F")]
    assert Run.objects.filter(pk__in=[restore.pk, current.pk]).count() == 2
    assert SinanStage.objects.filter(run__in=[restore, current]).count() == 6
    audit = RunRollback.objects.get(pk=result.rollback_id)
    assert audit.status == RollbackStatus.COMPLETED
    assert (audit.rows_deleted, audit.rows_restored) == (1, 1)


@pytest.mark.django_db(transaction=True)
def test_preview_classifies_large_retained_stage_snapshots() -> None:
    restore, current = _ordered_runs()
    _stage_many(restore, range(1, 1201))
    _stage_many(current, range(1, 1151), set(range(1, 101)))
    _stage_many(current, range(1201, 1276))

    preview = preview_rollback(current, restore)

    assert (
        preview.new_only,
        preview.old_only,
        preview.changed,
        preview.unchanged,
    ) == (75, 50, 100, 1050)
    common = preview.changed + preview.unchanged
    assert preview.new_only + common == 1225
    assert preview.old_only + common == 1200


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("municipio_notificacao_table")
def test_rollback_rejects_invalid_runs_and_duplicate_success(
    db_engine: Engine,
) -> None:
    restore, current = _ordered_runs()
    _stage(restore, 1)
    _stage(current, 1)
    _insert_final(db_engine, 1)
    execute_rollback(current, restore)
    with pytest.raises(RollbackValidationError, match="already rolled back"):
        execute_rollback(current, restore)

    pending = _run(status=RunStatus.STAGED)
    _stage(pending, 2)
    with pytest.raises(RollbackValidationError, match="not completed"):
        preview_rollback(pending, restore)


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("municipio_notificacao_table")
def test_rollback_failure_preserves_rows_and_records_failed_audit(
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    restore, current = _ordered_runs()
    _stage(restore, 1, "M")
    _stage(current, 1, "F")
    _insert_final(db_engine, 1, "F")

    def fail(*args: object) -> tuple[int, int]:
        raise RuntimeError("forced failure")

    monkeypatch.setattr("ingestion.rollback._execute_changes", fail)
    with pytest.raises(RuntimeError, match="forced failure"):
        execute_rollback(current, restore)

    with db_engine.begin() as conn:
        sex = conn.execute(
            text(
                """SELECT cs_sexo FROM "Municipio"."Notificacao"
                WHERE nu_notific = 1"""
            )
        ).scalar_one()
    assert sex == "F"
    assert (
        RunRollback.objects.get(current_run=current).status
        == RollbackStatus.FAILED
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("municipio_notificacao_table")
def test_rollback_matches_nullable_natural_key_values(
    db_engine: Engine,
) -> None:
    restore, current = _ordered_runs()
    _stage(restore, 1, None, None)
    _stage(current, 1, "F", None)
    _insert_final(db_engine, 1, "F", None)

    with pytest.raises(RollbackValidationError, match="non-null"):
        execute_rollback(current, restore)

    with db_engine.begin() as conn:
        sex = conn.execute(
            text(
                """SELECT cs_sexo FROM "Municipio"."Notificacao"
                WHERE nu_notific = 1 AND dt_notific IS NULL"""
            )
        ).scalar_one()
    assert sex == "F"


@pytest.mark.django_db(transaction=True)
def test_rollback_rejects_an_older_completed_run() -> None:
    restore, older_current = _ordered_runs()
    newer_current = _run(disease=older_current.disease, uf=older_current.uf)
    Run.objects.filter(pk=newer_current.pk).update(
        created_at=older_current.created_at + timedelta(seconds=1)
    )
    newer_current.refresh_from_db()
    _stage(restore, 1)
    _stage(older_current, 1)
    _stage(newer_current, 1)

    with pytest.raises(RollbackValidationError, match="latest completed"):
        preview_rollback(older_current, restore)


@pytest.mark.django_db(transaction=True)
def test_failed_or_staged_runs_do_not_block_latest_completed_rollback() -> (
    None
):
    restore, current = _ordered_runs()
    _run(status=RunStatus.FAILED, disease=current.disease, uf=current.uf)
    _run(status=RunStatus.STAGED, disease=current.disease, uf=current.uf)
    _stage(restore, 1)
    _stage(current, 1)

    assert preview_rollback(current, restore).unchanged == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("municipio_notificacao_table")
@pytest.mark.parametrize("notification", [3, 4])
def test_drifted_final_row_aborts_without_mutation(
    db_engine: Engine,
    notification: int,
) -> None:
    restore, current = _ordered_runs()
    _stage(restore, 3, "M")
    _stage(current, 3, "F")
    _stage(current, 4, "F")
    _insert_final(db_engine, 3, "F")
    _insert_final(db_engine, 4, "F")
    with db_engine.begin() as conn:
        conn.execute(
            text(
                """UPDATE "Municipio"."Notificacao"
                SET cs_sexo = 'X' WHERE nu_notific = :notification"""
            ),
            {"notification": notification},
        )

    with pytest.raises(RollbackValidationError, match="no longer match"):
        execute_rollback(current, restore)

    with db_engine.begin() as conn:
        rows = conn.execute(
            text(
                """SELECT nu_notific, cs_sexo
                FROM "Municipio"."Notificacao" ORDER BY nu_notific"""
            )
        ).all()
    assert rows == [
        (3, "X" if notification == 3 else "F"),
        (4, "X" if notification == 4 else "F"),
    ]
    assert (
        RunRollback.objects.get(current_run=current).status
        == RollbackStatus.FAILED
    )


@pytest.mark.django_db(transaction=True)
def test_database_prevents_two_completed_rollbacks_for_one_run() -> None:
    restore, current = _ordered_runs()
    RunRollback.objects.create(
        current_run=current,
        restore_run=restore,
        status=RollbackStatus.COMPLETED,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        RunRollback.objects.create(
            current_run=current,
            restore_run=restore,
            status=RollbackStatus.COMPLETED,
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("attribute", "value", "message"),
    [
        ("status", RunStatus.STAGED, "restore run is not completed"),
        ("disease", "B00", "same disease"),
        ("uf", "SP", "same UF"),
    ],
)
def test_preview_rejects_incompatible_restore_run(
    attribute: str,
    value: str,
    message: str,
) -> None:
    restore, current = _ordered_runs()
    setattr(restore, attribute, value)
    restore.save()
    _stage(restore, 1)
    _stage(current, 1)

    with pytest.raises(RollbackValidationError, match=message):
        preview_rollback(current, restore)


@pytest.mark.django_db(transaction=True)
def test_preview_rejects_newer_restore_run_and_missing_stage_rows() -> None:
    restore, current = _ordered_runs()
    _stage(current, 1)
    with pytest.raises(RollbackValidationError, match="no staging rows"):
        preview_rollback(current, restore)

    _stage(restore, 1)
    Run.objects.filter(pk=restore.pk).update(
        created_at=current.created_at + timedelta(seconds=1)
    )
    restore.refresh_from_db()
    with pytest.raises(RollbackValidationError, match="must precede"):
        preview_rollback(current, restore)


@pytest.mark.django_db(transaction=True)
def test_preview_rejects_same_run() -> None:
    run = _run()
    _stage(run, 1)

    with pytest.raises(RollbackValidationError, match="must be different"):
        preview_rollback(run, run)


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("municipio_notificacao_table")
def test_admin_requires_confirmation_and_executes_rollback(
    db_engine: Engine,
) -> None:
    restore, current = _ordered_runs()
    _stage(restore, 1, "M")
    _stage(current, 1, "F")
    _insert_final(db_engine, 1, "F")
    user = User.objects.create_superuser(
        "rollback-admin",
        "admin@example.com",
        "pw",
    )
    client = Client()
    client.force_login(user)
    url = f"/admin/ingestion/run/{current.pk}/rollback/"

    response = client.get(f"/admin/ingestion/run/{current.pk}/change/")
    assert response.status_code == 200
    assert b"Preview rollback" in response.content
    response = client.get(url)
    assert response.status_code == 200
    assert b"Confirm SINAN ingestion rollback" in response.content
    response = client.post(url, {})
    assert response.status_code == 302
    assert not RunRollback.objects.filter(current_run=current).exists()
    response = client.post(url, {"confirm": "rollback"})
    assert response.status_code == 302
    assert (
        RunRollback.objects.get(current_run=current).status
        == RollbackStatus.COMPLETED
    )


@pytest.mark.django_db(transaction=True)
def test_admin_rollback_preview_requires_change_permission() -> None:
    _, current = _ordered_runs()
    user = User.objects.create_user(
        "read-only-admin",
        "readonly@example.com",
        "pw",
        is_staff=True,
    )
    client = Client()
    client.force_login(user)

    response = client.get(f"/admin/ingestion/run/{current.pk}/rollback/")

    assert response.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_admin_invalid_rollback_displays_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _run(disease=f"rollback-{uuid.uuid4().hex[:7]}")
    Run.objects.filter(pk=run.pk).update(
        created_at=timezone.now() - timedelta(days=36500)
    )
    run.refresh_from_db()
    user = User.objects.create_superuser(
        "invalid-admin", "invalid@example.com", "pw"
    )
    client = Client()
    client.force_login(user)
    reported_messages: list[str] = []
    model_admin = admin.site._registry[Run]
    monkeypatch.setattr(
        model_admin,
        "message_user",
        lambda request, message, *args, **kwargs: reported_messages.append(
            str(message)
        ),
    )

    response = client.get(
        f"/admin/ingestion/run/{run.pk}/rollback/",
        follow=True,
    )

    assert response.status_code == 200
    assert reported_messages
    assert (
        "staging rows" in reported_messages[0]
        or "No previous" in reported_messages[0]
        or "latest completed" in reported_messages[0]
    )


@pytest.mark.django_db(transaction=True)
def test_admin_hides_rollback_link_for_non_completed_run() -> None:
    run = _run(status=RunStatus.STAGED)
    user = User.objects.create_superuser(
        "admin-link", "link@example.com", "pw"
    )
    client = Client()
    client.force_login(user)

    response = client.get(f"/admin/ingestion/run/{run.pk}/change/")

    assert response.status_code == 200
    assert b"Preview rollback" not in response.content


@pytest.mark.django_db(transaction=True)
def test_rollback_admin_is_read_only() -> None:
    user = User.objects.create_superuser(
        "audit-admin", "audit@example.com", "pw"
    )
    request_factory = RequestFactory()
    get_request = request_factory.get("/admin/ingestion/runrollback/")
    get_request.user = user
    post_request = request_factory.post("/admin/ingestion/runrollback/")
    post_request.user = user
    model_admin = admin.site._registry[RunRollback]

    assert not model_admin.has_add_permission(get_request)
    assert model_admin.has_change_permission(get_request)
    assert not model_admin.has_change_permission(post_request)
