from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from celery import shared_task

from dbf.models import DBF
from dbf.sinan import Sinan


def send_success_email(dbf):
    subject = "[InfoDengue] DBF enviado em {:%d/%m/%Y} importado com successo".format(
            dbf.uploaded_at)
    body = render_to_string("successful_import_email.txt",
            context={"dbf": dbf})

    send_mail(subject, body, settings.EMAIL_FROM_ADDRESS,
                [dbf.uploaded_by.email])

def send_failure_email(dbf, message):
    subject = "[InfoDengue] Falha ao importar DBF enviado em {:%d/%m/%Y}".format(
            dbf.uploaded_at)
    body = render_to_string("failed_import_email.txt",
            context={"dbf": dbf, "error_message": message})

    send_mail(subject, body, settings.EMAIL_FROM_ADDRESS,
                [dbf.uploaded_by.email])


@shared_task
def import_dbf_to_database(dbf_id):
    dbf = DBF.objects.get(id=dbf_id)
    try:
        # Unfortunately dbfread does not allow us to use a file object. We
        # have to give it a file path and it will read from the disc.
        sinan = Sinan(dbf.file.path, dbf.notification_year)
        sinan.save_to_pgsql()
        send_success_email(dbf)
    except ValidationError as exc:
        send_failure_email(dbf, exc.message)
