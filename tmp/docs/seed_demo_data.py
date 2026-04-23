#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "peds_edu.settings")

import django

django.setup()

from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import connections
from django.utils import timezone

from accounts.master_db import ensure_enrollment
from accounts.models import RedflagsDoctor, User
from catalog.models import Video, VideoCluster, VideoClusterLanguage, VideoClusterVideo, VideoLanguage
from peds_edu.master_db import build_patient_link_payload, fetch_master_doctor_row_by_id, master_row_to_template_context, sign_patient_payload
from publisher.models import Campaign


TMP_DOCS = ROOT / "tmp" / "docs"
MEDIA_ROOT = Path(settings.MEDIA_ROOT)
DEMO_INPUTS = TMP_DOCS / "demo-inputs"
MANIFEST_PATH = TMP_DOCS / "demo_manifest.json"


def env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "").strip()


def execute_many(alias: str, statements: Iterable[str]) -> None:
    with connections[alias].cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def make_artwork() -> dict[str, str]:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    DEMO_INPUTS.mkdir(parents=True, exist_ok=True)

    banner_dir = MEDIA_ROOT / "demo" / "banners"
    banner_dir.mkdir(parents=True, exist_ok=True)

    doctor_photo_path = DEMO_INPUTS / "doctor-photo.png"
    banner_small_path = banner_dir / "campaign-banner-small.png"
    banner_large_path = banner_dir / "campaign-banner-large.png"

    def draw_card(path: Path, size: tuple[int, int], title: str, subtitle: str, accent: tuple[int, int, int]) -> None:
        image = Image.new("RGB", size, (245, 248, 251))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((24, 24, size[0] - 24, size[1] - 24), radius=32, fill=(255, 255, 255))
        draw.rounded_rectangle((24, 24, size[0] - 24, 92), radius=32, fill=accent)
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        draw.text((48, 42), title, fill=(255, 255, 255), font=font_title)
        draw.text((48, 120), subtitle, fill=(31, 45, 61), font=font_body)
        draw.text((48, size[1] - 62), "Demo training asset", fill=(90, 105, 120), font=font_body)
        image.save(path)

    def draw_portrait(path: Path) -> None:
        image = Image.new("RGB", (512, 512), (236, 244, 247))
        draw = ImageDraw.Draw(image)
        draw.ellipse((96, 64, 416, 384), fill=(42, 167, 161))
        draw.ellipse((176, 116, 336, 276), fill=(255, 255, 255))
        draw.rounded_rectangle((156, 276, 356, 448), radius=60, fill=(47, 62, 158))
        draw.text((182, 468), "Demo Doctor", fill=(31, 45, 61), font=ImageFont.load_default())
        image.save(path)

    draw_portrait(doctor_photo_path)
    draw_card(
        banner_small_path,
        (960, 360),
        "Breathe Easy",
        "Campaign banner for the demo respiratory education workflow.",
        (42, 167, 161),
    )
    draw_card(
        banner_large_path,
        (1600, 480),
        "Pediatric Asthma Support",
        "Campaign banner shown to enrolled clinics on the sharing screen.",
        (47, 62, 158),
    )

    media_prefix = settings.MEDIA_URL.rstrip("/") + "/"
    base_url = settings.APP_BASE_URL.rstrip("/")

    return {
        "doctor_photo_path": str(doctor_photo_path),
        "banner_small_url": f"{base_url}{media_prefix}demo/banners/{banner_small_path.name}",
        "banner_large_url": f"{base_url}{media_prefix}demo/banners/{banner_large_path.name}",
    }


