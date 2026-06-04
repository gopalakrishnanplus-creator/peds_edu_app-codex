from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from pe_migration.models import MigrationExceptionV2, SourceMigrationBatchV2
from pe_migration.services import SYSTEM_NAME, db_name, to_json
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Stage the InClinic mismatch spreadsheet as non-official reconciliation exceptions. "
        "This does not populate PE rep credit or share attribution."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="/Users/inditech-tech/Desktop/raw_server1.campaign_campaignfieldrep (1) - mismatch data.csv",
            help="CSV with headers ID, mail, doctor.",
        )
        parser.add_argument("--database", default="default")
        parser.add_argument("--batch-id", default="")
        parser.add_argument("--created-by", default="codex")

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        batch_id = options["batch_id"] or f"pe-inclinic-stage-{timezone.now():%Y%m%d%H%M%S}"
        database = options["database"]
        SourceMigrationBatchV2.objects.using(database).update_or_create(
            migration_batch_id=batch_id,
            defaults={
                "system_name": SYSTEM_NAME,
                "database_name": db_name(database),
                "started_at": timezone.now(),
                "completed_at": timezone.now(),
                "status": "staged_non_official",
                "input_file_names": to_json([str(path)]),
                "created_by": options["created_by"],
                "notes": (
                    "InClinic mismatch sheet staged only for RFA/Master roster reconciliation. "
                    "Rows are not official PE rep credit and are not PE share events."
                ),
            },
        )

        count = 0
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            expected = {"ID", "mail", "doctor"}
            if set(reader.fieldnames or []) != expected:
                raise CommandError(f"Expected headers {sorted(expected)}, got {reader.fieldnames}")
            for row in reader:
                source_pk = str(row.get("ID") or "").strip()
                MigrationExceptionV2.objects.using(database).create(
                    migration_batch_id=batch_id,
                    system_name=SYSTEM_NAME,
                    database_name=db_name(database),
                    source_table="raw_server1.campaign_campaignfieldrep_mismatch_csv",
                    source_pk_column="ID",
                    source_pk_value=source_pk,
                    entity_type="inclinic_mismatch",
                    issue_code="PE_INCLINIC_MISMATCH_STAGED_NOT_OFFICIAL",
                    issue_details=to_json(
                        {
                            "reason": (
                                "PE must not apply InClinic legacy aliases directly. "
                                "Resolve through RFA/Master roster bridge first."
                            )
                        }
                    ),
                    raw_payload_json=to_json(row),
                    resolution_status="open",
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Staged {count} InClinic mismatch rows as non-official exceptions."))
