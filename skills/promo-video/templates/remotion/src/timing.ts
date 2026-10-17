import type { AspectRatio, Resolution, Storyboard } from "./types";
import { getTheme } from "./theme";

const SHORT_SIDE: Record<Resolution, number> = {
  "720p": 720,
  "1080p": 1080,
  "4k": 2160,
};

const RATIO: Record<AspectRatio, [number, number]> = {
  "16:9": [16, 9],
  "9:16": [9, 16],
  "1:1": [1, 1],
  "4:5": [4, 5],
};

export const getDimensions = (sb: Storyboard) => {
  const short = SHORT_SIDE[sb.format.resolution ?? "1080p"];
  const [w, h] = RATIO[sb.format.aspect ?? "16:9"];
  const even = (n: number) => Math.round(n / 2) * 2;
  return w >= h
    ? { width: even((short * w) / h), height: short }
    : { width: short, height: even((short * h) / w) };
};

/**
 * Net scene lengths (the frames each scene advances the timeline by).
 * With a BPM, every cut lands on a beat. Keep in sync with
 * scripts/check_storyboard.py, which uses the same formula.
 */
export const getNetFrames = (sb: Storyboard): number[] => {
  const fps = sb.format.fps;
  const bpm = sb.music?.bpm;
  if (!bpm) {
    return sb.scenes.map((s) => Math.max(1, Math.round(s.seconds * fps)));
  }
  const beat = (fps * 60) / bpm;
  let cumBeats = 0;
  let prev = 0;
  return sb.scenes.map((s) => {
    cumBeats += Math.max(1, Math.round((s.seconds * fps) / beat));
    const boundary = Math.round(cumBeats * beat);
    const net = boundary - prev;
    prev = boundary;
    return net;
  });
};

export const getTransitionFrames = (sb: Storyboard, index: number): number => {
  if (index >= sb.scenes.length - 1) return 0;
  const theme = getTheme(sb);
  const id = sb.scenes[index].transition ?? theme.transition;
  if (id === "none") return 0;
  const fps = sb.format.fps;
  const bpm = sb.music?.bpm;
  const target = theme.transitionSeconds * fps;
  let t = target;
  if (bpm) {
    t = (fps * 60) / bpm / 2;
    while (t < target * 0.6) t *= 2;
  }
  t = Math.round(t);
  const net = getNetFrames(sb);
  return Math.min(t, Math.floor(net[index] / 2), Math.floor(net[index + 1] / 2));
};

export const getTotalFrames = (sb: Storyboard) =>
  getNetFrames(sb).reduce((a, b) => a + b, 0);
