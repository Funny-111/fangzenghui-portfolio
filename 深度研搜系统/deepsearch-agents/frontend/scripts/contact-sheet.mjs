import { chromium } from "playwright-core";
import { readFile, writeFile } from "node:fs/promises";

const files = [
  ["01-home", "shots/01-home.png"],
  ["02-running", "shots/02-running.png"],
  ["03-done", "shots/03-done.png"],
  ["05-error", "shots/05-error.png"]
];

const cellW = 640;
const cellH = 400;
const cols = 2;
const rows = 3;

const parts = [];
for (const [name, file] of files) {
  const buf = await readFile(file);
  parts.push({ name, dataUrl: `data:image/png;base64,${buf.toString("base64")}` });
}

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage({ viewport: { width: cols * cellW, height: rows * cellH } });

const html = `<!doctype html><html><body style="margin:0;background:#333;display:grid;grid-template-columns:repeat(${cols},${cellW}px);grid-auto-rows:${cellH}px;gap:4px;font:14px sans-serif">
${parts
  .map(
    (p, i) => `<div style="position:relative;background:#000">
      <img src="${p.dataUrl}" style="width:100%;height:100%;object-fit:contain"/>
      <span style="position:absolute;left:6px;top:6px;background:#000c;color:#fff;padding:2px 8px;border-radius:4px">${i + 1}. ${p.name}</span>
    </div>`
  )
  .join("")}
</body></html>`;

await page.setContent(html);
await page.waitForTimeout(500);
const out = `contact-sheet-${Date.now()}.png`;
await page.screenshot({ path: out });
console.log("saved:", out);
await browser.close();
