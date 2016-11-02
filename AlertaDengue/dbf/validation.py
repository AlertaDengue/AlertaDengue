from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from contextlib import contextmanager
import datetime
import os
import struct
from tempfile import NamedTemporaryFile

import dbfread

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

@contextmanager
def get_namedtempfile_from_data(data):
    tempfile = NamedTemporaryFile(delete=False)
    tempfile.write(data)
    tempfile.seek(0)
    tempfile.close()
    try:
        yield tempfile.name
    finally:
        os.unlink(tempfile.name)


def is_valid_dbf(dbf_file, notification_year):
    with get_namedtempfile_from_data(dbf_file.read()) as tempfilename:
        try:
            dbf = dbfread.DBF(tempfilename, encoding="iso-8859-1")
        except struct.error:
            raise ValidationError({"filename": _("This file does not look like a valid "
                "DBF file")})


        for field in expected_fields:
            if field not in dbf.field_names:
                raise ValidationError({"filename": _("This file does not contain {}, "
                    "which is expected to be present in a valid SINAN "
                    "file".format(field))})

        if any((record['DT_NOTIFIC'].year != notification_year for record in dbf.records)):
            raise ValidationError( _("There are notifications in this file "
                "incompatible with the informed notification year. "
                "Make sure this notification year is the same for all the "
                "records in the file."))

        return True
