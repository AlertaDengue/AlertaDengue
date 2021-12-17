from django.core.management.base import BaseCommand
from datetime import datetime

from dbf.tasks import send_mail_partner


class Command(BaseCommand):
    help = '>>> Envia emails para as secretarias de saúde'

    def send_email(self):
        send_mail_partner()

    def handle(self, *args, **options):
        today = datetime.today()
        date_send = today.strftime("%d/%m/%Y")

        self.send_email()
        self.stdout.write(
            self.style.SUCCESS(
                'Successfully sent emails on "{}"!'.format(date_send)
            )
        )
