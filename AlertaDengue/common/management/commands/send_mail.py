from django.core.management.base import BaseCommand
from datetime import datetime

from common import mailing_partner


class Command(BaseCommand):
    help = '>>> Envia emails para as secretarias de saúde'

    def send_mail(self):
        mailing_partner.send_mail_partner()

    def handle(self, *args, **options):
        today = datetime.today()
        date_send = today.strftime("%d/%m/%Y")

        self.send_mail()
        self.stdout.write(
            self.style.SUCCESS(
                'Successfully send e-mail "{}"'.format(date_send)
            )
        )
