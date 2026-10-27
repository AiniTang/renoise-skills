#!/usr/bin/env python3
"""Media steps of a Pixel Breakdown project (ffmpeg / ffprobe), the same on macOS, Linux, Windows and the Renoise sandbox.
  python3 media.py probe <clip>                          duration, fps, size, orientation, audio (JSON)
  python3 media.py cuts <clip> [--threshold 0.3] [--out qa/cuts_<name>]
                                                          hard cuts (scene score) -> cuts.json, and labelled contact sheets at
                                                          4 frames per second (red frame = first frame after a cut)
  python3 media.py intra <clip> <out.mp4> [--size WxH]   all-intra H.264, 30 fps, yuv420p, no audio; 432x768 for vertical
                                                          clips, 768x432 for horizontal ones (centre crop to fill)
  python3 media.py thumb <clip> <out.jpg> [--at 1.0]     360x270 JPEG for chat attachments
  python3 media.py wav <in> <out.wav> [--stereo]         48 kHz 16-bit WAV (mono unless --stereo)
  python3 media.py final <frames_dir> <mix.wav> <out.mp4>
                                                          H.264 CRF 18 yuv420p + AAC 192k, fast start, audio normalised to
                                                          -16 LUFS integrated / -1.5 dBTP (two-pass loudnorm)
  python3 media.py qa <video.mp4> [--expect 74.2]        streams, duration, loudness, true peak, silent seconds, 6 frames
                                                          -> qa/final/sheet.jpg next to the video's project; exit 1 on a failure"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def tool(name):
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"{name} not found: run scripts/doctor.py")
    return path


def run(args, capture=False):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"{Path(args[0]).name} failed:\n" + "\n".join(r.stderr.strip().splitlines()[-12:]))
    return r


def ff(*args):
    return run([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)])


def probe(clip):
    info = json.loads(run([tool("ffprobe"), "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(clip)]).stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    out = {"file": str(clip), "duration": round(float(info["format"].get("duration", 0)), 3),
           "audio": any(s["codec_type"] == "audio" for s in info["streams"])}
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = v.get("tags", {}).get("rotate") or next((sd.get("rotation") for sd in v.get("side_data_list", []) if "rotation" in sd), 0)
        if abs(int(float(rot or 0))) % 180 == 90:
            w, h = h, w
        num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1").split("/")
        out.update(width=w, height=h, fps=round(float(num) / float(den), 3) if float(den) else 0,
                   orientation="vertical" if h > w else "horizontal" if w > h else "square")
    return out


def contact_sheets(frames, times, cut_times, out, per_sheet=48, cols=8):
    from PIL import Image, ImageDraw
    sheets = []
    for k in range(0, len(frames), per_sheet):
        chunk = frames[k:k + per_sheet]
        ims = [Image.open(f).convert("RGB") for f in chunk]
        w, h = ims[0].size
        sheet = Image.new("RGB", (cols * w, ((len(ims) + cols - 1) // cols) * (h + 14)), "black")
        d = ImageDraw.Draw(sheet)
        for i, (im, t) in enumerate(zip(ims, times[k:k + per_sheet])):
            x, y = (i % cols) * w, (i // cols) * (h + 14)
            sheet.paste(im, (x, y + 14))
            after_cut = any(t - 0.25 < c <= t for c in cut_times)
            d.text((x + 3, y + 1), f"{t:.2f}s" + ("  CUT" if after_cut else ""), fill="red" if after_cut else "yellow")
            if after_cut:
                d.rectangle([x, y + 14, x + w - 1, y + 13 + h], outline="red", width=3)
        path = out / f"sheet_{k // per_sheet + 1:02d}.jpg"
        sheet.save(path, quality=85)
        sheets.append(path)
    return sheets


def cmd_cuts(a):
    clip = Path(a.clip)
    out = Path(a.out or f"qa/cuts_{clip.stem}")
    (out / "frames").mkdir(parents=True, exist_ok=True)
    r = run([tool("ffmpeg"), "-hide_banner", "-i", str(clip), "-an", "-vf", f"select='gt(scene,{a.threshold})',showinfo", "-f", "null", "-"])
    cuts = [round(float(t), 3) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    for f in (out / "frames").glob("c_*.jpg"):
        f.unlink()
    ff("-i", clip, "-an", "-vf", "fps=4,scale=200:-2", out / "frames/c_%05d.jpg")
    frames = sorted((out / "frames").glob("c_*.jpg"))
    times = [i / 4 for i in range(len(frames))]
    sheets = contact_sheets(frames, times, cuts, out)
    meta = probe(clip)
    (out / "cuts.json").write_text(json.dumps({"clip": str(clip), "threshold": a.threshold, "cuts": cuts, **meta}, indent=1), encoding="utf-8")
    print(f"{len(cuts)} cuts: {', '.join(f'{c:.2f}' for c in cuts) or '-'}")
    print("sheets:", *sheets, sep="\n  ")


def cmd_intra(a):
    if a.size:
        w, h = map(int, a.size.lower().split("x"))
    else:
        w, h = (432, 768) if probe(a.clip).get("orientation") == "vertical" else (768, 432)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    ff("-i", a.clip, "-an", "-vf", f"fps=30,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1",
       "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-g", "1", "-keyint_min", "1", "-x264-params", "keyint=1:scenecut=0",
       "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out)
    print(f"{a.out}  {w}x{h} all-intra 30 fps, {probe(a.out)['duration']}s")


def cmd_thumb(a):
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    ff("-ss", a.at, "-i", a.clip, "-frames:v", "1", "-vf", "scale=360:270:force_original_aspect_ratio=increase,crop=360:270",
       "-q:v", "3", a.out)
    print(a.out)


def cmd_wav(a):
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    ff("-i", a.src, "-vn", "-ac", 2 if a.stereo else 1, "-ar", 48000, "-c:a", "pcm_s16le", a.out)
    print(f"{a.out}  48 kHz {'stereo' if a.stereo else 'mono'}, {probe(a.out)['duration']}s")


LOUD = "I=-16:TP=-1.5:LRA=11"


def cmd_final(a):
    frames = sorted(Path(a.frames).glob("f_*.jpg"))
    if not frames:
        raise SystemExit(f"no f_*.jpg frames in {a.frames}")
    dur = len(frames) / 30
    r = run([tool("ffmpeg"), "-hide_banner", "-i", a.mix, "-af", f"loudnorm={LOUD}:print_format=json", "-f", "null", "-"])
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    norm = (f"loudnorm={LOUD}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
            f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    ff("-framerate", 30, "-i", Path(a.frames) / "f_%05d.jpg", "-i", a.mix, "-af", norm, "-t", f"{dur:.3f}",
       "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", 30,
       "-c:a", "aac", "-b:a", "192k", "-ar", 48000, "-movflags", "+faststart", a.out)
    print(f"{a.out}  {len(frames)} frames = {dur:.2f}s (mix measured {m['input_i']} LUFS, {m['input_tp']} dBTP)")


def cmd_qa(a):
    import numpy as np
    video = Path(a.video).resolve()
    info = json.loads(run([tool("ffprobe"), "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(video)]).stdout)
    kinds = [s["codec_type"] for s in info["streams"]]
    dur = float(info["format"]["duration"])
    fails, notes = [], []
    if kinds.count("video") != 1 or kinds.count("audio") != 1:
        fails.append(f"streams: {kinds} (want one video, one audio)")
    if a.expect is not None and abs(dur - a.expect) > 0.2:
        fails.append(f"duration {dur:.2f}s, timeline says {a.expect:.2f}s")
    r = run([tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(video), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"])
    summary = r.stderr[r.stderr.rfind("Summary:"):]
    i_lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    tp = float(re.search(r"True peak:\s+Peak:\s+(-?[\d.inf]+) dBFS", summary, re.S).group(1))
    if abs(i_lufs + 16) > 1:
        fails.append(f"integrated loudness {i_lufs} LUFS (want -16 ± 1)")
    if tp > -1:
        fails.append(f"true peak {tp} dBTP (want below -1)")
    pcm = subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(pcm, "<i2").astype(np.float64) / 32768
    secs = len(x) // 8000
    rms = [20 * np.log10(np.sqrt((x[i * 8000:(i + 1) * 8000] ** 2).mean()) + 1e-9) for i in range(secs)]
    silent = [i for i, v in enumerate(rms) if v < -50]
    inner = [i for i in silent if 0 < i < secs - 2]  # the CRT start and the fade to black may be quiet
    if inner:
        fails.append(f"silent seconds: {inner}")
    elif silent:
        notes.append(f"quiet first/last seconds: {silent}")
    qa = next((d / "qa" for d in (video.parent, video.parent.parent) if (d / "qa").is_dir()), None)
    out = qa / "final" if qa else video.parent / f"{video.stem}_qa"
    out.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    shots = []
    for k in range(6):
        t = dur * (k + 0.5) / 6
        f = out / f"q_{k}.jpg"
        ff("-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", "scale=640:-2", f)
        shots.append(f)
    ims = [Image.open(f).convert("RGB") for f in shots]
    w, h = ims[0].size
    sheet = Image.new("RGB", (3 * w, 2 * h))
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % 3) * w, (k // 3) * h))
    sheet.save(out / "sheet.jpg", quality=85)
    print(f"{video.name}: {dur:.2f}s, streams {kinds}, {i_lufs} LUFS, true peak {tp} dBTP")
    for n in notes:
        print("  note:", n)
    for f in fails:
        print("  FAIL:", f)
    print("frames ->", out / "sheet.jpg")
    print("QA passed" if not fails else "QA failed")
    sys.exit(1 if fails else 0)


def main():
    ap = argparse.ArgumentParser(usage=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe"); p.add_argument("clip")
    p = sub.add_parser("cuts"); p.add_argument("clip"); p.add_argument("--threshold", type=float, default=0.3); p.add_argument("--out")
    p = sub.add_parser("intra"); p.add_argument("clip"); p.add_argument("out"); p.add_argument("--size")
    p = sub.add_parser("thumb"); p.add_argument("clip"); p.add_argument("out"); p.add_argument("--at", default="1.0")
    p = sub.add_parser("wav"); p.add_argument("src"); p.add_argument("out"); p.add_argument("--stereo", action="store_true")
    p = sub.add_parser("final"); p.add_argument("frames"); p.add_argument("mix"); p.add_argument("out")
    p = sub.add_parser("qa"); p.add_argument("video"); p.add_argument("--expect", type=float)
    a = ap.parse_args()
    if a.cmd == "probe":
        print(json.dumps(probe(a.clip), indent=1))
    else:
        globals()["cmd_" + a.cmd](a)


if __name__ == "__main__":
    main()
