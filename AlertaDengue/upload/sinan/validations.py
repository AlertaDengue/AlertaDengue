import os
from pathlib import Path
from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from upload.sinan.utils import REQUIRED_FIELDS


def validate_file_exists(file_path: str) -> None:
    if not os.path.exists(str(file_path)):
        raise ValidationError(_(f'File {str(file_path)} not found'))


def validate_file_type(file_name: str) -> None:
    file_path = Path(str(file_name))

    if file_path.suffix.lower() not in [".csv", ".dbf"]:
        raise ValidationError(_(f"Unknown file suffix {file_path.suffix}"))


def validate_misparsed_file_exists(file_path: str) -> None:
    if file_path:
        if not os.path.exists(str(file_path)):
            raise ValidationError(_(f'File {str(file_path)} not found'))


def validate_misparsed_file_name(file_path: str) -> None:
    if file_path:
        fpath = Path(str(file_path))

        if not fpath.name.startswith("MISPARSED_"):
            raise ValidationError(_(
                f"Misparsed file name {fpath.name} doesn't start with MISPARSED_"
            ))


def validate_year(year: int) -> None:
    if year > datetime.now().year:
        raise ValidationError(_(f"Invalid year {year}"))

    if year < 1970:
        raise ValidationError(_(f"Invalid year {year}"))


def validate_fields(columns: list[str]) -> None:
    if not all([c in columns for c in REQUIRED_FIELDS]):
        raise ValidationError(
            "Required field(s): "
            f"{list(set(REQUIRED_FIELDS).difference(set(columns)))} "
            "not found in data file"
        )
