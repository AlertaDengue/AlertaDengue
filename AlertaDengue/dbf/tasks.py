import logging
import os
import shutil
from datetime import datetime
from email.mime.image import MIMEImage

from celery import shared_task
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from ad_main import settings
from dados.episem import episem
from dbf.db import is_partner_active

from .models import DBF
from .sinan import Sinan


class MissingConnectionException(Exception):
    pass


def get_connection(label=None, **kwargs):
    if label is None:
        label = getattr(settings, 'EMAIL_CONNECTION_DEFAULT', None)

    try:
        connections = getattr(settings, 'EMAIL_CONNECTIONS')
        options = connections[label]
    except KeyError:
        raise MissingConnectionException(
            'Settings for connection "%s" were not found' % label
        )

    options.update(kwargs)
    return mail.get_connection(**options)


def send_success_email(dbf):
    connection = get_connection()
    messages = []

    subject = (
        "[InfoDengue] DBF enviado em {:%d/%m/%Y} "
        "importado com successo".format(dbf.uploaded_at)
    )
    body = render_to_string(
        "successful_import_email.txt", context={"dbf": dbf}
    )

    message = EmailMultiAlternatives(
        subject, body, settings.EMAIL_HOST_USER, [settings.EMAIL_TO_ADDRESS]
    )

    messages.append(message)

    return connection.send_messages(messages)


def send_failure_email(dbf, message):
    connection = get_connection()
    messages = []

    subject = (
        "[InfoDengue] Falha ao importar DBF enviado em "
        "{:%d/%m/%Y}".format(dbf.uploaded_at)
    )
    body = render_to_string(
        "failed_import_email.txt",
        context={"dbf": dbf, "error_message": message},
    )

    message = EmailMultiAlternatives(
        subject, body, settings.EMAIL_HOST_USER, [settings.EMAIL_TO_ADDRESS]
    )

    messages.append(message)

    return connection.send_messages(messages)


def copy_file_to_final_destination(dbf):
    new_filename = "{}_{}_{}_{}.dbf".format(
        dbf.abbreviation,
        dbf.municipio,
        dbf.export_date,
        dbf.notification_year,
    )
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


def send_mail_partner(
    fail_silently=False, connection=None,
):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), send
    each message to each recipient list. Return the number of emails sent.
    """
    mailing = is_partner_active()
    connection = get_connection()

    messages = []

    dt_now = datetime.now().strftime('%Y-%m-%d')
    year_week = episem(dt_now, sep='')
    week = year_week[-2:]
    last_week = int(week) - 1

    for idx, row in mailing.iterrows():
        subject = f'Informe de dados Infodengue SE{last_week}'
        body = render_to_string(
            "email_secretarias.txt",
            context={"name": row['contact'], "context_message": last_week},
        )
        message = EmailMultiAlternatives(
            subject, body, settings.EMAIL_HOST_USER, [row['email']]
        )
        logging.info(f"Enviando email para: {row['email']},")
        # message.attach_alternative(html, 'text/html')
        fp = open(
            os.path.join(
                settings.STATICFILES_DIRS[0], 'img/logo_signature.png'
            ),
            'rb',
        )
        msg_img = MIMEImage(fp.read())
        fp.close()
        # msg_img.add_header('Content-ID', '<{}>'.format("logo_signature.png"))
        message.attach(msg_img)
        messages.append(message)

    return connection.send_messages(messages)
