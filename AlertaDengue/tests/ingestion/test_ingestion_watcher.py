"""Tests for the decoupled ingestion watcher."""

from __future__ import annotations

import signal
from threading import Event, Thread
from unittest.mock import MagicMock, call, patch

import pytest
from watchdog.events import DirMovedEvent, FileMovedEvent, FileSystemEvent

from ingestion.management.commands.ingestion_watcher import (
    CommandAction,
    IngestionWatcherHandler,
    LogOnlyAction,
    WatcherAlreadyRunningError,
    _build_action,
    _build_parser,
    _install_shutdown_handlers,
    _parse_extensions,
    _run_observer,
    _watch_path_lock,
    main,
)


def _make_handler(
    *,
    action: MagicMock | None = None,
    settle_time: float = 0.1,
    extensions: frozenset[str] | None = None,
) -> IngestionWatcherHandler:
    return IngestionWatcherHandler(
        action=action or MagicMock(),
        settle_time=settle_time,
        extensions=extensions,
    )


class TestParseExtensions:
    def test_default_csv_dbf(self):
        result = _parse_extensions(".csv,.dbf")
        assert result == frozenset({".csv", ".dbf"})

    def test_without_leading_dot(self):
        result = _parse_extensions("csv,dbf,parquet")
        assert result == frozenset({".csv", ".dbf", ".parquet"})

    def test_mixed_and_whitespace(self):
        result = _parse_extensions(" .CSV , dbf , .Parquet ")
        assert result == frozenset({".csv", ".dbf", ".parquet"})

    def test_empty_string(self):
        result = _parse_extensions("")
        assert result == frozenset()


class TestHandlerEventRouting:
    def test_ignores_directories(self):
        handler = _make_handler()
        event = FileSystemEvent("some/dir")
        event.is_directory = True

        with patch.object(handler, "_handle_event") as mock_handle:
            handler.on_created(event)
            handler.on_modified(event)
            mock_handle.assert_not_called()

    def test_atomic_move_handles_only_final_destination(self):
        handler = _make_handler()
        source = "incoming/.f89abc.dbf.part-123"
        destination = "incoming/f89abc.dbf"
        event = FileMovedEvent(source, destination)

        with patch.object(handler, "_handle_event") as mock_handle:
            handler.on_moved(event)
            mock_handle.assert_called_once_with(destination)

    def test_ignores_moved_directories(self):
        handler = _make_handler()
        event = DirMovedEvent("incoming/old", "incoming/new")

        with patch.object(handler, "_handle_event") as mock_handle:
            handler.on_moved(event)
            mock_handle.assert_not_called()

    def test_move_to_unsupported_extension_schedules_nothing(self):
        handler = _make_handler()
        event = FileMovedEvent("incoming/.temporary.part", "incoming/file.txt")

        with patch(
            "ingestion.management.commands.ingestion_watcher.Timer"
        ) as mock_timer_cls:
            handler.on_moved(event)
            mock_timer_cls.assert_not_called()
        assert handler.timers == {}

    def test_ignores_non_data_files(self):
        handler = _make_handler()
        handler._handle_event("some/file.txt")
        handler._handle_event("some/image.png")
        assert len(handler.timers) == 0

    def test_accepts_csv(self):
        handler = _make_handler()
        with patch(
            "ingestion.management.commands.ingestion_watcher.Timer"
        ) as mock_timer_cls:
            mock_timer_cls.return_value = MagicMock()
            handler._handle_event("data.csv")
            assert "data.csv" in handler.timers

    def test_accepts_dbf(self):
        handler = _make_handler()
        with patch(
            "ingestion.management.commands.ingestion_watcher.Timer"
        ) as mock_timer_cls:
            mock_timer_cls.return_value = MagicMock()
            handler._handle_event("data.dbf")
            assert "data.dbf" in handler.timers

    def test_custom_extensions(self):
        handler = _make_handler(extensions=frozenset({".parquet"}))
        with patch(
            "ingestion.management.commands.ingestion_watcher.Timer"
        ) as mock_timer_cls:
            mock_timer_cls.return_value = MagicMock()
            handler._handle_event("data.parquet")
            assert "data.parquet" in handler.timers

            handler._handle_event("data.csv")
            assert "data.csv" not in handler.timers


