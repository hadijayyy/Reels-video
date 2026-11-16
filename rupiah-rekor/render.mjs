// Render reel.html frame-by-frame with Playwright and pipe into ffmpeg.
// Usage: node render.mjs            -> out/video.mp4 (silent)
//        node render.mjs still 1.5  -> out/still_1.50.jpg
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const root = path.dirname(fileURLToPath(import.meta.url));
const tl = JSON.parse(readFileSync(path.join(root, 'timeline.json'), 'utf8'));
mkdirSync(path.join(root, 'out'), { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(root, 'reel.html')).href);
await page.evaluate(async (tl) => {
  await Promise.all(['500', '600', '700', '800', '900'].map(w => document.fonts.load(`${w} 60px "Inter Display"`)));
  window.setTimeline(tl);
}, tl);
const grab = async (t) => Buffer.from(await page.evaluate((t) => {
  window.renderFrame(t);
  return document.getElementById('c').toDataURL('image/jpeg', 0.96).split(',')[1];
}, t), 'base64');

if (process.argv[2] === 'still') {
  for (const a of process.argv.slice(3)) {
    const t = parseFloat(a);
    writeFileSync(path.join(root, 'out', `still_${t.toFixed(2)}.jpg`), await grab(t));
  }
} else {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(tl.fps), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(tl.fps), path.join(root, 'out', 'video.mp4')],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const n = Math.round(tl.duration * tl.fps);
  for (let i = 0; i < n; i++) {
    if (!ff.stdin.write(await grab(i / tl.fps))) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  console.log('video ok');
}
await browser.close();
