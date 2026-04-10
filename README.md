# PedsEdu (CPD in Clinic Portal) — Django Patient Education Platform

PedsEdu is a multi-module Django application used to:

- authenticate doctors/clinic staff against a **master MySQL database**,
- let doctors share pediatric education videos/bundles to caregivers over WhatsApp,
- render multilingual patient-facing video pages,
- track sharing and playback analytics,
- power an SSO-based publisher workflow for campaign bundle creation and field-rep doctor enrollment,
- manage core content taxonomy (therapy areas, triggers, videos, bundles).

This README reflects the repository state in April 2026.

---

## 1) Tech stack

- **Backend framework:** Django 4.2.x
- **Language/runtime:** Python 3.10+
- **Datastore:** MySQL (two connections: `default` + `master`)
- **Static serving:** WhiteNoise
- **Email:** SendGrid (SMTP by default)
- **Cache:** LocMem by default; Redis optional (`django-redis`)
- **Media handling:** Django `FileField/ImageField` (`Pillow`)
- **Process/server (prod):** Gunicorn + Nginx (deployment samples under `deploy/`)

---

## 2) Repository map

- `peds_edu/` — project settings, root URLs, AWS secret helper, master DB integration helpers.
- `accounts/` — local auth model, doctor registration/login, password reset, pincode directory tooling, master DB write/read helpers.
- `catalog/` — content models (therapy/trigger/video/bundle) + CSV import command.
- `sharing/` — doctor share page, patient pages, analytics endpoints, catalog payload caching.
- `publisher/` —
  - staff-only internal content CRUD screens (`/publisher/...`),
  - SSO/campaign flows (`/publisher-landing-page`, `/add-campaign-details`, field-rep landing, publisher APIs).
- `sso/` — JWT consume endpoint and verification logic for publisher SSO.
- `templates/`, `static/` — server-rendered UI and front-end assets.
- `CSV/` — sample master CSV files for catalog import.
- `deploy/` — SQL bootstrap + sample service/reverse proxy files.

---

## 3) Runtime architecture

### Two-DB model

1. **`default` DB** (portal DB):
   - Django auth/session tables,
   - catalog data (`catalog_*`),
   - sharing analytics (`sharing_*`),
   - campaign records (`publisher_campaign`, unmanaged model).

2. **`master` DB** (external/master system DB):
   - doctor identities/passwords,
   - campaign enrollment relations,
   - publisher allowlist tables,
   - field-rep and campaign-field-rep mapping tables.

### URL composition (root)

- `/sso/...` → SSO token consumption.
- `/publisher-landing-page`, `/add-campaign-details`, `/campaigns/...`, `/field-rep-landing-page`, `/publisher-api/...` → campaign module.
- `/accounts/...` → registration/login/password reset.
- `/clinic/<doctor_id>/share/` and `/p/<doctor_id>/...` → doctor/patient flows.
- `/publisher/...` → staff/admin content editor UI.

---

## 4) Key domain concepts

- **TherapyArea**: top-level medical grouping.
- **TriggerCluster**: legacy grouping used by trigger taxonomy.
- **Trigger**: doctor-facing trigger/problem bucket.
- **Video**: single educational content item with per-language title+YouTube URL.
- **VideoCluster**: bundle of videos tied to a trigger (campaign bundles also map here).
- **VideoClusterVideo**: join table + sort order between cluster and video.
- **VideoTriggerMap**: additional trigger mapping for video.
- **Campaign** (`publisher_campaign`, unmanaged): campaign metadata + banner assets + one created cluster.
- **ShareActivity / SharePlaybackEvent / ShareBannerClickEvent**: analytics trail.

---

## 5) Local setup

> ⚠️ Important: `peds_edu/settings.py` currently contains hardcoded DB credentials/hosts for both DBs. Local `.env` values do not override those DB values in current code.

### 5.1 Prerequisites

- Python 3.10+
- MySQL 8+
- Build deps for `mysqlclient`

