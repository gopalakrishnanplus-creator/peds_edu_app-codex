from __future__ import annotations

import uuid
from typing import Any

from django.db.models import Model
from django.utils import timezone

from publisher.models import Campaign
from sharing.models import DoctorShareSummary, ShareActivity, ShareBannerClickEvent, SharePlaybackEvent

from .models import (
    PeBannerClickEventV2,
    PeCampaignV2,
    PeContentItemV2,
    PeDoctorShareSummaryV2,
    PeDoctorV2,
    PeMasterIdentityCacheV2,
    PePlaybackEventV2,
    PeShareEventV2,
)
from .runtime import is_v2_enabled
from .services import (
    SYSTEM_NAME,
    db_name,
    deterministic_uuid,
    model_payload,
    normalize_campaign_id,
    normalize_content_code,
    to_json,
)


LIVE_SYNC_BATCH_ID = "pe-live-v2-sync"
LIVE_PRIMARY_BATCH_ID = "pe-live-v2-primary"


def sync_campaign(campaign: Campaign) -> PeCampaignV2 | None:
    if not is_v2_enabled():
        return None

    campaign.refresh_from_db()
    source_pk = campaign.pk or campaign.campaign_id
    pe_norm = normalize_campaign_id(campaign.campaign_id)
    master = PeMasterIdentityCacheV2.objects.filter(
        entity_type="campaign",
        source_value_normalized=pe_norm,
        reconciliation_status="matched",
    ).first()
    campaign_uuid = master.entity_uuid if master else None
    version_key = campaign.updated_at.isoformat() if campaign.updated_at else timezone.now().isoformat()
    defaults = {
        "pe_campaign_uuid": deterministic_uuid(
            LIVE_SYNC_BATCH_ID,
            PeCampaignV2._meta.db_table,
            "publisher_campaign",
            source_pk,
            version_key,
        ),
        "id": campaign.pk,
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
        "campaign_mapping_status": "mapped" if campaign_uuid else "unmapped",
        "campaign_mapping_basis": "normalized_same_campaign_id",
        **common_fields(
            source_table="publisher_campaign",
            source_pk_value=source_pk,
            source_created_at=campaign.created_at,
            source_updated_at=campaign.updated_at,
            verification_status="verified" if campaign_uuid else "manual_review",
            verification_basis="normalized_same_campaign_id" if campaign_uuid else "master_campaign_missing",
            raw_payload=model_payload(campaign),
            valid_from=campaign.updated_at or campaign.created_at,
        ),
    }
    return update_current(PeCampaignV2, "publisher_campaign", source_pk, defaults)


