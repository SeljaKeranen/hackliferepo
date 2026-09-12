import { launch } from "./browser.mjs";
const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(
  (process.env.APP_URL || "http://127.0.0.1:5173") + "/country/sweden",
);
await page.getByRole("heading", { name: "Sweden", exact: true }).waitFor();
await page.screenshot({ path: "outputs/funding-country.png" });
await browser.close();
