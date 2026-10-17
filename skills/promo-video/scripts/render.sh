#!/usr/bin/env bash
# Render a promo project. Remotion draws the picture and the mix; rn (renoise-kit) finishes, checks and audits.
# Usage: render.sh <project-dir> <mode> [frames...]
# Template mode (Promo composition, storyboard-driven):
#   stills  -> out/stills/scene-N.png (one mid-frame per scene, for style/storyboard review)
#   preview -> out/preview.mp4 (half resolution, fast)
#   final   -> out/final.mp4 + out/cover.png (+ out/captions.srt when scenes have captions)
# Cinematic mode (Film composition in src/Film.tsx):
#   film-stills F1 F2 ... -> out/stills/fN.png
#   film-preview          -> out/film-preview.mp4 (half resolution)
#   film                  -> out/film.mp4 (+ out/film-1080p.mp4 for 4K renders)
#
# Every MP4 that leaves this script went through `rn finish`. The raw Remotion MP4 has fixed_frame_rate_flag=0 (some players
# and upload pipelines show it at half its length), full-range BT.601 colour and an uncompensated AAC delay (the sound plays
# 43.7 ms late). Finals take their sound from a separate WAV render of the mix, so nothing needs compensating; previews skip
# that render and move the sound 43.7 ms earlier instead. Loudness: -14 LUFS, encoded true peak <= -1 dBTP (LUFS=-16 to change).
# Audits (rn qa + rn cuts) never fail a render; findings judged intended go in qa-accept.txt (CHECK or CHECK@SECONDS per line).
set -euo pipefail

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "${1:?usage: render.sh <project-dir> <mode> [frames...]}" && pwd)"
MODE="${2:?mode: stills|preview|final|film-stills|film-preview|film}"
shift 2

cd "$PROJECT"
# shellcheck disable=SC1091
[ -f .promo-env ] && source .promo-env
export PATH="${NODE_BIN:-}:$PATH"
LUFS="${LUFS:--14}"
REMOTION_AAC_LEAD="-0.0437"  # seconds; measured on Remotion 4.0.408 at 48 kHz

if ! command -v rn >/dev/null 2>&1; then
  echo "rn not found: install renoise-kit (SKILL.md 依赖): uv tool install 'renoise-kit[all]'" >&2
  exit 1
fi

case "$MODE" in film*) ;; *) python3 "$SCRIPTS/check_storyboard.py" storyboard.json ;; esac
mkdir -p out/audit

# Continuity and delivery audit (references/detail-pass.md): rn qa covers format, loudness, true peak, dead air, level jumps,
# clicks, black and frozen frames; rn cuts lists the hard cuts with both sides of each on a sheet.
audit() {
  local accept=()
  if [ -f qa-accept.txt ]; then
    while IFS= read -r line; do
      line="${line%%#*}"; line="${line//[[:space:]]/}"
      [ -n "$line" ] && accept+=(--accept "$line")
    done < qa-accept.txt
  fi
  rn qa "$1" --json out/audit/qa.json ${accept[@]+"${accept[@]}"} || true
  rn cuts "$1" --sheet out/audit/cuts.jpg --json out/audit/cuts.json || true
}

# finish <raw.mp4> <out.mp4> [rn finish options]: the delivery encode; a 4K result also gets a 1080p copy.
finish() {
  local raw="$1" target="$2"
  shift 2
  rn finish "$raw" -o "$target" --lufs "$LUFS" "$@"
  local height
  height="$(rn probe "$target" | python3 -c 'import json,sys; print(json.load(sys.stdin)["video"]["height"])')"
  if [ "$height" -ge 2160 ]; then
    rn finish "$target" -o "${target%.mp4}-1080p.mp4" --height 1080 --lufs keep
  fi
}

case "$MODE" in
  stills)
    mkdir -p out/stills
    i=1
    for f in $(python3 "$SCRIPTS/check_storyboard.py" storyboard.json --frames); do
      npx remotion still Promo "out/stills/scene-$i.png" --frame="$f" --log=error
      echo "out/stills/scene-$i.png (frame $f)"
      i=$((i + 1))
    done
    rn sheet out/stills -o out/stills-sheet.jpg
    ;;
  preview)
    npx remotion render Promo out/preview-raw.mp4 --scale=0.5 --log=error
    finish out/preview-raw.mp4 out/preview.mp4 --preset veryfast --audio-offset "$REMOTION_AAC_LEAD"
    audit out/preview.mp4
    echo "out/preview.mp4"
    ;;
  final)
    npx remotion render Promo out/final-raw.mp4 --muted --log=error
    npx remotion render Promo out/mix.wav --codec=wav --config=remotion.audio.config.ts --log=error
    finish out/final-raw.mp4 out/final.mp4 --audio out/mix.wav
    frames=($(python3 "$SCRIPTS/check_storyboard.py" storyboard.json --frames))
    npx remotion still Promo out/cover.png --frame="${frames[1]:-${frames[0]}}" --log=error
    python3 "$SCRIPTS/check_storyboard.py" storyboard.json --srt out/captions.srt >/dev/null
    [ -s out/captions.srt ] || rm -f out/captions.srt
    audit out/final.mp4
    echo "out/final.mp4"
    ;;
  film-stills)
    [ $# -gt 0 ] || { echo "film-stills needs frame numbers" >&2; exit 1; }
    mkdir -p out/stills
    if [ -f stills.mjs ]; then
      # one bundle + one browser for all frames (much faster than a `remotion still` per frame)
      node stills.mjs Film out/stills "$@"
    else
      for f in "$@"; do
        npx remotion still src/index.ts Film "out/stills/f$f.png" --frame="$f" --log=error
        echo "out/stills/f$f.png"
      done
    fi
    rn sheet out/stills -o out/stills-sheet.jpg
    ;;
  film-preview)
    npx remotion render src/index.ts Film out/film-preview-raw.mp4 --scale=0.5 --log=error
    finish out/film-preview-raw.mp4 out/film-preview.mp4 --preset veryfast --audio-offset "$REMOTION_AAC_LEAD"
    audit out/film-preview.mp4
    echo "out/film-preview.mp4"
    ;;
  film)
    npx remotion render src/index.ts Film out/film-raw.mp4 --muted --log=error
    npx remotion render src/index.ts Film out/mix.wav --codec=wav --config=remotion.audio.config.ts --log=error
    finish out/film-raw.mp4 out/film.mp4 --audio out/mix.wav
    audit out/film.mp4
    echo "out/film.mp4"
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 1
    ;;
esac
