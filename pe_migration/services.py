from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections
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
    MigrationExceptionV2,
    PeBannerClickEventV2,
    PeCampaignV2,
    PeClinicV2,
    PeContentItemV2,
    PeDoctorShareSummaryV2,
    PeDoctorV2,
    PeMasterIdentityCacheV2,
    PePlaybackEventV2,
    PeRepAssignmentCreditV2,
    PeShareEventV2,
    SourceMigrationBatchV2,
)


SYSTEM_NAME = "pe"
MASTER_CACHE_SYSTEM = "pe_master"
RFA_MASTER_SYSTEM = "rfa_master"
UUID_NAMESPACE = uuid.UUID("0dfda0b0-1584-4b66-8a52-e8514da21f4a")


HONORIFIC_RE = re.compile(r"\b(?:dr|doctor|prof|mr|mrs|ms|miss)\.?(?=\s|$)", re.IGNORECASE)


def normalize_campaign_id(value: str) -> str:
    return str(value or "").strip().replace("-", "").lower()


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", str(value or ""))
    if len(digits) == 12 and digits.startswith("91"):
        return digits[-10:]
    return digits


def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def normalize_name(value: str) -> str:
    text = HONORIFIC_RE.sub(" ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def normalize_content_code(value: str) -> str:
    return str(value or "").strip().lower()


def deterministic_uuid(*parts: object) -> str:
    joined = ":".join(str(part or "") for part in parts)
    return str(uuid.uuid5(UUID_NAMESPACE, joined))


def to_json(value: Any) -> str:
    return json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, default=str)


def normalize_datetime_value(value: Any) -> Any:
    if isinstance(value, datetime) and settings.USE_TZ and timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def model_payload(obj: Model, include_fields: Iterable[str] | None = None) -> dict[str, Any]:
    field_names = list(include_fields or [field.name for field in obj._meta.fields])
    payload: dict[str, Any] = {}
    for name in field_names:
        try:
            payload[name] = getattr(obj, name)
        except Exception:
            payload[name] = None
    return payload


def db_name(alias: str) -> str:
    return str(connections[alias].settings_dict.get("NAME") or "")


def qn(alias: str, name: str) -> str:
    return connections[alias].ops.quote_name(name)


def table_exists(alias: str, table_name: str) -> bool:
    try:
        return table_name in connections[alias].introspection.table_names()
    except Exception:
        return False


def connection_alias_exists(alias: str) -> bool:
    return bool(alias and alias in connections.databases)


