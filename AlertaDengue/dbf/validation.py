import os
import struct
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

import dbfread
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from dbf.utils import expected_fields, synonyms, expected_date_fields


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
            raise ValidationError(
                {"filename": _("Este arquivo não parece um DBF válido ")}
            )

        for field in dbf.fields:
            if field.name in expected_date_fields and field.type != 'D':
                raise ValidationError(
                    {
                        "__all__": _(
                            "Espera-se que o campo {} seja "
                            "do tipo 'D' (data), mas o tipo do campo neste "
                            "arquivo é '{}'.".format(field.name, field.type)
                        )
                    }
                )

        for field in expected_fields:
            if field not in dbf.field_names:
                synonyms_for_this_field = synonyms.get(field, [])
                if not any(
                    s in dbf.field_names for s in synonyms_for_this_field
                ):
                    raise ValidationError(
                        {
                            "__all__": _(
                                "Este arquivo "
                                "não contém {}, que é esperado em um arquivo "
                                "válido do SINAN.".format(field)
                            )
                        }
                    )

        return True
