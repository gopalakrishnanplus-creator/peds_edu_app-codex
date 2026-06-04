from __future__ import annotations

import csv
import json
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.db.models import Model
from django.utils import timezone

from accounts.models import Clinic, DoctorProfile
from catalog.models import (
    TherapyArea,
    Trigger,
    TriggerCluster,
    Video,
    VideoCluster,
    VideoClusterLanguage,
    VideoClusterVideo,
    VideoLanguage,
    VideoTriggerMap,
)
from publisher.models import Campaign
from sharing.models import DoctorShareSummary, ShareActivity, ShareBannerClickEvent, SharePlaybackEvent

from .models import (
    PeBannerClickEventV2,
    PeCampaignV2,
    PeClinicV2,
    PeContentItemV2,
    PeDoctorShareSummaryV2,
    PeDoctorV2,
    PePlaybackEventV2,
    PeShareEventV2,
)
from .services import db_name, model_payload, to_json, validation_report


@dataclass(frozen=True)
class TableMapping:
    source_table: str
    source_model: type[Model]
    destination_table: str
    destination_model: type[Model]
    source_pk_column: str = "id"


@dataclass
class AuditResult:
    passed: bool
    started_at: str
    ended_at: str
    duration_seconds: float
    total_source_records: int
    total_migrated_records: int
    total_failed_records: int
    table_results: list[dict[str, Any]]
    success_csv: str
    failure_csv: str
    success_log: str
    failure_log: str
    validation_report_path: str
    validation: dict[str, Any]


TABLE_MAPPINGS: list[TableMapping] = [
    TableMapping("publisher_campaign", Campaign, "pe_campaign_v2", PeCampaignV2),
    TableMapping("accounts_clinic", Clinic, "pe_clinic_v2", PeClinicV2),
    TableMapping("accounts_doctorprofile", DoctorProfile, "pe_doctor_v2", PeDoctorV2),
    TableMapping("catalog_therapyarea", TherapyArea, "pe_content_item_v2", PeContentItemV2),
    TableMapping("catalog_triggercluster", TriggerCluster, "pe_content_item_v2", PeContentItemV2),
    TableMapping("catalog_trigger", Trigger, "pe_content_item_v2", PeContentItemV2),
    TableMapping("catalog_video", Video, "pe_content_item_v2", PeContentItemV2),
    TableMapping("catalog_videocluster", VideoCluster, "pe_content_item_v2", PeContentItemV2),
    TableMapping("catalog_videoclustervideo", VideoClusterVideo, "pe_content_item_v2", PeContentItemV2),
    TableMapping("catalog_videolanguage", VideoLanguage, "pe_content_item_v2", PeContentItemV2),
    TableMapping("catalog_videoclusterlanguage", VideoClusterLanguage, "pe_content_item_v2", PeContentItemV2),
    TableMapping("catalog_videotriggermap", VideoTriggerMap, "pe_content_item_v2", PeContentItemV2),
    TableMapping("sharing_doctorsharesummary", DoctorShareSummary, "pe_doctor_share_summary_v2", PeDoctorShareSummaryV2),
    TableMapping("sharing_shareactivity", ShareActivity, "pe_share_event_v2", PeShareEventV2),
    TableMapping("sharing_shareplaybackevent", SharePlaybackEvent, "pe_playback_event_v2", PePlaybackEventV2),
    TableMapping("sharing_sharebannerclickevent", ShareBannerClickEvent, "pe_banner_click_event_v2", PeBannerClickEventV2),
]


SUCCESS_FIELDS = [
    "migration_batch_id",
    "source_table",
    "destination_table",
    "source_pk_column",
    "source_pk_value",
    "destination_pk",
    "verification_status",
    "verification_basis",
    "is_current",
    "validation_status",
    "message",
]

FAILURE_FIELDS = [
    "migration_batch_id",
    "source_table",
    "destination_table",
    "source_pk_column",
    "source_pk_value",
    "failure_type",
    "failure_reason",
    "traceback",
]


