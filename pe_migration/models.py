from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


def default_uuid() -> str:
    return str(uuid.uuid4())


class SourceTrackedModel(models.Model):
    source_system = models.CharField(max_length=40)
    source_database = models.CharField(max_length=100)
    source_table = models.CharField(max_length=120)
    source_pk_column = models.CharField(max_length=120)
    source_pk_value = models.CharField(max_length=255)
    source_created_at = models.DateTimeField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    migration_batch_id = models.CharField(max_length=64, db_index=True)
    migrated_at = models.DateTimeField(default=timezone.now)
    verification_status = models.CharField(max_length=30, db_index=True)
    verification_basis = models.CharField(max_length=100)
    is_current = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    raw_payload_json = models.TextField()

    class Meta:
        abstract = True


class SourceMigrationBatchV2(models.Model):
    migration_batch_id = models.CharField(max_length=64, primary_key=True)
    system_name = models.CharField(max_length=40, default="pe")
    database_name = models.CharField(max_length=100)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30)
    input_file_names = models.TextField()
    created_by = models.CharField(max_length=120)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "source_migration_batch_v2"

    def __str__(self) -> str:
        return f"{self.migration_batch_id} ({self.status})"


class MigrationExceptionV2(models.Model):
    exception_id = models.BigAutoField(primary_key=True)
    migration_batch_id = models.CharField(max_length=64, db_index=True)
    system_name = models.CharField(max_length=40, default="pe")
    database_name = models.CharField(max_length=100)
    source_table = models.CharField(max_length=120)
    source_pk_column = models.CharField(max_length=120)
    source_pk_value = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=40)
    issue_code = models.CharField(max_length=80, db_index=True)
    issue_details = models.TextField()
    raw_payload_json = models.TextField()
    resolution_status = models.CharField(max_length=30, default="open", db_index=True)
    resolved_by = models.CharField(max_length=120, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "migration_exception_v2"
        indexes = [
            models.Index(fields=["migration_batch_id", "issue_code"], name="mig_exc_batch_issue_idx"),
            models.Index(fields=["source_table", "source_pk_value"], name="mig_exc_source_idx"),
        ]


class PeMasterIdentityCacheV2(SourceTrackedModel):
    cache_id = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    entity_type = models.CharField(max_length=40, db_index=True)
    entity_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    source_column = models.CharField(max_length=120)
    source_value = models.CharField(max_length=255)
    source_value_normalized = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    cache_loaded_at = models.DateTimeField(default=timezone.now)
    reconciliation_status = models.CharField(max_length=30, db_index=True)
    reconciliation_basis = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "pe_master_identity_cache_v2"
        indexes = [
            models.Index(fields=["entity_type", "source_value_normalized"], name="pe_master_cache_lookup_idx"),
            models.Index(fields=["entity_type", "entity_uuid"], name="pe_master_cache_uuid_idx"),
        ]


class PeCampaignV2(SourceTrackedModel):
    pe_campaign_uuid = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    id = models.BigIntegerField(null=True, blank=True)
    campaign_id = models.CharField(max_length=100, blank=True, default="")
    new_video_cluster_name = models.CharField(max_length=255, blank=True, default="")
    selection_json = models.TextField(blank=True, default="")
    doctors_supported = models.PositiveIntegerField(default=0)
    banner_small = models.CharField(max_length=500, blank=True, default="")
    banner_large = models.CharField(max_length=500, blank=True, default="")
    banner_target_url = models.CharField(max_length=500, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    video_cluster_id = models.BigIntegerField(null=True, blank=True)
    publisher_sub = models.CharField(max_length=100, blank=True, default="")
    publisher_username = models.CharField(max_length=150, blank=True, default="")
    publisher_roles = models.CharField(max_length=255, blank=True, default="")
    email_registration = models.TextField(blank=True, default="")
    wa_addition = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    campaign_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    pe_campaign_id_raw = models.CharField(max_length=100)
    pe_campaign_id_normalized = models.CharField(max_length=100, db_index=True)
    master_campaign_id_normalized = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    video_cluster_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    campaign_mapping_status = models.CharField(max_length=30, db_index=True)
    campaign_mapping_basis = models.CharField(max_length=100)

    class Meta:
        db_table = "pe_campaign_v2"
        indexes = [
            models.Index(fields=["pe_campaign_id_normalized"], name="pe_campaign_norm_idx"),
            models.Index(fields=["campaign_mapping_status"], name="pe_campaign_map_status_idx"),
        ]


class PeClinicV2(SourceTrackedModel):
    clinic_uuid = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    id = models.BigIntegerField(null=True, blank=True)
    clinic_code = models.CharField(max_length=50, blank=True, default="")
    display_name = models.CharField(max_length=255, blank=True, default="")
    clinic_phone = models.CharField(max_length=30, blank=True, default="")
    clinic_whatsapp_number = models.CharField(max_length=30, null=True, blank=True)
    address_text = models.TextField(blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    state = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    clinic_phone_normalized = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    clinic_whatsapp_normalized = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    global_clinic_uuid = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "pe_clinic_v2"
        indexes = [
            models.Index(fields=["clinic_code"], name="pe_clinic_code_idx"),
        ]


class PeDoctorV2(SourceTrackedModel):
    pe_doctor_uuid = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    id = models.BigIntegerField(null=True, blank=True)
    doctor_id = models.CharField(max_length=32, blank=True, default="")
    whatsapp_number = models.CharField(max_length=30, blank=True, default="")
    imc_number = models.CharField(max_length=64, blank=True, default="")
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    photo = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    clinic_id = models.BigIntegerField(null=True, blank=True)
    user_id = models.BigIntegerField(null=True, blank=True)
    doctor_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    clinic_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    doctor_id_raw = models.CharField(max_length=32, blank=True, default="")
    whatsapp_normalized = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    imc_number_normalized = models.CharField(max_length=64, null=True, blank=True)
    match_status = models.CharField(max_length=30, db_index=True)
    match_basis = models.CharField(max_length=100)

    class Meta:
        db_table = "pe_doctor_v2"
        indexes = [
            models.Index(fields=["doctor_id_raw"], name="pe_doctor_raw_id_idx"),
            models.Index(fields=["match_status"], name="pe_doctor_match_status_idx"),
        ]


class PeContentItemV2(SourceTrackedModel):
    content_uuid = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    id = models.BigIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=40, db_index=True)
    source_code = models.CharField(max_length=100, null=True, blank=True)
    source_code_normalized = models.CharField(max_length=100, null=True, blank=True)
    display_name_canonical = models.CharField(max_length=255, null=True, blank=True)
    parent_content_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    language_code = models.CharField(max_length=10, null=True, blank=True)
    is_active_canonical = models.BooleanField(default=True)
    code = models.CharField(max_length=100, null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True, default="")
    name = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    doctor_trigger_label = models.CharField(max_length=255, null=True, blank=True)
    subtopic_title = models.CharField(max_length=255, null=True, blank=True)
    navigation_pathways = models.TextField(blank=True, default="")
    search_keywords = models.TextField(blank=True, default="")
    thumbnail_url = models.CharField(max_length=500, null=True, blank=True)
    youtube_url = models.CharField(max_length=500, null=True, blank=True)
    primary_therapy_id = models.BigIntegerField(null=True, blank=True)
    primary_trigger_id = models.BigIntegerField(null=True, blank=True)
    trigger_id = models.BigIntegerField(null=True, blank=True)
    cluster_id = models.BigIntegerField(null=True, blank=True)
    video_id = models.BigIntegerField(null=True, blank=True)
    video_cluster_id = models.BigIntegerField(null=True, blank=True)
    sort_order = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(null=True, blank=True)
    is_published = models.BooleanField(null=True, blank=True)
    is_primary = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pe_content_item_v2"
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "source_code_normalized"],
                name="pe_content_type_code_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["content_type", "source_code_normalized"], name="pe_content_lookup_idx"),
        ]


