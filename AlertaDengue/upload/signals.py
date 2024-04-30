from typing import Type, Any
from pathlib import Path

from django.db.models import signals, Model
from django.dispatch import receiver

from .models import SINAN, Status
from .tasks import process_sinan_file


@receiver(signals.post_save, sender=SINAN)
def process_sinan_file_on_save(
    sender: Type[Model],
    instance: SINAN,
    **kwargs: Any
) -> None:
    sinan = SINAN.objects.get(pk=instance.pk)  # pylint: disable=E1101
    if sinan.status == Status.WAITING_CHUNK:
        process_sinan_file.delay(sinan.pk)


@receiver(signals.pre_delete, sender=SINAN)
def delete_sinan_file_on_delete(
    sender: Type[Model],
    instance: SINAN,
    **kwargs: Any
) -> None:
    if instance.chunks_dir:
        for chunk in Path(instance.chunks_dir).glob("*.parquet"):
            chunk.unlink(missing_ok=True)

        Path(instance.chunks_dir).rmdir()

    Path(str(instance.filepath)).unlink(missing_ok=True)
