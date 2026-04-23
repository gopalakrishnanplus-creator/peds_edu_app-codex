const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..", "..");
const manifestPath = path.join(__dirname, "demo_manifest.json");
const reportPath = path.join(
  root,
  "output",
  "doc",
  "user-flow-decks",
  "qa-previews",
  "navigation-audit.json",
);

if (!fs.existsSync(manifestPath)) {
  console.error(`Missing manifest: ${manifestPath}`);
  process.exit(1);
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
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

async function settle(page, ms = 800) {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(ms);
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
  await doctorPage.locator("#shareVideoBtn").click();
  await doctorPage.waitForTimeout(500);
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
  await clinicPage.waitForTimeout(500);
  await clinicContext.close();
}

async function runAudit() {
  const browser = await chromium.launch({ headless: true });
  const results = [];

  async function check(name, fn) {
    try {
      const detail = await fn();
      results.push({ name, status: "passed", detail });
    } catch (error) {
      results.push({
        name,
        status: "failed",
        detail: error && error.message ? error.message : String(error),
      });
    }
  }

  await check("accounts-forgot-password-navigation", async () => {
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(manifest.urls.login, { waitUntil: "domcontentloaded" });
    await page.getByRole("link", { name: /forgot password/i }).click();
    await page.waitForURL(/\/accounts\/request-password-reset\//, { timeout: 20000 });
    await context.close();
    return { target: "/accounts/request-password-reset/" };
  });

  await check("publisher-landing-to-campaign-form", async () => {
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(manifest.urls.publisher_entry, { waitUntil: "domcontentloaded" });
    await page.waitForURL(/\/publisher-landing-page\/\?campaign-id=/, { timeout: 20000 });
    await page.getByRole("link", { name: "Add details for this campaign" }).click();
    await page.waitForLoadState("domcontentloaded");
    await settle(page);
    const url = page.url();
    if (
      !/\/add-campaign-details\/\?campaign-id=/.test(url) &&
      !/\/campaigns\/.+\/edit\//.test(url)
    ) {
      throw new Error(`Expected add/edit campaign form, got ${url}`);
    }
    const heading = await page.locator("h1").first().textContent();
    await context.close();
    return { heading: (heading || "").trim(), target: url };
  });

  await check("field-rep-existing-doctor-whatsapp-redirect", async () => {
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(manifest.urls.field_rep, { waitUntil: "domcontentloaded" });
    await page.locator('[name="whatsapp_number"]').fill(manifest.doctor.existing_whatsapp);
    const response = await Promise.all([
      page.waitForResponse(
        (candidate) =>
          candidate.request().method() === "POST" &&
          candidate.url().includes("/field-rep-landing-page/"),
      ),
      page.getByRole("button", { name: "Submit" }).click(),
    ]).then(([postResponse]) => postResponse);
    const headers = response ? response.headers() : {};
    const location = headers.location || headers.Location || "";
    if (!location.includes("https://wa.me/")) {
      throw new Error(`Expected WhatsApp redirect location, got ${location || "<empty>"}`);
    }
    await context.close();
    return { target: location };
  });

  await check("field-rep-new-doctor-registration-redirect", async () => {
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(manifest.urls.field_rep, { waitUntil: "domcontentloaded" });
    await page.locator('[name="whatsapp_number"]').fill(manifest.doctor.new_doctor_whatsapp);
    await page.getByRole("button", { name: "Submit" }).click();
    await page.waitForURL(/\/accounts\/register\/\?/, { timeout: 20000 });
    const url = page.url();
    await context.close();
    return { target: url };
  });

  await check("doctor-share-video-button-result", async () => {
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
    const shareResponse = await Promise.all([
      page.waitForResponse(
        (response) =>
          response.request().method() === "POST" &&
          response.url().includes("/api/share-activity/"),
      ),
      page.locator("#shareVideoBtn").click(),
    ]).then(([response]) => response);
    await page.waitForTimeout(400);
    const urls = await getRecordedUrls(page);
    if (!urls.some((url) => url.includes("wa.me"))) {
      throw new Error("Video share did not open a WhatsApp URL.");
    }
    const payload = await shareResponse.json();
    if (!(payload && payload.ok)) {
      throw new Error("Video share did not record a successful share-activity response.");
    }
    await context.close();
    return { whatsappUrl: urls[0], shareResponse: payload };
  });

  await check("clinic-bundle-share-button-result", async () => {
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
    const shareResponse = await Promise.all([
      page.waitForResponse(
        (response) =>
          response.request().method() === "POST" &&
          response.url().includes("/api/share-activity/"),
      ),
      page.locator("#shareBundleBtn").click(),
    ]).then(([response]) => response);
    await page.waitForTimeout(400);
    const urls = await getRecordedUrls(page);
    if (!urls.some((url) => url.includes("wa.me"))) {
      throw new Error("Bundle share did not open a WhatsApp URL.");
    }
    const payload = await shareResponse.json();
    if (!(payload && payload.ok)) {
      throw new Error("Bundle share did not record a successful share-activity response.");
    }
    await context.close();
    return { whatsappUrl: urls[0], shareResponse: payload };
  });

  await check("patient-video-language-switch", async () => {
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(manifest.urls.patient_video_hi, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#lang");
    await page.selectOption("#lang", "en");
    await page.waitForLoadState("domcontentloaded");
    await settle(page, 1000);
    const url = page.url();
    if (!/[?&]lang=en\b/.test(url)) {
      throw new Error(`Expected language switch to update URL, got ${url}`);
    }
    await context.close();
    return { target: url };
  });

  await check("patient-bundle-language-switch", async () => {
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(manifest.urls.patient_cluster_ta, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#lang");
    await page.selectOption("#lang", "en");
    await page.waitForLoadState("domcontentloaded");
    await settle(page, 1000);
    const url = page.url();
    if (!/[?&]lang=en\b/.test(url)) {
      throw new Error(`Expected language switch to update URL, got ${url}`);
    }
    await context.close();
    return { target: url };
  });

  await check("tracking-login-and-dashboard", async () => {
    await seedTrackingActivity(browser);
    const context = await newContext(browser);
    const page = await context.newPage();
    await loginTracking(page);
    await page.waitForSelector("text=Tracking Dashboard");
    const hasSummaryCards = (await page.locator(".stat-card, .metric-card, .summary-card").count()) > 0;
    await context.close();
    return { summaryCardsDetected: hasSummaryCards };
  });

  await check("admin-video-edit-navigation", async () => {
    const context = await newContext(browser);
    const page = await context.newPage();
    await loginAdminToPublisher(page);
    await page.goto(manifest.urls.publisher_videos, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("text=Videos");
    const firstVideoLink = page.locator('a[href*="/publisher/videos/"]').first();
    if (!(await firstVideoLink.count())) {
      throw new Error("No video edit links found on publisher videos page.");
    }
    await firstVideoLink.click();
    await page.waitForLoadState("domcontentloaded");
    const url = page.url();
    await context.close();
    return { target: url };
  });

  await check("pe-records-login-and-edit-navigation", async () => {
    const context = await newContext(browser);
    const page = await context.newPage();
    await page.goto(manifest.urls.pe_records_login, { waitUntil: "domcontentloaded" });
    await page.locator('[name="email"]').fill(manifest.credentials.admin_email);
    await page.locator('[name="password"]').fill(manifest.credentials.admin_password);
    await page.getByRole("button", { name: "Open PE Records Dashboard" }).click();
    await page.waitForURL(/\/publisher\/pe-system\/$/, { timeout: 20000 });
    const firstDoctorUpdate = page.locator('a[href*="/publisher/pe-system/doctors/"]').first();
    if (!(await firstDoctorUpdate.count())) {
      throw new Error("No PE doctor edit links found.");
    }
    await firstDoctorUpdate.click();
    await page.waitForLoadState("domcontentloaded");
    const url = page.url();
    await context.close();
    return { target: url };
  });

  await check("system-records-navigation", async () => {
    const context = await newContext(browser);
    const page = await context.newPage();
    await loginAdminToPublisher(page);
    await page.goto(manifest.urls.system_records, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("text=System Records Hub");
    const firstFieldRepUpdate = page.locator('a[href*="/publisher/system-records/field-reps/"]').first();
    if (!(await firstFieldRepUpdate.count())) {
      throw new Error("No system field-rep edit links found.");
    }
    await firstFieldRepUpdate.click();
    await page.waitForLoadState("domcontentloaded");
    const url = page.url();
    await context.close();
    return { target: url };
  });

  await browser.close();

  const report = {
    generatedAt: new Date().toISOString(),
    baseUrl: manifest.urls.login.replace(/\/accounts\/login\/$/, ""),
    summary: {
      total: results.length,
      passed: results.filter((entry) => entry.status === "passed").length,
      failed: results.filter((entry) => entry.status === "failed").length,
    },
    results,
  };

  ensureDir(reportPath);
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`Wrote ${reportPath}`);

  if (report.summary.failed > 0) {
    process.exit(1);
  }
}

runAudit().catch((error) => {
  console.error(error);
  process.exit(1);
});
