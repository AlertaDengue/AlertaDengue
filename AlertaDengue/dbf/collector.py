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

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")


class FileHandler(FileSystemEventHandler):
    """
    Class that handles new file events.
    """

    def __init__(self):
        super().__init__()
        self.year = 2023
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
        self.insert_dbf()

    def insert_dbf(self):
        """
        Method to insert DBF data into the database.
        """
        try:
            minio_client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=False,
            )

            response = minio_client.get_object(
                bucket_name=MINIO_BUCKET_NAME, object_name=str(self.file_name)
            )

            file_data = response.data

            with tempfile.NamedTemporaryFile(
                suffix=".dbf", delete=False
            ) as temp_file:
                logger.info("Saving the DBF data to a temporary file")
                temp_file.write(file_data)

            sinan = Sinan(temp_file.name, self.year)
            sinan.save_to_pgsql(default_cid=self.default_cid)

            # Remove the temporary file
            temp_file.close()
            Path(temp_file.name).unlink()

        except ValidationError as e:
            logger.info(f"File not valid: {e.message}")


if __name__ == "__main__":
    logger.add(
        "file.log", rotation="500 MB"
    )  # Add a file logger with rotation
    observer = Observer()
    observer.schedule(
        FileHandler(),
        # path=Path(ROOT_DIR / "collector" / "data" / "dbf")
        path="/opt/services/collector/data/dbf",
    )
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
