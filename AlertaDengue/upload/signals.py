from pathlib import Path

from celery.result import AsyncResult
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import SINAN, Status
from .tasks import process_sinan_file


@receiver(post_save, sender=SINAN)
def process_sinan_file_on_save(sender, instance, **kwargs):
    sinan = SINAN.objects.get(pk=instance.pk)
    if sinan.status == Status.WAITING_CHUNK:
        process_sinan_file.delay(sinan.pk)  # pyright: ignore

        # TODO: should it unlink the data file on error?
        # Path(str(instance.filepath)).unlink(missing_ok=True)
        # instance.filepath = None
        # instance.save()


@receiver(pre_delete, sender=SINAN)
def delete_sinan_file_on_delete(sender, instance, **kwargs):
    if instance.chunks_dir:
        for chunk in Path(instance.chunks_dir).glob("*.parquet"):
            chunk.unlink(missing_ok=True)

        Path(instance.chunks_dir).rmdir()

    Path(str(instance.filepath)).unlink(missing_ok=True)
