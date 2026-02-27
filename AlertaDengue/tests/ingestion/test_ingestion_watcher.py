from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ingestion.management.commands.ingestion_watcher import (
    IngestionWatcherHandler,
)
from watchdog.events import FileSystemEvent


@pytest.fixture
def handler():
    # Use a small settle time for tests, though we won't wait for it
    return IngestionWatcherHandler(settle_time=0.1)


def test_handler_ignores_directories(handler):
    event = FileSystemEvent("some/dir")
    event.is_directory = True

    with patch.object(handler, "_handle_event") as mock_handle:
        handler.on_created(event)
        handler.on_modified(event)

        mock_handle.assert_not_called()


def test_handler_ignores_non_data_files(handler):
    with patch.object(handler, "process_file") as mock_process:
        handler._handle_event("some/file.txt")
        handler._handle_event("some/image.png")

        assert len(handler.timers) == 0


def test_handler_starts_timer_for_valid_files(handler):
    with patch(
        "ingestion.management.commands.ingestion_watcher.Timer"
    ) as mock_timer_class:
        mock_timer_instance = MagicMock()
        mock_timer_class.return_value = mock_timer_instance

        handler._handle_event("some/data.csv")

        assert "some/data.csv" in handler.timers
        mock_timer_class.assert_called_once_with(
            0.1, handler.process_file, args=["some/data.csv"]
        )
        mock_timer_instance.start.assert_called_once()


def test_handler_resets_timer_on_subsequent_events(handler):
    with patch(
        "ingestion.management.commands.ingestion_watcher.Timer"
    ) as mock_timer_class:
        mock_timer_instance1 = MagicMock()
        mock_timer_instance2 = MagicMock()
        mock_timer_class.side_effect = [
            mock_timer_instance1,
            mock_timer_instance2,
        ]

        # First event
        handler._handle_event("data.dbf")
        assert handler.timers["data.dbf"] == mock_timer_instance1
        mock_timer_instance1.start.assert_called_once()

        # Second event resets timer
        handler._handle_event("data.dbf")
        mock_timer_instance1.cancel.assert_called_once()
        assert handler.timers["data.dbf"] == mock_timer_instance2
        mock_timer_instance2.start.assert_called_once()


@patch("ingestion.management.commands.ingestion_watcher.Path.exists")
@patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
def test_process_file_executes_pipeline(mock_run, mock_exists, handler):
    mock_exists.return_value = True
    handler.timers["test.csv"] = MagicMock()

    handler.process_file("test.csv")

    # Timer should be removed
    assert "test.csv" not in handler.timers

    # Subprocess should be called with correct args
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args == ["makim", "ingestion.run", "--paths", "test.csv"]


@patch("ingestion.management.commands.ingestion_watcher.Path.exists")
@patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
def test_process_file_with_flags(mock_run, mock_exists):
    handler = IngestionWatcherHandler(include_existing=True, requeue=True)
    mock_exists.return_value = True

    handler.process_file("test.csv")

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "--include-existing" in args
    assert "--requeue" in args


@patch("ingestion.management.commands.ingestion_watcher.Path.exists")
@patch("ingestion.management.commands.ingestion_watcher.subprocess.run")
def test_process_file_vanished_file(mock_run, mock_exists, handler):
    # If the file vanishes before the timer runs out
    mock_exists.return_value = False

    handler.process_file("vanished.csv")

    # Should not trigger ingestion
    mock_run.assert_not_called()
