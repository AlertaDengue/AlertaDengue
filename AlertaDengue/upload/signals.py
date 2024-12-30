from pathlib import Path
from typing import Any, Type

from django.db.models import Model, signals
from django.dispatch import receiver
from django.db import transaction

from .models import (
    sinan_upload_log_path,
    SINANChunkedUpload,
    SINANUpload,
    SINANUploadLogStatus
)
from .tasks import sinan_process_file


@receiver(signals.pre_delete, sender=SINANChunkedUpload)
def delete_sinan_file_on_delete(
    sender: Type[Model], instance: SINANChunkedUpload, **kwargs: Any
) -> None:
    try:
        Path(instance.file.path).unlink(missing_ok=True)
    except ValueError:
        pass


@receiver(signals.post_save, sender=SINANUpload)
def create_sinan_upload(sender, instance: SINANUpload, created, **kwargs):
    if created:
        log_dir = Path(sinan_upload_log_path())
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{instance._final_basename()}-{instance.pk}.log"
        log_file.touch()

        log_status = SINANUploadLogStatus.objects.create(
            status=0,
            log_file=str(log_file.absolute())
        )
        log_status.debug(f"Log file '{log_file}' created")

        instance.status = log_status
        instance.save()

        transaction.on_commit(lambda: sinan_process_file.delay(instance.pk))
