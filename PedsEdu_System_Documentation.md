# PedsEdu System Documentation (Code-Accurate, April 2026)

## 1. Purpose of this document

This document is a technical, implementation-level description of the current repository (`/workspace/peds_edu_app`).

It is intended for:

- AI engineers onboarding to maintenance/extension work,
- backend/full-stack developers implementing new features,
- operators/deployment engineers maintaining runtime reliability.

It covers:

- architecture,
- module boundaries,
- data model,
- workflows and endpoints,
- setup/deployment,
- known technical debt and risk points.

---

## 2. System overview

PedsEdu is a Django monolith with five core business domains:

1. **Accounts**: doctor registration/login/password reset against external master DB.
2. **Catalog**: multilingual pediatric education content taxonomy and mappings.
3. **Sharing**: doctor share UI, patient pages, and usage analytics tracking.
4. **Publisher**:
   - internal staff CRUD for catalog,
   - SSO-enabled campaign publishing and field-rep onboarding flows.
5. **SSO**: JWT verification endpoint used by external publishing system.

The system is not API-first; it is mostly server-rendered templates + selective JSON APIs.

---

## 3. Architecture and runtime topology

### 3.1 Deployment style

- Single Django app process (Gunicorn in production pattern).
- Nginx reverse proxy and static/media handling (sample config in `deploy/`).
- MySQL backend.
- Optional Redis cache.

### 3.2 Dual database pattern

#### `default` DB
Stores portal-owned tables:

- Django auth/session/admin tables,
- `catalog_*` models,
- `sharing_*` analytics,
- `publisher_campaign` (via unmanaged model).

#### `master` DB
Used as system-of-record for cross-system workflows:

- doctor identity/password data,
- campaign enrollment joins,
- publisher authorization lookup,
- field-rep/campaign linking.

### 3.3 External integrations

- **SendGrid SMTP** for transactional mail.
- **WhatsApp deep links** (`wa.me`) for doctor and field-rep workflows.
- **YouTube** (`youtube-nocookie`) via per-language URLs.
- **AWS Secrets Manager** helper for fallback secret fetch.
- **External master publisher system** via SSO JWT handoff.

---

## 4. Codebase structure

```
.
├── peds_edu/                 # project config + global DB helpers
├── accounts/                 # auth/registration/password/pincode/master writes
├── catalog/                  # taxonomy and content models + importer
├── sharing/                  # share UI + patient pages + analytics endpoints
├── publisher/                # internal CRUD + campaign module + field-rep landing
├── sso/                      # JWT consume endpoint + verification
├── templates/                # django templates
├── static/                   # app CSS/JS/icons
├── CSV/                      # import seed files
├── deploy/                   # deployment snippets
└── manage.py
```

Key root URL composition (in order):

1. `/admin/`
2. `/sso/` include
3. campaign publisher routes mounted at root (`publisher.campaign_urls`)
4. sharing routes mounted at root (`sharing.urls`)
5. `/accounts/` include
6. `/publisher/` include (staff content CRUD)

Because multiple route sets are mounted at root, endpoint naming/ordering matters when introducing new paths.

---

## 5. Configuration model

### 5.1 Settings source behavior

- `load_dotenv("/var/www/secrets/.env")` is hardcoded.
- Helper `env(name, default)` reads environment with fallback/default behavior.

### 5.2 Important current-state caveat

`DATABASES["default"]` and most `master` DB credentials are currently hardcoded in `settings.py`, not environment-driven in practice.

This means local/prod behavior can diverge from `.env.example` expectations unless settings are refactored.

### 5.3 Security/session settings

- Long session age defaults (90 days unless overridden).
- Secure cookie and SSL redirect flags are env-controlled.
- `CSRF_TRUSTED_ORIGINS` includes portal domain.

### 5.4 Cache settings

- `REDIS_URL` present → `django_redis` backend.
- else `LocMemCache`.
- catalog cache timeout default: 3600s.

### 5.5 SSO settings

- `SSO_USE_ENV = False` currently hardcoded.
- Shared secret, issuer, audience are thus defaulted from in-file constants unless code is changed.

---

## 6. Data model

## 6.1 Accounts domain

### `accounts.User`
- Custom auth model (`AUTH_USER_MODEL`) with email as unique username.

### `accounts.Clinic`
- Clinic identity and location fields.
- Generates `clinic_code` if absent.

### `accounts.DoctorProfile`
- One-to-one with local user.
- Holds `doctor_id`, WhatsApp, IMC number, photo, and clinic FK.

### `accounts.RedflagsDoctor` (unmanaged)
- Maps to master table `redflags_doctor`.
- Includes doctor and clinic-user emails/password hashes.
- Used as schema mirror for integration logic.

## 6.2 Catalog domain

