from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs" / "product-user-flows"
ASSETS_ROOT = DOCS_ROOT / "assets"
OUTPUT_ROOT = REPO_ROOT / "output" / "doc" / "user-flow-decks"
QA_ROOT = OUTPUT_ROOT / "qa-previews"

PACK_TITLE = "PedsEdu User Flow Training Pack"
PACK_SUBTITLE = "Live-verified workflow guides for trainers, onboarding teams, and client stakeholders"
VERIFIED_ON = "2026-04-23"
STATUS_TEXT = (
    f"Live-verified against the local demo environment and refreshed with real screenshots on {VERIFIED_ON}."
)

SECTION_ORDER = [
    "Platform and Campaign Setup",
    "Clinic Onboarding and Sharing",
    "Caregiver Experience",
    "Internal Operations",
]


@dataclass(frozen=True)
class Step:
    number: int
    title: str
    user_does: str
    user_sees: str
    why_it_matters: str
    expected_result: str
    trainer_notes: str = ""
    screenshot_path: str = ""
    screenshot_caption: str = ""
    screenshot_show: str = ""
    deck_layout: str = "side"
    deck_crop: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class Workflow:
    number: int
    slug: str
    title: str
    short_title: str
    section: str
    document_purpose: str
    primary_user: str
    entry_point: str
    workflow_summary: list[str]
    success_criteria: list[str]
    related_documents: list[str]
    status: str
    steps: list[Step]
    common_issues: list[tuple[str, str]] = field(default_factory=list)
    decision_points: list[tuple[str, str, str]] = field(default_factory=list)
    cover_image: str = ""
    cover_crop: tuple[float, float, float, float] | None = None
    closing_text: str = ""
    role_map: list[tuple[str, str]] = field(default_factory=list)
    start_points: list[tuple[str, str]] = field(default_factory=list)
    flow_diagram_mermaid: str = ""

    @property
    def manual_filename(self) -> str:
        return f"{self.number:02d}-{self.slug}.md"

    @property
    def deck_filename(self) -> str:
        return f"{self.number:02d}-{self.slug}.pptx"

    @property
    def asset_dir(self) -> Path:
        return ASSETS_ROOT / f"{self.number:02d}-{self.slug}"


def rel_asset(path: str) -> str:
    return f"assets/{path}"


