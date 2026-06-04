from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from pe_migration.services import PeV2Backfill, exception_report, to_json, validation_report


class Command(BaseCommand):
    help = "Backfill PE v2 identity/reporting tables without modifying legacy source tables."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default", help="Django database alias to write v2 tables into.")
        parser.add_argument(
            "--master-database",
            default="master",
            help="Django database alias for the live RFA / Master identity database.",
        )
        parser.add_argument("--raw-master-schema", default="raw_pe_master", help="Schema containing raw_pe_master extract tables.")
        parser.add_argument("--batch-id", default="", help="Stable migration batch id. Defaults to pe-YYYYMMDDHHMMSS.")
        parser.add_argument("--created-by", default="codex", help="Operator/source recorded on source_migration_batch_v2.")
        parser.add_argument("--input-file", action="append", default=[], help="Input file name to record on the batch.")
        parser.add_argument("--notes", default="", help="Optional migration batch notes.")
        parser.add_argument(
            "--report-dir",
            default="output",
            help="Directory for validation and exception JSON reports.",
        )

    def handle(self, *args, **options):
        backfill = PeV2Backfill(
            database_alias=options["database"],
            master_database_alias=options["master_database"],
            raw_master_schema=options["raw_master_schema"],
            batch_id=options["batch_id"] or None,
            created_by=options["created_by"],
            input_file_names=options["input_file"],
            notes=options["notes"],
        )
        counts = backfill.run()
        report_dir = Path(options["report_dir"])
        report_dir.mkdir(parents=True, exist_ok=True)
        validation_path = report_dir / f"pe_v2_validation_report_{backfill.batch_id}.json"
        exception_path = report_dir / f"pe_v2_exception_report_{backfill.batch_id}.json"
        validation_path.write_text(to_json(validation_report(options["database"])), encoding="utf-8")
        exception_path.write_text(to_json(exception_report(options["database"])), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"PE v2 backfill completed: {backfill.batch_id}"))
        for key in sorted(counts):
            self.stdout.write(f"{key}: {counts[key]}")
        self.stdout.write(f"Validation report: {validation_path}")
        self.stdout.write(f"Exception report: {exception_path}")