def upsert_campaign_v2(
    *,
    campaign_id: str,
    new_video_cluster_name: str,
    selection_json: str,
    doctors_supported: int,
    banner_small: str = "",
    banner_large: str = "",
    banner_target_url: str = "",
    start_date: Any = None,
    end_date: Any = None,
    video_cluster_id: Any = None,
    publisher_sub: str = "",
    publisher_username: str = "",
    publisher_roles: str = "",
    email_registration: str = "",
    wa_addition: str = "",
    created_at: Any = None,
    updated_at: Any = None,
) -> PeCampaignV2 | None:
    if not is_v2_enabled():
        return None

    now = timezone.now()
    created_at = created_at or now
    updated_at = updated_at or now
    campaign_id = str(campaign_id or "").strip()
    pe_norm = normalize_campaign_id(campaign_id)
    master = PeMasterIdentityCacheV2.objects.filter(
        entity_type="campaign",
        source_value_normalized=pe_norm,
        reconciliation_status="matched",
    ).first()
    campaign_uuid = master.entity_uuid if master else None
    version_key = updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at)
    pe_campaign_uuid = deterministic_uuid(
        LIVE_PRIMARY_BATCH_ID,
        PeCampaignV2._meta.db_table,
        campaign_id,
        version_key,
    )
    raw_payload = {
        "campaign_id": campaign_id,
        "new_video_cluster_name": new_video_cluster_name,
        "selection_json": selection_json,
        "doctors_supported": doctors_supported,
        "banner_small": banner_small,
        "banner_large": banner_large,
        "banner_target_url": banner_target_url,
        "start_date": start_date,
        "end_date": end_date,
        "video_cluster_id": video_cluster_id,
        "publisher_sub": publisher_sub,
        "publisher_username": publisher_username,
        "publisher_roles": publisher_roles,
        "email_registration": email_registration,
        "wa_addition": wa_addition,
        "created_at": created_at,
        "updated_at": updated_at,
    }
    defaults = {
        "pe_campaign_uuid": pe_campaign_uuid,
        "id": None,
        "campaign_id": campaign_id,
        "new_video_cluster_name": new_video_cluster_name,
        "selection_json": selection_json,
        "doctors_supported": doctors_supported,
        "banner_small": str(banner_small or ""),
        "banner_large": str(banner_large or ""),
        "banner_target_url": str(banner_target_url or ""),
        "start_date": start_date,
        "end_date": end_date,
        "video_cluster_id": video_cluster_id,
        "publisher_sub": publisher_sub,
        "publisher_username": publisher_username,
        "publisher_roles": publisher_roles,
        "email_registration": email_registration,
        "wa_addition": wa_addition,
        "created_at": created_at,
        "updated_at": updated_at,
        "campaign_uuid": campaign_uuid,
        "pe_campaign_id_raw": campaign_id,
        "pe_campaign_id_normalized": pe_norm,
        "master_campaign_id_normalized": pe_norm if campaign_uuid else None,
        "video_cluster_uuid": deterministic_uuid("catalog_videocluster", video_cluster_id) if video_cluster_id else None,
        "campaign_mapping_status": "mapped" if campaign_uuid else "unmapped",
        "campaign_mapping_basis": "normalized_same_campaign_id",
        **common_fields(
            source_table=PeCampaignV2._meta.db_table,
            source_pk_column="campaign_id",
            source_pk_value=campaign_id,
            source_created_at=created_at,
            source_updated_at=updated_at,
            verification_status="verified" if campaign_uuid else "manual_review",
            verification_basis="normalized_same_campaign_id" if campaign_uuid else "master_campaign_missing",
            raw_payload=raw_payload,
            valid_from=updated_at,
            migration_batch_id=LIVE_PRIMARY_BATCH_ID,
        ),
    }
    PeCampaignV2.objects.filter(is_current=True, pe_campaign_id_normalized=pe_norm).exclude(
        pe_campaign_uuid=pe_campaign_uuid
    ).update(is_current=False, valid_to=now)
    obj, _ = PeCampaignV2.objects.update_or_create(pe_campaign_uuid=pe_campaign_uuid, defaults=defaults)
    return obj


def record_doctor_share_summary_v2(
    *,
    doctor_id: str,
    doctor_name: str,
    clinic_name: str,
    increment_total: bool = False,
    last_shared_at: Any = None,
) -> PeDoctorShareSummaryV2:
    now = timezone.now()
    doctor_id = str(doctor_id or "").strip()
    existing = PeDoctorShareSummaryV2.objects.filter(is_current=True, doctor_id=doctor_id).order_by("-migrated_at").first()
    pe_doctor = PeDoctorV2.objects.filter(is_current=True, doctor_id=doctor_id).first()
    summary_uuid = deterministic_uuid(LIVE_PRIMARY_BATCH_ID, PeDoctorShareSummaryV2._meta.db_table, doctor_id)
    total_shares = int(getattr(existing, "total_shares", 0) or 0) + (1 if increment_total else 0)
    created_at = getattr(existing, "created_at", None) or now
    updated_at = now
    last_shared_at = last_shared_at or getattr(existing, "last_shared_at", None)
    raw_payload = {
        "doctor_id": doctor_id,
        "doctor_name_snapshot": doctor_name,
        "clinic_name_snapshot": clinic_name,
        "total_shares": total_shares,
        "last_shared_at": last_shared_at,
    }
    defaults = {
        "doctor_share_summary_uuid": summary_uuid,
        "id": None,
        "doctor_id": doctor_id,
        "doctor_name_snapshot": doctor_name or getattr(existing, "doctor_name_snapshot", "") or "",
        "clinic_name_snapshot": clinic_name or getattr(existing, "clinic_name_snapshot", "") or "",
        "total_shares": total_shares,
        "last_shared_at": last_shared_at,
        "created_at": created_at,
        "updated_at": updated_at,
        "doctor_uuid": pe_doctor.doctor_uuid if pe_doctor else getattr(existing, "doctor_uuid", None),
        "pe_doctor_uuid": pe_doctor.pe_doctor_uuid if pe_doctor else getattr(existing, "pe_doctor_uuid", None),
        "clinic_uuid": pe_doctor.clinic_uuid if pe_doctor else getattr(existing, "clinic_uuid", None),
        **common_fields(
            source_table=PeDoctorShareSummaryV2._meta.db_table,
            source_pk_column="doctor_id",
            source_pk_value=doctor_id,
            source_created_at=created_at,
            source_updated_at=updated_at,
            verification_status="verified" if pe_doctor else "manual_review",
            verification_basis="doctor_id_lookup" if pe_doctor else "doctor_unresolved",
            raw_payload=raw_payload,
            valid_from=updated_at,
            migration_batch_id=LIVE_PRIMARY_BATCH_ID,
        ),
    }
    PeDoctorShareSummaryV2.objects.filter(is_current=True, doctor_id=doctor_id).exclude(
        doctor_share_summary_uuid=summary_uuid
    ).update(is_current=False, valid_to=now)
    obj, _ = PeDoctorShareSummaryV2.objects.update_or_create(
        doctor_share_summary_uuid=summary_uuid,
        defaults=defaults,
    )
    return obj


