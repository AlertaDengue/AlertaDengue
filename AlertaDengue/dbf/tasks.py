from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string
from celery import shared_task

from .models import DBF
from .sinan import Sinan

import os
import shutil


def send_success_email(dbf):
    subject = ("[InfoDengue] DBF enviado em {:%d/%m/%Y} "
               "importado com successo".format(dbf.uploaded_at))
    body = render_to_string("successful_import_email.txt",
                            context={"dbf": dbf})

    message_data = (
        (subject, body, settings.EMAIL_FROM_ADDRESS,
         [dbf.uploaded_by.email]),
        (subject, body, settings.EMAIL_FROM_ADDRESS,
         [settings.INFODENGUE_TEAM_EMAIL])
    )
    send_mass_mail(message_data)


def send_failure_email(dbf, message):
    subject = ("[InfoDengue] Falha ao importar DBF enviado em "
               "{:%d/%m/%Y}".format(dbf.uploaded_at))
    body = render_to_string("failed_import_email.txt",
                            context={"dbf": dbf, "error_message": message})

    message_data = (
        (subject, body, settings.EMAIL_FROM_ADDRESS,
         [dbf.uploaded_by.email]),
        (subject, body, settings.EMAIL_FROM_ADDRESS,
         [settings.INFODENGUE_TEAM_EMAIL])
    )
    send_mass_mail(message_data)


def copy_file_to_final_destination(dbf):
    new_filename = "{}_{}_{}_{}.dbf".format(dbf.state_abbreviation,
                                            dbf.municipio,
                                            dbf.export_date,
                                            dbf.notification_year)
    src = dbf.file.path
    dest = os.path.join(settings.IMPORTED_FILES_DIR, new_filename)
    shutil.copy(src, dest)


@shared_task
def import_dbf_to_database(dbf_id):
    dbf = DBF.objects.get(id=dbf_id)
    try:
        # Unfortunately dbfread does not allow us to use a file object. We
        # have to give it a file path and it will read from the disc.
        sinan = Sinan(dbf.file.path, dbf.notification_year)
        sinan.save_to_pgsql()
        send_success_email(dbf)
        copy_file_to_final_destination(dbf)
    except ValidationError as exc:
        send_failure_email(dbf, exc.message)
