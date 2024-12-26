from pathlib import Path
from typing import Any, Type

from django.db.models import Model, signals
from django.dispatch import receiver

from .models import SINANChunkedUpload


@receiver(signals.pre_delete, sender=SINANChunkedUpload)
def delete_sinan_file_on_delete(
    sender: Type[Model], instance: SINANChunkedUpload, **kwargs: Any
) -> None:
    try:
        Path(instance.file.path).unlink(missing_ok=True)
    except ValueError:
        pass