def record_share_activity_v2(
    *,
    public_id: Any,
    doctor_id: str,
    doctor_name: str,
    clinic_name: str,
    shared_by_role: str,
    shared_item_type: str,
    shared_item_code: str,
    shared_item_name: str,
    language_code: str,
    recipient_reference: str,
) -> tuple[PeShareEventV2, bool]:
    public_id_s = str(public_id or "").strip()
    existing = PeShareEventV2.objects.filter(is_current=True, public_id=public_id_s).first()
    if existing:
        return existing, False

    now = timezone.now()
    summary = record_doctor_share_summary_v2(
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        clinic_name=clinic_name,
        increment_total=True,
        last_shared_at=now,
    )
    pe_doctor = PeDoctorV2.objects.filter(is_current=True, doctor_id=doctor_id).first()
    content_uuid = resolve_content_uuid(shared_item_type, shared_item_code)
    attribution = "doctor_shared" if str(shared_by_role or "").strip().lower() == "doctor" else "clinic_or_doctor_shared"
    share_event_uuid = deterministic_uuid(LIVE_PRIMARY_BATCH_ID, PeShareEventV2._meta.db_table, public_id_s)
    raw_payload = {
        "public_id": public_id_s,
        "doctor_id": doctor_id,
        "doctor_name_snapshot": doctor_name,
        "clinic_name_snapshot": clinic_name,
        "share_channel": "whatsapp",
        "shared_by_role": shared_by_role,
        "shared_item_type": shared_item_type,
        "shared_item_code": shared_item_code,
        "shared_item_name": shared_item_name,
        "language_code": language_code,
        "recipient_reference": recipient_reference,
        "recipient_reference_version": 1,
        "shared_at": now,
    }
    defaults = {
        "share_event_uuid": share_event_uuid,
        "id": None,
        "public_id": public_id_s,
        "doctor_summary_id": None,
        "doctor_id": doctor_id,
        "doctor_name_snapshot": doctor_name,
        "clinic_name_snapshot": clinic_name,
        "share_channel": "whatsapp",
        "shared_by_role": shared_by_role,
        "shared_item_type": shared_item_type,
        "shared_item_code": shared_item_code,
        "shared_item_name": shared_item_name,
        "language_code": language_code,
        "recipient_reference": recipient_reference,
        "recipient_reference_version": 1,
        "shared_at": now,
        "campaign_uuid": None,
        "pe_campaign_uuid": None,
        "doctor_uuid": pe_doctor.doctor_uuid if pe_doctor else summary.doctor_uuid,
        "pe_doctor_uuid": pe_doctor.pe_doctor_uuid if pe_doctor else summary.pe_doctor_uuid,
        "clinic_uuid": pe_doctor.clinic_uuid if pe_doctor else summary.clinic_uuid,
        "content_uuid": content_uuid,
        "share_channel_normalized": "whatsapp",
        "share_attribution_type": attribution,
        "actual_shared_by_field_rep_uuid": None,
        "assignment_credit_field_rep_uuid": None,
        "assignment_credit_basis": None,
        **common_fields(
            source_table=PeShareEventV2._meta.db_table,
            source_pk_column="public_id",
            source_pk_value=public_id_s,
            source_created_at=now,
            source_updated_at=None,
            verification_status="verified" if content_uuid else "manual_review",
            verification_basis="shared_item_type_code" if content_uuid else "content_unresolved",
            raw_payload=raw_payload,
            valid_from=now,
            migration_batch_id=LIVE_PRIMARY_BATCH_ID,
        ),
    }
    PeShareEventV2.objects.filter(is_current=True, public_id=public_id_s).exclude(
        share_event_uuid=share_event_uuid
    ).update(is_current=False, valid_to=now)
    obj, _ = PeShareEventV2.objects.update_or_create(share_event_uuid=share_event_uuid, defaults=defaults)
    return obj, True


