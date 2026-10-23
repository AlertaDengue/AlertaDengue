"""
Standalone file-system watcher for SINAN ingestion.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
import fcntl
from pathlib import Path
import shlex
import signal
import subprocess
from threading import Condition, Event, Timer
from typing import Protocol

from loguru import logger
from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
    FileSystemMovedEvent,
)
from watchdog.observers.polling import PollingObserver


class FileAction(Protocol):
    """Protocol for pluggable processing actions."""

    def __call__(self, src_path: str) -> None: ...


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
    allow_outdated : bool
        Forward ``--allow-outdated`` flag.
    """

    DEFAULT_TEMPLATE = "makim ingestion.run --paths {path}"

    def __init__(
        self,
        template: str = DEFAULT_TEMPLATE,
        include_existing: bool = False,
        requeue: bool = False,
        allow_outdated: bool = False,
    ) -> None:
        self.template = template
        self.include_existing = include_existing
        self.requeue = requeue
        self.allow_outdated = allow_outdated

    def __call__(self, src_path: str) -> None:
        quoted_path = shlex.quote(src_path)
        command = self.template.replace("{path}", quoted_path)
        args = shlex.split(command)

        if self.include_existing or self.requeue:
            args.append("--include-existing")
        if self.requeue:
            args.append("--requeue")
        if self.allow_outdated:
            args.append("--allow-outdated")

        logger.debug(f"Executing: {shlex.join(args)}")
        result = subprocess.run(args, check=False)

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


class WatcherAlreadyRunningError(RuntimeError):
    """Raised when another watcher owns the same directory."""


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
        # Retain the last value so a later schedule never reuses a token.
        self._timer_generations: dict[str, int] = {}
        self._condition = Condition()
        self._active_actions = 0
        self._shutting_down = False

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def on_moved(self, event: FileSystemMovedEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.dest_path)

    def _handle_event(self, src_path: str) -> None:
        path = Path(src_path)
        if path.suffix.lower() not in self.extensions:
            return

        with self._condition:
            if self._shutting_down:
                return
            # Reset timer if it exists.
            if src_path in self.timers:
                self.timers[src_path].cancel()

            generation = self._timer_generations.get(src_path, 0) + 1
            self._timer_generations[src_path] = generation
            timer = Timer(
                self.settle_time,
                self.process_file,
                args=[src_path, generation],
            )
            timer.daemon = False
            self.timers[src_path] = timer
            timer.start()

    def process_file(
        self, src_path: str, generation: int | None = None
    ) -> None:
        """Trigger the configured action for *src_path*."""
        with self._condition:
            if generation is not None and (
                self._timer_generations.get(src_path) != generation
                or src_path not in self.timers
            ):
                return
            if self._shutting_down:
                return
            self.timers.pop(src_path, None)
            # This transition is atomic with shutdown's pending-timer cleanup.
            self._active_actions += 1
        try:
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
        finally:
            with self._condition:
                self._active_actions -= 1
                self._condition.notify_all()

    def reconcile_existing_files(
        self,
        watch_path: Path,
        recursive: bool,
        shutdown_requested: Event | None = None,
    ) -> None:
        """Schedule supported files already present at watcher startup."""
        candidates = (
            watch_path.rglob("*") if recursive else watch_path.iterdir()
        )
        for path in sorted(candidates):
            if shutdown_requested is not None and shutdown_requested.is_set():
                break
            if path.is_file() and path.suffix.lower() in self.extensions:
                self._handle_event(str(path))

    def _begin_shutdown(self) -> None:
        """Reject new events and timer callbacks before observer cleanup."""
        with self._condition:
            self._shutting_down = True

    def shutdown(self) -> None:
        """Cancel pending work and wait for actions already in progress."""
        self._begin_shutdown()
        with self._condition:
            for timer in self.timers.values():
                timer.cancel()
            self.timers.clear()
            self._timer_generations.clear()
            while self._active_actions:
                self._condition.wait()


def _install_shutdown_handlers(shutdown_requested: Event) -> None:
    """Make SIGTERM and SIGINT request a normal watcher shutdown."""

    def handle_shutdown(_signum: int, _frame: object) -> None:
        shutdown_requested.set()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)


@contextmanager
def _watch_path_lock(watch_path: Path) -> Iterator[None]:
    """Hold a kernel advisory lock for this watched directory."""
    lock_path = watch_path / ".ingestion-watcher.lock"
    lock_file = lock_path.open("a")
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WatcherAlreadyRunningError(
                f"Another ingestion watcher already owns {watch_path}"
            ) from error
        yield
    finally:
        lock_file.close()


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
    parser.add_argument(
        "--allow-outdated",
        action="store_true",
        help="Forward --allow-outdated to the action command.",
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
        allow_outdated=args.allow_outdated,
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


def _run_observer(
    observer: PollingObserver,
    handler: IngestionWatcherHandler,
    watch_path: Path,
    recursive: bool,
    shutdown_requested: Event,
) -> None:
    """Run the observer and release handler work on every exit path."""
    observer_started = False
    try:
        observer.start()
        observer_started = True
        if not shutdown_requested.is_set():
            handler.reconcile_existing_files(
                watch_path, recursive, shutdown_requested
            )
        shutdown_requested.wait()
        logger.info("Stopping watcher...")
    finally:
        try:
            try:
                handler._begin_shutdown()
            finally:
                if observer_started:
                    try:
                        observer.stop()
                    finally:
                        observer.join()
        finally:
            handler.shutdown()


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
    logger.info(f"Allow outdated: {args.allow_outdated}")

    shutdown_requested = Event()
    try:
        with _watch_path_lock(watch_path):
            _install_shutdown_handlers(shutdown_requested)
            handler = IngestionWatcherHandler(
                action=action,
                settle_time=args.settle_time,
                extensions=extensions,
            )

            observer = PollingObserver(timeout=args.poll_interval)
            observer.schedule(
                handler, str(watch_path), recursive=args.recursive
            )
            _run_observer(
                observer,
                handler,
                watch_path,
                args.recursive,
                shutdown_requested,
            )
    except WatcherAlreadyRunningError as error:
        logger.error(str(error))
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
