// Test-only approved response, routed inside this browser. Never published or imported.
import { launch } from "./browser.mjs";
import { readFileSync, writeFileSync } from "node:fs";
import assert from "node:assert/strict";
const base = process.env.APP_URL || "http://127.0.0.1:5180";
const release = JSON.parse(readFileSync("public/funding/current.json"));
const reports = JSON.parse(readFileSync("data/funding/report-preview.json"));
const browser = await launch(),
  page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.route("**/funding/current.json", (route) => {
  const fixture = structuredClone(release);
  fixture.reports.SE = {
    ...fixture.reports.SE,
    publication_ready: true,
    status: "TEST_FIXTURE",
    summary: reports.SE.summary,
  };
  route.fulfill({ json: fixture });
});
await page.goto(base + "/country/sweden");
await page.getByRole("heading", { name: "Sweden", exact: true }).waitFor();
assert.equal(
  await page.getByRole("button", { name: "Download share card" }).isDisabled(),
  false,
);
const download = page.waitForEvent("download");
await page.getByRole("button", { name: "Download share card" }).click();
await (await download).saveAs("outputs/approved-share-card-TEST-FIXTURE.png");
assert(
  readFileSync("outputs/approved-share-card-TEST-FIXTURE.png").length > 10000,
);
assert.match(
  await page.locator(".breakdown").innerText(),
  /Known-amount sensitivity/,
);
assert.equal(await page.locator(".money-grid i").count(), 100);
writeFileSync(
  "outputs/approved-ui-fixture-check.json",
  JSON.stringify(
    {
      passed: true,
      simulation: true,
      note: "An approved response was injected only in this isolated browser. No human export was imported and no approved response was written to public/.",
      checks: [
        "Share card download",
        "100-cell amount view",
        "Category totals and uncertainty",
      ],
    },
    null,
    2,
  ),
);
await browser.close();
console.log(
  "PASS isolated approved UI fixture: share-card download, 100-cell view, breakdown and sensitivity. No publication or human review occurred.",
);