def record_playback_event_v2(
    *,
    share_public_id: Any,
    doctor_id: str,
    doctor_name: str = "",
    clinic_name: str = "",
    page_item_type: str,
    event_type: str,
    video_code: str,
    video_name: str,
    milestone_percent: int | None,
) -> PePlaybackEventV2:
    now = timezone.now()
    share_public_id_s = str(share_public_id or "").strip()
    share = None
    if share_public_id_s:
        share = PeShareEventV2.objects.filter(is_current=True, public_id=share_public_id_s).first()
    if share:
        doctor_id = share.doctor_id
        doctor_name = share.doctor_name_snapshot
        clinic_name = share.clinic_name_snapshot
    record_doctor_share_summary_v2(
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        clinic_name=clinic_name,
        increment_total=False,
    )
    pe_doctor = PeDoctorV2.objects.filter(is_current=True, doctor_id=doctor_id).first()
    content_uuid = resolve_content_uuid("video", video_code)
    event_uuid = str(uuid.uuid4())
    basis_parts = ["share_public_id" if share else "share_unresolved"]
    basis_parts.append("video_code" if content_uuid else "content_unresolved")
    raw_payload = {
        "share_public_id": share_public_id_s,
        "doctor_id": doctor_id,
        "page_item_type": page_item_type,
        "event_type": event_type,
        "video_code": video_code,
        "video_name": video_name,
        "milestone_percent": milestone_percent,
        "occurred_at": now,
    }
    obj = PePlaybackEventV2.objects.create(
        playback_event_uuid=event_uuid,
        id=None,
        share_id=None,
        share_public_id=share_public_id_s or None,
        doctor_summary_id=None,
        doctor_id=doctor_id,
        page_item_type=page_item_type,
        event_type=event_type,
        video_code=video_code,
        video_name=video_name,
        milestone_percent=milestone_percent,
        occurred_at=now,
        share_event_uuid=share.share_event_uuid if share else None,
        doctor_uuid=pe_doctor.doctor_uuid if pe_doctor else None,
        pe_doctor_uuid=pe_doctor.pe_doctor_uuid if pe_doctor else None,
        campaign_uuid=share.campaign_uuid if share else None,
        content_uuid=content_uuid,
        assignment_credit_field_rep_uuid=share.assignment_credit_field_rep_uuid if share else None,
        event_type_normalized=str(event_type or "").strip().lower() or "unknown",
        **common_fields(
            source_table=PePlaybackEventV2._meta.db_table,
            source_pk_column="playback_event_uuid",
            source_pk_value=event_uuid,
            source_created_at=now,
            source_updated_at=None,
            verification_status="verified" if share and content_uuid else "manual_review",
            verification_basis=";".join(basis_parts),
            raw_payload=raw_payload,
            valid_from=now,
            migration_batch_id=LIVE_PRIMARY_BATCH_ID,
        ),
    )
    return obj


