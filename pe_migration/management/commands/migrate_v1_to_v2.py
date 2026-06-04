from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from pe_migration.runtime import activate_v2_tables
from pe_migration.services import PeV2Backfill, db_name
from pe_migration.v1_to_v2_audit import audit_v1_to_v2_batch


class Command(BaseCommand):
    help = "Safely migrate PE V1 source tables into PE V2 tables with audit reports and validation."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default", help="Django database alias for the PE database.")
        parser.add_argument("--master-database", default="master", help="Django database alias for RFA / Master.")
        parser.add_argument("--raw-master-schema", default="raw_pe_master", help="Fallback raw Master staging schema.")
        parser.add_argument("--batch-id", default="", help="Stable migration batch id. Defaults to pe-v1-to-v2-YYYYMMDDHHMMSS.")
        parser.add_argument("--created-by", default="codex", help="Operator recorded on source_migration_batch_v2.")
        parser.add_argument("--notes", default="", help="Optional notes for the migration batch.")
        parser.add_argument(
            "--report-dir",
            default="output/pe_v1_to_v2_migration",
            help="Directory for CSV, TXT, and validation reports.",
        )
        parser.add_argument("--progress-interval", type=int, default=500, help="Progress update interval per table.")
        parser.add_argument(
            "--no-activate-v2",
            action="store_true",
            help="Run and validate migration but do not write the runtime V2 switch marker.",
        )

    def handle(self, *args, **options):
        batch_id = options["batch_id"] or f"pe-v1-to-v2-{timezone.now():%Y%m%d%H%M%S}"
        database_alias = options["database"]
        report_dir = Path(options["report_dir"]) / batch_id
        report_dir.mkdir(parents=True, exist_ok=True)
        notes = options["notes"] or "Full audited V1 to V2 migration."

        self.stdout.write(f"Starting PE V1 -> V2 migration batch {batch_id}")
        self.stdout.write(f"PE database: {db_name(database_alias)}")
        self.stdout.write(f"Report directory: {report_dir}")

        with transaction.atomic(using=database_alias):
            backfill = PeV2Backfill(
                database_alias=database_alias,
                master_database_alias=options["master_database"],
                raw_master_schema=options["raw_master_schema"],
                batch_id=batch_id,
                created_by=options["created_by"],
                input_file_names=[],
                notes=notes,
            )
            counts = backfill.run()
            self.stdout.write(self.style.SUCCESS("Backfill phase completed."))
            for key in sorted(counts):
                self.stdout.write(f"{key}: {counts[key]}")

            audit = audit_v1_to_v2_batch(
                database_alias=database_alias,
                batch_id=batch_id,
                report_dir=report_dir,
                progress_callback=self.stdout.write,
                progress_interval=options["progress_interval"],
            )
            if not audit.passed:
                transaction.set_rollback(True, using=database_alias)
                raise CommandError(
                    "V1 -> V2 validation failed. V2 writes for this batch were rolled back. "
                    f"Failure report: {audit.failure_csv}"
                )

        switch_path = ""
        if not options["no_activate_v2"]:
            switch_path = str(
                activate_v2_tables(
                    batch_id=batch_id,
                    database_name=db_name(database_alias),
                    report_dir=str(report_dir),
                    activated_by=options["created_by"],
                )
            )

        self.stdout.write(self.style.SUCCESS("PE V1 -> V2 migration completed successfully."))
        self.stdout.write(f"Success CSV: {audit.success_csv}")
        self.stdout.write(f"Failure CSV: {audit.failure_csv}")
        self.stdout.write(f"Success log: {audit.success_log}")
        self.stdout.write(f"Failure log: {audit.failure_log}")
        self.stdout.write(f"Validation report: {audit.validation_report_path}")
        if switch_path:
            self.stdout.write(self.style.SUCCESS(f"V2 runtime switch enabled: {switch_path}"))
        else:
            self.stdout.write(self.style.WARNING("V2 runtime switch was not enabled (--no-activate-v2)."))