class TestHandlerTimerSettle:
    def test_starts_timer(self):
        handler = _make_handler()
        with patch(
            "ingestion.management.commands.ingestion_watcher.Timer"
        ) as mock_timer_cls:
            mock_t = MagicMock()
            mock_timer_cls.return_value = mock_t

            handler._handle_event("some/data.csv")

            assert "some/data.csv" in handler.timers
            mock_timer_cls.assert_called_once_with(
                0.1, handler.process_file, args=["some/data.csv"]
            )
            mock_t.start.assert_called_once()
            assert mock_t.daemon is False

    def test_resets_timer_on_subsequent_events(self):
        handler = _make_handler()
        with patch(
            "ingestion.management.commands.ingestion_watcher.Timer"
        ) as mock_timer_cls:
            t1, t2 = MagicMock(), MagicMock()
            mock_timer_cls.side_effect = [t1, t2]

            handler._handle_event("data.dbf")
            assert handler.timers["data.dbf"] == t1
            t1.start.assert_called_once()

            handler._handle_event("data.dbf")
            t1.cancel.assert_called_once()
            assert handler.timers["data.dbf"] == t2
            t2.start.assert_called_once()


class TestHandlerProcessFile:
    @patch("ingestion.management.commands.ingestion_watcher.Path.exists")
    def test_invokes_action(self, mock_exists):
        mock_action = MagicMock()
        handler = _make_handler(action=mock_action)
        mock_exists.return_value = True
        handler.timers["test.csv"] = MagicMock()

        handler.process_file("test.csv")

        assert "test.csv" not in handler.timers
        mock_action.assert_called_once_with("test.csv")

    @patch("ingestion.management.commands.ingestion_watcher.Path.exists")
    def test_skips_vanished_file(self, mock_exists):
        mock_action = MagicMock()
        handler = _make_handler(action=mock_action)
        mock_exists.return_value = False

        handler.process_file("vanished.csv")

        mock_action.assert_not_called()

    @patch("ingestion.management.commands.ingestion_watcher.Path.exists")
    def test_handles_action_exception(self, mock_exists):
        mock_action = MagicMock(side_effect=RuntimeError("boom"))
        handler = _make_handler(action=mock_action)
        mock_exists.return_value = True

        # Should not raise
        handler.process_file("error.csv")
        mock_action.assert_called_once_with("error.csv")


class TestHandlerShutdown:
    def test_rejects_new_events_after_shutdown(self):
        action = MagicMock()
        handler = _make_handler(action=action)
        handler.shutdown()

        with patch(
            "ingestion.management.commands.ingestion_watcher.Timer"
        ) as timer_cls:
            handler._handle_event("late.csv")

        timer_cls.assert_not_called()
        assert handler.timers == {}
        action.assert_not_called()

    def test_late_timer_callback_does_not_run_action(self):
        action = MagicMock()
        handler = _make_handler(action=action)
        handler.shutdown()

        handler.process_file("late.csv")

        action.assert_not_called()
        assert handler._active_actions == 0

    def test_cancels_pending_timers_without_running_actions(self):
        action = MagicMock()
        handler = _make_handler(action=action)
        with patch(
            "ingestion.management.commands.ingestion_watcher.Timer"
        ) as timer_cls:
            first, second = MagicMock(), MagicMock()
            timer_cls.side_effect = [first, second]
            handler._handle_event("one.csv")
            handler._handle_event("two.dbf")

        handler.shutdown()

        first.cancel.assert_called_once()
        second.cancel.assert_called_once()
        assert handler.timers == {}
        action.assert_not_called()

    def test_waits_for_active_action(self, tmp_path):
        started = Event()
        release = Event()
        shutdown_started = Event()
        shutdown_done = Event()

        def action(_path):
            started.set()
            assert release.wait(5)

        handler = _make_handler(action=action)
        source = tmp_path / "active.csv"
        source.touch()
        action_thread = Thread(
            target=handler.process_file, args=(str(source),)
        )
        action_thread.start()
        assert started.wait(5)

        def stop_handler():
            shutdown_started.set()
            handler.shutdown()
            shutdown_done.set()

        shutdown_thread = Thread(target=stop_handler)
        shutdown_thread.start()
        assert shutdown_started.wait(5)
        assert not shutdown_done.is_set()

        release.set()
        action_thread.join(5)
        shutdown_thread.join(5)
        assert not action_thread.is_alive()
        assert not shutdown_thread.is_alive()
        assert shutdown_done.is_set()


