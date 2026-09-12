import { launch } from "./browser.mjs";
import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
const base = process.env.DEMO_URL || "http://127.0.0.1:5173";
mkdirSync("outputs/recording", { recursive: true });
const release = JSON.parse(readFileSync("public/funding/current.json"));
const browser = await launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: "outputs/recording", size: { width: 1440, height: 900 } },
});
const page = await context.newPage();
const video = page.video();
const started = Date.now(),
  cues = [];
async function caption(text) {
  cues.push({ seconds: Math.round((Date.now() - started) / 1000), text });
  await page.evaluate((text) => {
    let el = document.getElementById("recording-caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "recording-caption";
      el.style.cssText =
        "position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:9999;background:#173f34f5;color:#eef2df;border:1px solid #9eb58380;padding:14px 25px;border-radius:8px;font:500 16px Inter,system-ui;box-shadow:0 4px 24px #0002;max-width:90vw;text-align:center;pointer-events:none";
      document.body.appendChild(el);
    }
    el.textContent = text;
  }, text);
}
let completed = false;
const hold = (ms) => page.waitForTimeout(ms);
try {
  await page.goto(base);
  await page.getByRole("heading", { name: /Where does ageing/ }).waitFor();
  await caption(
    "Where does public ageing research money go? A report for the public and advocates.",
  );
  await hold(6500);
  await page.locator("#portfolios").scrollIntoViewIfNeeded();
  await caption(
    "Two named government portfolios. These are not national totals or a country ranking.",
  );
  await hold(6500);
  await page.locator(".portfolio-card").first().click();
  await page.getByRole("heading", { name: "Sweden", exact: true }).waitFor();
  await caption(
    "Sweden: Research Council + Forte. Recorded commitments can fund several years.",
  );
  await hold(6500);
  await page.getByRole("link", { name: /Inspect the source records/ }).click();
  await page.getByPlaceholder(/Try metabolism/).fill("mitochondria");
  await page.locator(".grant-title").first().waitFor();
  await caption(
    "Search the complete selected portfolio, including projects under other labels.",
  );
  await hold(6500);
  await page.locator(".grant-title").first().click();
  await caption(
    "Each award keeps the amount, funding period, source date and original-source link.",
  );
  await hold(9000);
  await page.getByRole("button", { name: "Close source details" }).click();
  await page.goto(base + "/country/united-states");
  await page
    .getByRole("heading", { name: "United States", exact: true })
    .waitFor();
  await caption(
    "United States: NIA-administered FY2024 awards. Subprojects are removed to avoid duplicate totals.",
  );
  await hold(6500);
  await page.goto(base + "/method");
  await page
    .getByRole("heading", { name: "A ratio you can question." })
    .waitFor();
  await caption(
    "The numerator is ageing biology plus ageing interventions. We weight funding amounts, not grant counts.",
  );
  await hold(7000);
  await page
    .getByRole("heading", {
      name: "Classify the objective, not just the title.",
    })
    .scrollIntoViewIfNeeded();
  await caption(
    "Metabolism or neurodegeneration can hide an ageing objective. Unclear cases remain unresolved.",
  );
  await hold(6500);
  await page
    .getByRole("heading", { name: "Make uncertainty visible." })
    .scrollIntoViewIfNeeded();
  await caption(
    "Known unresolved amounts enter sensitivity scenarios. Missing amounts are counted separately.",
  );
  await hold(8000);
  await page.locator(".verification").scrollIntoViewIfNeeded();
  await caption(
    `The requirement: ≥90% human correctness overall AND per country. Current progress: ${release.review.overall.reviewed}/60.`,
  );
  await hold(8000);
  await page.goto(base + "/country/sweden");
  await page.getByRole("heading", { name: "Sweden", exact: true }).waitFor();
  await page.locator(".snapshot").scrollIntoViewIfNeeded();
  await caption(
    release.reports.SE.publication_ready
      ? "Frozen report links and share cards preserve the scope, source and date."
      : "Frozen report links preserve the scope and date. Numerical share cards wait for review.",
  );
  await hold(6500);
  await page.goto(base);
  await page.getByRole("heading", { name: /Where does ageing/ }).waitFor();
  await caption(
    "Selja · Max · Jan / Next: human review, biological boundary decisions and a reader test.",
  );
  const remaining = 95000 - (Date.now() - started);
  if (remaining > 0) await hold(remaining);
  completed = true;
} finally {
  await context.close();
  await video.saveAs("outputs/longview-demo.webm");
  await browser.close();
  writeFileSync("outputs/recording-cues.json", JSON.stringify(cues, null, 2));
  writeFileSync(
    "outputs/recording-verification.json",
    JSON.stringify(
      {
        funding_release: release.release_id,
        recorded_at: new Date().toISOString(),
        wall_duration_seconds: (Date.now() - started) / 1000,
        complete: completed,
        interaction:
          "Actual browser navigation, country reports, source search/details, method and frozen link.",
        captions: true,
        audio: false,
        synthetic_reviews: false,
        cues: cues.length,
      },
      null,
      2,
    ),
  );
  console.log(
    "Recorded the funding report walkthrough with captions. No human approvals were simulated.",
  );
}
