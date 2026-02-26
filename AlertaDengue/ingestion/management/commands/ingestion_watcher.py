from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path
from threading import Timer

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class IngestionWatcherHandler(FileSystemEventHandler):
    """
    Handles file system events for SINAN ingestion.

    It uses a 'settle' mechanism: when a file is modified or created,
    a timer is started. If another event occurs for the same file,
    the timer is reset. When the timer expires, the processing is triggered.
    This ensures that SFTP uploads are complete before we touch the file.
    """

    def __init__(
        self,
        settle_time: float = 5.0,
        include_existing: bool = False,
        requeue: bool = False,
    ):
        super().__init__()
        self.settle_time = settle_time
        self.include_existing = include_existing
        self.requeue = requeue
        self.timers: dict[str, Timer] = {}

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.src_path)

    def _handle_event(self, src_path: str) -> None:
        path = Path(src_path)
        if path.suffix.lower() not in (".csv", ".dbf"):
            return

        # Reset timer if it exists
        if src_path in self.timers:
            self.timers[src_path].cancel()

        # Start new timer
        t = Timer(self.settle_time, self.process_file, args=[src_path])
        self.timers[src_path] = t
        t.start()

    def process_file(self, src_path: str) -> None:
        """
        Trigger the makim ingestion.run command for the file.
        """
        if src_path in self.timers:
            del self.timers[src_path]

        path = Path(src_path)
        if not path.exists():
            logger.warning(f"File vanished before processing: {src_path}")
            return

        logger.info(f"Processing detected file: {src_path}")
        try:
            # We call makim directly to reuse the established pipeline
            cmd = ["makim", "ingestion.run", "--paths", src_path]

            if self.include_existing:
                cmd.append("--include-existing")
            if self.requeue:
                cmd.append("--requeue")

            logger.debug(f"Executing: {' '.join(cmd)}")

            # Use subprocess.run without capture_output to stream logs
            result = subprocess.run(cmd, check=False)

            if result.returncode == 0:
                logger.success(f"Pipeline finished for: {path.name}")
            else:
                logger.error(
                    f"Pipeline failed for {path.name} (exit {result.returncode})"
                )
        except Exception as e:
            logger.exception(
                f"Unexpected error while triggering makim for {src_path}: {e}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch directory for SINAN data."
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
        help="Wait N seconds after last modification to ensure upload is finished.",
    )
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Include files in manifest even if already moved.",
    )
    parser.add_argument(
        "--requeue",
        action="store_true",
        help="Re-enqueue even if run already exists.",
    )
    args = parser.parse_args()

    watch_path = Path(args.path).resolve()
    if not watch_path.exists():
        logger.info(f"Creating watch path: {watch_path}")
        watch_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting Ingestion Watcher on: {watch_path}")
    logger.info(f"Settle time: {args.settle_time}s")
    logger.info(f"Include existing: {args.include_existing}")
    logger.info(f"Requeue: {args.requeue}")

    event_handler = IngestionWatcherHandler(
        settle_time=args.settle_time,
        include_existing=args.include_existing,
        requeue=args.requeue,
    )
    observer = Observer()
    observer.schedule(event_handler, str(watch_path), recursive=False)
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
