"""Tests for the decoupled ingestion watcher."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from ingestion.management.commands.ingestion_watcher import (
    CommandAction,
    IngestionWatcherHandler,
    LogOnlyAction,
    _parse_extensions,
)
from watchdog.events import FileSystemEvent


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


class TestCommandAction:
    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_default_template(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction()

        action("/data/CHIK_ES_2026.csv")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "makim ingestion.run --paths /data/CHIK_ES_2026.csv" == cmd

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_quoting_with_special_characters(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction()

        # Filename with spaces and parentheses
        path = "/data/ChikInfodengue_202553 (3).dbf"
        action(path)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        # shlex.quote will wrap it in single quotes
        assert (
            "makim ingestion.run --paths '/data/ChikInfodengue_202553 (3).dbf'"
            == cmd
        )

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_custom_template(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction(template="echo {path}")

        action("/tmp/test.csv")

        cmd = mock_run.call_args[0][0]
        assert cmd == "echo /tmp/test.csv"

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_include_existing_flag(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction(include_existing=True)

        action("test.csv")

        cmd = mock_run.call_args[0][0]
        assert "--include-existing" in cmd
        assert "--requeue" not in cmd

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_requeue_flag(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        action = CommandAction(requeue=True)

        action("test.csv")

        cmd = mock_run.call_args[0][0]
        assert "--include-existing" in cmd
        assert "--requeue" in cmd

    @patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
    def test_nonzero_return_does_not_raise(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        action = CommandAction()

        # Should not raise
        action("fail.csv")


class TestLogOnlyAction:
    def test_does_not_raise(self):
        action = LogOnlyAction()
        # Should just log, not raise
        action("/some/path/test.csv")
