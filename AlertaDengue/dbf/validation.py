from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

import dbfread
import struct

def is_valid_dbf(dbf_file):
    try:
        dbfread.DBF(dbf_file.path)
    except struct.error:
        raise ValidationError({"file": _("This file does not look like a valid "
            "DBF file")})
    return True
