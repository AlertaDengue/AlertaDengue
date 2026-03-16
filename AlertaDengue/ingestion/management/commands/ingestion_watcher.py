"""
Standalone file-system watcher for SINAN ingestion.

Watches a directory for new data files and triggers a configurable action
when a file has settled (no further writes for ``--settle-time`` seconds).

Uses ``PollingObserver`` (stat-based) instead of inotify so that files
materialised via Docker bind-mount volumes are reliably detected.

Designed to be decoupled from AlertaDengue internals: the processing
action is configurable via ``--action`` and ``--action-command``, so any
external command (makim, curl, custom script …) can be injected.
"""
from __future__ import annotations

import argparse
import shlex
import subprocess
import time
from pathlib import Path
from threading import Timer
from typing import Protocol

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver


# ---------------------------------------------------------------------------
# Action backends
# ---------------------------------------------------------------------------
class FileAction(Protocol):
    """Protocol for pluggable processing actions."""

    def __call__(self, src_path: str) -> None:
        ...


class CommandAction:
    """
    Run an external command for each detected file.

    Parameters
    ----------
    template : str
        Command template. ``{path}`` is replaced with the file path.
    include_existing : bool
        Forward ``--include-existing`` flag.
    requeue : bool
        Forward ``--requeue`` flag.
    """

    DEFAULT_TEMPLATE = "makim ingestion.run --paths {path}"

    def __init__(
        self,
        template: str = DEFAULT_TEMPLATE,
        include_existing: bool = False,
        requeue: bool = False,
    ) -> None:
        self.template = template
        self.include_existing = include_existing
        self.requeue = requeue

    def __call__(self, src_path: str) -> None:
        quoted_path = shlex.quote(src_path)
        cmd_str = self.template.replace("{path}", quoted_path)

        if self.include_existing or self.requeue:
            cmd_str += " --include-existing"
        if self.requeue:
            cmd_str += " --requeue"

        logger.debug(f"Executing: {cmd_str}")
        result = subprocess.run(cmd_str, shell=True, check=False)

        name = Path(src_path).name
        if result.returncode == 0:
            logger.success(f"Pipeline finished for: {name}")
        else:
            logger.error(
                f"Pipeline failed for {name} (exit {result.returncode})"
            )


class LogOnlyAction:
    """Just log the event — useful for testing / dry-run."""

    def __call__(self, src_path: str) -> None:
        logger.info(f"[log-only] Would process: {src_path}")


# ---------------------------------------------------------------------------
# Watcher handler
# ---------------------------------------------------------------------------
class IngestionWatcherHandler(FileSystemEventHandler):
    """
    Handles file system events for SINAN ingestion.

    Uses a *settle* mechanism: when a file is created or modified a timer
    is started.  If another event fires for the same file the timer is
    reset.  When the timer expires without further events the configured
    ``action`` is invoked.  This ensures uploads (SFTP, mc mirror, …) are
    complete before processing begins.

    Parameters
    ----------
    action : FileAction
        Callable invoked when a file has settled.
    settle_time : float
        Seconds to wait after the last write event.
    extensions : frozenset[str]
        Lowercase file extensions to watch (including the dot).
    """

    def __init__(
        self,
        action: FileAction,
        settle_time: float = 5.0,
        extensions: frozenset[str] | None = None,
    ) -> None:
        super().__init__()
        self.action = action
        self.settle_time = settle_time
        self.extensions = extensions or frozenset({".csv", ".dbf"})
        self.timers: dict[str, Timer] = {}

    # -- watchdog callbacks --------------------------------------------------

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    # -- internal ------------------------------------------------------------

    def _handle_event(self, src_path: str) -> None:
        path = Path(src_path)
        if path.suffix.lower() not in self.extensions:
            return

        # Reset timer if it exists
        if src_path in self.timers:
            self.timers[src_path].cancel()

        t = Timer(self.settle_time, self.process_file, args=[src_path])
        self.timers[src_path] = t
        t.start()

    def process_file(self, src_path: str) -> None:
        """Trigger the configured action for *src_path*."""
        if src_path in self.timers:
            del self.timers[src_path]

        path = Path(src_path)
        if not path.exists():
            logger.warning(f"File vanished before processing: {src_path}")
            return

        logger.info(f"Processing detected file: {src_path}")
        try:
            self.action(src_path)
        except Exception as e:
            logger.exception(
                f"Unexpected error while processing {src_path}: {e}"
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Watch a directory for new SINAN data files and trigger "
            "an ingestion action when files settle."
        ),
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Directory to watch.",
    )
    parser.add_argument(
        "--settle-time",
        type=float,
        default=5.0,
        help=(
            "Wait N seconds after last modification before triggering "
            "(default: 5.0)."
        ),
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help=(
            "Polling interval in seconds for the PollingObserver "
            "(default: 2.0)."
        ),
    )
    parser.add_argument(
        "--extensions",
        type=str,
        default=".csv,.dbf",
        help=(
            "Comma-separated list of file extensions to watch "
            "(default: .csv,.dbf)."
        ),
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Watch subdirectories recursively.",
    )

    # Action configuration
    parser.add_argument(
        "--action",
        type=str,
        choices=["command", "log-only"],
        default="command",
        help="Action backend to use (default: command).",
    )
    parser.add_argument(
        "--action-command",
        type=str,
        default=CommandAction.DEFAULT_TEMPLATE,
        help=(
            "Command template for 'command' action. "
            "Use {path} as placeholder for the file path "
            f"(default: '{CommandAction.DEFAULT_TEMPLATE}')."
        ),
    )

    # Legacy flags forwarded to CommandAction
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Forward --include-existing to the action command.",
    )
    parser.add_argument(
        "--requeue",
        action="store_true",
        help="Forward --requeue to the action command.",
    )

    return parser


def _build_action(args: argparse.Namespace) -> FileAction:
    """Build the appropriate action backend from parsed CLI args."""
    if args.action == "log-only":
        return LogOnlyAction()
    return CommandAction(
        template=args.action_command,
        include_existing=args.include_existing,
        requeue=args.requeue,
    )


def _parse_extensions(raw: str) -> frozenset[str]:
    """Parse comma-separated extension string into a frozenset."""
    exts: set[str] = set()
    for part in raw.split(","):
        ext = part.strip().lower()
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        if ext:
            exts.add(ext)
    return frozenset(exts)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    watch_path = Path(args.path).resolve()
    if not watch_path.exists():
        logger.info(f"Creating watch path: {watch_path}")
        watch_path.mkdir(parents=True, exist_ok=True)

    extensions = _parse_extensions(args.extensions)
    action = _build_action(args)

    logger.info(f"Starting Ingestion Watcher on: {watch_path}")
    logger.info(f"Settle time: {args.settle_time}s")
    logger.info(f"Poll interval: {args.poll_interval}s")
    logger.info(f"Extensions: {', '.join(sorted(extensions))}")
    logger.info(f"Recursive: {args.recursive}")
    logger.info(f"Action: {args.action}")
    logger.info(f"Include existing: {args.include_existing}")
    logger.info(f"Requeue: {args.requeue}")

    handler = IngestionWatcherHandler(
        action=action,
        settle_time=args.settle_time,
        extensions=extensions,
    )

    observer = PollingObserver(timeout=args.poll_interval)
    observer.schedule(handler, str(watch_path), recursive=args.recursive)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