def record_banner_click_event_v2(
    *,
    doctor_id: str,
    doctor_name: str,
    clinic_name: str,
    page_type: str,
    banner_id: str,
    banner_name: str,
    banner_target_url: str,
) -> PeBannerClickEventV2:
    now = timezone.now()
    record_doctor_share_summary_v2(
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        clinic_name=clinic_name,
        increment_total=False,
    )
    pe_doctor = PeDoctorV2.objects.filter(is_current=True, doctor_id=doctor_id).first()
    campaign_norm = normalize_campaign_id(banner_id)
    pe_campaign = PeCampaignV2.objects.filter(is_current=True, pe_campaign_id_normalized=campaign_norm).first()
    event_uuid = str(uuid.uuid4())
    raw_payload = {
        "doctor_id": doctor_id,
        "page_type": page_type,
        "banner_id": banner_id,
        "banner_name": banner_name,
        "banner_target_url": banner_target_url,
        "clicked_at": now,
    }
    return PeBannerClickEventV2.objects.create(
        banner_click_event_uuid=event_uuid,
        id=None,
        page_type=page_type,
        banner_id=banner_id,
        banner_name=banner_name,
        banner_target_url=banner_target_url,
        clicked_at=now,
        doctor_id=doctor_id,
        doctor_summary_id=None,
        source_banner_click_id=event_uuid,
        doctor_uuid=pe_doctor.doctor_uuid if pe_doctor else None,
        pe_doctor_uuid=pe_doctor.pe_doctor_uuid if pe_doctor else None,
        campaign_uuid=pe_campaign.campaign_uuid if pe_campaign else None,
        content_uuid=None,
        **common_fields(
            source_table=PeBannerClickEventV2._meta.db_table,
            source_pk_column="banner_click_event_uuid",
            source_pk_value=event_uuid,
            source_created_at=now,
            source_updated_at=None,
            verification_status="verified" if pe_doctor else "manual_review",
            verification_basis="doctor_id_lookup;banner_id_campaign_lookup",
            raw_payload=raw_payload,
            valid_from=now,
            migration_batch_id=LIVE_PRIMARY_BATCH_ID,
        ),
    )


def sync_share_summary(summary: DoctorShareSummary) -> PeDoctorShareSummaryV2 | None:
    if not is_v2_enabled():
        return None

    summary.refresh_from_db()
    pe_doctor = PeDoctorV2.objects.filter(is_current=True, doctor_id=summary.doctor_id).first()
    defaults = {
        "doctor_share_summary_uuid": live_uuid(PeDoctorShareSummaryV2, "sharing_doctorsharesummary", summary.pk),
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
        **common_fields(
            source_table="sharing_doctorsharesummary",
            source_pk_value=summary.pk,
            source_created_at=summary.created_at,
            source_updated_at=summary.updated_at,
            verification_status="verified" if pe_doctor else "manual_review",
            verification_basis="doctor_id_lookup" if pe_doctor else "doctor_unresolved",
            raw_payload=model_payload(summary),
            valid_from=summary.created_at,
        ),
    }
    return update_current(PeDoctorShareSummaryV2, "sharing_doctorsharesummary", summary.pk, defaults)


def sync_share_activity(share: ShareActivity) -> PeShareEventV2 | None:
    if not is_v2_enabled():
        return None

    share.refresh_from_db()
    sync_share_summary(share.doctor_summary)
    pe_doctor = PeDoctorV2.objects.filter(is_current=True, doctor_id=share.doctor_id).first()
    content_uuid = resolve_content_uuid(share.shared_item_type, share.shared_item_code)
    verification_status = "verified" if content_uuid else "manual_review"
    verification_basis = "shared_item_type_code" if content_uuid else "content_unresolved"
    attribution = "doctor_shared" if str(share.shared_by_role or "").strip().lower() == "doctor" else "clinic_or_doctor_shared"
    defaults = {
        "share_event_uuid": live_uuid(PeShareEventV2, "sharing_shareactivity", share.pk),
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
        **common_fields(
            source_table="sharing_shareactivity",
            source_pk_value=share.pk,
            source_created_at=share.shared_at,
            source_updated_at=None,
            verification_status=verification_status,
            verification_basis=verification_basis,
            raw_payload=model_payload(share),
            valid_from=share.shared_at,
        ),
    }
    return update_current(PeShareEventV2, "sharing_shareactivity", share.pk, defaults)


def sync_playback_event(event: SharePlaybackEvent) -> PePlaybackEventV2 | None:
    if not is_v2_enabled():
        return None

    event.refresh_from_db()
    share_v2 = None
    if event.share_id:
        share_v2 = PeShareEventV2.objects.filter(
            is_current=True,
            source_table="sharing_shareactivity",
            source_pk_value=str(event.share_id),
        ).first()
    if not share_v2 and event.share_public_id:
        share_v2 = PeShareEventV2.objects.filter(is_current=True, public_id=str(event.share_public_id)).first()
    content_uuid = resolve_content_uuid("video", event.video_code)
    pe_doctor = PeDoctorV2.objects.filter(is_current=True, doctor_id=event.doctor_id).first()
    basis_parts = ["share_id_or_public_id" if share_v2 else "share_unresolved"]
    basis_parts.append("video_code" if content_uuid else "content_unresolved")
    defaults = {
        "playback_event_uuid": live_uuid(PePlaybackEventV2, "sharing_shareplaybackevent", event.pk),
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
        "share_event_uuid": share_v2.share_event_uuid if share_v2 else None,
        "doctor_uuid": pe_doctor.doctor_uuid if pe_doctor else None,
        "pe_doctor_uuid": pe_doctor.pe_doctor_uuid if pe_doctor else None,
        "campaign_uuid": share_v2.campaign_uuid if share_v2 else None,
        "content_uuid": content_uuid,
        "assignment_credit_field_rep_uuid": share_v2.assignment_credit_field_rep_uuid if share_v2 else None,
        "event_type_normalized": str(event.event_type or "").strip().lower() or "unknown",
        **common_fields(
            source_table="sharing_shareplaybackevent",
            source_pk_value=event.pk,
            source_created_at=event.occurred_at,
            source_updated_at=None,
            verification_status="verified" if share_v2 and content_uuid else "manual_review",
            verification_basis=";".join(basis_parts),
            raw_payload=model_payload(event),
            valid_from=event.occurred_at,
        ),
    }
    return update_current(PePlaybackEventV2, "sharing_shareplaybackevent", event.pk, defaults)


