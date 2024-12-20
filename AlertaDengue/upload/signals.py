from pathlib import Path
from typing import Any, Type

from django.db.models import Model, signals
from django.dispatch import receiver

from .models import SINAN, Status
from .tasks import process_sinan_file


@receiver(signals.post_save, sender=SINAN)
def process_sinan_file_on_save(
    sender: Type[Model], instance: SINAN, **kwargs: Any
) -> None:
    sinan = SINAN.objects.get(pk=instance.pk)  # pylint: disable=E1101
    if sinan.status == Status.WAITING_CHUNK:
        process_sinan_file.delay(sinan.pk)


@receiver(signals.pre_delete, sender=SINAN)
def delete_sinan_file_on_delete(
    sender: Type[Model], instance: SINAN, **kwargs: Any
) -> None:
    if instance.chunks_dir:
        for chunk in Path(instance.chunks_dir).glob("*.parquet"):
            chunk.unlink(missing_ok=True)

        for csv in Path(instance.chunks_dir).glob("*.csv"):
            csv.unlink(missing_ok=True)

        for dbf in Path(instance.chunks_dir).glob("*.dbf"):
            dbf.unlink(missing_ok=True)

        chunks_dir = Path(instance.chunks_dir)
        if chunks_dir.exists():
            chunks_dir.rmdir()

    Path(str(instance.filepath)).unlink(missing_ok=True)
    if instance.misparsed_file:
        Path(str(instance.misparsed_file)).unlink(missing_ok=True)