class TestStartupReconciliation:
    def test_schedules_existing_csv_dbf_only_and_ignores_lockfile(
        self, tmp_path
    ):
        csv = tmp_path / "incoming.csv"
        dbf = tmp_path / "outbreak.DBF"
        unsupported = tmp_path / "notes.txt"
        lock_file = tmp_path / ".ingestion-watcher.lock"
        for path in (csv, dbf, unsupported, lock_file):
            path.touch()

        handler = _make_handler()
        with patch.object(handler, "_handle_event") as handle_event:
            handler.reconcile_existing_files(tmp_path, recursive=False)

        assert {call.args[0] for call in handle_event.call_args_list} == {
            str(csv),
            str(dbf),
        }

    def test_recursive_option_controls_nested_scan(self, tmp_path):
        nested = tmp_path / "nested"
        nested.mkdir()
        file_path = nested / "nested.csv"
        file_path.touch()
        handler = _make_handler()

        with patch.object(handler, "_handle_event") as handle_event:
            handler.reconcile_existing_files(tmp_path, recursive=False)
            handle_event.assert_not_called()

            handler.reconcile_existing_files(tmp_path, recursive=True)
            handle_event.assert_called_once_with(str(file_path))


def test_shutdown_signal_handlers_set_event_and_register_both_signals():
    shutdown_requested = Event()
    registered = {}

    def capture_handler(signum, callback):
        registered[signum] = callback

    with patch(
        "ingestion.management.commands.ingestion_watcher.signal.signal",
        side_effect=capture_handler,
    ):
        _install_shutdown_handlers(shutdown_requested)

    assert signal.SIGTERM in registered
    assert signal.SIGINT in registered
    registered[signal.SIGTERM](signal.SIGTERM, None)
    assert shutdown_requested.is_set()
    shutdown_requested.clear()
    registered[signal.SIGINT](signal.SIGINT, None)
    assert shutdown_requested.is_set()


class TestObserverLifecycle:
    def test_normal_shutdown_orders_cleanup(self, tmp_path):
        calls = MagicMock()
        observer = MagicMock()
        handler = MagicMock()
        shutdown_requested = MagicMock(spec=Event)
        shutdown_requested.is_set.return_value = False
        calls.attach_mock(observer, "observer")
        calls.attach_mock(handler, "handler")
        calls.attach_mock(shutdown_requested, "shutdown_requested")

        _run_observer(observer, handler, tmp_path, False, shutdown_requested)

        assert calls.mock_calls == [
            call.observer.start(),
            call.shutdown_requested.is_set(),
            call.handler.reconcile_existing_files(tmp_path, False),
            call.shutdown_requested.wait(),
            call.observer.stop(),
            call.observer.join(),
            call.handler.shutdown(),
        ]

    def test_reconciliation_failure_cleans_up_and_propagates(self, tmp_path):
        observer = MagicMock()
        handler = MagicMock()
        error = RuntimeError("reconciliation exploded")
        handler.reconcile_existing_files.side_effect = error

        with pytest.raises(RuntimeError) as raised:
            _run_observer(observer, handler, tmp_path, False, Event())

        assert raised.value is error
        observer.stop.assert_called_once_with()
        observer.join.assert_called_once_with()
        handler.shutdown.assert_called_once_with()

    def test_shutdown_before_reconciliation_skips_existing_files(
        self, tmp_path
    ):
        observer = MagicMock()
        handler = MagicMock()
        shutdown_requested = Event()
        shutdown_requested.set()

        _run_observer(observer, handler, tmp_path, False, shutdown_requested)

        handler.reconcile_existing_files.assert_not_called()
        observer.stop.assert_called_once_with()
        observer.join.assert_called_once_with()
        handler.shutdown.assert_called_once_with()

    def test_stop_failure_still_joins_and_shuts_down(self, tmp_path):
        observer = MagicMock()
        handler = MagicMock()
        shutdown_requested = Event()
        shutdown_requested.set()
        error = RuntimeError("observer stop failed")
        observer.stop.side_effect = error

        with pytest.raises(RuntimeError) as raised:
            _run_observer(
                observer, handler, tmp_path, False, shutdown_requested
            )

        assert raised.value is error
        observer.join.assert_called_once_with()
        handler.shutdown.assert_called_once_with()


