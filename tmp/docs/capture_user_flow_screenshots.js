const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..", "..");
const manifest = JSON.parse(
  fs.readFileSync(path.join(__dirname, "demo_manifest.json"), "utf8"),
);

const assetsRoot = path.join(root, "docs", "product-user-flows", "assets");
const captureMetaPath = path.join(__dirname, "capture-metadata.json");

const workflowDirs = {
  overview: "01-platform-overview-role-map",
  publisher: "02-publisher-campaign-setup",
  fieldRep: "03-field-rep-doctor-recruitment",
  registration: "04-doctor-registration-and-first-access",
  doctor: "05-doctor-share-single-video",
  clinic: "06-clinic-staff-share-bundle",
  patientVideo: "07-caregiver-single-video-view",
  patientBundle: "08-caregiver-bundle-view",
  admin: "09-admin-content-management",
  tracking: "10-share-tracking-dashboard",
  peRecords: "11-pe-records-dashboard",
  systemRecords: "12-system-records-hub",
};

for (const dir of Object.values(workflowDirs)) {
  fs.mkdirSync(path.join(assetsRoot, dir), { recursive: true });
}

const argv = process.argv.slice(2);
const workflowsArgIndex = argv.indexOf("--workflows");
const rawSelection =
  workflowsArgIndex >= 0
    ? argv[workflowsArgIndex + 1] || ""
    : process.env.WORKFLOWS || "";
const selectedWorkflows = new Set(
  rawSelection
    .split(",")
    .map((value) => String(value || "").trim().toLowerCase())
    .filter(Boolean),
);

const captureMeta = {
  generatedAt: new Date().toISOString(),
  whatsappUrls: {},
  registrations: {},
};

function screenshotPath(workflowKey, filename) {
  return path.join(assetsRoot, workflowDirs[workflowKey], filename);
}

function shouldRun(...aliases) {
  if (!selectedWorkflows.size) {
    return true;
  }
  const normalized = aliases.map((value) => String(value || "").trim().toLowerCase());
  return normalized.some((value) => selectedWorkflows.has(value));
}

async function screenshot(page, workflowKey, filename, options = {}) {
  const target = screenshotPath(workflowKey, filename);
  await page.screenshot({
    path: target,
    fullPage: options.fullPage !== false,
  });
  return target;
}

async function settle(page, ms = 800) {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(ms);
}

async function newContext(browser) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1200 },
    colorScheme: "light",
  });
  await context.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await context.route("https://fonts.gstatic.com/**", (route) => route.abort());
  return context;
}

async function attachWindowOpenRecorder(page) {
  await page.evaluate(() => {
    window.__codexOpenedUrls = [];
    window.open = (url) => {
      window.__codexOpenedUrls.push(String(url || ""));
      return null;
    };
  });
}

async function getRecordedUrls(page) {
  return page.evaluate(() => window.__codexOpenedUrls || []);
}

function uniqueDigits(prefix) {
  const seed = String(Date.now());
  const body = seed.slice(-9).padStart(9, "0");
  return `${prefix}${body.slice(0, 9)}`;
}

