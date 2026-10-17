// Render many stills of one composition with a single bundle + browser.
// Usage: node stills.mjs <compId> <outDir> <frame> [frame...]
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition, openBrowser } from "@remotion/renderer";
import path from "node:path";
import fs from "node:fs";
const [id, outDir, ...frames] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const browser = await openBrowser("chrome", { chromiumOptions: { gl: "angle" } });
const composition = await selectComposition({ serveUrl, id, puppeteerInstance: browser });
for (const f of frames) {
  const t0 = Date.now();
  await renderStill({ serveUrl, composition, frame: Number(f), output: path.join(outDir, `f${f}.png`), puppeteerInstance: browser, chromiumOptions: { gl: "angle" }, timeoutInMilliseconds: 120000 });
  console.log(`f${f}.png ${Date.now() - t0}ms`);
}
await browser.close({ silent: true });
