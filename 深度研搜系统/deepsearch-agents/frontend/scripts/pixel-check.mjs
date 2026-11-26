import { chromium } from "playwright-core";
import { readFile } from "node:fs/promises";

const files = process.argv.slice(2);

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage();

for (const f of files) {
  const buf = await readFile(f);
  const url = `data:image/png;base64,${buf.toString("base64")}`;
  const stats = await page.evaluate(async (src) => {
    const img = new Image();
    img.src = src;
    await img.decode();
    const c = document.createElement("canvas");
    c.width = img.width;
    c.height = img.height;
    const ctx = c.getContext("2d");
    ctx.drawImage(img, 0, 0);
    function px(x, y) {
      const d = ctx.getImageData(x, y, 1, 1).data;
      return `${d[0]},${d[1]},${d[2]}`;
    }
    return {
      size: `${img.width}x${img.height}`,
      pillZone: px(1200, 33),
      centerZone: px(720, 350),
      inputZone: px(860, 790),
      redAlert: px(860, 86)
    };
  }, url);
  console.log(f, JSON.stringify(stats));
}

await browser.close();
