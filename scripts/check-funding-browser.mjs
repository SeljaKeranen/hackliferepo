import { launch } from "./browser.mjs";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import assert from "node:assert/strict";
const base = process.env.APP_URL || "http://127.0.0.1:5173";
const release = await fetch(base + "/funding/current.json").then((r) =>
  r.json(),
);
const browser = await launch();
const results = [];
mkdirSync("outputs", { recursive: true });
async function check(name, fn) {
  try {
    await fn();
    results.push({ name, passed: true });
    console.log("PASS", name);
  } catch (e) {
    results.push({ name, passed: false, error: e.message });
    console.error("FAIL", name, e.message);
  }
}
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await check("Landing report and 90% requirement", async () => {
  await page.goto(base);
  await page.getByRole("heading", { name: /Where does ageing/ }).waitFor();
  assert.equal(await page.locator(".portfolio-card").count(), 2);
  assert.match(await page.locator(".verification").innerText(), /90%/);
  if (release.review.overall.accuracy === null)
    assert.match(
      await page.locator(".verification").innerText(),
      /Accuracy not yet measured/,
    );
  await page.screenshot({
    path: "outputs/funding-desktop.png",
    fullPage: true,
  });
});
await check("Sweden report, gate and immutable permalink", async () => {
  await page.locator(".portfolio-card").first().click();
  await page.getByRole("heading", { name: "Sweden", exact: true }).waitFor();
  await page.screenshot({ path: "outputs/funding-country.png" });
  assert.equal(
    await page
      .getByRole("button", { name: "Download share card" })
      .isDisabled(),
    !release.reports.SE.publication_ready ||
      release.reports.SE.summary?.ratio == null,
  );
  const link = await page
    .getByRole("link", { name: /Open frozen report/ })
    .getAttribute("href");
  await page.goto(base + link);
  await page
    .getByRole("heading", {
      name:
        release.reports.SE.publication_ready &&
        release.reports.SE.summary?.ratio != null
          ? `${(release.reports.SE.summary.ratio * 100).toFixed(1)}%`
          : "Estimate pending human review",
      exact: true,
    })
    .waitFor();
  await page.getByRole("link", { name: /Explore this exact report/ }).click();
  assert.match(page.url(), /release=/);
  await page.getByRole("link", { name: /Inspect the source records/ }).click();
  await page.getByPlaceholder(/Try metabolism/).waitFor();
  assert.equal(
    await page.getByLabel("Country", { exact: true }).inputValue(),
    "SE",
  );
});
await check(
  "Source search, original award details and empty state",
  async () => {
    await page.getByPlaceholder(/Try metabolism/).fill("mitochondria");
    await page.locator(".grant-title").first().waitFor();
    assert((await page.locator(".grant-title").count()) > 0);
    await page.locator(".grant-title").first().click();
    await page.locator("dialog[open]").waitFor();
    const source = await page
      .getByRole("link", { name: /Open original award/ })
      .getAttribute("href");
    assert.match(source, /^https:\/\/www.vr.se/);
    assert.match(
      await page.locator("dialog").innerText(),
      /Funding year[\s\S]*2024/,
    );
    await page.getByRole("button", { name: "Close source details" }).click();
    await page
      .getByPlaceholder(/Try metabolism/)
      .fill("zz-no-such-award-178347");
    await page.getByRole("heading", { name: "No matching awards." }).waitFor();
    await page.screenshot({
      path: "outputs/funding-sources.png",
      fullPage: true,
    });
  },
);
await check("US source amounts sorted only within country", async () => {
  await page.goto(base + "/sources?country=US");
  await page.getByLabel("Sort", { exact: true }).selectOption("amount");
  await page.waitForTimeout(300);
  await page.locator(".grant-title").first().click();
  assert.match(
    await page.locator("dialog").innerText(),
    /Health and Retirement/,
  );
  await page.keyboard.press("Escape");
  await page.getByLabel("Country", { exact: true }).selectOption("all");
  assert.equal(
    await page.getByLabel("Sort", { exact: true }).inputValue(),
    "title",
  );
});
await check("Method, formula, dated provider crosschecks", async () => {
  await page.goto(base + "/method");
  await page
    .getByRole("heading", { name: "A ratio you can question." })
    .waitFor();
  assert.match(await page.locator("main").innerText(), /N \/ \(D \+ U\)/);
  await page.getByText("See the dated provider cross-checks").click();
  assert((await page.locator(".crosschecks a").count()) >= 12);
  assert.match(await page.locator("main").innerText(), /You.com and Tavily/);
});
await check("Mobile landing and source details fit viewport", async () => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base);
  await page.getByRole("heading", { name: /Where does ageing/ }).waitFor();
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({ path: "outputs/funding-mobile.png", fullPage: true });
  await page.goto(base + "/sources?country=SE");
  await page.locator(".grant-title").first().waitFor();
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.locator(".grant-title").first().click();
  assert(
    await page.evaluate(
      () =>
        document.querySelector("dialog").getBoundingClientRect().right <=
        innerWidth,
    ),
  );
});
await check(
  "Funding reviewer unlock, blinding and local fixture export",
  async () => {
    const key = readFileSync("outputs/funding-reviewer.key", "utf8").trim();
    const review = await context.newPage();
    await review.goto(base + "/review/funding/#key=" + key);
    await review.locator("#workspace:not([hidden])").waitFor();
    assert.equal(new URL(review.url()).hash, "");
    assert.equal(await review.locator("#list button").count(), 80);
    assert(
      !(await review
        .locator("#record")
        .innerText()
        .then((x) => x.includes("candidate share"))),
    );
    const queue = await review.locator("#list button").allTextContents();
    const alreadyCompleted = queue.filter((text) => text.startsWith("✓")).length;
    const pendingIndex = queue.findIndex((text) => !text.startsWith("✓"));
    if (pendingIndex >= 0) {
      await review.locator("#list button").nth(pendingIndex).click();
      await review.locator("#reviewer").fill("BROWSER TEST FIXTURE");
      await review.locator("#attest").check();
      await review.locator("#category").selectOption("unresolved");
      for (const s of await review.locator("#record [data-check]").all())
        await s.selectOption("false");
      await review.getByRole("button", { name: "Save human verdict" }).click();
      await review.getByRole("button", { name: "Saved · first verdict retained" }).waitFor();
    }
    assert.equal(await review.locator("#category").isDisabled(), true);
    const downloadPromise = review.waitForEvent("download");
    await review.locator("#export").click();
    const d = await downloadPromise;
    await d.saveAs("outputs/funding-browser-fixture-DO-NOT-IMPORT.json");
    const exported = JSON.parse(
      readFileSync("outputs/funding-browser-fixture-DO-NOT-IMPORT.json"),
    );
    exported.simulation = true;
    writeFileSync(
      "outputs/funding-browser-fixture-DO-NOT-IMPORT.json",
      JSON.stringify(exported, null, 2),
    );
    assert.equal(Object.keys(exported.verdicts).length, alreadyCompleted + (pendingIndex >= 0 ? 1 : 0));
    await review.locator("#reports-tab").click();
    assert.equal(await review.locator("#reports").isVisible(), true);
    assert.equal(await review.locator("#grants").isVisible(), false);
    await review.screenshot({
      path: "outputs/funding-review.png",
      fullPage: true,
    });
    await review.close();
  },
);
await check("Earlier policy reviewer remains available", async () => {
  await page.goto(base + "/review/");
  assert.match(await page.title(), /review/i);
});
await check("No application runtime errors", async () =>
  assert.deepEqual(errors, []),
);
await context.close();
await browser.close();
writeFileSync(
  "outputs/funding-browser-check.json",
  JSON.stringify(
    {
      base,
      checked_at: new Date().toISOString(),
      fixture_note:
        "The review export is a synthetic browser fixture in ignored outputs; it was not imported.",
      results,
    },
    null,
    2,
  ),
);
if (results.some((r) => !r.passed)) process.exitCode = 1;
