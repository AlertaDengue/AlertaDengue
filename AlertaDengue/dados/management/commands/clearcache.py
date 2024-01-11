from django.conf import settings
from django.core.cache import caches
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clear cache"

    def handle(self, **options):
        for k in settings.CACHES.keys():
            caches[k].clear()
            self.stdout.write("Cleared cache '{}'.\n".format(k))
