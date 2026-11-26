import { chromium } from "playwright-core";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const url = process.argv[2] || "http://127.0.0.1:5173";
const outDir = process.argv[3] || path.resolve("shots");

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

async function shot(name) {
  const outPath = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: outPath, fullPage: false });
  console.log(`saved: ${outPath}`);
}

async function gotoConnected() {
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForFunction(
    () => document.querySelector(".sidebar-footer")?.textContent?.includes("已连接"),
    { timeout: 8000 }
  );
  await page.waitForTimeout(300);
}

async function submitQuery(text) {
  const textarea = page.locator('textarea[aria-label="研搜任务"]');
  await textarea.fill(text);
  await textarea.press("Enter");
}

async function waitBodyText(text, timeout) {
  await page.waitForFunction(
    (needle) => document.body.innerText.includes(needle),
    text,
    { timeout }
  );
}

// 1) 空状态
await gotoConnected();
await shot("01-home");

// 2) 执行中（慢放剧本，约 40s 全程，15s 时事件已铺开）
await submitQuery(
  "慢放：请使用网络搜索工具，检索 2026 年跨境电商 AI 客服趋势，列出 5 条关键变化，并附上来源。"
);
await waitBodyText("正在研搜", 8000);
await page.waitForTimeout(15000);
await shot("02-running");

// 3) 完成态
await waitBodyText("已同步", 60000);
await page.waitForTimeout(500);
await shot("03-done");

// 4) 异常态
await submitQuery("请使用网络搜索工具检索测试，触发异常");
await waitBodyText("连接超时", 15000);
await page.waitForTimeout(400);
await shot("05-error");

await browser.close();
console.log("all states captured");
