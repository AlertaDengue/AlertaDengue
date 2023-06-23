import os
import tempfile
import time
from pathlib import Path

from dbf.sinan import Sinan
from django.core.exceptions import ValidationError
from loguru import logger
from minio import Minio
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent


class FileHandler(FileSystemEventHandler):
    """
    Class that handles new file events.
    """

    def __init__(self):
        super().__init__()
        self.file_name2 = ""
        self.year = 0
        self.default_cid = "zika"

    def on_created(self, event):
        """
        Method that is called when a new file is created.

        Parameters
        ----------
        event : watchdog.events.FileSystemEvent
            The event that was triggered by the file creation.
        """
        self.file_path = Path(event.src_path)
        self.file_name = self.file_path.name
        logger.info(f"Event source path: {self.file_path}")
        self.insert_dbf()

    def insert_dbf(self):
        """
        Method to insert DBF data into the database.
        """
        MINIO_BUCKET_NAME = "dbf"
        try:
            minio_client = Minio(
                "minio:9000",
                access_key="?",
                secret_key="?????",
                secure=False,
            )

            response = minio_client.get_object(
                bucket_name=MINIO_BUCKET_NAME, object_name=str(self.file_name)
            )

            file_data = response.data

            # Save the DBF data to a temporary file
            with tempfile.NamedTemporaryFile(
                suffix=".dbf", delete=False
            ) as temp_file:
                temp_file.write(file_data)

            sinan = Sinan(temp_file.name, self.year)
            sinan.save_to_pgsql(default_cid=self.default_cid)

            # Remove the temporary file
            temp_file.close()
            os.remove(temp_file.name)

        except ValidationError as e:
            logger.info(f"File not valid: {e.message}")


if __name__ == "__main__":
    logger.debug(ROOT_DIR)
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
