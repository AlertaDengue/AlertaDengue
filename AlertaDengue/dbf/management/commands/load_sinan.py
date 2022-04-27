#!/usr/bin/env python3
from dbf.sinan import Sinan
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Imports SINAN DBF into the database"

    def add_arguments(self, parser):
        parser.add_argument("filename")
        parser.add_argument("ano", type=int)
        parser.add_argument("--default-cid", default=None)

    def handle(self, *args, **options):
        try:
            sinan = Sinan(options["filename"], options["ano"])
            sinan.save_to_pgsql(default_cid=options["default_cid"])
        except ValidationError as e:
            raise CommandError("Arquivo inválido: {}".format(e.message))
