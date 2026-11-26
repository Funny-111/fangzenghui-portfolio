import { chromium } from "playwright-core";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const url = process.argv[2] || "http://127.0.0.1:5173";
const outDir = process.argv[3] || path.resolve("shots");
const name = process.argv[4] || "home";

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(url, { waitUntil: "networkidle" });

try {
  await page.waitForFunction(
    () => document.querySelector(".sidebar-footer")?.textContent?.includes("已连接"),
    { timeout: 6000 }
  );
} catch {
  console.log("warn: 未等到已连接状态，按当前画面截图");
}
await page.waitForTimeout(500);

const outPath = path.join(outDir, `${name}.png`);
await page.screenshot({ path: outPath, fullPage: false });
console.log(`saved: ${outPath}`);

await browser.close();
