# 09. Admin Content Management

## 1. Title

Admin Content Management

## 2. Document Purpose

Show internal staff how to enter the publishing dashboard, review the video catalog, and edit a video's metadata and language rows.

## 3. Primary User

Internal admin or staff user with access to the publishing dashboard

## 4. Entry Point

Staff login at `/admin/login/?next=/publisher/` leading into `/publisher/`.

## 5. Workflow Summary

- The publishing dashboard is the internal catalog-management surface for therapy areas, triggers, videos, bundles, and bundle-trigger maps.
- The Videos list is the fastest route for reviewing published media and opening a specific video for editing.
- Video edit pages enforce the rule that each video belongs to at least one bundle and carries language-specific title and YouTube URL rows.
- Campaign record governance and master data cleanup happen in the separate PE Records and System Records workflows, not on this dashboard.

## 6. Step-By-Step Instructions

### Step 1. Open the Publishing Dashboard

**What the user does**

Signs in with an internal staff account and lands on the publishing dashboard.

**What the user sees**

Publishing Dashboard with grouped links for content types, videos, bundles, maps, and quick actions.

**Why the step matters**

This is the root navigation page for all internal content maintenance.

**Expected result**

The admin can see the internal sections and choose the right management area.

**Common issues or trainer notes**

This workflow is staff-only and is separate from the clinic-facing share experience. Record-governance tasks use separate internal dashboards.

**Screenshot Placeholder**

- Suggested file path: `assets/09-admin-content-management/01-publisher-dashboard.png`
- Screenshot caption: Internal Publishing Dashboard.
- What the screenshot should show: Dashboard sections for content types, media, organization, and quick actions.

![Internal Publishing Dashboard.](assets/09-admin-content-management/01-publisher-dashboard.png)

### Step 2. Open the Videos list

**What the user does**

Chooses Videos from the dashboard or uses the quick route into the media list.

**What the user sees**

A searchable Videos table with code, published state, active state, and Edit actions.

**Why the step matters**

This list is the operational entry point for finding and maintaining specific videos.

**Expected result**

The admin can scan or search the video catalog and identify the right row.

**Common issues or trainer notes**

The video table can be long, so use search when a code or topic is known.

**Screenshot Placeholder**

- Suggested file path: `assets/09-admin-content-management/02-video-list.png`
- Screenshot caption: Videos list in the publishing dashboard.
- What the screenshot should show: Search input, New Video button, and the top of the video catalog table.

![Videos list in the publishing dashboard.](assets/09-admin-content-management/02-video-list.png)

### Step 3. Search for the target video

**What the user does**

Uses the list search field or scrolls to the desired video code.

**What the user sees**

Many video rows, each with an Edit action in the last column.

**Why the step matters**

Large catalogs are easier to work with when the admin understands how to narrow the list.

**Expected result**

The target video row is located and ready to open.

**Common issues or trainer notes**

Use code-based lookup where possible because titles live in the per-language edit rows.

**Screenshot Placeholder**

- Suggested file path: `assets/09-admin-content-management/02-video-list.png`
- Screenshot caption: Video rows and edit actions.
- What the screenshot should show: The searchable table with many catalog rows and inline Edit links.

![Video rows and edit actions.](assets/09-admin-content-management/02-video-list.png)

### Step 4. Open the video edit form

**What the user does**

Clicks Edit on the selected video row.

**What the user sees**

Edit Video with the bundle membership summary, main video fields, and the language-details table.

**Why the step matters**

The edit form is where both global metadata and language-specific content are maintained.

**Expected result**

The video edit screen opens successfully.

**Common issues or trainer notes**

The form explicitly reminds users that a video cannot exist standalone; it must belong to at least one bundle.

**Screenshot Placeholder**

- Suggested file path: `assets/09-admin-content-management/03-video-edit-form.png`
- Screenshot caption: Edit Video form.
- What the screenshot should show: Bundle membership summary, editable metadata, and the language-details table.

![Edit Video form.](assets/09-admin-content-management/03-video-edit-form.png)

### Step 5. Maintain language rows and save

**What the user does**

Updates the video metadata and the title and YouTube URL fields for the required language rows, then clicks Save.

**What the user sees**

A language-details table that expects complete per-language entries before saving.

**Why the step matters**

The caregiver-facing playback experience depends on accurate localized titles and source URLs.

**Expected result**

The video record saves cleanly with the updated language details.

**Common issues or trainer notes**

After saving, validate a downstream share flow if the change affects live caregiver content.

**Screenshot Placeholder**

- Suggested file path: `assets/09-admin-content-management/03-video-edit-form.png`
- Screenshot caption: Language detail rows inside the Edit Video form.
- What the screenshot should show: The language-specific title and YouTube URL fields plus the Save action.

![Language detail rows inside the Edit Video form.](assets/09-admin-content-management/03-video-edit-form.png)

## 7. Success Criteria

- The admin can open the publishing dashboard and navigate to Videos.
- The target video can be found from the list and opened for editing.
- Language rows and video metadata are updated without breaking the bundle relationship rule.

### Trainer Tips and Common Issues

- **Video-bundle dependency:** The app does not allow videos to exist outside a bundle, so bundle planning often needs to happen before adding or editing a video.
- **Large catalog navigation:** Use search and known codes to avoid manually scrolling the full video list.
- **Global impact:** Internal video edits affect downstream clinic and caregiver experiences, so validate carefully after saving production content changes.
- **Wrong internal tool:** If the task is to update campaigns, field reps, or doctor records, move to the PE Records or System Records workflows instead of editing content here.

## 8. Related Documents

- [`01-platform-overview-and-role-map.md`](01-platform-overview-and-role-map.md)
- [`11-pe-records-dashboard.md`](11-pe-records-dashboard.md)
- [`12-system-records-hub.md`](12-system-records-hub.md)
- [`../../publisher/templates/publisher/dashboard.html`](../../publisher/templates/publisher/dashboard.html)
- [`../../publisher/templates/publisher/video_list.html`](../../publisher/templates/publisher/video_list.html)
- [`../../publisher/templates/publisher/video_form.html`](../../publisher/templates/publisher/video_form.html)
- [`../../publisher/views.py`](../../publisher/views.py)

## 9. Status

Live-verified against the local demo environment and refreshed with real screenshots on 2026-04-23.
