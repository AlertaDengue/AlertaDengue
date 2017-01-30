from django.core.exceptions import ValidationError
from celery import shared_task

from dbf.models import DBF
from dbf.sinan import Sinan

@shared_task
def import_dbf_to_database(dbf_id):
    dbf = DBF.objects.get(id=dbf_id)
    try:
        # Unfortunately dbfread does not allow us to use a file object. We
        # have to give it a file path and it will read from the disc.
        sinan = Sinan(dbf.file.path, dbf.notification_year)
        sinan.save_to_pgsql()
    except ValidationError as exc:
        error_message = exc.message
        print(error_message)
