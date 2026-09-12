// End-to-end SOFTWARE TEST. All human decisions below are synthetic and confined
// to fresh browser contexts. Never import these into a researcher workspace.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const base = (process.argv[2] || "http://127.0.0.1:8015").replace(/\/$/, "");
const browser = process.env.INSTRUMENT_BROWSER_HELPER
  ? await (await import(process.env.INSTRUMENT_BROWSER_HELPER)).launch()
  : await (await import("playwright")).chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1050 },
  acceptDownloads: true,
});
const page = await context.newPage();
const errors = [],
  predictionFetches = [],
  checks = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("request", (r) => {
  if (r.url().includes("predictions.json")) predictionFetches.push(r.url());
});
try {
  await page.goto(`${base}/ratio/`);
  await page
    .getByRole("heading", {
      name: "A shared way to judge what ageing research is for.",
    })
    .waitFor();
  await page
    .getByText("No funding estimate is published by this instrument.", {
      exact: false,
    })
    .waitFor();
  assert.equal(
    await page.locator("body").evaluate((el) => el.scrollWidth > innerWidth),
    false,
  );
  checks.push(
    "Overview communicates unvalidated instrument and no funding result",
  );
  await page.getByRole("link", { name: "Label grants", exact: true }).click();
  await page.locator("#reviewer").fill("SOFTWARE_TEST_A");
  await page.locator("#attest").check();
  await page.locator("input[name=category][value=ambiguous]").check();
  await page
    .locator("#reason")
    .fill("SOFTWARE TEST ONLY: synthetic boundary judgment.");
  await page
    .getByRole("button", { name: "Save human verdict", exact: true })
    .click();
  await page
    .getByRole("button", { name: "First verdict saved", exact: true })
    .waitFor();
  assert.equal(await page.locator("#low-confidence").isChecked(), false);
  assert.equal(await page.locator("#reason").isDisabled(), true);
  assert.equal(
    predictionFetches.length,
    0,
    "The labeling view must not fetch model predictions",
  );
  checks.push("Blind labeling saves ambiguity independently of low confidence");
  await page.reload();
  await page
    .getByRole("button", { name: "First verdict saved", exact: true })
    .waitFor();
  checks.push("Browser progress persists and first verdict stays locked");
  const downloaded = page.waitForEvent("download");
  await page.locator("#export-reviews").click();
  const file = await downloaded;
  const a = JSON.parse(await readFile(await file.path(), "utf8"));
  assert.equal(a.decisions.length, 1);
  assert.equal(a.reviewer, "SOFTWARE_TEST_A");
  const b = {
    ...a,
    reviewer: "SOFTWARE_TEST_B",
    decisions: a.decisions.map((d) => ({
      ...d,
      label: "neither",
      low_confidence: true,
      reason: "SOFTWARE TEST ONLY: independent synthetic disagreement.",
    })),
  };
  const makeFile = (name, body) => ({
    name,
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(body)),
  });
  await page.getByRole("link", { name: "Research admin", exact: true }).click();
  await page
    .getByRole("heading", { name: "Items, disagreements first" })
    .waitFor();
  await page
    .getByText("No imported human decisions.", { exact: false })
    .waitFor();
  await page
    .locator("#import-reviews")
    .setInputFiles([makeFile("a.json", a), makeFile("b.json", b)]);
  await page
    .getByText("Human files imported. Existing first verdicts were preserved.")
    .waitFor();
  await page
    .getByText("2 reviewer codes · 2 individual decisions.", { exact: false })
    .waitFor();
  const top = page.locator("#app details[data-record-id]").first();
  assert.equal(
    await top.getAttribute("data-record-id"),
    a.decisions[0].record_id,
  );
  assert.match(await top.innerText(), /Disagreement/);
  await top.locator("summary").click();
  await top.getByText("SOFTWARE_TEST_A", { exact: true }).waitFor();
  await top.getByText("SOFTWARE_TEST_B", { exact: true }).waitFor();
  checks.push("Admin preserves both reviewers and ranks disagreements first");
  const csvDownload = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export decisions CSV", exact: true })
    .click();
  const csv = await readFile(await (await csvDownload).path(), "utf8");
  assert.equal(csv.split("\r\n").length, 4);
  assert.match(csv, /SOFTWARE_TEST_A/);
  assert.match(csv, /SOFTWARE_TEST_B/);
  checks.push(
    "CSV exports individual decisions with source and pipeline provenance",
  );
  const conflict = {
    ...a,
    decisions: a.decisions.map((d) => ({ ...d, label: "consequences" })),
  };
  await page
    .locator("#import-reviews")
    .setInputFiles(makeFile("conflict.json", conflict));
  await page.getByText("Conflicting first verdict", { exact: false }).waitFor();
  await page
    .getByText("2 reviewer codes · 2 individual decisions.", { exact: false })
    .waitFor();
  await page
    .locator("#import-reviews")
    .setInputFiles(makeFile("stale.json", { ...a, packet_id: "stale" }));
  await page
    .getByText("different corpus, pipeline or taxonomy version", {
      exact: false,
    })
    .waitFor();
  checks.push(
    "Conflicting and stale imports do not replace existing decisions",
  );
  if (process.env.INSTRUMENT_SCREENSHOT)
    await page.screenshot({
      path: process.env.INSTRUMENT_SCREENSHOT,
      fullPage: false,
    });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${base}/ratio/#label`);
  await page
    .getByRole("heading", { name: "Label the research purpose." })
    .waitFor();
  assert.equal(
    await page.locator("body").evaluate((el) => el.scrollWidth > innerWidth),
    false,
  );
  checks.push("Labeling page fits a 390-pixel viewport");
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify(
      { status: "passed", synthetic_fixtures: true, checks },
      null,
      2,
    ),
  );
} finally {
  await context.close();
  await browser.close();
}