def audit_v1_to_v2_batch(
    *,
    database_alias: str,
    batch_id: str,
    report_dir: Path,
    progress_callback: Any | None = None,
    progress_interval: int = 500,
) -> AuditResult:
    started = timezone.now()
    monotonic_start = time.monotonic()
    report_dir.mkdir(parents=True, exist_ok=True)

    success_csv = report_dir / f"v1_to_v2_success_{batch_id}.csv"
    failure_csv = report_dir / f"v1_to_v2_failures_{batch_id}.csv"
    success_log = report_dir / f"v1_to_v2_success_{batch_id}.txt"
    failure_log = report_dir / f"v1_to_v2_failures_{batch_id}.txt"
    validation_path = report_dir / f"v1_to_v2_validation_{batch_id}.json"

    success_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    success_log_lines = [
        f"PE V1 to V2 migration audit started at {started.isoformat()}",
        f"Database alias: {database_alias}",
        f"Database name: {db_name(database_alias)}",
        f"Migration batch: {batch_id}",
        "",
    ]
    failure_log_lines = [
        f"PE V1 to V2 migration failure log started at {started.isoformat()}",
        f"Database alias: {database_alias}",
        f"Database name: {db_name(database_alias)}",
        f"Migration batch: {batch_id}",
        "",
    ]

    total_source = 0
    total_migrated = 0
    total_failed = 0
    table_results: list[dict[str, Any]] = []

    for mapping in TABLE_MAPPINGS:
        table_started = timezone.now()
        source_qs = mapping.source_model.objects.using(database_alias).all().order_by("pk")
        source_count = source_qs.count()
        migrated_count = mapping.destination_model.objects.using(database_alias).filter(
            migration_batch_id=batch_id,
            source_table=mapping.source_table,
        ).count()
        table_success = 0
        table_failed = 0
        total_source += source_count
        total_migrated += migrated_count

        if migrated_count != source_count:
            reason = f"Record count mismatch: source={source_count}, destination_batch={migrated_count}"
            failure_rows.append(
                {
                    "migration_batch_id": batch_id,
                    "source_table": mapping.source_table,
                    "destination_table": mapping.destination_table,
                    "source_pk_column": "*",
                    "source_pk_value": "*",
                    "failure_type": "count_mismatch",
                    "failure_reason": reason,
                    "traceback": "",
                }
            )
            failure_log_lines.append(f"[COUNT MISMATCH] {mapping.source_table} -> {mapping.destination_table}: {reason}")
            table_failed += 1

        for index, source_obj in enumerate(source_qs.iterator(), start=1):
            source_pk_value = str(source_obj.pk)
            try:
                destination_rows = list(
                    mapping.destination_model.objects.using(database_alias).filter(
                        migration_batch_id=batch_id,
                        source_table=mapping.source_table,
                        source_pk_value=source_pk_value,
                    )
                )
                if len(destination_rows) != 1:
                    raise ValueError(
                        f"Expected exactly one destination row for {mapping.source_table}.{source_pk_value}; "
                        f"found {len(destination_rows)}"
                    )

                destination = destination_rows[0]
                source_payload = json.loads(to_json(model_payload(source_obj)))
                destination_payload = json.loads(destination.raw_payload_json or "{}")
                mismatches = payload_mismatches(source_payload, destination_payload)
                if mismatches:
                    raise ValueError("; ".join(mismatches[:20]))

                destination_pk = getattr(destination, destination._meta.pk.name)
                success_rows.append(
                    {
                        "migration_batch_id": batch_id,
                        "source_table": mapping.source_table,
                        "destination_table": mapping.destination_table,
                        "source_pk_column": mapping.source_pk_column,
                        "source_pk_value": source_pk_value,
                        "destination_pk": destination_pk,
                        "verification_status": destination.verification_status,
                        "verification_basis": destination.verification_basis,
                        "is_current": destination.is_current,
                        "validation_status": "matched",
                        "message": "Source raw payload matches destination raw_payload_json",
                    }
                )
                table_success += 1
            except Exception as exc:
                tb = traceback.format_exc()
                failure_rows.append(
                    {
                        "migration_batch_id": batch_id,
                        "source_table": mapping.source_table,
                        "destination_table": mapping.destination_table,
                        "source_pk_column": mapping.source_pk_column,
                        "source_pk_value": source_pk_value,
                        "failure_type": type(exc).__name__,
                        "failure_reason": str(exc),
                        "traceback": tb,
                    }
                )
                failure_log_lines.append(
                    f"[FAILED] {mapping.source_table}.{source_pk_value} -> {mapping.destination_table}: {type(exc).__name__}: {exc}"
                )
                failure_log_lines.append(tb)
                table_failed += 1

            if progress_callback and progress_interval > 0 and index % progress_interval == 0:
                progress_callback(
                    f"{mapping.source_table}: processed {index}/{source_count} records "
                    f"(success={table_success}, failed={table_failed})"
                )

        table_ended = timezone.now()
        total_failed += table_failed
        table_results.append(
            {
                "source_table": mapping.source_table,
                "destination_table": mapping.destination_table,
                "started_at": table_started.isoformat(),
                "ended_at": table_ended.isoformat(),
                "source_records": source_count,
                "destination_records_for_batch": migrated_count,
                "successful_records": table_success,
                "failed_records": table_failed,
                "validation_status": "PASS" if table_failed == 0 and migrated_count == source_count else "FAIL",
            }
        )
        success_log_lines.append(
            f"[{mapping.source_table} -> {mapping.destination_table}] "
            f"source={source_count} migrated={migrated_count} success={table_success} failed={table_failed}"
        )

    validation = validation_report(database_alias)
    ended = timezone.now()
    duration = time.monotonic() - monotonic_start
    passed = total_failed == 0 and all(row["validation_status"] == "PASS" for row in table_results)
    overall_result = "PASS" if passed and validation.get("passed") else "FAIL"

    final_report = {
        "migration_batch_id": batch_id,
        "database_name": db_name(database_alias),
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_seconds": round(duration, 3),
        "total_source_records": total_source,
        "total_migrated_records": total_migrated,
        "total_failed_records": total_failed,
        "validation_status": "PASS" if passed else "FAIL",
        "record_count_comparison_status": "PASS"
        if all(row["source_records"] == row["destination_records_for_batch"] for row in table_results)
        else "FAIL",
        "pe_v2_gate_validation_passed": bool(validation.get("passed")),
        "overall_migration_result": overall_result,
        "table_results": table_results,
        "pe_v2_validation": validation,
    }

    write_csv(success_csv, SUCCESS_FIELDS, success_rows)
    write_csv(failure_csv, FAILURE_FIELDS, failure_rows)
    validation_path.write_text(json.dumps(final_report, indent=2, sort_keys=True, default=str), encoding="utf-8")

    success_log_lines.extend(
        [
            "",
            f"Completed at: {ended.isoformat()}",
            f"Duration seconds: {duration:.3f}",
            f"Total source records: {total_source}",
            f"Total migrated records: {total_migrated}",
            f"Total failed records: {total_failed}",
            f"Validation status: {final_report['validation_status']}",
            f"PE v2 gate validation passed: {validation.get('passed')}",
            f"Overall migration result: {overall_result}",
            f"Success CSV: {success_csv}",
            f"Failure CSV: {failure_csv}",
            f"Validation report: {validation_path}",
        ]
    )
    if not failure_rows:
        failure_log_lines.append("No failed transfers recorded.")
    failure_log_lines.extend(
        [
            "",
            f"Completed at: {ended.isoformat()}",
            f"Total failed records: {total_failed}",
            f"Overall migration result: {overall_result}",
        ]
    )
    success_log.write_text("\n".join(success_log_lines) + "\n", encoding="utf-8")
    failure_log.write_text("\n".join(failure_log_lines) + "\n", encoding="utf-8")

    return AuditResult(
        passed=overall_result == "PASS",
        started_at=started.isoformat(),
        ended_at=ended.isoformat(),
        duration_seconds=duration,
        total_source_records=total_source,
        total_migrated_records=total_migrated,
        total_failed_records=total_failed,
        table_results=table_results,
        success_csv=str(success_csv),
        failure_csv=str(failure_csv),
        success_log=str(success_log),
        failure_log=str(failure_log),
        validation_report_path=str(validation_path),
        validation=final_report,
    )


def payload_mismatches(source_payload: dict[str, Any], destination_payload: dict[str, Any]) -> list[str]:
    mismatches = []
    for key, source_value in source_payload.items():
        destination_value = destination_payload.get(key)
        if normalize_payload_value(source_value) != normalize_payload_value(destination_value):
            mismatches.append(
                f"{key}: source={source_value!r} destination_raw_payload={destination_value!r}"
            )
    return mismatches


def normalize_payload_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
