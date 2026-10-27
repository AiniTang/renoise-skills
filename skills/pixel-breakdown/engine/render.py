"""Render page.html with headless Chromium (Playwright).
  python3 render.py stills 0.5,2.1,4.0 [--out qa/st]   check frames + qa/st/sheet.jpg contact sheet (4 per row)
  python3 render.py frames [--workers 6] [--out frames] every frame as frames/f_00000.jpg (30 fps) for encoding
  python3 render.py cues                                sound cue list -> audio/events.json (read by mix.py)
  python3 render.py cover cover.png                     3:4 cover (1080x1440) + cover_grid.png (profile-grid size)
Set CHROME=/path/to/chrome to use an installed browser instead of Playwright's bundled Chromium."""
import json, os, sys, time
from multiprocessing import Process
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
ARGS = ['--allow-file-access-from-files', '--disable-web-security', '--autoplay-policy=no-user-gesture-required', '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', '--force-device-scale-factor=1', '--mute-audio']


def open_page(p, w=1920, h=1080):
    kw = {'args': ARGS, 'headless': True}
    if os.environ.get('CHROME'):
        kw['executable_path'] = os.environ['CHROME']
    browser = p.chromium.launch(**kw)
    page = browser.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: m.type in ('error', 'warning') and print('console:', m.text, file=sys.stderr, flush=True))
    page.goto((ROOT / 'page.html').as_uri(), wait_until='load')
    if errors:
        raise SystemExit('page error: ' + errors[0])
    page.evaluate('window.ready()')
    if errors:
        raise SystemExit('page error: ' + errors[0])
    return browser, page, errors


def shot(page, frame, path):
    page.evaluate(f'window.render({frame})')
    page.screenshot(path=str(path), type='jpeg', quality=92, clip={'x': 0, 'y': 0, 'width': 1920, 'height': 1080})


def worker(frames, out, k):
    with sync_playwright() as p:
        browser, page, errors = open_page(p)
        t0 = time.time()
        for j, f in enumerate(frames):
            ts = time.time()
            shot(page, f, out / f'f_{f:05d}.jpg')
            if time.time() - ts > 2:
                print(f'worker {k}: slow frame {f} ({time.time() - ts:.1f}s, late seeks so far: {page.evaluate("window.SLOW_SEEKS || 0")})', flush=True)
            if errors:
                raise SystemExit(f'worker {k}: page error at frame {f}: {errors[0]}')
            if j % 150 == 0:
                print(f'worker {k}: {j}/{len(frames)} {time.time() - t0:.0f}s', flush=True)
        browser.close()


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == 'stills':
        times = [float(x) for x in sys.argv[2].split(',')]
        out = ROOT / arg('--out', 'qa/st')
        out.mkdir(parents=True, exist_ok=True)
        files = []
        with sync_playwright() as p:
            browser, page, _ = open_page(p)
            fps = page.evaluate('window.TL.fps')
            for t in times:
                f = out / f's_{t:06.2f}.jpg'
                shot(page, round(t * fps), f)
                files.append(f)
            browser.close()
        from PIL import Image, ImageDraw
        cols, w, h = 4, 480, 270
        sheet = Image.new('RGB', (cols * w, ((len(files) + cols - 1) // cols) * h), 'black')
        for i, f in enumerate(files):
            im = Image.open(f).convert('RGB').resize((w, h))
            ImageDraw.Draw(im).text((6, 4), f'{times[i]:.2f}s', fill='yellow')
            sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        sheet.save(out / 'sheet.jpg', quality=85)
        print('sheet ->', out / 'sheet.jpg')
    elif mode == 'frames':
        out = ROOT / arg('--out', 'frames')
        out.mkdir(parents=True, exist_ok=True)
        n_workers = int(arg('--workers', '6'))
        with sync_playwright() as p:
            browser, page, _ = open_page(p)
            total = int(page.evaluate('Math.round(window.TL.dur * window.TL.fps)'))
            browser.close()
        chunks = [list(range(total))[k::n_workers] for k in range(n_workers)]
        procs = [Process(target=worker, args=(c, out, k)) for k, c in enumerate(chunks)]
        for pr in procs:
            pr.start()
        for pr in procs:
            pr.join()
        bad = [pr.exitcode for pr in procs if pr.exitcode]
        missing = [f for f in range(total) if not (out / f'f_{f:05d}.jpg').exists()]
        if bad or missing:
            raise SystemExit(f'render failed: exit codes {bad}, {len(missing)} frames missing')
        print(f'frames -> {out} ({total} frames, 30 fps)')
    elif mode == 'cues':
        with sync_playwright() as p:
            browser, page, _ = open_page(p)
            cues = page.evaluate('window.CUES()')
            browser.close()
        (ROOT / 'audio').mkdir(exist_ok=True)
        (ROOT / 'audio/events.json').write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding='utf-8')
        print('cues ->', ROOT / 'audio/events.json', len(cues['events']), 'events')
    elif mode == 'cover':
        path = Path(sys.argv[2]).resolve()
        with sync_playwright() as p:
            browser, page, _ = open_page(p, 1080, 1440)
            url = page.evaluate('window.renderCover().then(() => document.getElementById("cover").toDataURL("image/png"))')
            browser.close()
        import base64
        from PIL import Image
        path.write_bytes(base64.b64decode(url.split(',')[1]))
        Image.open(path).convert('RGB').resize((180, 240), Image.LANCZOS).save(path.with_name('cover_grid.png'))
        print('cover ->', path, '| profile-grid preview ->', path.with_name('cover_grid.png'))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
