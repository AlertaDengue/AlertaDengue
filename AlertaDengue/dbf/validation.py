from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

import dbfread
import struct

expected_fields = [
    u'NU_ANO',
    u'ID_MUNICIP',
    u'NM_BAIRRO',
    u'ID_BAIRRO',
    u'ID_AGRAVO',
    u'DT_SIN_PRI',
    u'SEM_PRI',
    u'DT_NOTIFIC',
    u'NU_NOTIFIC',
    u'SEM_NOT',
    u'DT_DIGITA',
    u'DT_NASC',
    u'NU_IDADE_N',
    u'CS_SEXO'
]

def is_valid_dbf(dbf_file):
    try:
        dbf = dbfread.DBF(dbf_file.path)
    except struct.error:
        raise ValidationError({"file": _("This file does not look like a valid "
            "DBF file")})

    for field in expected_fields:
        if field not in dbf.field_names:
            raise ValidationError({"file": _("This file does not contain {}, "
                "which is expected to be present in a valid SINAN "
                "file".format(field))})

    return True
