import os
from dotenv import load_dotenv
from os.path import join, dirname
from datetime import datetime

from django.core.mail import EmailMultiAlternatives
from django.utils.module_loading import import_string
from django.template.loader import render_to_string

from sqlalchemy import create_engine
import logging

from ad_main import settings
from dados.episem import episem


env_file = os.environ.get('ENV_FILE', '.env')

dotenv_path = join(dirname(dirname(dirname(__file__))), env_file)
load_dotenv(dotenv_path)

PSQL_URI = "postgresql://{}:{}@{}:{}/{}".format(
    settings.PSQL_USER,
    settings.PSQL_PASSWORD,
    settings.PSQL_HOST,
    settings.PSQL_PORT,
    settings.PSQL_DBF,
)
db_engine = create_engine(PSQL_URI)

dt_now = datetime.now().strftime('%Y-%m-%d')
year_week = episem(dt_now, sep='')
year, week = year_week[:4], year_week[-2:]


def get_connection(backend=None, fail_silently=False, **kwds):
    """Load an email backend and return an instance of it.

    If backend is None (default), use settings.EMAIL_BACKEND.

    Both fail_silently and other keyword arguments are used in the
    constructor of the backend.
    """
    klass = import_string(backend or settings.EMAIL_BACKEND)
    return klass(fail_silently=fail_silently, **kwds)


def get_partner_active():
    """
    :return: dict
    """
    sql = '''
      SELECT name, contact FROM dbf_sendtoPartner
      WHERE status = 'True'
      ORDER BY name
    '''

    with db_engine.connect() as conn:
        return dict(conn.execute(sql).fetchall())


def send_email_partner(
    fail_silently=False, connection=None,
):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), send
    each message to each recipient list. Return the number of emails sent.

    If from_email is None, use the DEFAULT_FROM_EMAIL setting.
    If auth_user and auth_password are set, use them to log in.
    If auth_user is None, use the EMAIL_HOST_USER setting.
    If auth_password is None, use the EMAIL_HOST_PASSWORD setting.
    """

    mail_from = os.getenv("EMAIL_FROM_ADDRESS")
    mail_password = os.getenv("MAIL_PASSWORD")
    # mail_host = os.getenv('MAIL_HOST')
    mailing = get_partner_active()

    recipient = []
    for email in mailing.values():
        recipient.append(email)

    connection = connection or get_connection(
        username=mail_from,
        password=mail_password,
        # hostname=mail_host,
        fail_silently=fail_silently,
    )

    subject = f'Informe de dados Infodengue SE{week}'
    body = render_to_string(
        "email_secretarias.txt", context={"context_message": week},
    )

    messages = [
        EmailMultiAlternatives(
            subject, body, mail_from, recipient, connection=connection
        )
    ]

    # html_content = '<p>This is an <strong>important</strong> message.</p>'
    # messages.attach_alternative(html_content, "text/html")

    logging.info(f"Enviando email para: {recipient} em {dt_now}")

    return connection.send_messages(messages)