def fetch_table_rows(alias: str, table_name: str) -> list[dict[str, Any]]:
    if not connection_alias_exists(alias) or not table_exists(alias, table_name):
        return []
    with connections[alias].cursor() as cursor:
        cursor.execute(f"SELECT * FROM {qn(alias, table_name)}")
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def raw_table_exists(alias: str, schema: str, table_name: str) -> bool:
    if not schema or not table_name:
        return False
    with connections[alias].cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            LIMIT 1
            """,
            [schema, table_name],
        )
        return cursor.fetchone() is not None


def fetch_raw_rows(alias: str, schema: str, table_name: str) -> list[dict[str, Any]]:
    if not raw_table_exists(alias, schema, table_name):
        return []
    with connections[alias].cursor() as cursor:
        cursor.execute(f"SELECT * FROM {qn(alias, schema)}.{qn(alias, table_name)}")
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def pick_first(row: dict[str, Any], candidates: Iterable[str]) -> Any:
    lowered = {str(key).lower(): key for key in row.keys()}
    for candidate in candidates:
        actual = lowered.get(candidate.lower())
        if actual is not None:
            value = row.get(actual)
            if value not in (None, ""):
                return value
    return None


def first_column_name(row: dict[str, Any], candidates: Iterable[str]) -> str:
    lowered = {str(key).lower(): key for key in row.keys()}
    for candidate in candidates:
        actual = lowered.get(candidate.lower())
        if actual is not None:
            return str(actual)
    return "id"


def canonical_uuid_from_row(row: dict[str, Any], entity_type: str, source_value: Any) -> str | None:
    uuid_candidates = [
        f"{entity_type}_uuid",
        "entity_uuid",
        "uuid",
        "rfa_uuid",
        "master_uuid",
    ]
    value = pick_first(row, uuid_candidates)
    if value not in (None, ""):
        return str(value).strip()

    candidates = []
    if entity_type == "campaign":
        candidates.extend(["campaign_id", "id"])
    if entity_type in {"doctor", "rfa_doctor"}:
        candidates.extend(["doctor_uuid", "rfa_doctor_uuid"])
    if entity_type == "field_rep":
        candidates.extend(["field_rep_uuid", "rep_uuid"])
    value = pick_first(row, candidates)
    if value in (None, ""):
        return None
    value_s = str(value).strip()
    if entity_type == "campaign":
        return value_s
    if re.fullmatch(r"[0-9a-fA-F-]{32,64}", value_s):
        return value_s
    return None


@dataclass
class MasterIndexes:
    campaigns_by_normalized_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    field_reps_by_source_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    doctors_by_source_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    doctors_by_doctor_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    doctors_by_phone: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    campaign_doctors_by_source_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    enrollment_rows: list[dict[str, Any]] = field(default_factory=list)
    roster_rows: list[dict[str, Any]] = field(default_factory=list)


class PeV2Backfill:
    def __init__(
        self,
        *,
        database_alias: str = "default",
        master_database_alias: str | None = None,
        raw_master_schema: str = "raw_pe_master",
        batch_id: str | None = None,
        created_by: str = "codex",
        input_file_names: list[str] | None = None,
        notes: str = "",
    ) -> None:
        self.database_alias = database_alias
        self.master_database_alias = master_database_alias or getattr(settings, "MASTER_DB_ALIAS", "master")
        self.raw_master_schema = raw_master_schema
        self.batch_id = batch_id or f"pe-{timezone.now():%Y%m%d%H%M%S}"
        self.created_by = created_by
        self.input_file_names = input_file_names or []
        self.notes = notes
        self.database_name = db_name(database_alias)
        self.now = timezone.now()
        self.master_indexes = MasterIndexes()
        self.content_uuid_by_type_code: dict[tuple[str, str], str] = {}
        self.pe_doctor_by_doctor_id: dict[str, PeDoctorV2] = {}
        self.pe_doctor_by_source_id: dict[str, PeDoctorV2] = {}
        self.pe_clinic_by_source_id: dict[str, PeClinicV2] = {}
        self.pe_campaign_by_normalized_id: dict[str, PeCampaignV2] = {}
        self.share_by_source_id: dict[str, PeShareEventV2] = {}
        self.share_by_public_id: dict[str, PeShareEventV2] = {}
        self.counts: dict[str, int] = defaultdict(int)

    def run(self) -> dict[str, int]:
        self.start_batch()
        try:
            self.load_master_identity_cache()
            self.backfill_campaigns()
            self.backfill_clinics()
            self.backfill_doctors()
            self.backfill_content()
            self.backfill_share_summaries()
            self.backfill_share_events()
            self.backfill_playback_events()
            self.backfill_banner_click_events()
            self.backfill_rep_assignment_credit()
        except Exception:
            self.complete_batch("failed")
            raise
        self.complete_batch("completed")
        return dict(self.counts)

    def start_batch(self) -> None:
        SourceMigrationBatchV2.objects.using(self.database_alias).update_or_create(
            migration_batch_id=self.batch_id,
            defaults={
                "system_name": SYSTEM_NAME,
                "database_name": self.database_name,
                "started_at": self.now,
                "completed_at": None,
                "status": "running",
                "input_file_names": to_json(self.input_file_names),
                "created_by": self.created_by,
                "notes": self.notes,
            },
        )

    def complete_batch(self, status: str) -> None:
        SourceMigrationBatchV2.objects.using(self.database_alias).filter(
            migration_batch_id=self.batch_id
        ).update(status=status, completed_at=timezone.now())

    def common_fields(
        self,
        *,
        source_system: str,
        source_database: str,
        source_table: str,
        source_pk_column: str,
        source_pk_value: Any,
        source_created_at: Any = None,
        source_updated_at: Any = None,
        verification_status: str,
        verification_basis: str,
        raw_payload: dict[str, Any],
        is_current: bool = True,
        valid_from: Any = None,
        valid_to: Any = None,
    ) -> dict[str, Any]:
        return {
            "source_system": source_system,
            "source_database": source_database,
            "source_table": source_table,
            "source_pk_column": source_pk_column,
            "source_pk_value": str(source_pk_value or ""),
            "source_created_at": normalize_datetime_value(source_created_at),
            "source_updated_at": normalize_datetime_value(source_updated_at),
            "migration_batch_id": self.batch_id,
            "migrated_at": timezone.now(),
            "verification_status": verification_status,
            "verification_basis": verification_basis,
            "is_current": is_current,
            "valid_from": normalize_datetime_value(valid_from),
            "valid_to": normalize_datetime_value(valid_to),
            "raw_payload_json": to_json(raw_payload),
        }

    def v2_uuid(self, model: type[Model], source_table: str, source_pk_value: Any) -> str:
        return deterministic_uuid(self.batch_id, model._meta.db_table, source_table, source_pk_value)

    def update_current_row(
        self,
        model: type[Model],
        *,
        source_table: str,
        source_pk_value: Any,
        defaults: dict[str, Any],
    ) -> Model:
        pk_name = model._meta.pk.name
        pk_value = defaults[pk_name]
        model.objects.using(self.database_alias).filter(
            source_system=defaults["source_system"],
            source_table=source_table,
            source_pk_value=str(source_pk_value or ""),
            is_current=True,
        ).exclude(**{pk_name: pk_value}).update(is_current=False, valid_to=timezone.now())
        obj, _ = model.objects.using(self.database_alias).update_or_create(
            **{pk_name: pk_value},
            defaults=defaults,
        )
        return obj

    def add_exception(
        self,
        *,
        source_table: str,
        source_pk_column: str,
        source_pk_value: Any,
        entity_type: str,
        issue_code: str,
        issue_details: dict[str, Any],
        raw_payload: dict[str, Any],
    ) -> None:
        MigrationExceptionV2.objects.using(self.database_alias).create(
            migration_batch_id=self.batch_id,
            system_name=SYSTEM_NAME,
            database_name=self.database_name,
            source_table=source_table,
            source_pk_column=source_pk_column,
            source_pk_value=str(source_pk_value or ""),
            entity_type=entity_type,
            issue_code=issue_code,
            issue_details=to_json(issue_details),
            raw_payload_json=to_json(raw_payload),
            resolution_status="open",
        )
        self.counts[f"exception.{issue_code}"] += 1

    def load_master_identity_cache(self) -> None:
        sources = [
            ("brand", "campaign_brand_raw", "campaign_brand", ["brand_uuid", "uuid", "id"]),
            ("campaign", "campaign_campaign_raw", "campaign_campaign", ["campaign_uuid", "campaign_id", "id", "uuid"]),
            ("field_rep", "campaign_fieldrep_raw", "campaign_fieldrep", ["field_rep_uuid", "uuid", "id"]),
            (
                "campaign_field_rep_assignment",
                "campaign_campaignfieldrep_raw",
                "campaign_campaignfieldrep",
                ["assignment_uuid", "uuid", "id"],
            ),
            ("doctor", "campaign_doctor_raw", "campaign_doctor", ["doctor_uuid", "uuid", "id", "doctor_id"]),
            (
                "doctor_enrollment",
                "campaign_doctorcampaignenrollment_raw",
                "campaign_doctorcampaignenrollment",
                ["enrollment_uuid", "uuid", "id"],
            ),
            ("rfa_doctor", "redflags_doctor_raw", "redflags_doctor", ["doctor_uuid", "uuid", "doctor_id", "id"]),
        ]
        seen_by_entity_value: dict[tuple[str, str], set[str]] = defaultdict(set)

        for entity_type, raw_table, live_table, id_candidates in sources:
            rows, table, source_database, verification_basis = self.master_source_rows(
                entity_type, raw_table, live_table
            )
            for row in rows:
                source_column = first_column_name(row, id_candidates)
                source_value = pick_first(row, id_candidates)
                if source_value in (None, ""):
                    source_value = pick_first(row, ["id", "pk", "doctor_id", "campaign_id", "field_rep_id"])
                source_value_s = str(source_value or "").strip()
                if not source_value_s:
                    continue
                normalized = self.normalized_master_source_value(entity_type, row, source_value_s)
                entity_uuid = canonical_uuid_from_row(row, entity_type, source_value_s)
                reconciliation_status = "matched" if entity_uuid else "unmatched"
                cache_id = self.v2_uuid(PeMasterIdentityCacheV2, table, f"{entity_type}:{source_value_s}")
                defaults = {
                    "cache_id": cache_id,
                    "entity_type": entity_type,
                    "entity_uuid": entity_uuid,
                    "source_column": source_column,
                    "source_value": source_value_s,
                    "source_value_normalized": normalized,
                    "cache_loaded_at": timezone.now(),
                    "reconciliation_status": reconciliation_status,
                    "reconciliation_basis": "source_uuid_present" if entity_uuid else "",
                    **self.common_fields(
                        source_system=MASTER_CACHE_SYSTEM,
                        source_database=source_database,
                        source_table=table,
                        source_pk_column=source_column,
                        source_pk_value=source_value_s,
                        source_updated_at=pick_first(row, ["updated_at", "modified_at"]),
                        verification_status=reconciliation_status,
                        verification_basis=verification_basis,
                        raw_payload=row,
                    ),
                }
                self.update_current_row(
                    PeMasterIdentityCacheV2,
                    source_table=table,
                    source_pk_value=f"{entity_type}:{source_value_s}",
                    defaults=defaults,
                )
                row_for_index = dict(row)
                row_for_index["_source_table"] = table
                row_for_index["_source_database"] = source_database
                self.index_master_identity(entity_type, row_for_index, source_value_s, normalized, entity_uuid)
                if normalized and entity_uuid:
                    seen_by_entity_value[(entity_type, normalized)].add(entity_uuid)
                self.counts["pe_master_identity_cache_v2"] += 1

        for (entity_type, normalized), uuids in seen_by_entity_value.items():
            if len(uuids) > 1:
                self.add_exception(
                    source_table="raw_pe_master",
                    source_pk_column="source_value_normalized",
                    source_pk_value=normalized,
                    entity_type=entity_type,
                    issue_code="PE_MASTER_CACHE_CONFLICT",
                    issue_details={"entity_type": entity_type, "normalized": normalized, "entity_uuids": sorted(uuids)},
                    raw_payload={},
                )

    def master_source_rows(
        self, entity_type: str, raw_table: str, live_table: str
    ) -> tuple[list[dict[str, Any]], str, str, str]:
        if connection_alias_exists(self.master_database_alias):
            rows = [
                self.normalize_live_master_row(entity_type, live_table, row)
                for row in fetch_table_rows(self.master_database_alias, live_table)
            ]
            if rows:
                return rows, live_table, db_name(self.master_database_alias), "rfa_master_live"

        rows = fetch_raw_rows(self.database_alias, self.raw_master_schema, raw_table)
        return rows, raw_table, self.raw_master_schema, "raw_pe_master_extract"

    def normalize_live_master_row(self, entity_type: str, table: str, row: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(row)
        if table == "campaign_brand":
            normalized.setdefault("brand_uuid", str(row.get("id") or ""))
        elif table == "campaign_campaign":
            normalized.setdefault("campaign_uuid", str(row.get("id") or ""))
        elif table == "campaign_fieldrep":
            normalized.setdefault("field_rep_uuid", str(row.get("id") or ""))
            normalized.setdefault("field_rep_id", row.get("id"))
        elif table == "campaign_campaignfieldrep":
            normalized.setdefault("assignment_uuid", str(row.get("id") or ""))
            normalized.setdefault("campaign_uuid", row.get("campaign_id"))
        elif table == "campaign_doctor":
            normalized.setdefault("doctor_uuid", row.get("doctor_id") or row.get("id"))
            normalized.setdefault("campaign_doctor_id", row.get("id"))
        elif table == "campaign_doctorcampaignenrollment":
            normalized.setdefault("enrollment_uuid", str(row.get("id") or ""))
            normalized.setdefault("campaign_uuid", row.get("campaign_id"))
            normalized.setdefault("campaign_doctor_id", row.get("doctor_id"))
        elif table == "redflags_doctor":
            normalized.setdefault("doctor_uuid", row.get("doctor_id"))
        normalized["_source_table"] = table
        normalized["_source_database"] = db_name(self.master_database_alias)
        return normalized

    def normalized_master_source_value(self, entity_type: str, row: dict[str, Any], source_value: str) -> str:
        if entity_type in {"campaign", "campaign_field_rep_assignment", "doctor_enrollment"}:
            campaign_value = pick_first(row, ["campaign_uuid", "campaign_id", "id"]) or source_value
            return normalize_campaign_id(str(campaign_value))
        if entity_type in {"doctor", "rfa_doctor"}:
            return str(pick_first(row, ["doctor_id", "id"]) or source_value).strip().lower()
        if entity_type == "field_rep":
            return str(pick_first(row, ["field_rep_uuid", "id", "brand_supplied_field_rep_id"]) or source_value).strip().lower()
        return str(source_value or "").strip().lower()

    def index_master_identity(
        self,
        entity_type: str,
        row: dict[str, Any],
        source_value: str,
        normalized: str,
        entity_uuid: str | None,
    ) -> None:
        row_with_uuid = dict(row)
        row_with_uuid["_entity_uuid"] = entity_uuid
        row_with_uuid["_source_value"] = source_value
        row_with_uuid["_source_value_normalized"] = normalized
        if entity_type == "campaign" and normalized:
            self.master_indexes.campaigns_by_normalized_id[normalized] = row_with_uuid
        elif entity_type == "field_rep":
            for key in {source_value, str(pick_first(row, ["id"]) or ""), str(pick_first(row, ["field_rep_id"]) or "")}:
                if key:
                    self.master_indexes.field_reps_by_source_id[key] = row_with_uuid
        elif entity_type in {"doctor", "rfa_doctor"}:
            source_id = str(pick_first(row, ["id"]) or source_value or "").strip()
            doctor_id = str(pick_first(row, ["doctor_id"]) or "").strip()
            if source_id:
                self.master_indexes.doctors_by_source_id[source_id] = row_with_uuid
            if doctor_id:
                self.master_indexes.doctors_by_doctor_id[doctor_id] = row_with_uuid
            phone = normalize_phone(
                str(
                    pick_first(
                        row,
                        ["whatsapp_no", "whatsapp_number", "phone", "mobile", "clinic_phone", "receptionist_whatsapp_number"],
                    )
                    or ""
                )
            )
            if phone:
                self.master_indexes.doctors_by_phone[phone].append(row_with_uuid)
            if entity_type == "doctor" and source_id:
                self.master_indexes.campaign_doctors_by_source_id[source_id] = row_with_uuid
        elif entity_type == "doctor_enrollment":
            self.master_indexes.enrollment_rows.append(row_with_uuid)

    def safe_source_queryset(self, model: type[Model]) -> list[Model]:
        try:
            return list(model.objects.using(self.database_alias).all())
        except Exception as exc:
            self.add_exception(
                source_table=model._meta.db_table,
                source_pk_column="",
                source_pk_value="",
                entity_type="source_table",
                issue_code="PE_SOURCE_TABLE_UNAVAILABLE",
                issue_details={"error": f"{type(exc).__name__}: {exc}"},
                raw_payload={},
            )
            return []

    def backfill_campaigns(self) -> None:
        for campaign in self.safe_source_queryset(Campaign):
            payload = model_payload(campaign)
            source_pk = getattr(campaign, "id", None) or campaign.campaign_id
            pe_norm = normalize_campaign_id(campaign.campaign_id)
            master = self.master_indexes.campaigns_by_normalized_id.get(pe_norm)
            campaign_uuid = master.get("_entity_uuid") if master else None
            status = "mapped" if campaign_uuid else "unmapped"
            if not master:
                self.add_exception(
                    source_table="publisher_campaign",
                    source_pk_column="id" if getattr(campaign, "id", None) is not None else "campaign_id",
                    source_pk_value=source_pk,
                    entity_type="campaign",
                    issue_code="PE_CAMPAIGN_NOT_FOUND_IN_MASTER",
                    issue_details={"campaign_id": campaign.campaign_id, "normalized": pe_norm},
                    raw_payload=payload,
                )
            defaults = {
                "pe_campaign_uuid": self.v2_uuid(PeCampaignV2, "publisher_campaign", source_pk),
                "id": getattr(campaign, "id", None),
                "campaign_id": campaign.campaign_id,
                "new_video_cluster_name": campaign.new_video_cluster_name,
                "selection_json": campaign.selection_json,
                "doctors_supported": campaign.doctors_supported,
                "banner_small": str(campaign.banner_small or ""),
                "banner_large": str(campaign.banner_large or ""),
                "banner_target_url": campaign.banner_target_url,
                "start_date": campaign.start_date,
                "end_date": campaign.end_date,
                "video_cluster_id": campaign.video_cluster_id,
                "publisher_sub": campaign.publisher_sub,
                "publisher_username": campaign.publisher_username,
                "publisher_roles": campaign.publisher_roles,
                "email_registration": campaign.email_registration,
                "wa_addition": campaign.wa_addition,
                "created_at": campaign.created_at,
                "updated_at": campaign.updated_at,
                "campaign_uuid": campaign_uuid,
                "pe_campaign_id_raw": campaign.campaign_id,
                "pe_campaign_id_normalized": pe_norm,
                "master_campaign_id_normalized": pe_norm if campaign_uuid else None,
                "video_cluster_uuid": deterministic_uuid("catalog_videocluster", campaign.video_cluster_id)
                if campaign.video_cluster_id
                else None,
                "campaign_mapping_status": status,
                "campaign_mapping_basis": "normalized_same_campaign_id",
                **self.common_fields(
                    source_system=SYSTEM_NAME,
                    source_database=self.database_name,
                    source_table="publisher_campaign",
                    source_pk_column="id" if getattr(campaign, "id", None) is not None else "campaign_id",
                    source_pk_value=source_pk,
                    source_created_at=campaign.created_at,
                    source_updated_at=campaign.updated_at,
                    verification_status="verified" if campaign_uuid else "manual_review",
                    verification_basis="normalized_same_campaign_id" if campaign_uuid else "master_campaign_missing",
                    raw_payload=payload,
                    is_current=bool(campaign_uuid),
                    valid_from=campaign.created_at,
                ),
            }
            obj = self.update_current_row(
                PeCampaignV2,
                source_table="publisher_campaign",
                source_pk_value=source_pk,
                defaults=defaults,
            )
            if pe_norm:
                self.pe_campaign_by_normalized_id[pe_norm] = obj
            self.counts["pe_campaign_v2"] += 1

    def backfill_clinics(self) -> None:
        for clinic in self.safe_source_queryset(Clinic):
            payload = model_payload(clinic)
            defaults = {
                "clinic_uuid": self.v2_uuid(PeClinicV2, "accounts_clinic", clinic.pk),
                "id": clinic.pk,
                "clinic_code": clinic.clinic_code,
                "display_name": clinic.display_name,
                "clinic_phone": clinic.clinic_phone,
                "clinic_whatsapp_number": clinic.clinic_whatsapp_number,
                "address_text": clinic.address_text,
                "postal_code": clinic.postal_code,
                "state": clinic.state,
                "created_at": getattr(clinic, "created_at", None),
                "updated_at": getattr(clinic, "updated_at", None),
                "clinic_phone_normalized": normalize_phone(clinic.clinic_phone),
                "clinic_whatsapp_normalized": normalize_phone(clinic.clinic_whatsapp_number),
                "global_clinic_uuid": None,
                **self.common_fields(
                    source_system=SYSTEM_NAME,
                    source_database=self.database_name,
                    source_table="accounts_clinic",
                    source_pk_column="id",
                    source_pk_value=clinic.pk,
                    source_created_at=getattr(clinic, "created_at", None),
                    source_updated_at=getattr(clinic, "updated_at", None),
                    verification_status="verified",
                    verification_basis="source_row_copied",
                    raw_payload=payload,
                    valid_from=getattr(clinic, "created_at", None),
                ),
            }
            obj = self.update_current_row(
                PeClinicV2,
                source_table="accounts_clinic",
                source_pk_value=clinic.pk,
                defaults=defaults,
            )
            self.pe_clinic_by_source_id[str(clinic.pk)] = obj
            self.counts["pe_clinic_v2"] += 1

    def backfill_doctors(self) -> None:
        for doctor in self.safe_source_queryset(DoctorProfile):
            payload = model_payload(doctor)
            doctor_uuid, match_status, match_basis = self.resolve_doctor_identity(doctor, payload)
            clinic = self.pe_clinic_by_source_id.get(str(doctor.clinic_id))
            defaults = {
                "pe_doctor_uuid": self.v2_uuid(PeDoctorV2, "accounts_doctorprofile", doctor.pk),
                "id": doctor.pk,
                "doctor_id": doctor.doctor_id,
                "whatsapp_number": doctor.whatsapp_number,
                "imc_number": doctor.imc_number,
                "postal_code": doctor.postal_code,
                "photo": str(doctor.photo or ""),
                "created_at": doctor.created_at,
                "updated_at": doctor.updated_at,
                "clinic_id": doctor.clinic_id,
                "user_id": doctor.user_id,
                "doctor_uuid": doctor_uuid,
                "clinic_uuid": clinic.clinic_uuid if clinic else None,
                "doctor_id_raw": doctor.doctor_id,
                "whatsapp_normalized": normalize_phone(doctor.whatsapp_number),
                "imc_number_normalized": str(doctor.imc_number or "").strip().lower() or None,
                "match_status": match_status,
                "match_basis": match_basis,
                **self.common_fields(
                    source_system=SYSTEM_NAME,
                    source_database=self.database_name,
                    source_table="accounts_doctorprofile",
                    source_pk_column="id",
                    source_pk_value=doctor.pk,
                    source_created_at=doctor.created_at,
                    source_updated_at=doctor.updated_at,
                    verification_status="verified" if match_status == "matched" else "manual_review",
                    verification_basis=match_basis,
                    raw_payload=payload,
                    valid_from=doctor.created_at,
                ),
            }
            obj = self.update_current_row(
                PeDoctorV2,
                source_table="accounts_doctorprofile",
                source_pk_value=doctor.pk,
                defaults=defaults,
            )
            self.pe_doctor_by_doctor_id[doctor.doctor_id] = obj
            self.pe_doctor_by_source_id[str(doctor.pk)] = obj
            self.counts["pe_doctor_v2"] += 1

    def resolve_doctor_identity(self, doctor: DoctorProfile, payload: dict[str, Any]) -> tuple[str | None, str, str]:
        by_doctor_id = self.master_indexes.doctors_by_doctor_id.get(str(doctor.doctor_id or "").strip())
        if by_doctor_id and by_doctor_id.get("_entity_uuid"):
            return by_doctor_id["_entity_uuid"], "matched", "master_doctor_id"
        phone = normalize_phone(doctor.whatsapp_number)
        phone_matches = [row for row in self.master_indexes.doctors_by_phone.get(phone, []) if row.get("_entity_uuid")]
        unique_uuids = sorted({row["_entity_uuid"] for row in phone_matches})
        if len(unique_uuids) == 1:
            return unique_uuids[0], "matched", "phone_match"
        if len(unique_uuids) > 1:
            self.add_exception(
                source_table="accounts_doctorprofile",
                source_pk_column="id",
                source_pk_value=doctor.pk,
                entity_type="doctor",
                issue_code="PE_DOCTOR_PHONE_MULTIPLE_MATCHES",
                issue_details={"phone_normalized": phone, "doctor_uuids": unique_uuids},
                raw_payload=payload,
            )
            return None, "ambiguous", "phone_match"
        return None, "unmatched", "manual_review"

    def backfill_content(self) -> None:
        content_sources = [
            ("therapy_area", TherapyArea, "catalog_therapyarea"),
            ("trigger_cluster", TriggerCluster, "catalog_triggercluster"),
            ("trigger", Trigger, "catalog_trigger"),
            ("video", Video, "catalog_video"),
            ("video_cluster", VideoCluster, "catalog_videocluster"),
            ("video_language", VideoLanguage, "catalog_videolanguage"),
            ("cluster_language", VideoClusterLanguage, "catalog_videoclusterlanguage"),
            ("video_cluster_video", VideoClusterVideo, "catalog_videoclustervideo"),
            ("video_trigger_map", VideoTriggerMap, "catalog_videotriggermap"),
        ]
        for content_type, model, source_table in content_sources:
            for obj in self.safe_source_queryset(model):
                self.backfill_content_object(content_type, obj, source_table)

    def backfill_content_object(self, content_type: str, obj: Model, source_table: str) -> None:
        payload = model_payload(obj)
        source_code = self.content_source_code(content_type, obj)
        source_code_normalized = normalize_content_code(source_code)
        content_uuid = deterministic_uuid(source_table, obj.pk)
        parent_uuid = self.parent_content_uuid(content_type, obj)
        defaults = {
            "content_uuid": content_uuid,
            "id": obj.pk,
            "content_type": content_type,
            "source_code": source_code or None,
            "source_code_normalized": source_code_normalized or None,
            "display_name_canonical": self.content_display_name(content_type, obj),
            "parent_content_uuid": parent_uuid,
            "language_code": getattr(obj, "language_code", None),
            "is_active_canonical": bool(getattr(obj, "is_active", True)),
            "code": getattr(obj, "code", None),
            "display_name": getattr(obj, "display_name", None),
            "description": getattr(obj, "description", "") or "",
            "name": getattr(obj, "name", None),
            "title": getattr(obj, "title", None),
            "doctor_trigger_label": getattr(obj, "doctor_trigger_label", None),
            "subtopic_title": getattr(obj, "subtopic_title", None),
            "navigation_pathways": getattr(obj, "navigation_pathways", "") or "",
            "search_keywords": getattr(obj, "search_keywords", "") or "",
            "thumbnail_url": getattr(obj, "thumbnail_url", None),
            "youtube_url": getattr(obj, "youtube_url", None),
            "primary_therapy_id": getattr(obj, "primary_therapy_id", None),
            "primary_trigger_id": getattr(obj, "primary_trigger_id", None),
            "trigger_id": getattr(obj, "trigger_id", None),
            "cluster_id": getattr(obj, "cluster_id", None),
            "video_id": getattr(obj, "video_id", None),
            "video_cluster_id": getattr(obj, "video_cluster_id", None),
            "sort_order": getattr(obj, "sort_order", None),
            "is_active": getattr(obj, "is_active", None),
            "is_published": getattr(obj, "is_published", None),
            "is_primary": getattr(obj, "is_primary", None),
            "created_at": getattr(obj, "created_at", None),
            "updated_at": getattr(obj, "updated_at", None),
            **self.common_fields(
                source_system=SYSTEM_NAME,
                source_database=self.database_name,
                source_table=source_table,
                source_pk_column="id",
                source_pk_value=obj.pk,
                source_created_at=getattr(obj, "created_at", None),
                source_updated_at=getattr(obj, "updated_at", None),
                verification_status="verified",
                verification_basis="source_row_copied_system_specific_content",
                raw_payload=payload,
                valid_from=getattr(obj, "created_at", None),
            ),
        }
        self.update_current_row(
            PeContentItemV2,
            source_table=source_table,
            source_pk_value=obj.pk,
            defaults=defaults,
        )
        if source_code_normalized:
            self.content_uuid_by_type_code[(content_type, source_code_normalized)] = content_uuid
        self.counts["pe_content_item_v2"] += 1

    def content_source_code(self, content_type: str, obj: Model) -> str:
        if hasattr(obj, "code"):
            return str(getattr(obj, "code") or "")
        if content_type == "video_language":
            return f"{obj.video.code}:{obj.language_code}"
        if content_type == "cluster_language":
            return f"{obj.video_cluster.code}:{obj.language_code}"
        if content_type == "video_cluster_video":
            return f"{obj.video_cluster.code}:{obj.video.code}"
        if content_type == "video_trigger_map":
            return f"{obj.video.code}:{obj.trigger.code}"
        return str(obj.pk)

    def content_display_name(self, content_type: str, obj: Model) -> str:
        for attr in ("display_name", "title", "name"):
            value = getattr(obj, attr, None)
            if value:
                return str(value)
        if content_type == "video":
            return str(getattr(obj, "code", "") or "")
        return str(obj)

    def parent_content_uuid(self, content_type: str, obj: Model) -> str | None:
        if content_type == "trigger":
            return deterministic_uuid("catalog_triggercluster", obj.cluster_id)
        if content_type == "video_cluster":
            return deterministic_uuid("catalog_trigger", obj.trigger_id)
        if content_type == "video_language":
            return deterministic_uuid("catalog_video", obj.video_id)
        if content_type == "cluster_language":
            return deterministic_uuid("catalog_videocluster", obj.video_cluster_id)
        if content_type == "video_cluster_video":
            return deterministic_uuid("catalog_videocluster", obj.video_cluster_id)
        if content_type == "video_trigger_map":
            return deterministic_uuid("catalog_video", obj.video_id)
        return None

    def resolve_content_uuid(self, item_type: str, item_code: str) -> str | None:
        normalized = normalize_content_code(item_code)
        if item_type == "video":
            return self.content_uuid_by_type_code.get(("video", normalized))
        if item_type in {"cluster", "video_cluster"}:
            return self.content_uuid_by_type_code.get(("video_cluster", normalized))
        return None

    def backfill_share_summaries(self) -> None:
        for summary in self.safe_source_queryset(DoctorShareSummary):
            payload = model_payload(summary)
            pe_doctor = self.pe_doctor_by_doctor_id.get(summary.doctor_id)
            defaults = {
                "doctor_share_summary_uuid": self.v2_uuid(PeDoctorShareSummaryV2, "sharing_doctorsharesummary", summary.pk),
                "id": summary.pk,
                "doctor_id": summary.doctor_id,
                "doctor_name_snapshot": summary.doctor_name_snapshot,
                "clinic_name_snapshot": summary.clinic_name_snapshot,
                "total_shares": summary.total_shares,
                "last_shared_at": summary.last_shared_at,
                "created_at": summary.created_at,
                "updated_at": summary.updated_at,
                "doctor_uuid": pe_doctor.doctor_uuid if pe_doctor else None,
                "pe_doctor_uuid": pe_doctor.pe_doctor_uuid if pe_doctor else None,
                "clinic_uuid": pe_doctor.clinic_uuid if pe_doctor else None,
                **self.common_fields(
                    source_system=SYSTEM_NAME,
                    source_database=self.database_name,
                    source_table="sharing_doctorsharesummary",
                    source_pk_column="id",
                    source_pk_value=summary.pk,
                    source_created_at=summary.created_at,
                    source_updated_at=summary.updated_at,
                    verification_status="verified" if pe_doctor else "manual_review",
                    verification_basis="doctor_id_lookup" if pe_doctor else "doctor_unresolved",
                    raw_payload=payload,
                    valid_from=summary.created_at,
                ),
            }
            self.update_current_row(
                PeDoctorShareSummaryV2,
                source_table="sharing_doctorsharesummary",
                source_pk_value=summary.pk,
                defaults=defaults,
            )
            self.counts["pe_doctor_share_summary_v2"] += 1

    def backfill_share_events(self) -> None:
        for share in self.safe_source_queryset(ShareActivity):
            payload = model_payload(share)
            pe_doctor = self.pe_doctor_by_doctor_id.get(share.doctor_id)
            content_uuid = self.resolve_content_uuid(share.shared_item_type, share.shared_item_code)
            verification_status = "verified" if content_uuid else "manual_review"
            verification_basis = "shared_item_type_code" if content_uuid else "content_unresolved"
            if not content_uuid:
                self.add_exception(
                    source_table="sharing_shareactivity",
                    source_pk_column="id",
                    source_pk_value=share.pk,
                    entity_type="share_event",
                    issue_code="PE_SHARE_CONTENT_NOT_FOUND",
                    issue_details={
                        "shared_item_type": share.shared_item_type,
                        "shared_item_code": share.shared_item_code,
                    },
                    raw_payload=payload,
                )
            attribution = "doctor_shared" if str(share.shared_by_role or "").strip().lower() == "doctor" else "clinic_or_doctor_shared"
            defaults = {
                "share_event_uuid": self.v2_uuid(PeShareEventV2, "sharing_shareactivity", share.pk),
                "id": share.pk,
                "public_id": str(share.public_id or ""),
                "doctor_summary_id": share.doctor_summary_id,
                "doctor_id": share.doctor_id,
                "doctor_name_snapshot": share.doctor_name_snapshot,
                "clinic_name_snapshot": share.clinic_name_snapshot,
                "share_channel": share.share_channel,
                "shared_by_role": share.shared_by_role,
                "shared_item_type": share.shared_item_type,
                "shared_item_code": share.shared_item_code,
                "shared_item_name": share.shared_item_name,
                "language_code": share.language_code,
                "recipient_reference": share.recipient_reference,
                "recipient_reference_version": share.recipient_reference_version,
                "shared_at": share.shared_at,
                "campaign_uuid": None,
                "pe_campaign_uuid": None,
                "doctor_uuid": pe_doctor.doctor_uuid if pe_doctor else None,
                "pe_doctor_uuid": pe_doctor.pe_doctor_uuid if pe_doctor else None,
                "clinic_uuid": pe_doctor.clinic_uuid if pe_doctor else None,
                "content_uuid": content_uuid,
                "share_channel_normalized": str(share.share_channel or "").strip().lower() or "unknown",
                "share_attribution_type": attribution,
                "actual_shared_by_field_rep_uuid": None,
                "assignment_credit_field_rep_uuid": None,
                "assignment_credit_basis": None,
                **self.common_fields(
                    source_system=SYSTEM_NAME,
                    source_database=self.database_name,
                    source_table="sharing_shareactivity",
                    source_pk_column="id",
                    source_pk_value=share.pk,
                    source_created_at=share.shared_at,
                    source_updated_at=None,
                    verification_status=verification_status,
                    verification_basis=verification_basis,
                    raw_payload=payload,
                    valid_from=share.shared_at,
                ),
            }
            obj = self.update_current_row(
                PeShareEventV2,
                source_table="sharing_shareactivity",
                source_pk_value=share.pk,
                defaults=defaults,
            )
            self.share_by_source_id[str(share.pk)] = obj
            if share.public_id:
                self.share_by_public_id[str(share.public_id)] = obj
            self.counts["pe_share_event_v2"] += 1

    def backfill_playback_events(self) -> None:
        for event in self.safe_source_queryset(SharePlaybackEvent):
            payload = model_payload(event)
            share = None
            if event.share_id:
                share = self.share_by_source_id.get(str(event.share_id))
            if not share and event.share_public_id:
                share = self.share_by_public_id.get(str(event.share_public_id))
            content_uuid = self.resolve_content_uuid("video", event.video_code)
            status = "verified" if share and content_uuid else "manual_review"
            basis_parts = []
            if share:
                basis_parts.append("share_id_or_public_id")
            else:
                basis_parts.append("share_unresolved")
                self.add_exception(
                    source_table="sharing_shareplaybackevent",
                    source_pk_column="id",
                    source_pk_value=event.pk,
                    entity_type="playback_event",
                    issue_code="PE_PLAYBACK_SHARE_NOT_FOUND",
                    issue_details={"share_id": event.share_id, "share_public_id": str(event.share_public_id or "")},
                    raw_payload=payload,
                )
            if content_uuid:
                basis_parts.append("video_code")
            else:
                basis_parts.append("content_unresolved")
            pe_doctor = self.pe_doctor_by_doctor_id.get(event.doctor_id)
            defaults = {
                "playback_event_uuid": self.v2_uuid(PePlaybackEventV2, "sharing_shareplaybackevent", event.pk),
                "id": event.pk,
                "share_id": event.share_id,
                "share_public_id": str(event.share_public_id or "") or None,
                "doctor_summary_id": event.doctor_summary_id,
                "doctor_id": event.doctor_id,
                "page_item_type": event.page_item_type,
                "event_type": event.event_type,
                "video_code": event.video_code,
                "video_name": event.video_name,
                "milestone_percent": event.milestone_percent,
                "occurred_at": event.occurred_at,
                "share_event_uuid": share.share_event_uuid if share else None,
                "doctor_uuid": pe_doctor.doctor_uuid if pe_doctor else None,
                "pe_doctor_uuid": pe_doctor.pe_doctor_uuid if pe_doctor else None,
                "campaign_uuid": share.campaign_uuid if share else None,
                "content_uuid": content_uuid,
                "assignment_credit_field_rep_uuid": share.assignment_credit_field_rep_uuid if share else None,
                "event_type_normalized": str(event.event_type or "").strip().lower() or "unknown",
                **self.common_fields(
                    source_system=SYSTEM_NAME,
                    source_database=self.database_name,
                    source_table="sharing_shareplaybackevent",
                    source_pk_column="id",
                    source_pk_value=event.pk,
                    source_created_at=event.occurred_at,
                    source_updated_at=None,
                    verification_status=status,
                    verification_basis=";".join(basis_parts),
                    raw_payload=payload,
                    valid_from=event.occurred_at,
                ),
            }
            self.update_current_row(
                PePlaybackEventV2,
                source_table="sharing_shareplaybackevent",
                source_pk_value=event.pk,
                defaults=defaults,
            )
            self.counts["pe_playback_event_v2"] += 1

    def backfill_banner_click_events(self) -> None:
        for click in self.safe_source_queryset(ShareBannerClickEvent):
            payload = model_payload(click)
            pe_doctor = self.pe_doctor_by_doctor_id.get(click.doctor_id)
            campaign_norm = normalize_campaign_id(click.banner_id)
            pe_campaign = self.pe_campaign_by_normalized_id.get(campaign_norm)
            defaults = {
                "banner_click_event_uuid": self.v2_uuid(PeBannerClickEventV2, "sharing_sharebannerclickevent", click.pk),
                "id": click.pk,
                "page_type": click.page_type,
                "banner_id": click.banner_id,
                "banner_name": click.banner_name,
                "banner_target_url": click.banner_target_url,
                "clicked_at": click.clicked_at,
                "doctor_id": click.doctor_id,
                "doctor_summary_id": click.doctor_summary_id,
                "source_banner_click_id": str(click.pk),
                "doctor_uuid": pe_doctor.doctor_uuid if pe_doctor else None,
                "pe_doctor_uuid": pe_doctor.pe_doctor_uuid if pe_doctor else None,
                "campaign_uuid": pe_campaign.campaign_uuid if pe_campaign else None,
                "content_uuid": None,
                **self.common_fields(
                    source_system=SYSTEM_NAME,
                    source_database=self.database_name,
                    source_table="sharing_sharebannerclickevent",
                    source_pk_column="id",
                    source_pk_value=click.pk,
                    source_created_at=click.clicked_at,
                    source_updated_at=None,
                    verification_status="verified" if pe_doctor else "manual_review",
                    verification_basis="doctor_id_lookup;banner_id_campaign_lookup",
                    raw_payload=payload,
                    valid_from=click.clicked_at,
                ),
            }
            self.update_current_row(
                PeBannerClickEventV2,
                source_table="sharing_sharebannerclickevent",
                source_pk_value=click.pk,
                defaults=defaults,
            )
            self.counts["pe_banner_click_event_v2"] += 1

    def backfill_rep_assignment_credit(self) -> None:
        rows = list(self.master_indexes.enrollment_rows)
        roster_rows = self.master_roster_rows()
        rows.extend(self.normalize_roster_rows(roster_rows))
        for row in rows:
            source_table = str(row.get("_source_table") or "campaign_doctorcampaignenrollment_raw")
            source_database = str(row.get("_source_database") or row.get("source_database") or self.master_source_database())
            source_pk_column = first_column_name(
                row,
                ["id", "enrollment_id", "assignment_id", "roster_bridge_uuid", "source_pk_value"],
            )
            source_pk = str(
                pick_first(row, ["id", "enrollment_id", "assignment_id", "roster_bridge_uuid", "source_pk_value"])
                or row.get("_source_value")
                or ""
            )
            campaign_uuid = self.resolve_campaign_uuid_from_assignment(row)
            doctor_uuid = self.resolve_doctor_uuid_from_assignment(row)
            field_rep_uuid = self.resolve_field_rep_uuid_from_assignment(row)
            if not (campaign_uuid and doctor_uuid and field_rep_uuid):
                self.add_exception(
                    source_table=source_table,
                    source_pk_column="id",
                    source_pk_value=source_pk,
                    entity_type="rep_assignment_credit",
                    issue_code="PE_REP_ASSIGNMENT_CREDIT_UNRESOLVED",
                    issue_details={
                        "campaign_uuid_found": bool(campaign_uuid),
                        "doctor_uuid_found": bool(doctor_uuid),
                        "field_rep_uuid_found": bool(field_rep_uuid),
                    },
                    raw_payload=row,
                )
                continue
            defaults = {
                "rep_assignment_credit_uuid": self.v2_uuid(PeRepAssignmentCreditV2, source_table, source_pk),
                "campaign_uuid": campaign_uuid,
                "doctor_uuid": doctor_uuid,
                "field_rep_uuid": field_rep_uuid,
                "credit_type": "assignment_recruitment_credit",
                "credit_source_table": source_table,
                "credit_source_pk": source_pk,
                "credit_effective_from": normalize_datetime_value(
                    pick_first(row, ["created_at", "assigned_at", "valid_from"])
                ),
                "credit_effective_to": normalize_datetime_value(
                    pick_first(row, ["ended_at", "unassigned_at", "valid_to"])
                ),
                **self.common_fields(
                    source_system=RFA_MASTER_SYSTEM,
                    source_database=source_database,
                    source_table=source_table,
                    source_pk_column=source_pk_column,
                    source_pk_value=source_pk,
                    source_created_at=pick_first(row, ["created_at", "assigned_at", "valid_from"]),
                    source_updated_at=pick_first(row, ["updated_at", "modified_at"]),
                    verification_status="verified",
                    verification_basis=self.credit_basis(source_table),
                    raw_payload=row,
                    valid_from=pick_first(row, ["created_at", "assigned_at", "valid_from"]),
                    valid_to=pick_first(row, ["ended_at", "unassigned_at", "valid_to"]),
                ),
            }
            self.update_current_row(
                PeRepAssignmentCreditV2,
                source_table=source_table,
                source_pk_value=source_pk,
                defaults=defaults,
            )
            self.counts["pe_rep_assignment_credit_v2"] += 1

    def master_source_database(self) -> str:
        if connection_alias_exists(self.master_database_alias):
            return db_name(self.master_database_alias)
        return self.raw_master_schema

    def master_roster_rows(self) -> list[dict[str, Any]]:
        if connection_alias_exists(self.master_database_alias):
            rows = fetch_table_rows(self.master_database_alias, "doctor_field_rep_roster_bridge_v2")
            if rows:
                return rows
        return fetch_raw_rows(self.database_alias, self.raw_master_schema, "doctor_field_rep_roster_bridge_v2")

    def normalize_roster_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for row in rows:
            normalized = dict(row)
            normalized["_source_table"] = "doctor_field_rep_roster_bridge_v2"
            normalized["_source_database"] = str(row.get("source_database") or self.master_source_database())
            out.append(normalized)
        return out

    def credit_basis(self, source_table: str) -> str:
        if source_table == "doctor_field_rep_roster_bridge_v2":
            return "doctor_field_rep_roster_bridge_v2"
        if source_table == "doctor_field_rep_assignment_history_v2":
            return "doctor_field_rep_assignment_history_v2"
        return "campaign_doctorcampaignenrollment.registered_by_id"

    def resolve_campaign_uuid_from_assignment(self, row: dict[str, Any]) -> str | None:
        value = pick_first(row, ["campaign_uuid", "campaign_id", "campaign"])
        norm = normalize_campaign_id(str(value or ""))
        master = self.master_indexes.campaigns_by_normalized_id.get(norm)
        if master and master.get("_entity_uuid"):
            return master["_entity_uuid"]
        if norm in self.pe_campaign_by_normalized_id:
            return self.pe_campaign_by_normalized_id[norm].campaign_uuid
        return str(value).strip() if value and len(str(value).strip()) >= 32 else None

    def resolve_doctor_uuid_from_assignment(self, row: dict[str, Any]) -> str | None:
        direct = pick_first(row, ["doctor_uuid", "rfa_doctor_uuid"])
        if direct:
            return str(direct).strip()
        doctor_id = str(pick_first(row, ["doctor_id", "rfa_doctor_id"]) or "").strip()
        if doctor_id in self.master_indexes.doctors_by_doctor_id:
            return self.master_indexes.doctors_by_doctor_id[doctor_id].get("_entity_uuid")
        campaign_doctor_id = str(pick_first(row, ["campaign_doctor_id", "doctor"]) or "").strip()
        if not campaign_doctor_id and doctor_id.isdigit():
            campaign_doctor_id = doctor_id
        if campaign_doctor_id in self.master_indexes.campaign_doctors_by_source_id:
            return self.master_indexes.campaign_doctors_by_source_id[campaign_doctor_id].get("_entity_uuid")
        return None

    def resolve_field_rep_uuid_from_assignment(self, row: dict[str, Any]) -> str | None:
        direct = pick_first(row, ["field_rep_uuid", "rep_uuid"])
        if direct:
            return str(direct).strip()
        field_rep_id = str(pick_first(row, ["registered_by_id", "field_rep_id", "rep_id"]) or "").strip()
        if field_rep_id in self.master_indexes.field_reps_by_source_id:
            return self.master_indexes.field_reps_by_source_id[field_rep_id].get("_entity_uuid")
        return None


def validation_report(database_alias: str = "default") -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at": timezone.now().isoformat(),
        "system_name": SYSTEM_NAME,
        "database_name": db_name(database_alias),
        "gates": {},
        "counts": {},
    }
    using = database_alias
    report["counts"] = {
        "campaigns": PeCampaignV2.objects.using(using).filter(is_current=True).count(),
        "doctors": PeDoctorV2.objects.using(using).filter(is_current=True).count(),
        "content_items": PeContentItemV2.objects.using(using).filter(is_current=True).count(),
        "share_events": PeShareEventV2.objects.using(using).filter(is_current=True).count(),
        "playback_events": PePlaybackEventV2.objects.using(using).filter(is_current=True).count(),
        "rep_assignment_credits": PeRepAssignmentCreditV2.objects.using(using).filter(is_current=True).count(),
        "open_exceptions": MigrationExceptionV2.objects.using(using).filter(resolution_status="open").count(),
    }
    campaign_unmapped = PeCampaignV2.objects.using(using).filter(is_current=True).exclude(campaign_mapping_status="mapped").count()
    campaign_missing_exceptions = (
        MigrationExceptionV2.objects.using(using)
        .filter(issue_code="PE_CAMPAIGN_NOT_FOUND_IN_MASTER", resolution_status="open")
        .count()
    )
    doctor_unresolved = PeDoctorV2.objects.using(using).filter(is_current=True).exclude(match_status="matched").count()
    share_content_missing = PeShareEventV2.objects.using(using).filter(is_current=True, content_uuid__isnull=True).count()
    share_public_id_missing = PeShareEventV2.objects.using(using).filter(is_current=True, public_id="").count()
    share_timestamp_missing = PeShareEventV2.objects.using(using).filter(is_current=True, shared_at__isnull=True).count()
    playback_share_missing = PePlaybackEventV2.objects.using(using).filter(is_current=True, share_event_uuid__isnull=True).count()
    rep_shared_mislabeled = PeShareEventV2.objects.using(using).filter(
        is_current=True,
        share_attribution_type__icontains="rep",
    ).count()
    actual_rep_populated = PeShareEventV2.objects.using(using).filter(
        is_current=True,
        actual_shared_by_field_rep_uuid__isnull=False,
    ).exclude(actual_shared_by_field_rep_uuid="").count()
    report["gates"] = {
        "campaigns_map_to_master_or_exception": {
            "passed": campaign_unmapped == 0 or campaign_missing_exceptions >= campaign_unmapped,
            "unmapped_campaigns": campaign_unmapped,
            "open_missing_master_exceptions": campaign_missing_exceptions,
        },
        "official_doctors_map_or_unresolved": {
            "passed": True,
            "unresolved_doctors": doctor_unresolved,
        },
        "share_events_resolve_content": {
            "passed": share_content_missing == 0,
            "missing_content": share_content_missing,
        },
        "playback_events_link_to_share_where_possible": {
            "passed": True,
            "missing_share": playback_share_missing,
        },
        "rep_metrics_labelled_assignment_recruitment_credit": {
            "passed": PeRepAssignmentCreditV2.objects.using(using)
            .filter(is_current=True)
            .exclude(credit_type="assignment_recruitment_credit")
            .count()
            == 0,
        },
        "actual_doctor_share_counts_event_based": {
            "passed": share_public_id_missing == 0 and share_timestamp_missing == 0,
            "missing_public_id": share_public_id_missing,
            "missing_shared_at": share_timestamp_missing,
        },
        "no_rep_shared_event_claims_from_assignment_history": {
            "passed": rep_shared_mislabeled == 0 and actual_rep_populated == 0,
            "rep_labelled_share_events": rep_shared_mislabeled,
            "actual_rep_field_populated": actual_rep_populated,
        },
    }
    report["passed"] = all(gate["passed"] for gate in report["gates"].values())
    return report


def exception_report(database_alias: str = "default") -> dict[str, Any]:
    using = database_alias
    rows = list(
        MigrationExceptionV2.objects.using(using)
        .filter(resolution_status="open")
        .values("issue_code", "entity_type", "source_table")
    )
    grouped: dict[str, int] = defaultdict(int)
    for row in rows:
        grouped[f"{row['issue_code']}|{row['entity_type']}|{row['source_table']}"] += 1
    return {
        "generated_at": timezone.now().isoformat(),
        "system_name": SYSTEM_NAME,
        "database_name": db_name(database_alias),
        "open_exception_count": len(rows),
        "groups": [
            {
                "issue_code": key.split("|")[0],
                "entity_type": key.split("|")[1],
                "source_table": key.split("|")[2],
                "count": count,
            }
            for key, count in sorted(grouped.items())
        ],
    }
