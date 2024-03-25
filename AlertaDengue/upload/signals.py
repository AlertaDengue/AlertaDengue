from pathlib import Path
from loguru import logger

from celery.result import AsyncResult
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import SINAN, Status
from .tasks import process_sinan_file


@receiver(post_save, sender=SINAN)
def process_sinan_file_on_save(sender, instance, created, **kwargs):
    if created:  # runs only after create
        sinan = SINAN.objects.get(instance.pk)

        try:
            result: AsyncResult = process_sinan_file.delay(  # pyright: ignore
                sinan.pk
            )

            if not result.get(follow_parents=True):
                logger.error(f"Error processing {sinan.filename}")
                sinan.status = Status.ERROR
                sinan.save()

        except Exception as e:
            logger.error(f"Error processing {sinan.filename}: {str(e)}")
            sinan.status = Status.ERROR
            sinan.save()

            chunks_dir = Path(sinan.chunks_dir)

            for chunk in list(chunks_dir.glob("*.parquet")):
                chunk.unlink(missing_ok=True)

            Path(sinan.chunks_dir).rmdir()


@receiver(pre_delete, sender=SINAN)
def delete_sinan_file_on_delete(sender, instance, **kwargs):
    sinan = SINAN.objects.get(instance.pk)

    for chunk in Path(sinan.chunks_dir).glob("*.parquet"):
        chunk.unlink(missing_ok=True)

    Path(sinan.chunks_dir).rmdir()

    Path(sinan.filepath).unlink(missing_ok=True)