def sync_banner_click_event(click: ShareBannerClickEvent) -> PeBannerClickEventV2 | None:
    if not is_v2_enabled():
        return None

    click.refresh_from_db()
    sync_share_summary(click.doctor_summary)
    pe_doctor = PeDoctorV2.objects.filter(is_current=True, doctor_id=click.doctor_id).first()
    campaign_norm = normalize_campaign_id(click.banner_id)
    pe_campaign = PeCampaignV2.objects.filter(is_current=True, pe_campaign_id_normalized=campaign_norm).first()
    defaults = {
        "banner_click_event_uuid": live_uuid(PeBannerClickEventV2, "sharing_sharebannerclickevent", click.pk),
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
        **common_fields(
            source_table="sharing_sharebannerclickevent",
            source_pk_value=click.pk,
            source_created_at=click.clicked_at,
            source_updated_at=None,
            verification_status="verified" if pe_doctor else "manual_review",
            verification_basis="doctor_id_lookup" if pe_doctor else "doctor_unresolved",
            raw_payload=model_payload(click),
            valid_from=click.clicked_at,
        ),
    }
    return update_current(PeBannerClickEventV2, "sharing_sharebannerclickevent", click.pk, defaults)


def resolve_content_uuid(item_type: str, item_code: str) -> str | None:
    normalized = normalize_content_code(item_code)
    content_type = "video" if item_type == "video" else "video_cluster"
    item = PeContentItemV2.objects.filter(
        is_current=True,
        content_type=content_type,
        source_code_normalized=normalized,
    ).first()
    return item.content_uuid if item else None


def live_uuid(model: type[Model], source_table: str, source_pk_value: Any) -> str:
    return deterministic_uuid(LIVE_SYNC_BATCH_ID, model._meta.db_table, source_table, source_pk_value)


def update_current(model: type[Model], source_table: str, source_pk_value: Any, defaults: dict[str, Any]) -> Any:
    pk_name = model._meta.pk.name
    pk_value = defaults[pk_name]
    model.objects.filter(
        source_system=SYSTEM_NAME,
        source_table=source_table,
        source_pk_value=str(source_pk_value or ""),
        is_current=True,
    ).exclude(**{pk_name: pk_value}).update(is_current=False, valid_to=timezone.now())
    obj, _ = model.objects.update_or_create(**{pk_name: pk_value}, defaults=defaults)
    return obj


def common_fields(
    *,
    source_table: str,
    source_pk_column: str = "id",
    source_pk_value: Any,
    source_created_at: Any,
    source_updated_at: Any,
    verification_status: str,
    verification_basis: str,
    raw_payload: dict[str, Any],
    valid_from: Any,
    migration_batch_id: str = LIVE_SYNC_BATCH_ID,
) -> dict[str, Any]:
    return {
        "source_system": SYSTEM_NAME,
        "source_database": db_name("default"),
        "source_table": source_table,
        "source_pk_column": source_pk_column,
        "source_pk_value": str(source_pk_value or ""),
        "source_created_at": source_created_at,
        "source_updated_at": source_updated_at,
        "migration_batch_id": migration_batch_id,
        "migrated_at": timezone.now(),
        "verification_status": verification_status,
        "verification_basis": verification_basis,
        "is_current": True,
        "valid_from": valid_from,
        "valid_to": None,
        "raw_payload_json": to_json(raw_payload),
    }