### Core tables
- `TherapyArea`
- `TriggerCluster`
- `Trigger`
- `Video`
- `VideoLanguage`
- `VideoCluster`
- `VideoClusterLanguage`
- `VideoClusterVideo` (through model)
- `VideoTriggerMap`

Notable constraints:

- video language uniqueness: `(video, language_code)`.
- cluster language uniqueness: `(video_cluster, language_code)`.
- cluster-video uniqueness: `(video_cluster, video)`.

## 6.3 Publisher domain

### `publisher.Campaign` (unmanaged)
Backed by MySQL table `publisher_campaign` with `managed=False`.

Contains:

- campaign id,
- one linked created `VideoCluster`,
- selection JSON,
- doctor support cap,
- banner assets/target URL,
- campaign dates,
- publisher identity snapshot,
- campaign template fields (`email_registration`, `wa_addition`).

## 6.4 Sharing analytics domain

- `DoctorShareSummary`
- `ShareActivity`
- `SharePlaybackEvent`
- `ShareBannerClickEvent`

Plus HMAC-based recipient anonymization helper using Django `SECRET_KEY`.

---

## 7. Module behavior by app

## 7.1 `accounts`

Responsibilities:

- doctor registration to master DB,
- login via master DB credential verification,
- optional local Django auth fallback,
- password reset flows for master-stored credentials and local users,
- campaign enrollment support during registration,
- SendGrid email generation/delivery,
- pincode → state/district enrichment.

Important implementation notes:

- Login sets session values like `master_doctor_id`, role, login email.
- Doctor share authorization relies on session doctor ID matching path doctor ID.
- Registration supports both `campaign_id` and `campaign-id` query conventions.
- Registration has fallback behavior for WhatsApp field naming mismatches.

## 7.2 `catalog`

Responsibilities:

- authoritative content taxonomy model layer,
- admin registrations,
- signals to clear cached catalog payload on updates,
- CSV importer command for idempotent upserts.

Importer (`import_master_data`) pipeline:

1. validates required CSV files,
2. seeds predefined trigger clusters,
3. derives therapy areas from trigger+video CSVs,
4. upserts triggers,
5. upserts videos + language rows,
6. upserts video clusters + language rows,
7. writes cluster-video and video-trigger mappings.

If `ai4bharat-transliteration` is available, importer auto-generates non-English localized titles.

## 7.3 `sharing`

Responsibilities:

- doctor share page preparation,
- patient page rendering,
- catalog JSON construction + caching,
- share/playback/banner analytics ingestion,
- tracking dashboard authentication and rendering.

`sharing.services._build_catalog_payload()` constructs one normalized payload containing:

- therapy areas,
- triggers,
- legacy `topics` (trigger clusters),
- bundles with localized names and video codes,
- videos with localized titles/urls and derived trigger/therapy metadata,
- WhatsApp message prefixes.

`sharing.views.doctor_share` enriches this payload per-request with:

- doctor id,
- doctor-specific WhatsApp prefixes,
- signed doctor payload for patient links,
- campaign-specific bundle filtering logic based on doctor support mappings.

## 7.4 `publisher` (two subdomains)

### A) Staff content CRUD (`publisher/views.py`)

`@staff_member_required` server-rendered CRUD for:

- therapy areas,
- trigger clusters,
- triggers,
- videos + multilingual inline formsets,
- bundles + language/video formsets,
- trigger maps.

### B) Campaign module (`publisher/campaign_views.py`)

Includes:

- publisher landing,
- add/edit/list campaign screens,
- search + selection expansion APIs,
- field rep landing flow.

Campaign flows interact with:

- SSO session identity,
- master DB publisher authorization checks,
- campaign metadata capture in session,
- creation/update of campaign-specific `VideoCluster` and `publisher_campaign` rows.

Field-rep landing flow includes robust parameter normalization, optional debug mode, lookup fallbacks, master DB validation, and registration/WhatsApp branching.

## 7.5 `sso`

`/sso/consume/` expects query params:

- `token` (also accepts aliases: `sso_token`, `jwt`, `access_token`),
- `campaign_id` (or `campaign-id`),
- optional `next` redirect.

Validation performed:

- HS256 signature,
- issuer/audience match,
- expiration (`exp`),
- required claims (`sub`, `username`, `roles`).

On success, it writes identity + campaign into session and redirects safely.

---

## 8. End-to-end workflows

## 8.1 Doctor login and sharing workflow

1. User authenticates on `/accounts/login/`.
2. System resolves identity/role from master DB by email and verifies password.
3. Session is set with `master_doctor_id`.
4. User opens `/clinic/<doctor_id>/share/`.
5. View validates session doctor id matches URL.
6. View fetches doctor/clinic context from master DB.
7. View builds catalog payload and applies campaign bundle restrictions.
8. Front-end creates WhatsApp deeplink with localized prefix + selected title + signed patient URL.
9. Optional tracking events are posted to sharing APIs.