class PeDoctorShareSummaryV2(SourceTrackedModel):
    doctor_share_summary_uuid = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    id = models.BigIntegerField(null=True, blank=True)
    doctor_id = models.CharField(max_length=32, blank=True, default="")
    doctor_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    clinic_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    total_shares = models.PositiveBigIntegerField(default=0)
    last_shared_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    doctor_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    pe_doctor_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    clinic_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    class Meta:
        db_table = "pe_doctor_share_summary_v2"


class PeShareEventV2(SourceTrackedModel):
    share_event_uuid = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    id = models.BigIntegerField(null=True, blank=True)
    public_id = models.CharField(max_length=64, blank=True, default="")
    doctor_summary_id = models.BigIntegerField(null=True, blank=True)
    doctor_id = models.CharField(max_length=32, blank=True, default="")
    doctor_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    clinic_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    share_channel = models.CharField(max_length=30, blank=True, default="")
    shared_by_role = models.CharField(max_length=30, blank=True, default="")
    shared_item_type = models.CharField(max_length=20, blank=True, default="")
    shared_item_code = models.CharField(max_length=80, blank=True, default="")
    shared_item_name = models.CharField(max_length=255, blank=True, default="")
    language_code = models.CharField(max_length=10, blank=True, default="")
    recipient_reference = models.CharField(max_length=80, blank=True, default="")
    recipient_reference_version = models.PositiveSmallIntegerField(default=1)
    shared_at = models.DateTimeField(null=True, blank=True)
    campaign_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    pe_campaign_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    doctor_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    pe_doctor_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    clinic_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    content_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    share_channel_normalized = models.CharField(max_length=30)
    share_attribution_type = models.CharField(max_length=40)
    actual_shared_by_field_rep_uuid = models.CharField(max_length=64, null=True, blank=True)
    assignment_credit_field_rep_uuid = models.CharField(max_length=64, null=True, blank=True)
    assignment_credit_basis = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "pe_share_event_v2"
        indexes = [
            models.Index(fields=["public_id"], name="pe_share_public_id_idx"),
            models.Index(fields=["shared_item_type", "shared_item_code"], name="pe_share_item_idx"),
            models.Index(fields=["share_attribution_type"], name="pe_share_attr_idx"),
        ]