WORKFLOWS: list[Workflow] = [
    Workflow(
        number=1,
        slug="platform-overview-and-role-map",
        title="Platform Overview and Role Map",
        short_title="Platform Overview",
        section="Platform and Campaign Setup",
        document_purpose=(
            "Explain what the product does, which roles participate in the end-to-end journey, "
            "where each operational workflow starts, and how internal oversight surfaces support rollout."
        ),
        primary_user="Trainers, implementation leads, client stakeholders, and internal onboarding teams",
        entry_point=(
            "This overview spans the four main entry points: publisher SSO campaign links, "
            "field rep campaign links, clinic login at `/accounts/login/`, and the internal "
            "operations surfaces at `/publisher/`, `/publisher/pe-system/`, `/publisher/system-records/`, "
            "and `/tracking/`."
        ),
        workflow_summary=[
            "Publishers configure campaign-specific bundles, outreach copy, and activation windows from an authenticated landing page.",
            "Field reps recruit clinics into a campaign by checking a doctor's WhatsApp number against the master database.",
            "Doctors and clinic staff use the same clinic workspace to share a single video or a full bundle with caregivers over WhatsApp.",
            "Caregivers open secure patient pages without logging in and can switch languages directly on the page.",
            "Internal admins maintain the reusable catalog of videos, bundles, triggers, and therapy areas that power all downstream sharing.",
            "Superusers also monitor share analytics and govern PE-only or system-wide records through separate internal dashboards.",
        ],
        success_criteria=[
            "Each stakeholder can identify their entry point and the handoff to the next role.",
            "Training teams can distinguish campaign setup work from clinic-sharing work and from internal content administration.",
            "Internal teams can separate catalog maintenance, analytics review, PE-only record governance, and broader system-record maintenance.",
            "Users understand that caregiver links are generated from the clinic sharing workspace and are campaign-aware.",
        ],
        related_documents=[
            "PedsEdu_System_Documentation.md",
            "README.md",
            "02-publisher-campaign-setup.md",
            "03-field-rep-doctor-recruitment.md",
            "05-doctor-share-single-video.md",
            "09-admin-content-management.md",
            "10-share-tracking-dashboard.md",
            "11-pe-records-dashboard.md",
            "12-system-records-hub.md",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("01-platform-overview-role-map/01-login-entry.png"),
        cover_crop=(0.0, 0.0, 1.0, 1.0),
        closing_text=(
            "Use this deck first in training sessions, then move into the role-specific decks in the order "
            "shown in the master index."
        ),
        role_map=[
            ("Publisher", "Creates campaign detail records, bundle selection, and outbound templates."),
            ("Field rep", "Registers clinics into the correct campaign and handles existing-versus-new clinic routing."),
            ("Doctor", "Selects a single video or bundle and shares it with caregivers."),
            ("Clinic staff", "Uses the same clinic workspace for bundle sharing and caregiver follow-up."),
            ("Caregiver", "Consumes multilingual content through secure patient links without logging in."),
            ("Internal admin", "Maintains the master catalog, monitors sharing activity, and governs PE or system records."),
        ],
        start_points=[
            ("Publisher campaign setup", "`/publisher-landing-page/?campaign-id=...&token=...`"),
            ("Field rep recruitment", "`/field-rep-landing-page/?campaign-id=...&field_rep_id=...`"),
            ("Doctor and clinic staff sharing", "`/accounts/login/`"),
            ("Doctor self-registration", "`/accounts/register/`"),
            ("Caregiver single-video playback", "`/p/<doctor_id>/v/<video_code>/?lang=<code>&d=<signed-payload>`"),
            ("Caregiver bundle playback", "`/p/<doctor_id>/c/<cluster_code>/?lang=<code>&d=<signed-payload>`"),
            ("Internal content management", "`/admin/login/?next=/publisher/` then `/publisher/`"),
            ("Share tracking dashboard", "`/tracking/login/` then `/tracking/`"),
            ("PE records dashboard", "`/publisher/pe-system/login/` then `/publisher/pe-system/`"),
            ("System records hub", "`/admin/login/?next=/publisher/system-records/` then `/publisher/system-records/`"),
        ],
        flow_diagram_mermaid=dedent(
            """
            ```mermaid
            flowchart LR
              Publisher["Publisher / Brand Team"] --> Campaign["Campaign setup"]
              Admin["Internal admin"] --> Catalog["Catalog and bundles"]
              Admin --> Governance["Records and reporting"]
              Catalog --> Campaign
              Campaign --> FieldRep["Field rep recruitment"]
              FieldRep --> Registration["Clinic registration"]
              Registration --> Clinic["Doctor or clinic staff share workspace"]
              Catalog --> Clinic
              Clinic --> Caregiver["Caregiver patient pages"]
              Clinic --> Analytics["Share analytics"]
              Governance --> Analytics
            ```
            """
        ).strip(),
        steps=[
            Step(
                number=1,
                title="Identify the shared entry surfaces",
                user_does=(
                    "Reviews the main product entry points for publishers, field reps, clinic users, caregivers, and internal admins."
                ),
                user_sees=(
                    "Distinct role-specific URLs: external campaign links for publishers and field reps, a shared clinic login page, and staff-only publishing pages."
                ),
                why_it_matters=(
                    "Most support questions come from role confusion, so training starts by making each entry point explicit."
                ),
                expected_result=(
                    "Trainees can say which URL each role uses and which workflows require authentication."
                ),
                trainer_notes=(
                    "Doctors and clinic staff share the same login page. Caregivers do not log in at all."
                ),
                screenshot_path=rel_asset("01-platform-overview-role-map/01-login-entry.png"),
                screenshot_caption="Shared clinic login entry for registered doctors and clinic staff.",
                screenshot_show="The `/accounts/login/` page with the Login and Forgot password actions.",
                deck_layout="wide",
            ),
            Step(
                number=2,
                title="Map campaign setup to campaign activation",
                user_does=(
                    "Traces how a publisher receives an SSO-backed campaign link and adds campaign details before clinics can use that campaign."
                ),
                user_sees=(
                    "A publisher landing page that exposes the campaign context and a launch action for Add details for this campaign."
                ),
                why_it_matters=(
                    "Campaign setup controls which bundles are available downstream and what enrollment messaging is sent."
                ),
                expected_result=(
                    "Stakeholders understand that publisher work happens before field reps or clinics start sharing content."
                ),
                trainer_notes=(
                    "If campaign details already exist, the product redirects publishers into the edit flow rather than duplicating the record."
                ),
                screenshot_path=rel_asset("02-publisher-campaign-setup/01-publisher-landing.png"),
                screenshot_caption="Publisher campaign landing page.",
                screenshot_show="Campaign metadata, the Add details action, and the route into campaign management.",
            ),
            Step(
                number=3,
                title="Trace clinic enrollment from the field rep workflow",
                user_does=(
                    "Follows the field rep handoff that checks a doctor's WhatsApp number and decides whether to enroll an existing clinic or redirect a new clinic to registration."
                ),
                user_sees=(
                    "A campaign-aware field rep page with the campaign ID, enrollment counts, and a doctor WhatsApp input."
                ),
                why_it_matters=(
                    "This is the operational bridge between campaign setup and clinic activation."
                ),
                expected_result=(
                    "Trainees understand the existing-versus-new doctor decision point and the downstream handoff."
                ),
                trainer_notes=(
                    "Existing clinics are enrolled and sent a WhatsApp deeplink. New clinics are redirected to `/accounts/register/` with campaign context."
                ),
                screenshot_path=rel_asset("03-field-rep-doctor-recruitment/01-field-rep-landing.png"),
                screenshot_caption="Field rep campaign recruitment page.",
                screenshot_show="Campaign-aware registration page for a field rep.",
            ),
            Step(
                number=4,
                title="Connect clinic sharing to caregiver playback",
                user_does=(
                    "Views how doctors or clinic staff search the library, choose a video or bundle, and generate a WhatsApp share to a caregiver."
                ),
                user_sees=(
                    "The clinic sharing workspace with filter controls, bundle and video selection, and share actions."
                ),
                why_it_matters=(
                    "This is the core day-to-day workflow for clinic teams and the point where patient education becomes visible to caregivers."
                ),
                expected_result=(
                    "Users understand that caregiver links are created inside the clinic workspace and are language-aware."
                ),
                trainer_notes=(
                    "Selecting a video exposes Share Video. Selecting a bundle exposes Share Bundle."
                ),
                screenshot_path=rel_asset("05-doctor-share-single-video/01-doctor-share-single-video.png"),
                screenshot_caption="Clinic sharing workspace for a registered doctor.",
                screenshot_show="Filters, selected video state, WhatsApp input, language chooser, and share controls.",
                deck_layout="wide",
                deck_crop=(0.0, 0.18, 1.0, 0.58),
            ),
            Step(
                number=5,
                title="Show the caregiver-facing experience",
                user_does=(
                    "Opens a secure patient link to see the branded clinic context, embedded content, and language selector."
                ),
                user_sees=(
                    "A no-login patient page branded with the clinic identity and the selected educational content."
                ),
                why_it_matters=(
                    "Training is easier when caregivers know what to expect after a clinic shares content."
                ),
                expected_result=(
                    "Stakeholders can explain the caregiver experience and confirm that language switching happens on the patient page."
                ),
                trainer_notes=(
                    "Single-video links open one item. Bundle links open a multi-video collection."
                ),
                screenshot_path=rel_asset("07-caregiver-single-video-view/02-patient-video-english.png"),
                screenshot_caption="Single-video caregiver page in English.",
                screenshot_show="Doctor and clinic context, the educational video area, and the language selector.",
                deck_layout="wide",
            ),
            Step(
                number=6,
                title="Position internal administration as the catalog source of truth",
                user_does=(
                    "Reviews the internal publishing dashboard that manages reusable videos, bundles, triggers, and therapy areas."
                ),
                user_sees=(
                    "A staff-only Publishing Dashboard with links to content types, media management, and quick actions."
                ),
                why_it_matters=(
                    "Campaign setup and clinic sharing depend on this internal catalog being correct and publish-ready."
                ),
                expected_result=(
                    "Trainees understand that catalog maintenance is a separate internal responsibility."
                ),
                trainer_notes=(
                    "Catalog changes are global. Campaign-specific availability is handled later in the publisher campaign workflow."
                ),
                screenshot_path=rel_asset("09-admin-content-management/01-publisher-dashboard.png"),
                screenshot_caption="Internal Publishing Dashboard.",
                screenshot_show="The dashboard sections for content types, videos, bundles, maps, and quick actions.",
            ),
            Step(
                number=7,
                title="Show the internal oversight dashboards",
                user_does=(
                    "Reviews the internal reporting and governance surfaces used after campaigns and sharing are live."
                ),
                user_sees=(
                    "A Share Activity Overview for analytics plus separate PE Records and System Records dashboards for data maintenance."
                ),
                why_it_matters=(
                    "Operations teams need a clear split between tracking engagement, governing PE-only records, and maintaining broader system records."
                ),
                expected_result=(
                    "Trainees know which internal dashboard to open for analytics, PE-only governance, or broader record cleanup."
                ),
                trainer_notes=(
                    "The tracking dashboard uses `/tracking/login/`. The PE records dashboard uses a dedicated superuser session at `/publisher/pe-system/login/`. The System Records Hub is a local superuser route at `/publisher/system-records/`."
                ),
                screenshot_path=rel_asset("10-share-tracking-dashboard/02-tracking-dashboard.png"),
                screenshot_caption="Internal share tracking dashboard.",
                screenshot_show="The share activity summary cards and the tables for recent shares, playback events, and banner clicks.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.28),
            ),
        ],
        common_issues=[
            (
                "Wrong entry point",
                "A clinic user who opens a publisher or field rep link will not see the clinic sharing workspace. Start training by matching role to URL.",
            ),
            (
                "Documentation drift",
                "Older project notes do not always reflect current routes or environment behavior. Use live product behavior and current code as the source of truth.",
            ),
            (
                "Campaign expectations",
                "Clinic users only see campaign-supported bundles in the share workspace, so a missing bundle usually points back to campaign setup rather than a clinic-side issue.",
            ),
            (
                "Internal dashboard mix-ups",
                "The publishing dashboard, tracking dashboard, PE records dashboard, and System Records Hub are all different surfaces with different scopes and access rules.",
            ),
        ],
    ),
    Workflow(
        number=2,
        slug="publisher-campaign-setup",
        title="Publisher Campaign Setup",
        short_title="Publisher Campaign Setup",
        section="Platform and Campaign Setup",
        document_purpose=(
            "Show a publisher how to open a campaign from an SSO link, select campaign content, configure templates, and save the campaign record."
        ),
        primary_user="Publisher or brand manager using the campaign-specific SSO link",
        entry_point=(
            "Publisher SSO entry link such as `/publisher-landing-page/?campaign-id=...&token=...`."
        ),
        workflow_summary=[
            "The publisher lands on a campaign-aware page that carries campaign metadata from the upstream system.",
            "Add Campaign Details creates a local campaign record, a new campaign bundle, and the outbound registration templates used downstream.",
            "The campaign list is the operational place to confirm that a record exists and to re-open it for editing.",
        ],
        success_criteria=[
            "The campaign record exists and appears on the Campaigns list.",
            "At least one valid video or cluster has been selected and expanded into campaign content.",
            "Registration email text, existing-doctor WhatsApp text, and campaign dates are saved.",
        ],
        related_documents=[
            "01-platform-overview-and-role-map.md",
            "03-field-rep-doctor-recruitment.md",
            "../../publisher/campaign_views.py",
            "../../publisher/templates/publisher/add_campaign_details.html",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("02-publisher-campaign-setup/01-publisher-landing.png"),
        cover_crop=(0.0, 0.0, 1.0, 1.0),
        closing_text=(
            "Once this workflow is complete, field reps can recruit clinics into the campaign and clinics will inherit the campaign-supported bundle selection."
        ),
        decision_points=[
            (
                "New campaign detail set",
                "Use Add details for this campaign when the campaign has not yet been configured in this app.",
                "The app creates a new campaign record and bundle mapping.",
            ),
            (
                "Existing campaign detail set",
                "If the campaign already exists, the product redirects the publisher into the edit flow.",
                "The user updates the existing campaign instead of creating a duplicate.",
            ),
        ],
        steps=[
            Step(
                number=1,
                title="Open the publisher landing page from the campaign link",
                user_does=(
                    "Opens the authenticated campaign link supplied by the upstream system or brand workflow."
                ),
                user_sees=(
                    "Publisher Landing Page with the authenticated publisher identity, campaign ID, and campaign metadata such as company name and doctors supported."
                ),
                why_it_matters=(
                    "This page confirms the publisher is in the right campaign context before configuration begins."
                ),
                expected_result=(
                    "The publisher can verify the campaign context and proceed into Add details for this campaign."
                ),
                trainer_notes=(
                    "If no campaign ID is supplied, the landing page still opens but the add-details action is disabled."
                ),
                screenshot_path=rel_asset("02-publisher-campaign-setup/01-publisher-landing.png"),
                screenshot_caption="Publisher landing page with campaign metadata.",
                screenshot_show="Campaign metadata cards and the two main actions: add details or edit existing campaigns.",
            ),
            Step(
                number=2,
                title="Launch Add Campaign Details",
                user_does=(
                    "Selects Add details for this campaign to open the campaign form."
                ),
                user_sees=(
                    "Add Campaign Details with read-only campaign data from the master system, including the campaign ID, supported doctor count, and banner data."
                ),
                why_it_matters=(
                    "The page separates master-managed fields from the fields the publisher is allowed to configure locally."
                ),
                expected_result=(
                    "The campaign form is open and ready for local configuration."
                ),
                trainer_notes=(
                    "The master-managed banner click URL and campaign banner are informational unless the local fallback banner URL field is needed."
                ),
                screenshot_path=rel_asset("02-publisher-campaign-setup/02-add-campaign-details-empty.png"),
                screenshot_caption="Blank Add Campaign Details form.",
                screenshot_show="Read-only master fields, the new video-cluster name field, and the content search area.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.58),
            ),
            Step(
                number=3,
                title="Select the campaign videos and bundle inputs",
                user_does=(
                    "Names the campaign cluster, searches the catalog, and adds the required video or cluster items to the selected list."
                ),
                user_sees=(
                    "Search results with Add actions, a Selected items panel, and an expanded Selected videos panel showing the final content set."
                ),
                why_it_matters=(
                    "Campaign visibility downstream depends on the content selected here."
                ),
                expected_result=(
                    "The selected-items list is populated and the expanded-videos panel confirms the final campaign content."
                ),
                trainer_notes=(
                    "The form will not save if no valid videos can be expanded from the selection."
                ),
                screenshot_path=rel_asset("02-publisher-campaign-setup/03-add-campaign-details-complete.png"),
                screenshot_caption="Campaign content selection completed.",
                screenshot_show="Search results, selected items, and the expanded video list for the configured campaign.",
                deck_layout="wide",
                deck_crop=(0.0, 0.42, 1.0, 0.28),
            ),
            Step(
                number=4,
                title="Configure registration messaging and campaign dates",
                user_does=(
                    "Enters the registration email text, existing-doctor WhatsApp text, and campaign start and end dates."
                ),
                user_sees=(
                    "Text areas with merge-token placeholders such as `<doctor_name>`, `<clinic_link>`, and `<setup_link>`, plus date pickers."
                ),
                why_it_matters=(
                    "These templates drive the onboarding experience for doctors recruited into the campaign."
                ),
                expected_result=(
                    "All required campaign communication fields and dates are ready to save."
                ),
                trainer_notes=(
                    "Local templates override missing master text and should be written in trainer-ready copy before launch."
                ),
                screenshot_path=rel_asset("02-publisher-campaign-setup/03-add-campaign-details-complete.png"),
                screenshot_caption="Messaging and date configuration.",
                screenshot_show="Email registration message, WhatsApp addition message, and the campaign date controls.",
                deck_layout="wide",
                deck_crop=(0.0, 0.72, 1.0, 0.28),
            ),
            Step(
                number=5,
                title="Save the campaign and return to the landing page",
                user_does=(
                    "Clicks Save after validating the selected content and templates."
                ),
                user_sees=(
                    "The publisher landing page again, now with the campaign detail set created in the app."
                ),
                why_it_matters=(
                    "Saving creates the local campaign record and associated bundle mapping used by later workflows."
                ),
                expected_result=(
                    "The app confirms the campaign was saved successfully."
                ),
                trainer_notes=(
                    "A duplicate campaign ID is blocked and redirected to the edit flow."
                ),
                screenshot_path=rel_asset("02-publisher-campaign-setup/04-publisher-landing-after-save.png"),
                screenshot_caption="Publisher landing page after saving the campaign.",
                screenshot_show="Return state after the campaign record is created.",
            ),
            Step(
                number=6,
                title="Review the campaign from the Campaigns list",
                user_does=(
                    "Opens the Campaigns list to confirm the record and use the Edit action when needed."
                ),
                user_sees=(
                    "A searchable campaign table with campaign ID, cluster name, capacity, dates, and Edit."
                ),
                why_it_matters=(
                    "This is the operational page for verifying the saved record and managing future updates."
                ),
                expected_result=(
                    "The campaign appears in the list and can be re-opened for edits."
                ),
                trainer_notes=(
                    "Search supports campaign ID and cluster-name lookup."
                ),
                screenshot_path=rel_asset("02-publisher-campaign-setup/05-campaign-list.png"),
                screenshot_caption="Campaign list with edit actions.",
                screenshot_show="The searchable campaigns table used for verification and maintenance.",
            ),
        ],
        common_issues=[
            (
                "Expired or missing SSO context",
                "Without a valid campaign ID and token, the landing page cannot create a campaign detail set.",
            ),
            (
                "No selected videos",
                "The form saves only when the selected items expand into at least one valid video.",
            ),
            (
                "Duplicate cluster naming",
                "If the proposed campaign cluster name already exists, the user must choose a different name.",
            ),
        ],
    ),
    Workflow(
        number=3,
        slug="field-rep-doctor-recruitment",
        title="Field Rep Doctor Recruitment",
        short_title="Field Rep Recruitment",
        section="Platform and Campaign Setup",
        document_purpose=(
            "Show how a field rep uses the campaign link to recruit a clinic by checking a doctor's WhatsApp number and routing the clinic correctly."
        ),
        primary_user="Field rep assigned to a campaign",
        entry_point=(
            "Campaign recruitment link such as `/field-rep-landing-page/?campaign-id=...&field_rep_id=...`."
        ),
        workflow_summary=[
            "The field rep page validates both the campaign and the field rep against the master database before allowing recruitment.",
            "Entering an existing doctor's WhatsApp number enrolls the clinic into the campaign and opens a WhatsApp deeplink with the clinic link.",
            "Entering a new doctor's WhatsApp number redirects into the doctor registration flow with campaign context preserved.",
        ],
        success_criteria=[
            "Existing clinics are enrolled without manual database work.",
            "New clinics are redirected to the registration form with campaign context and prefilling.",
            "The field rep can explain which path happened and why.",
        ],
        related_documents=[
            "01-platform-overview-and-role-map.md",
            "04-doctor-registration-and-first-access.md",
            "../../publisher/campaign_views.py",
            "../../publisher/templates/publisher/field_rep_landing_page.html",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("03-field-rep-doctor-recruitment/01-field-rep-landing.png"),
        cover_crop=(0.0, 0.0, 1.0, 1.0),
        closing_text=(
            "When the field rep flow ends on the registration page, the next operational deck is Doctor Registration and First Access."
        ),
        decision_points=[
            (
                "Existing doctor match",
                "The entered WhatsApp number matches an existing doctor in the master database.",
                "The system ensures campaign enrollment and opens a WhatsApp message containing the clinic share link.",
            ),
            (
                "New doctor",
                "No doctor record matches the WhatsApp number.",
                "The system redirects to `/accounts/register/` with campaign and field rep context preserved.",
            ),
        ],
        steps=[
            Step(
                number=1,
                title="Open the field rep campaign page",
                user_does=(
                    "Launches the campaign recruitment link supplied for the field rep."
                ),
                user_sees=(
                    "Register doctor for campaign with the campaign ID, campaign name, and doctors registered count."
                ),
                why_it_matters=(
                    "This page confirms the field rep is working inside the correct campaign before recruitment begins."
                ),
                expected_result=(
                    "The field rep sees a valid campaign context and an input for doctor WhatsApp number."
                ),
                trainer_notes=(
                    "If the campaign license cap has been reached or the link is invalid, the page surfaces a blocking message instead of the form."
                ),
                screenshot_path=rel_asset("03-field-rep-doctor-recruitment/01-field-rep-landing.png"),
                screenshot_caption="Field rep campaign recruitment landing page.",
                screenshot_show="Campaign context cards and the single WhatsApp input used to begin recruitment.",
            ),
            Step(
                number=2,
                title="Enter the doctor's WhatsApp number",
                user_does=(
                    "Types the doctor's 10-digit WhatsApp number and prepares to submit the campaign registration check."
                ),
                user_sees=(
                    "The WhatsApp number inside the campaign-bound form with the Submit action."
                ),
                why_it_matters=(
                    "The WhatsApp number is the matching key used to determine whether the clinic already exists."
                ),
                expected_result=(
                    "The form is ready to evaluate whether the clinic is already registered."
                ),
                trainer_notes=(
                    "Use the clinic's actual doctor WhatsApp number rather than a generic clinic front-desk number when possible."
                ),
                screenshot_path=rel_asset("03-field-rep-doctor-recruitment/02-existing-doctor-number-entered.png"),
                screenshot_caption="Field rep form with an existing doctor number entered.",
                screenshot_show="The campaign registration form ready for submission.",
            ),
            Step(
                number=3,
                title="Handle an existing doctor match",
                user_does=(
                    "Submits a WhatsApp number that already belongs to a doctor in the master database."
                ),
                user_sees=(
                    "A backend-driven redirect into a WhatsApp deeplink rather than a visible intermediate success page."
                ),
                why_it_matters=(
                    "This path avoids duplicate registration and immediately gives the clinic the correct share link."
                ),
                expected_result=(
                    "The doctor is enrolled into the campaign and a WhatsApp message opens with the clinic share URL."
                ),
                trainer_notes=(
                    "The message uses the campaign's existing-doctor WhatsApp template when one is available."
                ),
                screenshot_path=rel_asset("03-field-rep-doctor-recruitment/02-existing-doctor-number-entered.png"),
                screenshot_caption="Existing doctor branch starts from the same recruitment form.",
                screenshot_show="The page state before submission on the existing-doctor path.",
                deck_layout="side",
            ),
            Step(
                number=4,
                title="Route a new doctor into registration",
                user_does=(
                    "Submits a WhatsApp number that is not yet present in the master database."
                ),
                user_sees=(
                    "The public doctor registration page with campaign and field rep parameters carried into the URL."
                ),
                why_it_matters=(
                    "This handoff preserves campaign attribution and keeps recruitment operational without manual intervention."
                ),
                expected_result=(
                    "The doctor registration form opens with campaign context in place."
                ),
                trainer_notes=(
                    "The doctor WhatsApp number can be prefilled from the field rep page to reduce re-entry."
                ),
                screenshot_path=rel_asset("03-field-rep-doctor-recruitment/03-new-doctor-redirected-to-registration.png"),
                screenshot_caption="New doctor redirected to registration.",
                screenshot_show="The doctor registration form opened from the field rep flow.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.72),
            ),
            Step(
                number=5,
                title="Hand off to clinic onboarding",
                user_does=(
                    "Explains to the clinic that the next step is completing registration and then logging into the clinic workspace."
                ),
                user_sees=(
                    "A seamless transition from field rep recruitment into clinic onboarding."
                ),
                why_it_matters=(
                    "Successful recruitment is not complete until the clinic can actually log in and share content."
                ),
                expected_result=(
                    "The clinic understands the next step and moves into registration or login."
                ),
                trainer_notes=(
                    "Use the Doctor Registration and First Access deck immediately after this one in training sessions."
                ),
                screenshot_path=rel_asset("04-doctor-registration-and-first-access/01-register-form.png"),
                screenshot_caption="Clinic onboarding handoff.",
                screenshot_show="The registration page that follows the new-doctor branch.",
            ),
        ],
        common_issues=[
            (
                "Field rep not linked to the campaign",
                "The page blocks if the field rep identity is inactive or not authorized for the supplied campaign.",
            ),
            (
                "Campaign cap reached",
                "If doctors supported has been reached, recruitment is blocked until additional licenses are available.",
            ),
            (
                "Wrong WhatsApp number",
                "Using the wrong number can route an existing clinic into the new-doctor path or vice versa, so confirm the number before submission.",
            ),
        ],
    ),
    Workflow(
        number=4,
        slug="doctor-registration-and-first-access",
        title="Doctor Registration and First Access",
        short_title="Doctor Registration",
        section="Clinic Onboarding and Sharing",
        document_purpose=(
            "Show a new clinic how to complete doctor registration and understand the first-login handoff."
        ),
        primary_user="New doctor or clinic representative completing the registration form",
        entry_point="Public registration form at `/accounts/register/`.",
        workflow_summary=[
            "The registration form creates the doctor and clinic record and can carry campaign context from the field rep flow.",
            "The page collects doctor identity, clinic profile, address, WhatsApp, and a photo upload.",
            "After successful registration, the system instructs the clinic to log in or use Forgot password to set credentials if needed.",
        ],
        success_criteria=[
            "The registration completes successfully and shows the confirmation page.",
            "The clinic receives login and clinic-link instructions by email.",
            "The clinic can proceed to login or password setup without manual admin help.",
        ],
        related_documents=[
            "03-field-rep-doctor-recruitment.md",
            "05-doctor-share-single-video.md",
            "../../accounts/views.py",
            "../../templates/accounts/register.html",
            "../../templates/accounts/register_success.html",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("04-doctor-registration-and-first-access/01-register-form.png"),
        cover_crop=(0.0, 0.0, 1.0, 0.8),
        closing_text=(
            "After registration, move directly into the clinic login and sharing workflows."
        ),
        steps=[
            Step(
                number=1,
                title="Open the registration form",
                user_does=(
                    "Starts from the public register page, either directly or from the field rep handoff."
                ),
                user_sees=(
                    "Doctor Registration with the Register your clinic heading and a full onboarding form."
                ),
                why_it_matters=(
                    "This is the official entry point for clinics that do not already exist in the system."
                ),
                expected_result=(
                    "The clinic can see all required onboarding fields before data entry begins."
                ),
                trainer_notes=(
                    "If the clinic already exists, stop and use the login or password-reset route instead of registering again."
                ),
                screenshot_path=rel_asset("04-doctor-registration-and-first-access/01-register-form.png"),
                screenshot_caption="Blank doctor registration form.",
                screenshot_show="The registration page before clinic details are entered.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.76),
            ),
            Step(
                number=2,
                title="Complete doctor and clinic details",
                user_does=(
                    "Enters the doctor's name, email, clinic name, registration number, phone numbers, address, postal code, WhatsApp number, and doctor photo."
                ),
                user_sees=(
                    "A fully populated registration form with all required onboarding fields visible."
                ),
                why_it_matters=(
                    "Accurate clinic identity and contact details are required for both login support and caregiver communication."
                ),
                expected_result=(
                    "The form is complete and ready for submission."
                ),
                trainer_notes=(
                    "The same clinic WhatsApp number is used later in caregiver-facing contact sections."
                ),
                screenshot_path=rel_asset("04-doctor-registration-and-first-access/02-register-form-completed.png"),
                screenshot_caption="Completed doctor registration form.",
                screenshot_show="Doctor profile, clinic profile, and photo upload fields filled in.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.84),
            ),
            Step(
                number=3,
                title="Submit the registration",
                user_does=(
                    "Clicks Register Doctor once all fields are complete."
                ),
                user_sees=(
                    "The same page validates the input and sends the data into the registration workflow."
                ),
                why_it_matters=(
                    "Submission creates the clinic identity used for future login and sharing."
                ),
                expected_result=(
                    "The form submits successfully with no validation errors."
                ),
                trainer_notes=(
                    "If validation fails, correct the highlighted field and resubmit instead of refreshing the page."
                ),
                screenshot_path=rel_asset("04-doctor-registration-and-first-access/02-register-form-completed.png"),
                screenshot_caption="Registration ready for submission.",
                screenshot_show="The Register Doctor action with the completed onboarding form.",
                deck_layout="wide",
                deck_crop=(0.0, 0.62, 1.0, 0.38),
            ),
            Step(
                number=4,
                title="Review the completion page and next-step instructions",
                user_does=(
                    "Reads the Registration Complete screen and follows the Login or Forgot password guidance."
                ),
                user_sees=(
                    "A confirmation page stating that credentials and the clinic link were sent to the doctor by email."
                ),
                why_it_matters=(
                    "This page closes the onboarding loop and points the clinic toward first access."
                ),
                expected_result=(
                    "The clinic understands that login is next and knows how to request a password setup link if needed."
                ),
                trainer_notes=(
                    "Current product behavior uses the Forgot password action on the login page for first-time password setup when a password has not yet been set."
                ),
                screenshot_path=rel_asset("04-doctor-registration-and-first-access/03-registration-complete.png"),
                screenshot_caption="Registration Complete confirmation screen.",
                screenshot_show="Confirmation copy, the Login link, and the first-access guidance.",
            ),
        ],
        common_issues=[
            (
                "Already registered clinic",
                "If the clinic already exists, use login or password reset instead of creating a duplicate registration.",
            ),
            (
                "Missing required fields",
                "The form requires a complete clinic profile, so blank clinic contact or address fields will block submission.",
            ),
            (
                "Password expectations",
                "The confirmation page points the user to login first and to Forgot password when a password setup link is needed.",
            ),
        ],
    ),
    Workflow(
        number=5,
        slug="doctor-share-single-video",
        title="Doctor Share Single Video",
        short_title="Doctor Single Video Share",
        section="Clinic Onboarding and Sharing",
        document_purpose=(
            "Show a doctor how to log in, search the catalog, select a single video, and share it to a caregiver through WhatsApp."
        ),
        primary_user="Registered doctor using the clinic sharing workspace",
        entry_point="Doctor login at `/accounts/login/`.",
        workflow_summary=[
            "The doctor logs into the clinic workspace and lands directly on the Share Patient Education page for the clinic.",
            "Selecting a video activates the Share Video action and generates a secure patient link in the chosen language.",
            "The caregiver receives a WhatsApp message containing the video title and the secure patient page link.",
        ],
        success_criteria=[
            "The doctor can find the correct video in the clinic workspace.",
            "A valid patient WhatsApp number and language are selected before sharing.",
            "WhatsApp opens with a prefilled message containing the secure single-video link.",
        ],
        related_documents=[
            "04-doctor-registration-and-first-access.md",
            "07-caregiver-single-video-view.md",
            "../../templates/accounts/login.html",
            "../../templates/sharing/share.html",
            "../../sharing/views.py",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("05-doctor-share-single-video/01-doctor-share-single-video.png"),
        cover_crop=(0.0, 0.18, 1.0, 0.58),
        closing_text=(
            "Use the caregiver single-video deck after this one to show exactly what the recipient sees."
        ),
        steps=[
            Step(
                number=1,
                title="Log into the clinic sharing workspace",
                user_does=(
                    "Signs in with the registered doctor email address and password."
                ),
                user_sees=(
                    "The shared Doctor Login page and, after sign-in, the clinic's Share Patient Education workspace."
                ),
                why_it_matters=(
                    "Clinic sharing is only available after a successful authenticated login."
                ),
                expected_result=(
                    "The doctor lands on the clinic share page for the correct doctor ID."
                ),
                trainer_notes=(
                    "The same login page is also used by clinic staff accounts tied to the same clinic."
                ),
                screenshot_path=rel_asset("01-platform-overview-role-map/01-login-entry.png"),
                screenshot_caption="Doctor login page.",
                screenshot_show="The login form used before entering the sharing workspace.",
            ),
            Step(
                number=2,
                title="Filter the catalog and select the target video",
                user_does=(
                    "Uses therapy, trigger, bundle, or search controls to narrow the catalog and then selects the required video."
                ),
                user_sees=(
                    "A selected video state inside the clinic sharing page, with the active bundle and the matching video highlighted."
                ),
                why_it_matters=(
                    "Selecting the video is what enables the single-video share action."
                ),
                expected_result=(
                    "The correct video is active and ready to share."
                ),
                trainer_notes=(
                    "Clicking a bundle alone is not enough for this workflow; the doctor must click the specific video to activate Share Video."
                ),
                screenshot_path=rel_asset("05-doctor-share-single-video/01-doctor-share-single-video.png"),
                screenshot_caption="Doctor workspace with a selected video.",
                screenshot_show="Catalog filters, selected bundle context, and the active video item.",
                deck_layout="wide",
                deck_crop=(0.0, 0.18, 1.0, 0.42),
            ),
            Step(
                number=3,
                title="Enter the caregiver WhatsApp number and choose language",
                user_does=(
                    "Types the caregiver's 10-digit WhatsApp number and selects the content language."
                ),
                user_sees=(
                    "The Share with Patient panel containing the patient WhatsApp field and language selector."
                ),
                why_it_matters=(
                    "The share message is personalized to the caregiver number and the selected language."
                ),
                expected_result=(
                    "The share panel is complete and ready for action."
                ),
                trainer_notes=(
                    "The clinic workspace expects a 10-digit India-format WhatsApp number."
                ),
                screenshot_path=rel_asset("05-doctor-share-single-video/01-doctor-share-single-video.png"),
                screenshot_caption="Single-video share panel ready for use.",
                screenshot_show="Patient WhatsApp input and language selection for the chosen video.",
                deck_layout="wide",
                deck_crop=(0.0, 0.47, 1.0, 0.31),
            ),
            Step(
                number=4,
                title="Share the single video through WhatsApp",
                user_does=(
                    "Clicks Share Video after the patient number, language, and selected video are all in place."
                ),
                user_sees=(
                    "The Share Single Video action tile and a backend redirect into a WhatsApp deeplink."
                ),
                why_it_matters=(
                    "This is the moment the secure caregiver link is generated and delivered."
                ),
                expected_result=(
                    "WhatsApp opens with a prefilled message containing the video title and the secure link."
                ),
                trainer_notes=(
                    "If Share Video is not visible, confirm that a specific video rather than only a bundle is selected."
                ),
                screenshot_path=rel_asset("05-doctor-share-single-video/01-doctor-share-single-video.png"),
                screenshot_caption="Share Video action tile.",
                screenshot_show="The active Share Single Video card and button.",
                deck_layout="wide",
                deck_crop=(0.0, 0.62, 1.0, 0.28),
            ),
            Step(
                number=5,
                title="Explain what the caregiver receives",
                user_does=(
                    "Reviews the caregiver-facing page to confirm the shared result."
                ),
                user_sees=(
                    "A secure patient video page with clinic branding, contact details, the selected video, and a language chooser."
                ),
                why_it_matters=(
                    "Doctors are more confident sharing content when they know exactly what the caregiver will see."
                ),
                expected_result=(
                    "The doctor can describe the caregiver experience and confirm the share worked."
                ),
                trainer_notes=(
                    "The caregiver page does not require login. Language can be changed after the link is opened."
                ),
                screenshot_path=rel_asset("07-caregiver-single-video-view/01-patient-video-hindi.png"),
                screenshot_caption="Shared caregiver page for a single video.",
                screenshot_show="Clinic branding, doctor context, and the linked educational video in the chosen language.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.86),
            ),
        ],
        common_issues=[
            (
                "Share button not available",
                "Share Video appears only after a specific video is selected.",
            ),
            (
                "Invalid WhatsApp number",
                "The share form expects a 10-digit number and will not work correctly with partial or formatted values.",
            ),
            (
                "Wrong content level",
                "If the doctor wants the caregiver to receive a full collection rather than one item, switch to the bundle-sharing workflow instead.",
            ),
        ],
    ),
    Workflow(
        number=6,
        slug="clinic-staff-share-bundle",
        title="Clinic Staff Share Bundle",
        short_title="Clinic Staff Bundle Share",
        section="Clinic Onboarding and Sharing",
        document_purpose=(
            "Show a clinic staff member how to log in to the same clinic workspace, choose a full bundle, and share it with a caregiver."
        ),
        primary_user="Registered clinic staff user linked to an existing clinic",
        entry_point="Clinic staff login at `/accounts/login/`.",
        workflow_summary=[
            "Clinic staff use the same clinic share workspace as doctors, but they often share complete bundles for repeated counseling.",
            "Selecting a bundle activates Share Bundle and produces a secure multi-video patient link.",
            "The caregiver receives a WhatsApp deeplink to a page that contains the full bundle in the chosen language.",
        ],
        success_criteria=[
            "The clinic staff user can log in to the correct clinic workspace.",
            "A full bundle is selected and the caregiver number and language are set.",
            "The WhatsApp deeplink contains the secure bundle page rather than a single-video link.",
        ],
        related_documents=[
            "05-doctor-share-single-video.md",
            "08-caregiver-bundle-view.md",
            "../../templates/accounts/login.html",
            "../../templates/sharing/share.html",
            "../../sharing/views.py",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("06-clinic-staff-share-bundle/01-clinic-staff-share-bundle.png"),
        cover_crop=(0.0, 0.18, 1.0, 0.58),
        closing_text=(
            "Follow this deck with the caregiver bundle view deck whenever staff need to understand the recipient experience."
        ),
        decision_points=[
            (
                "Share a single video",
                "Use when the caregiver needs one targeted item only.",
                "Select the video and use Share Video.",
            ),
            (
                "Share a complete bundle",
                "Use when the caregiver should receive the full condition-specific sequence.",
                "Select the bundle and use Share Bundle.",
            ),
        ],
        steps=[
            Step(
                number=1,
                title="Log in with clinic staff credentials",
                user_does=(
                    "Signs in through the shared clinic login page with the clinic staff email and password."
                ),
                user_sees=(
                    "The same clinic-sharing workspace used by doctors."
                ),
                why_it_matters=(
                    "Clinic staff do not need a separate app; they work inside the same operational share page."
                ),
                expected_result=(
                    "The clinic share workspace opens for the correct clinic."
                ),
                trainer_notes=(
                    "The page layout is role-aware only for access control and banners; the main sharing controls remain the same."
                ),
                screenshot_path=rel_asset("01-platform-overview-role-map/01-login-entry.png"),
                screenshot_caption="Shared clinic login page for staff and doctors.",
                screenshot_show="The common login page used before entering the clinic share workspace.",
            ),
            Step(
                number=2,
                title="Select the required bundle",
                user_does=(
                    "Uses the bundle selector and search tools to choose the correct caregiver education bundle."
                ),
                user_sees=(
                    "The active bundle context with the videos listed beneath it."
                ),
                why_it_matters=(
                    "Bundle selection determines the collection of videos the caregiver will receive."
                ),
                expected_result=(
                    "The correct bundle is active and visible in the clinic workspace."
                ),
                trainer_notes=(
                    "For this workflow the staff user should stop at the bundle level instead of clicking down into a single video."
                ),
                screenshot_path=rel_asset("06-clinic-staff-share-bundle/01-clinic-staff-share-bundle.png"),
                screenshot_caption="Clinic staff workspace with a selected bundle.",
                screenshot_show="Bundle selection, listed videos, and the context for sharing the full collection.",
                deck_layout="wide",
                deck_crop=(0.0, 0.18, 1.0, 0.40),
            ),
            Step(
                number=3,
                title="Enter the caregiver number and set language",
                user_does=(
                    "Types the caregiver WhatsApp number and selects the preferred language for the bundle link."
                ),
                user_sees=(
                    "The Share with Patient panel containing the WhatsApp field and language picker."
                ),
                why_it_matters=(
                    "The caregiver's number and chosen language are required to build the correct WhatsApp message."
                ),
                expected_result=(
                    "The share panel is ready for the bundle action."
                ),
                trainer_notes=(
                    "Bundle shares are especially useful when the clinic wants caregivers to review a full set of counseling videos over time."
                ),
                screenshot_path=rel_asset("06-clinic-staff-share-bundle/01-clinic-staff-share-bundle.png"),
                screenshot_caption="Bundle share panel ready for action.",
                screenshot_show="Patient WhatsApp input and language selection for the selected bundle.",
                deck_layout="wide",
                deck_crop=(0.0, 0.46, 1.0, 0.26),
            ),
            Step(
                number=4,
                title="Share the complete bundle",
                user_does=(
                    "Clicks Share Bundle once the patient number, language, and bundle are confirmed."
                ),
                user_sees=(
                    "The Share Complete Bundle card with the Share Bundle button and a redirect into WhatsApp."
                ),
                why_it_matters=(
                    "This action creates a secure bundle page that preserves the clinic context and language choice."
                ),
                expected_result=(
                    "WhatsApp opens with a prefilled message containing the secure bundle link."
                ),
                trainer_notes=(
                    "If Share Bundle is hidden, confirm that the user selected the bundle instead of a single video."
                ),
                screenshot_path=rel_asset("06-clinic-staff-share-bundle/01-clinic-staff-share-bundle.png"),
                screenshot_caption="Share Bundle action tile.",
                screenshot_show="The active Share Complete Bundle card and button.",
                deck_layout="wide",
                deck_crop=(0.0, 0.62, 1.0, 0.26),
            ),
            Step(
                number=5,
                title="Review the caregiver bundle page outcome",
                user_does=(
                    "Checks the recipient experience to make sure the caregiver receives the full collection."
                ),
                user_sees=(
                    "A secure bundle page listing multiple videos under the selected bundle title."
                ),
                why_it_matters=(
                    "This confirms that the clinic sent a collection and not only a single item."
                ),
                expected_result=(
                    "The clinic staff user can describe how the caregiver will step through the bundle."
                ),
                trainer_notes=(
                    "Language changes happen on the patient page and refresh the bundle display."
                ),
                screenshot_path=rel_asset("08-caregiver-bundle-view/02-patient-bundle-english.png"),
                screenshot_caption="Caregiver bundle page in English.",
                screenshot_show="Bundle title, multiple video items, and the language selector on the caregiver page.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.76),
            ),
        ],
        common_issues=[
            (
                "Single-video selection by mistake",
                "If a staff user clicks a video, the UI switches toward Share Video. Return to the bundle selector to share the whole collection.",
            ),
            (
                "Incomplete caregiver number",
                "Bundle sharing expects the same 10-digit WhatsApp number format as single-video sharing.",
            ),
            (
                "Campaign visibility limits",
                "If the expected bundle does not appear, confirm that the current clinic is supported by the campaign that contains that bundle.",
            ),
        ],
    ),
    Workflow(
        number=7,
        slug="caregiver-single-video-view",
        title="Caregiver Single Video View",
        short_title="Caregiver Single Video View",
        section="Caregiver Experience",
        document_purpose=(
            "Show what a caregiver sees after opening a shared single-video link from WhatsApp."
        ),
        primary_user="Caregiver receiving a single-video patient link",
        entry_point=(
            "Secure patient link in WhatsApp such as `/p/<doctor_id>/v/<video_code>/?lang=<code>&d=<signed-payload>`."
        ),
        workflow_summary=[
            "The caregiver does not log in and is taken directly to a patient page branded with the clinic and doctor context.",
            "The page exposes clinic phone and WhatsApp contact options, the selected video, and a language picker.",
            "Changing language reloads the page content in the chosen language while keeping the clinic context intact.",
        ],
        success_criteria=[
            "The caregiver can identify which clinic sent the content.",
            "The video page loads with the selected language and content title.",
            "The caregiver can switch language without re-requesting a new share link.",
        ],
        related_documents=[
            "05-doctor-share-single-video.md",
            "../../templates/sharing/patient_video.html",
            "../../sharing/views.py",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("07-caregiver-single-video-view/02-patient-video-english.png"),
        cover_crop=(0.0, 0.0, 1.0, 0.88),
        closing_text=(
            "This view is the direct result of a single-video WhatsApp share from the clinic workspace."
        ),
        steps=[
            Step(
                number=1,
                title="Open the secure patient link from WhatsApp",
                user_does=(
                    "Taps the shared clinic link in WhatsApp."
                ),
                user_sees=(
                    "A branded patient page showing the doctor name, clinic name, address, contact options, and the selected educational video."
                ),
                why_it_matters=(
                    "The caregiver immediately knows which clinic sent the content and that no login is required."
                ),
                expected_result=(
                    "The patient page loads successfully in the default shared language."
                ),
                trainer_notes=(
                    "The link is signed and tied to the clinic context, so caregivers should use the original shared message rather than trying to rebuild the URL."
                ),
                screenshot_path=rel_asset("07-caregiver-single-video-view/01-patient-video-hindi.png"),
                screenshot_caption="Single-video caregiver page in Hindi.",
                screenshot_show="Clinic branding, doctor context, contact pills, and the educational video title.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.88),
            ),
            Step(
                number=2,
                title="Review clinic contact information and context",
                user_does=(
                    "Checks the doctor identity, clinic name, address, phone, and WhatsApp contact chips before watching the content."
                ),
                user_sees=(
                    "Doctor and clinic details at the top of the patient page."
                ),
                why_it_matters=(
                    "This reinforces trust and gives the caregiver clear return-contact options."
                ),
                expected_result=(
                    "The caregiver can identify the sending clinic and the available contact routes."
                ),
                trainer_notes=(
                    "Use this section during training to show where caregivers go if they need to call or message the clinic."
                ),
                screenshot_path=rel_asset("07-caregiver-single-video-view/02-patient-video-english.png"),
                screenshot_caption="Clinic context on the caregiver page.",
                screenshot_show="Doctor name, clinic details, address, and clinic contact pills.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.36),
            ),
            Step(
                number=3,
                title="Watch the educational video",
                user_does=(
                    "Plays the embedded video or uses the fallback behavior if the source cannot be embedded."
                ),
                user_sees=(
                    "A video player area underneath the title and language selector."
                ),
                why_it_matters=(
                    "The patient page keeps the clinic identity visible while the caregiver consumes the content."
                ),
                expected_result=(
                    "The caregiver can start the content from the same page without extra navigation."
                ),
                trainer_notes=(
                    "Some source videos may have external playback limitations. If that occurs, direct the caregiver to the fallback action shown by the page."
                ),
                screenshot_path=rel_asset("07-caregiver-single-video-view/02-patient-video-english.png"),
                screenshot_caption="Embedded single-video player.",
                screenshot_show="The educational video area inside the patient page.",
                deck_layout="wide",
                deck_crop=(0.0, 0.29, 1.0, 0.62),
            ),
            Step(
                number=4,
                title="Switch language on the patient page",
                user_does=(
                    "Uses the Language selector to change from the originally shared language to another supported language."
                ),
                user_sees=(
                    "A language dropdown on the top-right of the patient content card."
                ),
                why_it_matters=(
                    "The caregiver can self-serve into a more comfortable language without asking the clinic to resend the link."
                ),
                expected_result=(
                    "The page reloads with the selected language and retains the clinic context."
                ),
                trainer_notes=(
                    "Changing language reloads the content rather than opening a separate application."
                ),
                screenshot_path=rel_asset("07-caregiver-single-video-view/02-patient-video-english.png"),
                screenshot_caption="Language selector on the single-video page.",
                screenshot_show="The Language control used to change the caregiver page language.",
                deck_layout="wide",
                deck_crop=(0.65, 0.22, 0.35, 0.18),
            ),
        ],
        common_issues=[
            (
                "Link opened outside the original message",
                "Caregivers should use the original shared link because it contains the signed context needed by the patient page.",
            ),
            (
                "Video source limitations",
                "If a source blocks inline playback, rely on the page's fallback behavior rather than assuming the clinic shared the wrong link.",
            ),
            (
                "Language expectations",
                "The shared link may open in a preset language, but the caregiver can change it from the page itself.",
            ),
        ],
    ),
    Workflow(
        number=8,
        slug="caregiver-bundle-view",
        title="Caregiver Bundle View",
        short_title="Caregiver Bundle View",
        section="Caregiver Experience",
        document_purpose=(
            "Show what a caregiver sees after receiving a bundle link that contains multiple educational videos."
        ),
        primary_user="Caregiver receiving a bundle patient link",
        entry_point=(
            "Secure bundle link in WhatsApp such as `/p/<doctor_id>/c/<cluster_code>/?lang=<code>&d=<signed-payload>`."
        ),
        workflow_summary=[
            "The caregiver lands on a multi-video patient page that retains the same clinic context as the single-video flow.",
            "The bundle page presents the collection title, the number of videos, and each video in sequence on the same page.",
            "The caregiver can switch language directly on the bundle page to reload the collection in another language.",
        ],
        success_criteria=[
            "The caregiver can see that the page contains a full collection rather than one video.",
            "The page shows the clinic identity and the selected bundle title clearly.",
            "Language can be changed on the same page without needing a new message from the clinic.",
        ],
        related_documents=[
            "06-clinic-staff-share-bundle.md",
            "../../templates/sharing/patient_cluster.html",
            "../../sharing/views.py",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("08-caregiver-bundle-view/02-patient-bundle-english.png"),
        cover_crop=(0.0, 0.0, 1.0, 0.82),
        closing_text=(
            "This page is the caregiver outcome when clinic staff or doctors use Share Bundle from the clinic workspace."
        ),
        steps=[
            Step(
                number=1,
                title="Open the secure bundle link",
                user_does=(
                    "Taps the WhatsApp link that was shared from the clinic."
                ),
                user_sees=(
                    "A clinic-branded bundle page showing the doctor identity, clinic details, bundle title, and video count."
                ),
                why_it_matters=(
                    "The caregiver immediately knows this is a collection of related educational videos rather than a single item."
                ),
                expected_result=(
                    "The bundle page opens in the shared language and shows the correct clinic context."
                ),
                trainer_notes=(
                    "The bundle page keeps the same trust signals as the single-video page: doctor, clinic, address, and contact options."
                ),
                screenshot_path=rel_asset("08-caregiver-bundle-view/01-patient-bundle-tamil.png"),
                screenshot_caption="Bundle page in Tamil.",
                screenshot_show="Clinic branding, doctor context, and the bundle title with video count.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.42),
            ),
            Step(
                number=2,
                title="Review the bundle title and listed videos",
                user_does=(
                    "Scrolls through the bundle to understand the sequence of educational videos provided by the clinic."
                ),
                user_sees=(
                    "Multiple video cards stacked under the bundle heading."
                ),
                why_it_matters=(
                    "The caregiver can consume the collection as a guided set rather than looking for separate links."
                ),
                expected_result=(
                    "The caregiver can identify how many videos are included and where each video begins."
                ),
                trainer_notes=(
                    "During training, show caregivers how to continue scrolling after the first video rather than assuming the page stops there."
                ),
                screenshot_path=rel_asset("08-caregiver-bundle-view/02-patient-bundle-english.png"),
                screenshot_caption="Bundle page showing multiple video entries.",
                screenshot_show="The bundle title and the stacked list of included videos.",
                deck_layout="wide",
                deck_crop=(0.0, 0.18, 1.0, 0.64),
            ),
            Step(
                number=3,
                title="Play the videos in sequence",
                user_does=(
                    "Starts with the first item and continues through the remaining content in the bundle."
                ),
                user_sees=(
                    "Each video embedded inside its own content card on the same patient page."
                ),
                why_it_matters=(
                    "The bundle workflow is designed for structured counseling or follow-up, not one-off playback."
                ),
                expected_result=(
                    "The caregiver can navigate the sequence without needing more links."
                ),
                trainer_notes=(
                    "Some sources may show video-availability limitations from the provider. That is a source behavior, not a clinic-sharing failure."
                ),
                screenshot_path=rel_asset("08-caregiver-bundle-view/01-patient-bundle-tamil.png"),
                screenshot_caption="Embedded videos inside the bundle page.",
                screenshot_show="The first and second bundle videos displayed on the same page.",
                deck_layout="wide",
                deck_crop=(0.0, 0.18, 1.0, 0.58),
            ),
            Step(
                number=4,
                title="Change language for the full bundle",
                user_does=(
                    "Uses the Language dropdown to switch the bundle page into another supported language."
                ),
                user_sees=(
                    "A single language control that refreshes the full bundle page."
                ),
                why_it_matters=(
                    "The caregiver does not need the clinic to send a second bundle link for another language."
                ),
                expected_result=(
                    "The bundle page reloads in the chosen language while keeping the clinic context and video sequence."
                ),
                trainer_notes=(
                    "Show caregivers that the language control lives in the bundle header area and applies across the whole page."
                ),
                screenshot_path=rel_asset("08-caregiver-bundle-view/02-patient-bundle-english.png"),
                screenshot_caption="Language selector on the bundle page.",
                screenshot_show="The top-right language control used to refresh the bundle in a new language.",
                deck_layout="wide",
                deck_crop=(0.66, 0.08, 0.34, 0.18),
            ),
        ],
        common_issues=[
            (
                "Bundle versus single-video expectation",
                "Caregivers should expect a scrollable sequence of videos on this page, not a single embedded item only.",
            ),
            (
                "Video source restrictions",
                "When a provider blocks embedded playback, the issue is with the source content rather than the clinic share action.",
            ),
            (
                "Language confusion",
                "The selected language applies to the bundle page itself, so remind caregivers to use the top-right selector if the default language is not ideal.",
            ),
        ],
    ),
    Workflow(
        number=9,
        slug="admin-content-management",
        title="Admin Content Management",
        short_title="Admin Content Management",
        section="Internal Operations",
        document_purpose=(
            "Show internal staff how to enter the publishing dashboard, review the video catalog, and edit a video's metadata and language rows."
        ),
        primary_user="Internal admin or staff user with access to the publishing dashboard",
        entry_point="Staff login at `/admin/login/?next=/publisher/` leading into `/publisher/`.",
        workflow_summary=[
            "The publishing dashboard is the internal catalog-management surface for therapy areas, triggers, videos, bundles, and bundle-trigger maps.",
            "The Videos list is the fastest route for reviewing published media and opening a specific video for editing.",
            "Video edit pages enforce the rule that each video belongs to at least one bundle and carries language-specific title and YouTube URL rows.",
            "Campaign record governance and master data cleanup happen in the separate PE Records and System Records workflows, not on this dashboard.",
        ],
        success_criteria=[
            "The admin can open the publishing dashboard and navigate to Videos.",
            "The target video can be found from the list and opened for editing.",
            "Language rows and video metadata are updated without breaking the bundle relationship rule.",
        ],
        related_documents=[
            "01-platform-overview-and-role-map.md",
            "11-pe-records-dashboard.md",
            "12-system-records-hub.md",
            "../../publisher/templates/publisher/dashboard.html",
            "../../publisher/templates/publisher/video_list.html",
            "../../publisher/templates/publisher/video_form.html",
            "../../publisher/views.py",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("09-admin-content-management/01-publisher-dashboard.png"),
        cover_crop=(0.0, 0.0, 1.0, 0.82),
        closing_text=(
            "Catalog maintenance is global. Use the PE Records or System Records dashboards when the work involves campaign, field-rep, or doctor records instead of reusable content."
        ),
        steps=[
            Step(
                number=1,
                title="Open the Publishing Dashboard",
                user_does=(
                    "Signs in with an internal staff account and lands on the publishing dashboard."
                ),
                user_sees=(
                    "Publishing Dashboard with grouped links for content types, videos, bundles, maps, and quick actions."
                ),
                why_it_matters=(
                    "This is the root navigation page for all internal content maintenance."
                ),
                expected_result=(
                    "The admin can see the internal sections and choose the right management area."
                ),
                trainer_notes=(
                    "This workflow is staff-only and is separate from the clinic-facing share experience. Record-governance tasks use separate internal dashboards."
                ),
                screenshot_path=rel_asset("09-admin-content-management/01-publisher-dashboard.png"),
                screenshot_caption="Internal Publishing Dashboard.",
                screenshot_show="Dashboard sections for content types, media, organization, and quick actions.",
            ),
            Step(
                number=2,
                title="Open the Videos list",
                user_does=(
                    "Chooses Videos from the dashboard or uses the quick route into the media list."
                ),
                user_sees=(
                    "A searchable Videos table with code, published state, active state, and Edit actions."
                ),
                why_it_matters=(
                    "This list is the operational entry point for finding and maintaining specific videos."
                ),
                expected_result=(
                    "The admin can scan or search the video catalog and identify the right row."
                ),
                trainer_notes=(
                    "The video table can be long, so use search when a code or topic is known."
                ),
                screenshot_path=rel_asset("09-admin-content-management/02-video-list.png"),
                screenshot_caption="Videos list in the publishing dashboard.",
                screenshot_show="Search input, New Video button, and the top of the video catalog table.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.22),
            ),
            Step(
                number=3,
                title="Search for the target video",
                user_does=(
                    "Uses the list search field or scrolls to the desired video code."
                ),
                user_sees=(
                    "Many video rows, each with an Edit action in the last column."
                ),
                why_it_matters=(
                    "Large catalogs are easier to work with when the admin understands how to narrow the list."
                ),
                expected_result=(
                    "The target video row is located and ready to open."
                ),
                trainer_notes=(
                    "Use code-based lookup where possible because titles live in the per-language edit rows."
                ),
                screenshot_path=rel_asset("09-admin-content-management/02-video-list.png"),
                screenshot_caption="Video rows and edit actions.",
                screenshot_show="The searchable table with many catalog rows and inline Edit links.",
                deck_layout="wide",
                deck_crop=(0.0, 0.02, 1.0, 0.30),
            ),
            Step(
                number=4,
                title="Open the video edit form",
                user_does=(
                    "Clicks Edit on the selected video row."
                ),
                user_sees=(
                    "Edit Video with the bundle membership summary, main video fields, and the language-details table."
                ),
                why_it_matters=(
                    "The edit form is where both global metadata and language-specific content are maintained."
                ),
                expected_result=(
                    "The video edit screen opens successfully."
                ),
                trainer_notes=(
                    "The form explicitly reminds users that a video cannot exist standalone; it must belong to at least one bundle."
                ),
                screenshot_path=rel_asset("09-admin-content-management/03-video-edit-form.png"),
                screenshot_caption="Edit Video form.",
                screenshot_show="Bundle membership summary, editable metadata, and the language-details table.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.82),
            ),
            Step(
                number=5,
                title="Maintain language rows and save",
                user_does=(
                    "Updates the video metadata and the title and YouTube URL fields for the required language rows, then clicks Save."
                ),
                user_sees=(
                    "A language-details table that expects complete per-language entries before saving."
                ),
                why_it_matters=(
                    "The caregiver-facing playback experience depends on accurate localized titles and source URLs."
                ),
                expected_result=(
                    "The video record saves cleanly with the updated language details."
                ),
                trainer_notes=(
                    "After saving, validate a downstream share flow if the change affects live caregiver content."
                ),
                screenshot_path=rel_asset("09-admin-content-management/03-video-edit-form.png"),
                screenshot_caption="Language detail rows inside the Edit Video form.",
                screenshot_show="The language-specific title and YouTube URL fields plus the Save action.",
                deck_layout="wide",
                deck_crop=(0.0, 0.28, 1.0, 0.60),
            ),
        ],
        common_issues=[
            (
                "Video-bundle dependency",
                "The app does not allow videos to exist outside a bundle, so bundle planning often needs to happen before adding or editing a video.",
            ),
            (
                "Large catalog navigation",
                "Use search and known codes to avoid manually scrolling the full video list.",
            ),
            (
                "Global impact",
                "Internal video edits affect downstream clinic and caregiver experiences, so validate carefully after saving production content changes.",
            ),
            (
                "Wrong internal tool",
                "If the task is to update campaigns, field reps, or doctor records, move to the PE Records or System Records workflows instead of editing content here.",
            ),
        ],
    ),
    Workflow(
        number=10,
        slug="share-tracking-dashboard",
        title="Share Tracking Dashboard",
        short_title="Share Tracking Dashboard",
        section="Internal Operations",
        document_purpose=(
            "Show internal superusers how to open the share tracking dashboard and review doctor shares, "
            "playback milestones, and banner engagement."
        ),
        primary_user="Internal analytics, audit, or operations user with superuser access",
        entry_point="Tracking login at `/tracking/login/`.",
        workflow_summary=[
            "The tracking flow starts from a dedicated login page that is limited to superusers.",
            "The dashboard summarizes doctor-level sharing activity, playback events, and banner clicks in one place.",
            "Recent activity tables help trainers or operations teams confirm that clinic sharing is flowing into analytics correctly.",
        ],
        success_criteria=[
            "The user can open the tracking login page and authenticate successfully.",
            "The dashboard summary cards and recent activity tables are visible.",
            "The user can identify where to audit doctor share volume, playback milestones, and banner click activity.",
        ],
        related_documents=[
            "01-platform-overview-and-role-map.md",
            "05-doctor-share-single-video.md",
            "06-clinic-staff-share-bundle.md",
            "07-caregiver-single-video-view.md",
            "08-caregiver-bundle-view.md",
            "../../templates/sharing/tracking_login.html",
            "../../templates/sharing/tracking_dashboard.html",
            "../../sharing/views.py",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("10-share-tracking-dashboard/02-tracking-dashboard.png"),
        cover_crop=(0.0, 0.0, 1.0, 0.24),
        closing_text=(
            "Use this dashboard after live clinic sharing is in progress. It complements the operational setup decks by proving what has actually been shared and viewed."
        ),
        steps=[
            Step(
                number=1,
                title="Open the tracking login page",
                user_does=(
                    "Navigates to the dedicated tracking login route and enters the approved superuser credentials."
                ),
                user_sees=(
                    "A restricted-access login page with email and password fields plus the Open Tracking Dashboard action."
                ),
                why_it_matters=(
                    "The tracking dashboard is isolated from the clinic workflow so only authorized internal users can review share analytics."
                ),
                expected_result=(
                    "The user can submit valid credentials and continue to the dashboard."
                ),
                trainer_notes=(
                    "Only a superuser can enter this flow. Clinic credentials do not work here."
                ),
                screenshot_path=rel_asset("10-share-tracking-dashboard/01-tracking-login.png"),
                screenshot_caption="Tracking login page.",
                screenshot_show="The restricted-access login form and the Open Tracking Dashboard button.",
            ),
            Step(
                number=2,
                title="Review the activity overview cards",
                user_does=(
                    "Signs in and reviews the top summary cards before drilling into the detail tables."
                ),
                user_sees=(
                    "Share Activity Overview with counts for doctors tracked, total shares, playback events, banner clicks, and unique items shared."
                ),
                why_it_matters=(
                    "The summary cards give trainers and operations users an immediate health check of adoption and content engagement."
                ),
                expected_result=(
                    "The user can confirm that share counts and downstream activity totals are being recorded, even if playback remains at zero before a video starts."
                ),
                trainer_notes=(
                    "If counts are unexpectedly zero, verify that live share activity was created. Playback remains at zero until the embedded player actually starts."
                ),
                screenshot_path=rel_asset("10-share-tracking-dashboard/02-tracking-dashboard.png"),
                screenshot_caption="Share tracking dashboard overview.",
                screenshot_show="The dashboard header and top summary cards.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.24),
            ),
            Step(
                number=3,
                title="Inspect doctor summary and recent shares",
                user_does=(
                    "Scrolls through the Doctor Summary and Recent Shares sections to see which clinics are sharing which items."
                ),
                user_sees=(
                    "Tables for doctor-level totals, recent share timestamps, item names, anonymized recipient references, and language codes."
                ),
                why_it_matters=(
                    "These tables are the fastest route to confirm who shared content and whether the correct videos or bundles were used."
                ),
                expected_result=(
                    "The user can identify the doctor, shared item, language, and share timing for recent activity."
                ),
                trainer_notes=(
                    "Recipient references are anonymized hashes, so trainers should not expect to see raw caregiver phone numbers here."
                ),
                screenshot_path=rel_asset("10-share-tracking-dashboard/02-tracking-dashboard.png"),
                screenshot_caption="Doctor summary and recent share tables.",
                screenshot_show="The Doctor Summary and Recent Shares sections.",
                deck_layout="wide",
                deck_crop=(0.0, 0.18, 1.0, 0.58),
            ),
            Step(
                number=4,
                title="Inspect playback and banner events",
                user_does=(
                    "Reviews the playback milestones and banner click tables to confirm downstream caregiver engagement."
                ),
                user_sees=(
                    "Recent Playback Events and Recent Banner Clicks tables with doctor IDs, event types, milestone percentages, and banner targets."
                ),
                why_it_matters=(
                    "These tables show whether a share translated into viewing behavior and whether campaign banners were interacted with."
                ),
                expected_result=(
                    "The user can confirm whether playback data is present yet and can still review any recorded banner activity."
                ),
                trainer_notes=(
                    "Playback rows appear only after the caregiver starts a video. Bundle shares can generate multiple playback rows because each embedded video logs play and progress milestones separately."
                ),
                screenshot_path=rel_asset("10-share-tracking-dashboard/02-tracking-dashboard.png"),
                screenshot_caption="Playback and banner event tables.",
                screenshot_show="The Recent Playback Events and Recent Banner Clicks sections.",
                deck_layout="wide",
                deck_crop=(0.0, 0.58, 1.0, 1.0),
            ),
        ],
        common_issues=[
            (
                "Wrong account type",
                "The tracking dashboard only allows a superuser account, so clinic or publisher credentials will be rejected.",
            ),
            (
                "No recent activity",
                "If the tables are empty, confirm that a doctor or clinic staff member completed a share and that the caregiver page was opened afterward.",
            ),
            (
                "Recipient privacy",
                "Recipient references are intentionally anonymized. Use doctor, item, and timestamp context for troubleshooting instead of expecting raw phone numbers.",
            ),
        ],
    ),
    Workflow(
        number=11,
        slug="pe-records-dashboard",
        title="PE Records Dashboard",
        short_title="PE Records Dashboard",
        section="Internal Operations",
        document_purpose=(
            "Show internal superusers how to open the PE-only records dashboard and manage campaign, field-rep, and doctor records scoped to Patient Education campaigns."
        ),
        primary_user="System superuser responsible for PE-only record governance",
        entry_point="Dedicated PE records login at `/publisher/pe-system/login/`.",
        workflow_summary=[
            "The PE Records Dashboard uses its own superuser session and only surfaces campaigns marked as Patient Education campaigns.",
            "Campaign rows merge master campaign data with local portal setup status so teams can see whether PE campaigns are configured downstream.",
            "Field rep and doctor sections only show PE-linked records, with direct update and delete actions for operational cleanup.",
        ],
        success_criteria=[
            "The user can authenticate into the PE records session and open the dashboard.",
            "PE campaign, field rep, and doctor sections are visible and searchable.",
            "The user can open an edit form for a PE campaign or PE-linked doctor and understand the scope of those changes.",
        ],
        related_documents=[
            "01-platform-overview-and-role-map.md",
            "02-publisher-campaign-setup.md",
            "03-field-rep-doctor-recruitment.md",
            "../../publisher/templates/publisher/pe_records_login.html",
            "../../publisher/templates/publisher/pe_records_dashboard.html",
            "../../publisher/templates/publisher/pe_master_campaign_form.html",
            "../../publisher/templates/publisher/doctor_record_form.html",
            "../../publisher/views.py",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("11-pe-records-dashboard/02-pe-records-dashboard.png"),
        cover_crop=(0.0, 0.0, 1.0, 0.24),
        closing_text=(
            "Use this dashboard when the task is specific to Patient Education campaigns and their linked people. Use the broader System Records Hub for cross-campaign record maintenance."
        ),
        steps=[
            Step(
                number=1,
                title="Open the PE records login",
                user_does=(
                    "Navigates to the PE records login page and signs in with a local superuser account."
                ),
                user_sees=(
                    "PE System Records login with a dedicated email and password form."
                ),
                why_it_matters=(
                    "This dashboard keeps PE-only record governance separate from the broader publisher dashboard and other superuser tools."
                ),
                expected_result=(
                    "The PE records session opens and redirects to the dashboard."
                ),
                trainer_notes=(
                    "This flow creates a separate PE records session, so it is different from the standard `/admin/` login redirect into `/publisher/`."
                ),
                screenshot_path=rel_asset("11-pe-records-dashboard/01-pe-records-login.png"),
                screenshot_caption="PE records login page.",
                screenshot_show="The PE System Records login form.",
            ),
            Step(
                number=2,
                title="Review the PE records dashboard",
                user_does=(
                    "Scans the dashboard cards and campaign table to compare master PE campaigns with local portal setup coverage."
                ),
                user_sees=(
                    "PE Records Dashboard with summary cards for master campaigns, local PE setups, PE field reps, and PE doctors, followed by searchable tables."
                ),
                why_it_matters=(
                    "This page is the operational command center for understanding which PE campaigns are configured and which related records exist."
                ),
                expected_result=(
                    "The user can identify configured versus unconfigured PE campaigns and the volume of related field reps and doctors."
                ),
                trainer_notes=(
                    "The Local PE Setups count comes from the portal-side `publisher_campaign` data layered onto the master PE campaign list."
                ),
                screenshot_path=rel_asset("11-pe-records-dashboard/02-pe-records-dashboard.png"),
                screenshot_caption="PE records dashboard overview.",
                screenshot_show="The dashboard heading, summary cards, and the top of the Campaigns table.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.28),
            ),
            Step(
                number=3,
                title="Update a PE campaign record",
                user_does=(
                    "Opens Update from a campaign row to edit master PE campaign details such as doctor limits, templates, banner URLs, and dates."
                ),
                user_sees=(
                    "A PE campaign edit form populated from the master campaign record, with linked local setup context shown alongside it."
                ),
                why_it_matters=(
                    "Campaign metadata drives field-rep onboarding, campaign messaging, and banner behavior, so PE campaign records need a dedicated update path."
                ),
                expected_result=(
                    "The user can edit a master PE campaign without leaving the PE records flow."
                ),
                trainer_notes=(
                    "Deleting from this flow removes both the master PE campaign record and any linked local portal setup, so confirm scope before using Delete."
                ),
                screenshot_path=rel_asset("11-pe-records-dashboard/03-pe-campaign-edit.png"),
                screenshot_caption="Master PE campaign edit form.",
                screenshot_show="The PE campaign update form with campaign metadata and linked local setup context.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.72),
            ),
            Step(
                number=4,
                title="Review a PE-linked doctor record",
                user_does=(
                    "Opens Update from the Doctors table to review and edit a PE-linked doctor record."
                ),
                user_sees=(
                    "A doctor record form showing master identity fields, clinic details, field rep context, and whether a local profile is also present."
                ),
                why_it_matters=(
                    "PE doctors often need cleanup or alignment when field-rep recruitment and clinic registration intersect."
                ),
                expected_result=(
                    "The user can review or update a PE-linked doctor from the PE-specific governance flow."
                ),
                trainer_notes=(
                    "If a local portal profile exists, the system attempts to sync that local profile after a successful master-record update."
                ),
                screenshot_path=rel_asset("11-pe-records-dashboard/04-pe-doctor-edit.png"),
                screenshot_caption="PE-linked doctor edit form.",
                screenshot_show="The doctor record form with clinic details, recruiter fields, and local-profile context.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.78),
            ),
        ],
        common_issues=[
            (
                "Session confusion",
                "The PE records dashboard uses its own session. Logging into `/admin/` alone does not automatically open this PE-only tool.",
            ),
            (
                "Scope confusion",
                "This dashboard only shows Patient Education-linked campaigns, field reps, and doctors. Broader record maintenance belongs in the System Records Hub.",
            ),
            (
                "Delete impact",
                "Deleting from the PE campaign section can remove both master and linked local setup data, so confirm scope before proceeding.",
            ),
        ],
    ),
    Workflow(
        number=12,
        slug="system-records-hub",
        title="System Records Hub",
        short_title="System Records Hub",
        section="Internal Operations",
        document_purpose=(
            "Show local superusers how to use the broader System Records Hub to review local campaign configurations and maintain master field-rep and doctor records."
        ),
        primary_user="Local superuser responsible for system-wide campaign, field-rep, and doctor record maintenance",
        entry_point="Superuser route at `/publisher/system-records/` after logging in through `/admin/login/`.",
        workflow_summary=[
            "The System Records Hub combines local `publisher_campaign` rows with master field-rep and doctor records in one superuser-only view.",
            "Campaign rows update through the existing campaign editor, while field-rep and doctor rows open dedicated maintenance forms.",
            "Doctor rows show whether a local portal profile exists, which helps operators understand whether master edits will also sync local data.",
        ],
        success_criteria=[
            "The superuser can open the System Records Hub from the internal admin session.",
            "Campaign, field-rep, and doctor sections are visible and searchable.",
            "The superuser can open the field-rep and doctor maintenance forms and understand the local-versus-master scope.",
        ],
        related_documents=[
            "01-platform-overview-and-role-map.md",
            "02-publisher-campaign-setup.md",
            "09-admin-content-management.md",
            "../../publisher/templates/publisher/system_records.html",
            "../../publisher/templates/publisher/field_rep_record_form.html",
            "../../publisher/templates/publisher/doctor_record_form.html",
            "../../publisher/views.py",
        ],
        status=STATUS_TEXT,
        cover_image=rel_asset("12-system-records-hub/01-system-records-hub.png"),
        cover_crop=(0.0, 0.0, 1.0, 0.24),
        closing_text=(
            "Use the System Records Hub when the task spans local campaign configurations or broader master record cleanup. Use the PE Records Dashboard when the scope is strictly PE-linked data."
        ),
        steps=[
            Step(
                number=1,
                title="Open the System Records Hub",
                user_does=(
                    "Signs in as a local superuser and navigates to the System Records Hub."
                ),
                user_sees=(
                    "A superuser-only dashboard with summary cards for campaigns, field reps, and doctors plus searchable maintenance sections."
                ),
                why_it_matters=(
                    "This hub is the broadest record-maintenance surface in the product and is separate from day-to-day content editing."
                ),
                expected_result=(
                    "The superuser can access the full System Records Hub."
                ),
                trainer_notes=(
                    "This route is part of the internal publisher area and requires a normal local superuser session, not the dedicated PE records login."
                ),
                screenshot_path=rel_asset("12-system-records-hub/01-system-records-hub.png"),
                screenshot_caption="System Records Hub overview.",
                screenshot_show="The System Records Hub heading, summary cards, and top of the Campaigns section.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.28),
            ),
            Step(
                number=2,
                title="Review local campaign configurations",
                user_does=(
                    "Uses the Campaigns section to search for a local `publisher_campaign` row and open the linked update path."
                ),
                user_sees=(
                    "Local campaign rows with campaign ID, generated bundle name, supported doctor count, active window, and publisher owner."
                ),
                why_it_matters=(
                    "This is the fastest route to confirm or clean up portal-side PE campaign configuration records."
                ),
                expected_result=(
                    "The superuser can find the correct local campaign row and reach the update or delete action."
                ),
                trainer_notes=(
                    "Deleting from this section removes the local campaign configuration and the generated bundle, but it does not edit the upstream master campaign record."
                ),
                screenshot_path=rel_asset("12-system-records-hub/02-system-campaigns.png"),
                screenshot_caption="System records campaign table.",
                screenshot_show="The Campaigns section showing local portal campaign configuration rows.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.40),
            ),
            Step(
                number=3,
                title="Update a field rep record",
                user_does=(
                    "Opens Update from the Field Reps section to maintain a master field-rep record and its campaign links."
                ),
                user_sees=(
                    "A field rep edit form with full name, phone number, external brand ID, state, and active status."
                ),
                why_it_matters=(
                    "Field rep accuracy is essential because campaign onboarding links and doctor recruitment depend on these master records."
                ),
                expected_result=(
                    "The superuser can edit or delete a field rep record from the broader system hub."
                ),
                trainer_notes=(
                    "This form edits master DB-backed data, so the impact can extend across campaigns."
                ),
                screenshot_path=rel_asset("12-system-records-hub/03-system-field-rep-edit.png"),
                screenshot_caption="System field-rep edit form.",
                screenshot_show="The field rep maintenance form with identity, phone, and active-status fields.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.72),
            ),
            Step(
                number=4,
                title="Review doctor sync state and update the doctor record",
                user_does=(
                    "Uses the Doctors section to inspect whether a doctor is master-only or also synced to a local portal profile, then opens the update form."
                ),
                user_sees=(
                    "A doctor edit form with identity, clinic details, recruiter fields, clinic user emails, and local-profile context."
                ),
                why_it_matters=(
                    "The local-profile badge helps operations teams understand whether a master update should also cascade into the local portal record."
                ),
                expected_result=(
                    "The superuser can update a doctor with clear awareness of local-sync implications."
                ),
                trainer_notes=(
                    "If a doctor has a local profile, updates attempt to sync both the master row and the local portal profile. Delete actions may also remove the local profile."
                ),
                screenshot_path=rel_asset("12-system-records-hub/04-system-doctor-edit.png"),
                screenshot_caption="System doctor edit form.",
                screenshot_show="The doctor maintenance form with clinic fields, recruiter fields, and clinic user email fields.",
                deck_layout="wide",
                deck_crop=(0.0, 0.0, 1.0, 0.82),
            ),
        ],
        common_issues=[
            (
                "PE versus system scope",
                "Use this hub for broader record cleanup. Use the PE Records Dashboard when the task is specific to PE-linked campaigns, reps, or doctors only.",
            ),
            (
                "Local versus master impact",
                "Campaign rows here are local portal records, while field-rep and doctor rows are master records. The scope is different depending on which section you edit.",
            ),
            (
                "Local profile sync",
                "When a doctor has a local portal profile, master updates can also affect the local profile. Trainers should call out that badge before editing.",
            ),
        ],
    ),
]


WORKFLOW_BY_SLUG = {workflow.slug: workflow for workflow in WORKFLOWS}


def _workflow_aliases(workflow: Workflow) -> set[str]:
    return {
        str(workflow.number).lower(),
        f"{workflow.number:02d}".lower(),
        workflow.slug.lower(),
        workflow.manual_filename.lower(),
        workflow.deck_filename.lower(),
        f"{workflow.number:02d}-{workflow.slug}".lower(),
    }


def select_workflows(selection: str | list[str] | tuple[str, ...] | None) -> list[Workflow]:
    if not selection:
        return WORKFLOWS

    raw_tokens: list[str] = []
    if isinstance(selection, str):
        raw_tokens.extend(selection.split(","))
    else:
        for item in selection:
            raw_tokens.extend(str(item).split(","))

    tokens = [token.strip().lower() for token in raw_tokens if token and token.strip()]
    if not tokens or tokens == ["all"]:
        return WORKFLOWS

    selected: list[Workflow] = []
    seen: set[str] = set()
    unknown: list[str] = []

    for token in tokens:
        matches = [workflow for workflow in WORKFLOWS if token in _workflow_aliases(workflow)]
        if not matches:
            unknown.append(token)
            continue
        for workflow in matches:
            if workflow.slug in seen:
                continue
            selected.append(workflow)
            seen.add(workflow.slug)

    if unknown:
        raise ValueError(f"Unknown workflow selector(s): {', '.join(unknown)}")

    return selected
