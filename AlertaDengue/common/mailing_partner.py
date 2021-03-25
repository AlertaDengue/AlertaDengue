import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# from django.core.mail import EmailMultiAlternatives
from datetime import datetime
import logging

from sqlalchemy import create_engine
from ad_main import settings

import datetime as dt
from dados.episem import episem
from dotenv import load_dotenv
from os.path import join, dirname

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


dt_now = dt.datetime.now()
year_week = episem(dt_now, sep='')
year, week = year_week[:4], year_week[-2:]


def get_partner_active():
    """
    :return: dict
    """
    sql = '''
      SELECT name, contact FROM common_requestpartnerdata
      WHERE status = 'True'
      ORDER BY name
    '''

    with db_engine.connect() as conn:
        return dict(conn.execute(sql).fetchall())


def send_mail_partner():
    mail_host = os.getenv("MAIL_HOST")
    mail_port = os.getenv("MAIL_PORT")
    mail_sender = os.getenv("MAIL_FROM")
    mail_password = os.getenv("MAIL_PASSWORD")

    message = MIMEMultipart("alternative")
    message["Subject"] = f'Informe de dados Infodengue SE{week}'

    text = f"""\
    Olá, bom dia, tudo bem?

    Vocês já possuem  os dados de dengue, chikungunya e Zika  da SE {week}?
    Se sim, poderiam nos enviar?
    Caso já tenha enviado , gentileza desconsiderar esse e-mail.

    Obrigada ,
    Atenciosamente;
    """

    # html = ""
    to_text = MIMEText(text, "plain")
    # to_html = MIMEText(html, "html")
    message.attach(to_text)
    # message.attach(to_html)

    mailing = get_partner_active()
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(mail_host, mail_port, context=context) as server:
        server.login(mail_sender, mail_password)
        for to_name, to_addrs in mailing.items():
            server.sendmail(mail_sender, to_addrs, message.as_string())
            logging.info(f"e-mail enviado para: {to_name}")