class PePlaybackEventV2(SourceTrackedModel):
    playback_event_uuid = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    id = models.BigIntegerField(null=True, blank=True)
    share_id = models.BigIntegerField(null=True, blank=True)
    share_public_id = models.CharField(max_length=64, null=True, blank=True)
    doctor_summary_id = models.BigIntegerField(null=True, blank=True)
    doctor_id = models.CharField(max_length=32, blank=True, default="")
    page_item_type = models.CharField(max_length=20, blank=True, default="")
    event_type = models.CharField(max_length=20, blank=True, default="")
    video_code = models.CharField(max_length=80, blank=True, default="")
    video_name = models.CharField(max_length=255, blank=True, default="")
    milestone_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    share_event_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    doctor_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    pe_doctor_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    campaign_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    content_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    assignment_credit_field_rep_uuid = models.CharField(max_length=64, null=True, blank=True)
    event_type_normalized = models.CharField(max_length=40)

    class Meta:
        db_table = "pe_playback_event_v2"
        indexes = [
            models.Index(fields=["share_event_uuid"], name="pe_playback_share_idx"),
            models.Index(fields=["video_code", "event_type_normalized"], name="pe_playback_video_idx"),
        ]


class PeBannerClickEventV2(SourceTrackedModel):
    banner_click_event_uuid = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    id = models.BigIntegerField(null=True, blank=True)
    page_type = models.CharField(max_length=20, blank=True, default="")
    banner_id = models.CharField(max_length=80, blank=True, default="")
    banner_name = models.CharField(max_length=255, blank=True, default="")
    banner_target_url = models.CharField(max_length=500, blank=True, default="")
    clicked_at = models.DateTimeField(null=True, blank=True)
    doctor_id = models.CharField(max_length=32, blank=True, default="")
    doctor_summary_id = models.BigIntegerField(null=True, blank=True)
    source_banner_click_id = models.CharField(max_length=255)
    doctor_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    pe_doctor_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    campaign_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    content_uuid = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    class Meta:
        db_table = "pe_banner_click_event_v2"
        indexes = [
            models.Index(fields=["source_banner_click_id"], name="pe_banner_source_idx"),
        ]


class PeRepAssignmentCreditV2(SourceTrackedModel):
    rep_assignment_credit_uuid = models.CharField(max_length=64, primary_key=True, default=default_uuid)
    campaign_uuid = models.CharField(max_length=64, db_index=True)
    doctor_uuid = models.CharField(max_length=64, db_index=True)
    field_rep_uuid = models.CharField(max_length=64, db_index=True)
    credit_type = models.CharField(max_length=40, default="assignment_recruitment_credit")
    credit_source_table = models.CharField(max_length=120)
    credit_source_pk = models.CharField(max_length=255)
    credit_effective_from = models.DateTimeField(null=True, blank=True)
    credit_effective_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pe_rep_assignment_credit_v2"
        indexes = [
            models.Index(fields=["campaign_uuid", "doctor_uuid"], name="pe_rep_credit_doc_campaign_idx"),
            models.Index(fields=["field_rep_uuid", "is_current"], name="pe_rep_credit_rep_current_idx"),
        ]