async function loginDoctor(page, email, password) {
  await page.goto(manifest.urls.login, { waitUntil: "domcontentloaded" });
  await page.locator('[name="username"]').fill(email);
  await page.locator('[name="password"]').fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await page.waitForURL(/\/clinic\/.*\/share\//, { timeout: 20000 });
  await settle(page);
}

async function loginTracking(page) {
  await page.goto(manifest.urls.tracking_login, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Restricted Access");
  await settle(page);
  await page.locator("#email").fill(manifest.credentials.admin_email);
  await page.locator("#password").fill(manifest.credentials.admin_password);
  await page.getByRole("button", { name: "Open Tracking Dashboard" }).click();
  await page.waitForURL(/\/tracking\/$/, { timeout: 20000 });
  await settle(page);
}

async function loginAdminToPublisher(page) {
  await page.goto(manifest.urls.admin_login, { waitUntil: "domcontentloaded" });
  await page.locator('[name="username"]').fill(manifest.credentials.admin_email);
  await page.locator('[name="password"]').fill(manifest.credentials.admin_password);
  await page.locator('input[type="submit"]').click();
  await page.waitForURL(/\/publisher\/?$/, { timeout: 20000 });
  await page.waitForSelector("text=Publishing Dashboard");
  await settle(page);
}

async function seedTrackingActivity(browser) {
  const doctorContext = await newContext(browser);
  const doctorPage = await doctorContext.newPage();
  await loginDoctor(
    doctorPage,
    manifest.credentials.doctor_email,
    manifest.credentials.doctor_password,
  );
  await attachWindowOpenRecorder(doctorPage);
  await doctorPage.locator("#searchBox").fill("Bronchiolitis");
  await doctorPage.waitForTimeout(900);
  await doctorPage.getByText(manifest.content.video_title, { exact: false }).first().click();
  await doctorPage.locator("#waNumber").fill(manifest.doctor.share_patient_whatsapp);
  await doctorPage.selectOption("#lang", "hi");
  await settle(doctorPage, 500);
  const bannerLink = doctorPage.locator(".banner-link").first();
  if (await bannerLink.count()) {
    await bannerLink.click({ force: true });
    await doctorPage.waitForTimeout(300);
  }
  await doctorPage.locator("#shareVideoBtn").click();
  await doctorPage.waitForTimeout(400);
  await doctorContext.close();

  const clinicContext = await newContext(browser);
  const clinicPage = await clinicContext.newPage();
  await loginDoctor(
    clinicPage,
    manifest.credentials.clinic_staff_email,
    manifest.credentials.clinic_staff_password,
  );
  await attachWindowOpenRecorder(clinicPage);
  await clinicPage.selectOption("#bundleSel", { label: manifest.content.cluster_title });
  await clinicPage.locator("#waNumber").fill(manifest.doctor.share_patient_whatsapp);
  await clinicPage.selectOption("#lang", "ta");
  await settle(clinicPage, 500);
  await clinicPage.locator("#shareBundleBtn").click();
  await clinicPage.waitForTimeout(400);
  await clinicContext.close();

  const patientVideoContext = await newContext(browser);
  const patientVideoPage = await patientVideoContext.newPage();
  await patientVideoPage.goto(manifest.urls.patient_video_hi, { waitUntil: "domcontentloaded" });
  await patientVideoPage.waitForSelector("#lang");
  await settle(patientVideoPage, 1400);
  await patientVideoPage.selectOption("#lang", "en");
  await patientVideoPage.waitForLoadState("domcontentloaded");
  await settle(patientVideoPage, 1200);
  await patientVideoContext.close();

  const patientBundleContext = await newContext(browser);
  const patientBundlePage = await patientBundleContext.newPage();
  await patientBundlePage.goto(manifest.urls.patient_cluster_ta, { waitUntil: "domcontentloaded" });
  await patientBundlePage.waitForSelector("#lang");
  await settle(patientBundlePage, 1400);
  await patientBundlePage.selectOption("#lang", "en");
  await patientBundlePage.waitForLoadState("domcontentloaded");
  await settle(patientBundlePage, 1200);
  await patientBundleContext.close();
}

async function captureOverview(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();
  await page.goto(manifest.urls.login, { waitUntil: "domcontentloaded" });
  await settle(page);
  await screenshot(page, "overview", "01-login-entry.png", { fullPage: false });
  await context.close();
}

async function capturePublisherFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();

  await page.goto(manifest.urls.publisher_entry, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/\/publisher-landing-page\/\?campaign-id=.*company_name=/, {
    timeout: 20000,
  });
  await page.waitForSelector("text=Publisher Landing Page");
  await settle(page);
  await screenshot(page, "publisher", "01-publisher-landing.png");

  await page.getByRole("link", { name: "Add details for this campaign" }).click();
  await page.waitForURL(/\/add-campaign-details\/\?campaign-id=/, { timeout: 20000 });
  await page.waitForSelector("text=Add Campaign Details");
  await settle(page);
  await screenshot(page, "publisher", "02-add-campaign-details-empty.png");

  await page.locator('[name="new_video_cluster_name"]').fill(
    manifest.campaign.cluster_name,
  );

  const searchInput = page.locator("#searchInput");
  await searchInput.fill("bronchiolitis");
  await page.waitForSelector('button:has-text("Add")', { timeout: 10000 });
  await page.locator('button:has-text("Add")').first().click();
  await page.waitForTimeout(500);

  await searchInput.fill("acute allergy");
  await page.waitForSelector('button:has-text("Add")', { timeout: 10000 });
  await page.locator('button:has-text("Add")').first().click();
  await page.waitForTimeout(750);

  await page.locator('[name="email_registration"]').fill(
    "Welcome <doctor_name>.\nClinic portal: <clinic_link>\nPassword setup: <setup_link>",
  );
  await page.locator('[name="wa_addition"]').fill(
    "Hello <doctor_name>, this clinic is already active for the campaign. Share from <clinic_link>",
  );
  await page.locator('[name="start_date"]').fill("2026-04-10");
  await page.locator('[name="end_date"]').fill("2026-06-30");
  await settle(page, 500);
  await screenshot(page, "publisher", "03-add-campaign-details-complete.png");

  await page.getByRole("button", { name: "Save" }).click();
  await page.waitForURL(/\/publisher-landing-page\/\?campaign-id=/, { timeout: 20000 });
  await settle(page);
  await screenshot(page, "publisher", "04-publisher-landing-after-save.png");

  await page.goto(manifest.urls.campaign_list, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Campaigns");
  await settle(page);
  await screenshot(page, "publisher", "05-campaign-list.png");

  await context.close();
}

async function captureFieldRepFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();

  await page.goto(manifest.urls.field_rep, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Register doctor for campaign");
  await settle(page);
  await screenshot(page, "fieldRep", "01-field-rep-landing.png");

  await page.locator('[name="whatsapp_number"]').fill(manifest.doctor.existing_whatsapp);
  await screenshot(page, "fieldRep", "02-existing-doctor-number-entered.png", {
    fullPage: false,
  });

  await page.goto(manifest.urls.field_rep, { waitUntil: "domcontentloaded" });
  await page.locator('[name="whatsapp_number"]').fill(manifest.doctor.new_doctor_whatsapp);
  await page.getByRole("button", { name: "Submit" }).click();
  await page.waitForURL(/\/accounts\/register\/\?/, { timeout: 20000 });
  await settle(page);
  await screenshot(page, "fieldRep", "03-new-doctor-redirected-to-registration.png");

  await context.close();
}

async function captureRegistrationFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();
  const uniqueEmail = `selfreg.${Date.now()}@pedsedu.local`;
  const uniqueWhatsapp = uniqueDigits("9");
  const uniqueClinicPhone = uniqueDigits("8");

  captureMeta.registrations.selfService = {
    email: uniqueEmail,
    whatsapp: uniqueWhatsapp,
  };

  await page.goto(manifest.urls.register, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Register your clinic");
  await settle(page);
  await screenshot(page, "registration", "01-register-form.png");

  await page.locator('[name="first_name"]').fill("Neha");
  await page.locator('[name="last_name"]').fill("Sharma");
  await page.locator('[name="email"]').fill(uniqueEmail);
  await page.locator('[name="clinic_name"]').fill("Sunrise Kids Care");
  await page.locator('[name="imc_registration_number"]').fill("778899");
  await page.locator('[name="clinic_appointment_number"]').fill(uniqueClinicPhone);
  await page.locator('[name="clinic_address"]').fill(
    "44 Green Avenue, Bengaluru, Karnataka",
  );
  await page.locator('[name="postal_code"]').fill("560001");
  await page.locator('[name="clinic_whatsapp_number"]').fill(uniqueWhatsapp);
  await page.locator('[name="photo"]').setInputFiles(manifest.artifacts.doctor_photo_upload);
  await screenshot(page, "registration", "02-register-form-completed.png");

  await page.getByRole("button", { name: "Register Doctor" }).click();
  await page.waitForSelector("text=Registration Complete", { timeout: 20000 });
  await settle(page);
  await screenshot(page, "registration", "03-registration-complete.png");

  await context.close();
}

async function captureDoctorShareFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();

  await loginDoctor(
    page,
    manifest.credentials.doctor_email,
    manifest.credentials.doctor_password,
  );
  await attachWindowOpenRecorder(page);

  await page.locator("#searchBox").fill("Bronchiolitis");
  await page.waitForTimeout(900);
  await page.getByText(manifest.content.video_title, { exact: false }).first().click();
  await page.locator("#waNumber").fill(manifest.doctor.share_patient_whatsapp);
  await page.selectOption("#lang", "hi");
  await settle(page, 600);
  await screenshot(page, "doctor", "01-doctor-share-single-video.png");

  await page.locator("#shareVideoBtn").click();
  await page.waitForTimeout(500);
  captureMeta.whatsappUrls.doctorSingleVideo = await getRecordedUrls(page);

  await context.close();
}

async function captureClinicStaffFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();

  await loginDoctor(
    page,
    manifest.credentials.clinic_staff_email,
    manifest.credentials.clinic_staff_password,
  );
  await attachWindowOpenRecorder(page);

  await page.selectOption("#bundleSel", { label: manifest.content.cluster_title });
  await page.locator("#waNumber").fill(manifest.doctor.share_patient_whatsapp);
  await page.selectOption("#lang", "ta");
  await settle(page, 750);
  await screenshot(page, "clinic", "01-clinic-staff-share-bundle.png");

  await page.locator("#shareBundleBtn").click();
  await page.waitForTimeout(500);
  captureMeta.whatsappUrls.clinicBundleShare = await getRecordedUrls(page);

  await context.close();
}