def test_main_preserves_unrelated_runtime_error(tmp_path):
    error = RuntimeError("reconciliation exploded")
    with (
        patch("sys.argv", ["ingestion_watcher", "--path", str(tmp_path)]),
        patch(
            "ingestion.management.commands.ingestion_watcher.PollingObserver"
        ),
        patch(
            "ingestion.management.commands.ingestion_watcher._install_shutdown_handlers"
        ),
        patch(
            "ingestion.management.commands.ingestion_watcher._run_observer",
            side_effect=error,
        ),
    ):
        with pytest.raises(RuntimeError) as raised:
            main()

    assert raised.value is error


def test_watch_path_lock_rejects_second_owner_then_releases(tmp_path):
    with _watch_path_lock(tmp_path):
        with pytest.raises(WatcherAlreadyRunningError, match="already owns"):
            with _watch_path_lock(tmp_path):
                pass

    with _watch_path_lock(tmp_path):
        pass


class TestCommandAction:
    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_default_template(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction()

        action("/data/CHIK_ES_2026.csv")

        mock_run.assert_called_once_with(
            [
                "makim",
                "ingestion.run",
                "--paths",
                "/data/CHIK_ES_2026.csv",
            ],
            check=False,
        )

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_quoting_with_special_characters(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction()

        path = "/data/ChikInfodengue_202553 (3).dbf"
        action(path)

        mock_run.assert_called_once_with(
            [
                "makim",
                "ingestion.run",
                "--paths",
                path,
            ],
            check=False,
        )

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_custom_template(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction(template="echo {path}")

        action("/tmp/test.csv")

        mock_run.assert_called_once_with(
            ["echo", "/tmp/test.csv"],
            check=False,
        )

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_include_existing_flag(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction(include_existing=True)

        action("test.csv")

        mock_run.assert_called_once_with(
            [
                "makim",
                "ingestion.run",
                "--paths",
                "test.csv",
                "--include-existing",
            ],
            check=False,
        )

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_requeue_flag(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction(requeue=True)

        action("test.csv")

        mock_run.assert_called_once_with(
            [
                "makim",
                "ingestion.run",
                "--paths",
                "test.csv",
                "--include-existing",
                "--requeue",
            ],
            check=False,
        )

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_allow_outdated_flag(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction(allow_outdated=True)

        action("test.dbf")

        mock_run.assert_called_once_with(
            [
                "makim",
                "ingestion.run",
                "--paths",
                "test.dbf",
                "--allow-outdated",
            ],
            check=False,
        )

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_combined_flags(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction(
            include_existing=True, requeue=True, allow_outdated=True
        )

        action("test.dbf")

        mock_run.assert_called_once_with(
            [
                "makim",
                "ingestion.run",
                "--paths",
                "test.dbf",
                "--include-existing",
                "--requeue",
                "--allow-outdated",
            ],
            check=False,
        )

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_nonzero_return_does_not_raise(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        action = CommandAction()

        action("fail.csv")

        mock_run.assert_called_once_with(
            [
                "makim",
                "ingestion.run",
                "--paths",
                "fail.csv",
            ],
            check=False,
        )


class TestLogOnlyAction:
    def test_does_not_raise(self):
        action = LogOnlyAction()
        # Should just log, not raise
        action("/some/path/test.csv")


def test_parser_builds_allow_outdated_command_action():
    args = _build_parser().parse_args(["--path", "/tmp", "--allow-outdated"])

    action = _build_action(args)

    assert isinstance(action, CommandAction)
    assert action.allow_outdated is True
    assert action.include_existing is False
    assert action.requeue is False
