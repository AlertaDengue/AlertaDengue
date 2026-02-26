from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

# Sort key: ES before BR, then ascending by sem_not_max.
_COUNTRY_ORDER = {"es": 0, "br": 1}


def _sort_key(entry: dict[str, Any]) -> tuple[int, int]:
    """Sort manifest entries: ES before BR, earlier epiweeks first."""
    country = str(entry.get("country", "zz")).lower()
    sem = int(entry.get("sem_not_max", 0))
    return (_COUNTRY_ORDER.get(country, 99), sem)


class Command(BaseCommand):
    help = "Read a mover manifest and enqueue runs in priority order."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--manifest",
            required=True,
            type=str,
            help="Path to the JSON manifest from mover_sinan_data.py.",
        )
        parser.add_argument(
            "--host-base",
            type=str,
            default="",
            help="Host-side base path (for path translation).",
        )
        parser.add_argument(
            "--worker-base",
            type=str,
            default="",
            help="Worker-side base path (for path translation).",
        )
        parser.add_argument(
            "--requeue",
            action="store_true",
            help="Re-enqueue even if run already exists.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the sorted enqueue plan without enqueuing.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        manifest_path = Path(options["manifest"]).expanduser()
        if not manifest_path.exists():
            raise CommandError(f"Manifest not found: {manifest_path}")

        try:
            entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise CommandError(f"Failed to read manifest: {exc}") from exc

        if not isinstance(entries, list):
            raise CommandError("Manifest is not a JSON list.")

        if not entries:
            self.stdout.write(
                self.style.WARNING(f"Manifest is empty: {manifest_path}")
            )
            return

        entries.sort(key=_sort_key)

        host_base = str(options["host_base"]).strip()
        worker_base = str(options["worker_base"]).strip()
        requeue = bool(options["requeue"])
        dry_run = bool(options["dry_run"])

        self.stdout.write(
            f"Manifest: {len(entries)} entries from {manifest_path}"
        )

        enqueued = 0
        failed = 0

        for i, entry in enumerate(entries, 1):
            dest = entry.get("dest", "")
            country = entry.get("country", "??")
            disease = entry.get("disease", "")
            year = entry.get("year", 0)
            week = entry.get("week", 0)
            uf = entry.get("uf", country).upper()

            label = (
                f"[{i}/{len(entries)}] {country}/{disease} {year}w{week:02d}"
            )

            if dry_run:
                self.stdout.write(f"DRY-RUN: {label} -> {dest}")
                continue

            if not dest:
                self.stderr.write(f"SKIP: {label} — missing dest")
                failed += 1
                continue

            try:
                cmd_args = [
                    dest,
                    "--uf",
                    uf if len(uf) == 2 else country.upper(),
                    "--disease",
                    disease,
                    "--year",
                    str(year),
                    "--week",
                    str(week),
                ]
                if host_base:
                    cmd_args.extend(["--host-base", host_base])
                if worker_base:
                    cmd_args.extend(["--worker-base", worker_base])
                if requeue:
                    cmd_args.append("--requeue")

                call_command("ingestion_enqueue_sinan", *cmd_args)
                enqueued += 1
                self.stdout.write(self.style.SUCCESS(f"OK: {label}"))

            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"FAIL: {label} — {exc}"))

        if not dry_run:
            self.stdout.write(f"DONE: enqueued={enqueued} failed={failed}")