async function capturePatientVideoFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();

  await page.goto(manifest.urls.patient_video_hi, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#lang");
  await settle(page, 1200);
  await screenshot(page, "patientVideo", "01-patient-video-hindi.png");

  await page.selectOption("#lang", "en");
  await page.waitForLoadState("domcontentloaded");
  await settle(page, 1000);
  await screenshot(page, "patientVideo", "02-patient-video-english.png");

  await context.close();
}

async function capturePatientBundleFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();

  await page.goto(manifest.urls.patient_cluster_ta, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#lang");
  await settle(page, 1200);
  await screenshot(page, "patientBundle", "01-patient-bundle-tamil.png");

  await page.selectOption("#lang", "en");
  await page.waitForLoadState("domcontentloaded");
  await settle(page, 1000);
  await screenshot(page, "patientBundle", "02-patient-bundle-english.png");

  await context.close();
}

async function captureAdminFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();

  await loginAdminToPublisher(page);
  await screenshot(page, "admin", "01-publisher-dashboard.png");

  await page.goto(manifest.urls.publisher_videos, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Videos");
  await settle(page);
  await screenshot(page, "admin", "02-video-list.png");

  const firstVideoLink = page.locator('a[href*="/publisher/videos/"]').first();
  if (await firstVideoLink.count()) {
    await firstVideoLink.click();
    await page.waitForLoadState("domcontentloaded");
    await settle(page);
    await screenshot(page, "admin", "03-video-edit-form.png");
  }

  await context.close();
}

