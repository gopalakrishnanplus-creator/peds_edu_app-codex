from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from pe_migration.services import exception_report, to_json, validation_report


class Command(BaseCommand):
    help = "Validate PE v2 reporting gates and write validation/exception reports."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default", help="Django database alias to validate.")
        parser.add_argument("--report-dir", default="output", help="Directory for JSON reports.")

    def handle(self, *args, **options):
        report_dir = Path(options["report_dir"])
        report_dir.mkdir(parents=True, exist_ok=True)
        validation = validation_report(options["database"])
        exceptions = exception_report(options["database"])
        validation_path = report_dir / "pe_v2_validation_report_latest.json"
        exception_path = report_dir / "pe_v2_exception_report_latest.json"
        validation_path.write_text(to_json(validation), encoding="utf-8")
        exception_path.write_text(to_json(exceptions), encoding="utf-8")
        style = self.style.SUCCESS if validation["passed"] else self.style.WARNING
        self.stdout.write(style(f"PE v2 validation passed={validation['passed']}"))
        self.stdout.write(f"Validation report: {validation_path}")
        self.stdout.write(f"Exception report: {exception_path}")
