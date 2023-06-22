#!/usr/bin/env python3

import datetime
import os
import time
from pathlib import Path

from dbf.sinan import Sinan
from django.core.exceptions import ValidationError
from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent


class FileHandler(FileSystemEventHandler):
    """
    Class that handles new file events.

    Attributes:
        None

    Methods:
        on_created(event): Method that is called when a new file is created.
    """

    def on_created(self, event) -> None:
        """
        Method that is called when a new file is created.

        Args:
            event: The event that was triggered by the file creation.

        Returns:
            None
        """

        logger.info(event.src_path)
        if event.is_directory:
            self.file_name = os.path.basename(event.src_path)
            today = datetime.datetime.today()
            self.year = today.year
            self.default_cid = "chikungunya"
            logger.info(
                f"New file created: {self.file_name}, {today}, {self.year}"
            )
            return

    def insert_dbf(self, *args, **options):
        try:
            sinan = Sinan(options[self.filename], options[self.year])
            sinan.save_to_pgsql(default_cid=options[self.default_cid])
        except ValidationError as e:
            logger.info(f"File not valid: {e.message}")


if __name__ == "__main__":
    logger.debug(os.getcwd())
    logger.add(
        "file.log", rotation="500 MB"
    )  # Add a file logger with rotation
    observer = Observer()
    observer.schedule(FileHandler(), path="/opt/services/collector/data/dbf")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