async function captureTrackingFlow(browser) {
  await seedTrackingActivity(browser);

  const context = await newContext(browser);
  const page = await context.newPage();

  await page.goto(manifest.urls.tracking_login, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Restricted Access");
  await settle(page);
  await screenshot(page, "tracking", "01-tracking-login.png");

  await loginTracking(page);
  await screenshot(page, "tracking", "02-tracking-dashboard.png");

  await context.close();
}

async function capturePERecordsFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();

  await page.goto(manifest.urls.pe_records_login, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=PE System Records");
  await settle(page);
  await screenshot(page, "peRecords", "01-pe-records-login.png");

  await page.locator('[name="email"]').fill(manifest.credentials.admin_email);
  await page.locator('[name="password"]').fill(manifest.credentials.admin_password);
  await page.getByRole("button", { name: "Open PE Records Dashboard" }).click();
  await page.waitForURL(/\/publisher\/pe-system\/$/, { timeout: 20000 });
  await page.waitForSelector("text=PE Records Dashboard");
  await settle(page);
  await screenshot(page, "peRecords", "02-pe-records-dashboard.png");

  const firstCampaignUpdate = page.locator('a[href*="/publisher/pe-system/campaigns/"]').first();
  if (await firstCampaignUpdate.count()) {
    await firstCampaignUpdate.click();
    await page.waitForLoadState("domcontentloaded");
    await settle(page);
    await screenshot(page, "peRecords", "03-pe-campaign-edit.png");
    await page.goBack({ waitUntil: "domcontentloaded" });
    await settle(page);
  }

  const firstDoctorUpdate = page.locator('a[href*="/publisher/pe-system/doctors/"]').first();
  if (await firstDoctorUpdate.count()) {
    await firstDoctorUpdate.click();
    await page.waitForLoadState("domcontentloaded");
    await settle(page);
    await screenshot(page, "peRecords", "04-pe-doctor-edit.png");
  }

  await context.close();
}

async function captureSystemRecordsFlow(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();

  await loginAdminToPublisher(page);

  await page.goto(manifest.urls.system_records, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=System Records Hub");
  await settle(page);
  await screenshot(page, "systemRecords", "01-system-records-hub.png");
  await screenshot(page, "systemRecords", "02-system-campaigns.png");

  const firstFieldRepUpdate = page.locator('a[href*="/publisher/system-records/field-reps/"]').first();
  if (await firstFieldRepUpdate.count()) {
    await firstFieldRepUpdate.click();
    await page.waitForLoadState("domcontentloaded");
    await settle(page);
    await screenshot(page, "systemRecords", "03-system-field-rep-edit.png");
    await page.goBack({ waitUntil: "domcontentloaded" });
    await settle(page);
  }

  const firstDoctorUpdate = page.locator('a[href*="/publisher/system-records/doctors/"]').first();
  if (await firstDoctorUpdate.count()) {
    await firstDoctorUpdate.click();
    await page.waitForLoadState("domcontentloaded");
    await settle(page);
    await screenshot(page, "systemRecords", "04-system-doctor-edit.png");
  }

  await context.close();
}

async function main() {
  const browser = await chromium.launch({ headless: true });

  try {
    if (shouldRun("01", "platform-overview-and-role-map", "overview")) {
      await captureOverview(browser);
    }
    if (shouldRun("02", "publisher-campaign-setup", "publisher")) {
      await capturePublisherFlow(browser);
    }
    if (shouldRun("03", "field-rep-doctor-recruitment", "fieldrep", "field-rep")) {
      await captureFieldRepFlow(browser);
    }
    if (shouldRun("04", "doctor-registration-and-first-access", "registration")) {
      await captureRegistrationFlow(browser);
    }
    if (shouldRun("05", "doctor-share-single-video", "doctor")) {
      await captureDoctorShareFlow(browser);
    }
    if (shouldRun("06", "clinic-staff-share-bundle", "clinic")) {
      await captureClinicStaffFlow(browser);
    }
    if (shouldRun("07", "caregiver-single-video-view", "patientvideo", "patient-video")) {
      await capturePatientVideoFlow(browser);
    }
    if (shouldRun("08", "caregiver-bundle-view", "patientbundle", "patient-bundle")) {
      await capturePatientBundleFlow(browser);
    }
    if (shouldRun("09", "admin-content-management", "admin")) {
      await captureAdminFlow(browser);
    }
    if (shouldRun("10", "share-tracking-dashboard", "tracking")) {
      await captureTrackingFlow(browser);
    }
    if (shouldRun("11", "pe-records-dashboard", "perecords", "pe-records")) {
      await capturePERecordsFlow(browser);
    }
    if (shouldRun("12", "system-records-hub", "systemrecords", "system-records")) {
      await captureSystemRecordsFlow(browser);
    }
  } finally {
    await browser.close();
  }

  fs.writeFileSync(captureMetaPath, JSON.stringify(captureMeta, null, 2));
  console.log(`Screenshots captured. Metadata written to ${captureMetaPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