## 8.2 Patient content consumption workflow

1. Caregiver opens shared patient URL.
2. System validates/decodes signed payload.
3. System resolves requested language with fallback to English.
4. Renders patient single-video or bundle page with localized labels and media links.
5. Playback milestones may be logged through `/api/playback-event/`.

## 8.3 Publisher SSO and campaign creation workflow

1. External system redirects to `/sso/consume/` with signed JWT.
2. Session is established if token is valid.
3. Publisher accesses campaign screens.
4. Publisher searches catalog and selects items.
5. App creates/updates campaign-linked cluster and `publisher_campaign` row.
6. Campaign list/edit pages allow later revision.

## 8.4 Field rep doctor onboarding workflow

1. Field rep opens `/field-rep-landing-page/?campaign-id=...&field_rep_id=...`.
2. System validates campaign and field rep mapping in master DB.
3. Rep submits doctor WhatsApp number.
4. If doctor exists, enrollment is ensured and WhatsApp redirection path is prepared.
5. If not, rep is redirected to doctor registration with campaign context prefilled.

---

## 9. APIs and machine interfaces

### Sharing APIs

- `POST /api/share-activity/`
- `POST /api/playback-event/`
- `POST /api/banner-click/`

Used by share/patient pages for analytics capture.

### Publisher APIs

- `GET /publisher-api/search/`
- `POST /publisher-api/expand-selection/`

Used by campaign UI to query/expand catalog selections.

### SSO interface

- `GET /sso/consume/`

Cross-system trust boundary. Any change here requires coordinated upstream changes.

---

## 10. Setup and developer onboarding

## 10.1 Environment bootstrap

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# optional
pip install -r requirements-dev.txt
cp .env.example .env
```

## 10.2 Database readiness

- Ensure both configured DB endpoints are reachable, or refactor settings to local DB values.
- Run migrations for managed tables:

```bash
python manage.py migrate
python manage.py createsuperuser
```

## 10.3 Content import

```bash
python manage.py import_master_data --path ./CSV
```

## 10.4 Local run

```bash
python manage.py runserver 0.0.0.0:8000
```

---

## 11. Deployment and operations

Recommended production pattern:

- Gunicorn workers serving Django app,
- Nginx reverse proxy,
- persistent media storage path,
- Redis for cache in multi-worker/multi-node deployments,
- environment/secrets manager for all sensitive values.

Operational files in repo:

- `deploy/gunicorn.service`
- `deploy/nginx.conf`
- SQL bootstrap files in `deploy/`.

---

## 12. Testing and observability guidance

Current repository has minimal automated tests (`sharing/tests.py` placeholder-level).

For reliability, add:

1. unit tests for master DB helper adapters,
2. endpoint tests for login/share/patient/SSO,
3. fixture-driven tests for importer idempotency,
4. integration tests for campaign bundle filtering rules.

Existing observability hooks:

- structured prints/logging in SSO and field-rep flows,
- `EmailLog` persistence for outbound email status,
- analytics event tables under `sharing` app.

---

## 13. Known technical debt / risk register

1. **Hardcoded secrets and DB credentials in settings**: immediate security hardening needed.
2. **Unmanaged critical tables** (`publisher_campaign`, master DB tables): schema drift risk.
3. **Mixed config style** (env + hardcoded + fallback constants): fragile deployments.
4. **Large, complex views** (notably registration and field-rep landing): refactor into services.
5. **Low automated test coverage**: high regression risk when modifying cross-system logic.

---

## 14. Extension guidelines for contributors

When adding or changing behavior:

1. Preserve two-DB boundaries (portal data vs master data).
2. Avoid direct SQL where ORM/service abstraction is viable; if using SQL, validate identifiers.
3. Keep campaign and sharing route interactions backward compatible with existing links.
4. Invalidate/share cache intentionally when catalog-facing models change.
5. Add migration + docs updates together for managed schema changes.
6. Add integration tests for any workflow touching SSO, enrollment, or link generation.

---

## 15. Command reference

```bash
# Run dev server
python manage.py runserver 0.0.0.0:8000

# Apply migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Import catalog master CSVs
python manage.py import_master_data --path ./CSV

# Build pincode directory JSON
python manage.py build_pincode_directory --input /path/to/all_india_pincode.csv

# Ensure campaign enrollment in master DB
python manage.py ensure_campaign_enrollment --doctor-id DRXXXXXX --campaign-id <uuid-or-hex>
```

---

## 16. Glossary

- **Bundle**: `VideoCluster` (group of videos shared together).
- **Trigger**: doctor-facing condition/topic cue for content discovery.
- **Campaign**: externally originated program that constrains/augments available bundles.
- **Master DB**: external operational database used for cross-system identities and enrollment.
- **Portal DB**: local Django-owned database.