def ensure_default_tables() -> None:
    execute_many(
        "default",
        [
            """
            CREATE TABLE IF NOT EXISTS publisher_campaign (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                campaign_id VARCHAR(100) NOT NULL UNIQUE,
                new_video_cluster_name VARCHAR(255) NOT NULL,
                selection_json LONGTEXT NOT NULL,
                doctors_supported INT UNSIGNED NOT NULL DEFAULT 0,
                banner_small VARCHAR(500) NOT NULL DEFAULT '',
                banner_large VARCHAR(500) NOT NULL DEFAULT '',
                banner_target_url VARCHAR(500) NOT NULL DEFAULT '',
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                video_cluster_id BIGINT NOT NULL,
                publisher_sub VARCHAR(100) NOT NULL DEFAULT '',
                publisher_username VARCHAR(150) NOT NULL DEFAULT '',
                publisher_roles VARCHAR(255) NOT NULL DEFAULT '',
                email_registration LONGTEXT NOT NULL,
                wa_addition LONGTEXT NOT NULL,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                KEY publisher_campaign_video_cluster_idx (video_cluster_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
        ],
    )


def ensure_master_tables() -> None:
    execute_many(
        "master",
        [
            """
            CREATE TABLE IF NOT EXISTS campaign_authorizedpublisher (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS campaign_brand (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS campaign_fieldrep (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NULL,
                brand_supplied_field_rep_id VARCHAR(80) NOT NULL UNIQUE,
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                full_name VARCHAR(255) NOT NULL,
                phone_number VARCHAR(30) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS campaign_campaign (
                id CHAR(32) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                num_doctors_supported INT NOT NULL DEFAULT 0,
                add_to_campaign_message LONGTEXT NOT NULL,
                register_message LONGTEXT NOT NULL,
                banner_small_url VARCHAR(500) NOT NULL DEFAULT '',
                banner_large_url VARCHAR(500) NOT NULL DEFAULT '',
                banner_target_url VARCHAR(500) NOT NULL DEFAULT '',
                brand_id BIGINT NULL,
                system_pe TINYINT(1) NOT NULL DEFAULT 1,
                start_date DATE NOT NULL,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS campaign_campaignfieldrep (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                campaign_id CHAR(32) NOT NULL,
                field_rep_id BIGINT NOT NULL,
                UNIQUE KEY campaign_field_rep_unique (campaign_id, field_rep_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS campaign_doctor (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL DEFAULT '',
                phone VARCHAR(30) NOT NULL DEFAULT '',
                city VARCHAR(255) NOT NULL DEFAULT '',
                state VARCHAR(255) NOT NULL DEFAULT '',
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS campaign_doctorcampaignenrollment (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                whitelabel_enabled TINYINT(1) NOT NULL DEFAULT 1,
                whitelabel_subdomain VARCHAR(255) NOT NULL DEFAULT '',
                registered_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                campaign_id CHAR(32) NOT NULL,
                doctor_id BIGINT NOT NULL,
                registered_by_id BIGINT NULL,
                UNIQUE KEY campaign_doctor_unique (campaign_id, doctor_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS redflags_doctor (
                doctor_id VARCHAR(12) PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL DEFAULT '',
                email VARCHAR(255) NOT NULL,
                whatsapp_no VARCHAR(20) NOT NULL DEFAULT '',
                clinic_name VARCHAR(255) NOT NULL DEFAULT '',
                clinic_phone VARCHAR(20) NOT NULL DEFAULT '',
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                imc_registration_number VARCHAR(30) NOT NULL DEFAULT '',
                clinic_appointment_number VARCHAR(20) NOT NULL DEFAULT '',
                clinic_address VARCHAR(500) NOT NULL DEFAULT '',
                postal_code VARCHAR(6) NOT NULL DEFAULT '',
                state VARCHAR(64) NOT NULL DEFAULT 'Maharashtra',
                district VARCHAR(100) NOT NULL DEFAULT '',
                receptionist_whatsapp_number VARCHAR(20) NOT NULL DEFAULT '',
                photo VARCHAR(255) NOT NULL DEFAULT '',
                partner_id BIGINT NULL,
                field_rep_id VARCHAR(64) NOT NULL DEFAULT '',
                recruited_via VARCHAR(20) NOT NULL DEFAULT 'SELF',
                clinic_password_hash VARCHAR(255) NOT NULL DEFAULT '',
                clinic_password_set_at DATETIME(6) NULL,
                clinic_user1_name VARCHAR(120) NOT NULL DEFAULT '',
                clinic_user1_email VARCHAR(255) NOT NULL DEFAULT '',
                clinic_user1_password_hash VARCHAR(255) NOT NULL DEFAULT '',
                clinic_user2_name VARCHAR(120) NOT NULL DEFAULT '',
                clinic_user2_email VARCHAR(255) NOT NULL DEFAULT '',
                clinic_user2_password_hash VARCHAR(255) NOT NULL DEFAULT ''
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
        ],
    )


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def make_hs256_jwt(*, secret: str, issuer: str, audience: str, sub: str, username: str, campaign_id: str, email: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": sub,
        "username": username,
        "email": email,
        "publisher_email": email,
        "roles": ["publisher"],
        "campaign_id": campaign_id,
        "iat": now,
        "exp": now + 60 * 60,
    }
    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{b64url(signature)}"


def ensure_admin_user() -> None:
    admin_email = env("DEMO_ADMIN_EMAIL")
    admin_password = env("DEMO_ADMIN_PASSWORD")
    user, _ = User.objects.get_or_create(
        email=admin_email,
        defaults={"full_name": "Demo Admin", "is_staff": True, "is_superuser": True},
    )
    user.full_name = "Demo Admin"
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.set_password(admin_password)
    user.save()


def cleanup_existing_campaign(cluster_name: str, campaign_id: str) -> None:
    existing = Campaign.objects.filter(campaign_id=campaign_id).first()
    if existing:
        cluster = existing.video_cluster
        existing.delete()
        if cluster:
            VideoClusterVideo.objects.filter(video_cluster=cluster).delete()
            VideoClusterLanguage.objects.filter(video_cluster=cluster).delete()
            cluster.delete()

    stale_cluster_ids = list(
        VideoClusterLanguage.objects.filter(language_code="en", name__iexact=cluster_name)
        .values_list("video_cluster_id", flat=True)
    )
    if stale_cluster_ids:
        VideoClusterVideo.objects.filter(video_cluster_id__in=stale_cluster_ids).delete()
        VideoClusterLanguage.objects.filter(video_cluster_id__in=stale_cluster_ids).delete()
        VideoCluster.objects.filter(id__in=stale_cluster_ids).delete()


def seed_master_records(artwork: dict[str, str]) -> dict[str, str]:
    campaign_uuid = env("DEMO_CAMPAIGN_ID")
    campaign_id_db = campaign_uuid.replace("-", "")
    publisher_email = env("DEMO_PUBLISHER_EMAIL")
    field_rep_external_id = env("DEMO_FIELD_REP_EXTERNAL_ID")
    doctor_email = env("DEMO_DOCTOR_EMAIL")
    doctor_password = env("DEMO_DOCTOR_PASSWORD")
    staff_email = env("DEMO_CLINIC_STAFF_EMAIL")
    staff_password = env("DEMO_CLINIC_STAFF_PASSWORD")
    doctor_whatsapp = env("DEMO_EXISTING_DOCTOR_WHATSAPP")
    new_doctor_email = env("DEMO_NEW_DOCTOR_EMAIL")
    new_doctor_whatsapp = env("DEMO_NEW_DOCTOR_WHATSAPP")

    with connections["master"].cursor() as cursor:
        cursor.execute("INSERT INTO campaign_authorizedpublisher (email) VALUES (%s) ON DUPLICATE KEY UPDATE email = VALUES(email)", [publisher_email])
        cursor.execute("INSERT INTO campaign_brand (id, name) VALUES (1, %s) ON DUPLICATE KEY UPDATE name = VALUES(name)", ["Little Steps Pediatrics"])
        cursor.execute(
            """
            INSERT INTO campaign_fieldrep (brand_supplied_field_rep_id, is_active, full_name, phone_number)
            VALUES (%s, 1, %s, %s)
            ON DUPLICATE KEY UPDATE
                is_active = VALUES(is_active),
                full_name = VALUES(full_name),
                phone_number = VALUES(phone_number)
            """,
            [field_rep_external_id, "Asha Nair", "9000012345"],
        )
        cursor.execute(
            "SELECT id FROM campaign_fieldrep WHERE brand_supplied_field_rep_id = %s LIMIT 1",
            [field_rep_external_id],
        )
        field_rep_id = int(cursor.fetchone()[0])

        cursor.execute(
            """
            INSERT INTO campaign_campaign (
                id, name, num_doctors_supported, add_to_campaign_message, register_message,
                banner_small_url, banner_large_url, banner_target_url, brand_id, system_pe,
                start_date, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 1, CURDATE(), CURRENT_TIMESTAMP(6))
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                num_doctors_supported = VALUES(num_doctors_supported),
                add_to_campaign_message = VALUES(add_to_campaign_message),
                register_message = VALUES(register_message),
                banner_small_url = VALUES(banner_small_url),
                banner_large_url = VALUES(banner_large_url),
                banner_target_url = VALUES(banner_target_url),
                brand_id = VALUES(brand_id),
                system_pe = VALUES(system_pe),
                start_date = VALUES(start_date)
            """,
            [
                campaign_id_db,
                "Asthma Care Spring 2026",
                25,
                "Hello <doctor_name>, this clinic is already registered for the pediatric education campaign. Share resources here: <clinic_link>",
                "Hello <doctor_name>, welcome to the pediatric education campaign. Open your sharing portal here: <clinic_link>\nSet your password here: <setup_link>",
                artwork["banner_small_url"],
                artwork["banner_large_url"],
                "https://example.com/campaign/asthma-care",
            ],
        )
        cursor.execute(
            """
            INSERT INTO campaign_campaignfieldrep (campaign_id, field_rep_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE field_rep_id = VALUES(field_rep_id)
            """,
            [campaign_id_db, field_rep_id],
        )
        cursor.execute(
            "DELETE FROM campaign_doctorcampaignenrollment WHERE campaign_id = %s",
            [campaign_id_db],
        )
        cursor.execute(
            "DELETE FROM campaign_doctor WHERE email IN (%s, %s, %s) OR RIGHT(phone, 10) IN (%s, %s)",
            [doctor_email, staff_email, new_doctor_email, doctor_whatsapp, new_doctor_whatsapp],
        )

    RedflagsDoctor.objects.using("master").filter(email=new_doctor_email).delete()
    RedflagsDoctor.objects.using("master").filter(whatsapp_no__endswith=new_doctor_whatsapp).delete()

    RedflagsDoctor.objects.using("master").update_or_create(
        doctor_id="DR900001",
        defaults={
            "first_name": "Aarav",
            "last_name": "Menon",
            "email": doctor_email,
            "whatsapp_no": doctor_whatsapp,
            "clinic_name": "Little Steps Child Health",
            "clinic_phone": "02041234567",
            "imc_registration_number": "889977",
            "clinic_appointment_number": "02041234567",
            "clinic_address": "22 River Park Road, Pune",
            "postal_code": "411001",
            "state": "Maharashtra",
            "district": "Pune",
            "receptionist_whatsapp_number": "9980011223",
            "photo": "",
            "field_rep_id": field_rep_external_id,
            "recruited_via": "FIELD_REP",
            "clinic_password_hash": make_password(doctor_password),
            "clinic_password_set_at": timezone.now(),
            "clinic_user1_name": "Anika Rao",
            "clinic_user1_email": staff_email,
            "clinic_user1_password_hash": make_password(staff_password),
            "clinic_user2_name": "",
            "clinic_user2_email": "",
            "clinic_user2_password_hash": "",
        },
    )

    ensure_enrollment(
        doctor_id="DR900001",
        campaign_id=campaign_uuid,
        registered_by=field_rep_external_id,
    )

    return {
        "campaign_id": campaign_uuid,
        "campaign_id_db": campaign_id_db,
        "field_rep_external_id": field_rep_external_id,
        "field_rep_id": str(field_rep_id),
        "doctor_id": "DR900001",
    }


def pick_demo_content() -> dict[str, str]:
    Video.objects.update(is_published=True, is_active=True)
    VideoCluster.objects.update(is_published=True, is_active=True)

    preferred_titles = [
        "bronchiolitis in babies",
        "after an asthma attack",
        "mild head injury",
    ]

    chosen_language = None
    for phrase in preferred_titles:
        chosen_language = (
            VideoLanguage.objects.select_related("video")
            .filter(language_code="en", title__icontains=phrase, video__is_published=True)
            .order_by("video__code")
            .first()
        )
        if chosen_language:
            break

    if chosen_language is None:
        chosen_language = (
            VideoLanguage.objects.select_related("video")
            .filter(language_code="en", video__is_published=True)
            .order_by("video__code")
            .first()
        )

    if chosen_language is None:
        raise RuntimeError("No published videos were imported into the catalog.")

    cluster_language = None
    for candidate in (
        VideoClusterLanguage.objects.select_related("video_cluster")
        .filter(language_code="en", video_cluster__is_published=True)
        .order_by("video_cluster__code")
    ):
        video_count = VideoClusterVideo.objects.filter(video_cluster=candidate.video_cluster).count()
        if video_count > 1:
            cluster_language = candidate
            break

    if cluster_language is None:
        cluster_language = (
            VideoClusterLanguage.objects.select_related("video_cluster")
            .filter(language_code="en", video_cluster__is_published=True)
            .order_by("video_cluster__code")
            .first()
        )

    if cluster_language is None:
        raise RuntimeError("No published video bundles were imported into the catalog.")

    cluster = cluster_language.video_cluster
    if not VideoClusterVideo.objects.filter(video_cluster=cluster).exists():
        raise RuntimeError("Selected demo bundle does not contain any videos.")

    return {
        "video_code": chosen_language.video.code,
        "video_title": chosen_language.title,
        "cluster_code": cluster.code,
        "cluster_title": cluster_language.name,
    }


def build_manifest(master_meta: dict[str, str], content_meta: dict[str, str]) -> None:
    base_url = settings.APP_BASE_URL.rstrip("/")
    doctor_row = fetch_master_doctor_row_by_id(master_meta["doctor_id"])
    if not doctor_row:
        raise RuntimeError("Demo doctor record is missing.")

    doctor_ctx, clinic_ctx = master_row_to_template_context(doctor_row)
    patient_payload = sign_patient_payload(build_patient_link_payload(doctor_ctx, clinic_ctx))

    token = make_hs256_jwt(
        secret=env("SSO_SHARED_SECRET"),
        issuer=env("SSO_EXPECTED_ISSUER", "project1"),
        audience=env("SSO_EXPECTED_AUDIENCE", "project2"),
        sub="publisher_demo_1",
        username=env("DEMO_PUBLISHER_EMAIL"),
        campaign_id=master_meta["campaign_id"],
        email=env("DEMO_PUBLISHER_EMAIL"),
    )

    publisher_entry_url = (
        f"{base_url}/publisher-landing-page/?campaign-id={master_meta['campaign_id']}"
        f"&token={token}"
        "&num_doctors_supported=25"
        "&name=Asthma+Care+Spring+2026"
        "&company_name=Little+Steps+Pediatrics"
        "&contact_person_name=Riya+Shah"
        "&contact_person_phone=9810011001"
        "&contact_person_email=riya.shah%40pedsedu.local"
    )

    manifest = {
        "credentials": {
            "admin_email": env("DEMO_ADMIN_EMAIL"),
            "admin_password": env("DEMO_ADMIN_PASSWORD"),
            "publisher_email": env("DEMO_PUBLISHER_EMAIL"),
            "doctor_email": env("DEMO_DOCTOR_EMAIL"),
            "doctor_password": env("DEMO_DOCTOR_PASSWORD"),
            "clinic_staff_email": env("DEMO_CLINIC_STAFF_EMAIL"),
            "clinic_staff_password": env("DEMO_CLINIC_STAFF_PASSWORD"),
        },
        "campaign": {
            "campaign_id": master_meta["campaign_id"],
            "campaign_id_db": master_meta["campaign_id_db"],
            "cluster_name": env("DEMO_CAMPAIGN_CLUSTER_NAME"),
            "field_rep_external_id": master_meta["field_rep_external_id"],
        },
        "doctor": {
            "doctor_id": master_meta["doctor_id"],
            "existing_whatsapp": env("DEMO_EXISTING_DOCTOR_WHATSAPP"),
            "new_doctor_email": env("DEMO_NEW_DOCTOR_EMAIL"),
            "new_doctor_whatsapp": env("DEMO_NEW_DOCTOR_WHATSAPP"),
            "share_patient_whatsapp": env("DEMO_SHARE_PATIENT_WHATSAPP"),
        },
        "content": content_meta,
        "artifacts": {
            "doctor_photo_upload": str((DEMO_INPUTS / "doctor-photo.png").resolve()),
            "manifest": str(MANIFEST_PATH.resolve()),
        },
        "urls": {
            "login": f"{base_url}/accounts/login/",
            "register": f"{base_url}/accounts/register/",
            "share": f"{base_url}/clinic/{master_meta['doctor_id']}/share/",
            "tracking_login": f"{base_url}/tracking/login/",
            "tracking_dashboard": f"{base_url}/tracking/",
            "patient_video_hi": (
                f"{base_url}/p/{master_meta['doctor_id']}/v/{content_meta['video_code']}/"
                f"?lang=hi&d={patient_payload}"
            ),
            "patient_cluster_ta": (
                f"{base_url}/p/{master_meta['doctor_id']}/c/{content_meta['cluster_code']}/"
                f"?lang=ta&d={patient_payload}"
            ),
            "field_rep": (
                f"{base_url}/field-rep-landing-page/?campaign-id={master_meta['campaign_id']}"
                f"&field_rep_id={master_meta['field_rep_external_id']}"
            ),
            "publisher_entry": publisher_entry_url,
            "campaign_list": f"{base_url}/campaigns/",
            "publisher_dashboard": f"{base_url}/publisher/",
            "publisher_videos": f"{base_url}/publisher/videos/",
            "pe_records_login": f"{base_url}/publisher/pe-system/login/",
            "pe_records_dashboard": f"{base_url}/publisher/pe-system/",
            "system_records": f"{base_url}/publisher/system-records/",
            "admin_login": f"{base_url}/admin/login/?next=/publisher/",
        },
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def main() -> None:
    ensure_default_tables()
    ensure_master_tables()
    artwork = make_artwork()
    ensure_admin_user()
    cleanup_existing_campaign(env("DEMO_CAMPAIGN_CLUSTER_NAME"), env("DEMO_CAMPAIGN_ID"))
    master_meta = seed_master_records(artwork)
    content_meta = pick_demo_content()
    cache.clear()
    build_manifest(master_meta, content_meta)
    print(f"Demo manifest written to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