Ubuntu example:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential default-libmysqlclient-dev pkg-config
```

### 5.2 Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional transliteration support used by import command:

```bash
pip install -r requirements-dev.txt
```

### 5.3 Environment file

```bash
cp .env.example .env
```

Set at minimum:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `ALLOWED_HOSTS`
- `APP_BASE_URL`
- SendGrid values (`SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`) if you need real email sends

Load env in shell:

```bash
set -a
source .env
set +a
```

### 5.4 Database and migrations

Because DB connection values in settings are currently hardcoded, either:

- provision access to those configured DB endpoints, or
- update `peds_edu/settings.py` to env-driven DB settings before local use.

Then run:

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5.5 Seed catalog from CSV

```bash
python manage.py import_master_data --path ./CSV
```

This command expects these exact file names in the path:

- `trigger_master.csv`
- `video_master.csv`
- `video_cluster_master.csv`
- `video_cluster_video_master.csv`
- `video_trigger_map_master.csv`

### 5.6 Start dev server

```bash
python manage.py runserver 0.0.0.0:8000
```

---

## 6) Core flows

### Doctor/clinic flow

1. Doctor or clinic user logs in at `/accounts/login/`.
2. Credentials are validated against master DB (`redflags_doctor` and clinic-user password columns).
3. Session stores `master_doctor_id` and role.
4. User accesses `/clinic/<doctor_id>/share/`.
5. Share page receives cached catalog JSON + signed doctor payload.
6. Front-end builds WhatsApp text and patient link (`/p/<doctor_id>/v/<video_code>/` or `/p/<doctor_id>/c/<cluster_code>/`).

### Patient flow

- Caregiver opens shared link.
- Page resolves selected language and shows video (or bundle list) with YouTube embeds.
- Playback/banner events can be posted to tracking APIs.

### Publisher/campaign flow

1. External system sends user to `/sso/consume/?token=...&campaign_id=...`.
2. JWT is verified (`HS256`, issuer/audience/exp checks).
3. Session identity is created.
4. Publisher uses campaign pages to create/edit campaign bundle metadata.
5. Field-rep link flow (`/field-rep-landing-page/`) validates rep/campaign, enrolls doctor, and routes to WhatsApp or registration.

---

## 7) Management commands

- `python manage.py import_master_data --path <dir>`
  - Imports/updates triggers/videos/clusters/mappings.
  - Can transliterate non-English titles if `ai4bharat-transliteration` is installed.

- `python manage.py build_pincode_directory --input <csv> [--output <json>]`
  - Builds `accounts/data/india_pincode_directory.json` for PIN→state lookups.

- `python manage.py ensure_campaign_enrollment --doctor-id <id>|--email <email> --campaign-id <id> [--registered-by <id>]`
  - Ensures master DB campaign enrollment rows exist.

---

## 8) Caching and invalidation

- Main doctor-share payload cache key: `clinic_catalog_payload_v7` (via `sharing.services`).
- Timeout defaults to 1 hour.
- Backend is LocMem unless `REDIS_URL` is configured.
- `catalog.signals` clears cache on catalog model changes.

---

## 9) Deployment notes

- Use Gunicorn for Django app process.
- Put Nginx in front for TLS + static/media routing.
- Run `python manage.py collectstatic` before deploy.
- Mount a persistent media path for campaign banners and doctor photos.
- Sample files:
  - `deploy/gunicorn.service`
  - `deploy/nginx.conf`
  - `deploy/mysql_create_db.sql`

---

## 10) Security and operational caveats (current codebase)

- `settings.py` includes hardcoded secrets and DB credentials; move to env/secrets manager before production hardening.
- `.env.example` also contains sensitive-looking placeholder values; rotate and sanitize before sharing publicly.
- SSO has `SSO_USE_ENV = False`, meaning defaults are used unless code is changed.
- `Campaign` model is unmanaged (`managed=False`), so schema migrations for it are not auto-managed by Django.

---

## 11) Quick route reference

- `/accounts/register/` — doctor registration
- `/accounts/login/` — doctor/clinic login
- `/accounts/request-password-reset/` — password reset request
- `/clinic/<doctor_id>/share/` — authenticated doctor share UI
- `/p/<doctor_id>/v/<video_code>/` — patient single-video page
- `/p/<doctor_id>/c/<cluster_code>/` — patient bundle page
- `/tracking/login/` and `/tracking/` — analytics dashboard login/view
- `/sso/consume/` — SSO entrypoint for publisher
- `/publisher-landing-page/`, `/add-campaign-details/`, `/campaigns/` — campaign module
- `/publisher/...` — staff content management pages
