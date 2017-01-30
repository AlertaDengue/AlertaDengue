#!/usr/bin/env python3
from django.core.management.base import BaseCommand, CommandError

from dbf.sinan import Sinan

class Command(BaseCommand):
    help = "Imports SINAN DBF into the database"

    def add_arguments(self, parser):
        parser.add_argument("filename")
        parser.add_argument("ano", type=int)

    def handle(self, *args, **options):
        try:
            sinan = Sinan(options["filename"], options["ano"])
            sinan.save_to_pgsql()
        except ValidationError as e:
            raise CommandError("Arquivo inválido: {}".format(e.message))
