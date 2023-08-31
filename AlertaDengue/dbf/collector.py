import os
import tempfile
import time
from datetime import datetime as dt
from pathlib import Path
from typing import Optional

from dbf.sinan import Sinan
from django.conf import settings
from django.core.exceptions import ValidationError
from loguru import logger
from minio import Minio
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class FileHandler(FileSystemEventHandler):
    """
    Class that handles new file events.
    """

    def __init__(self):
        super().__init__()
        self.year = dt.today().strftime("%Y")
        self.default_cid = "dengue"

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Called when a new file is created.

        Parameters
        ----------
        event : watchdog.events.FileSystemEvent
            The event triggered by the file creation.
        """
        # Extract the file path from the event
        self.file_path = Path(event.src_path)

        # Extract the file name from the file path
        self.file_name = self.file_path.name

        # Insert the file into the database
        self.insert_dbf_from_minio(year=self.year)

    # @app.task(name="insert_dbf_from_minio")
    def insert_dbf_from_minio(
        self, year: int, default_cid: Optional[str] = None
    ) -> None:
        """
        Insert DBF data into the database.

        Parameters
        ----------
        year : int
            The year of the data.
        default_cid : str, optional
            The default cid.

        Raises
        ------
        ValidationError
            If the file is not valid.
        """
        try:
            # Create a Minio client
            minio_client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=False,
            )

            # Get the DBF data from the Minio bucket
            response = minio_client.get_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=str(self.file_name),
            )

            # Read the file data
            file_data = response.data

            # Save the DBF data to a temporary file
            with tempfile.NamedTemporaryFile(
                suffix=".dbf", delete=False
            ) as temp_file:
                logger.info("Saving the DBF data to a temporary file")
                temp_file.write(file_data)

            # Create a Sinan instance with the temporary file and year
            sinan = Sinan(temp_file.name, year)

            # Save the data to the PostgreSQL database
            sinan.save_to_pgsql(default_cid=default_cid)
            # Remove the temporary file
            temp_file.close()
            Path(temp_file.name).unlink()

        except ValidationError as e:
            logger.info(f"File not valid: {e.message}")
            temp_file.close()
            Path(temp_file.name).unlink()


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
