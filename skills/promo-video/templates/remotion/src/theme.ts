import { createContext, useContext } from "react";
import { useVideoConfig } from "remotion";
import type { CameraMove, StyleId, Storyboard, Tone, TransitionId } from "./types";

export type Theme = {
  id: StyleId;
  light: boolean;
  bg: string;
  bg2: string;
  fg: string;
  muted: string;
  accent: string;
  accent2: string;
  /** Color for highlighted words, eyebrows, icons; must contrast with bg. */
  highlight: string;
  button: string;
  onButton: string;
  surface: string;
  border: string;
  displayFont: string;
  bodyFont: string;
  displayWeight: number;
  tracking: string;
  transition: TransitionId;
  transitionSeconds: number;
  camera: CameraMove;
  cameraIntensity: number;
  textAnim: "rise" | "pop" | "blur";
  stagger: number;
  radius: number;
};

const SANS =
  '"SF Pro Display", "Inter", "PingFang SC", "Hiragino Sans", "Helvetica Neue", Arial, sans-serif';
const SERIF =
  '"Songti SC", "Noto Serif SC", "Hiragino Mincho ProN", Georgia, "Times New Roman", serif';

type Preset = Omit<Theme, "button" | "onButton">;

const PRESETS: Record<StyleId, Preset> = {
  keynote: {
    id: "keynote",
    light: false,
    bg: "#050507",
    bg2: "#101014",
    fg: "#F5F5F7",
    muted: "#8E8E93",
    accent: "#2997FF",
    accent2: "#BF5AF2",
    highlight: "#2997FF",
    surface: "rgba(255,255,255,0.05)",
    border: "rgba(255,255,255,0.10)",
    displayFont: SANS,
    bodyFont: SANS,
    displayWeight: 700,
    tracking: "-0.035em",
    transition: "fade",
    transitionSeconds: 0.5,
    camera: "push-in",
    cameraIntensity: 0.7,
    textAnim: "blur",
    stagger: 1.2,
    radius: 28,
  },
  kinetic: {
    id: "kinetic",
    light: false,
    bg: "#0A0A0A",
    bg2: "#161616",
    fg: "#FFFFFF",
    muted: "#9A9A9A",
    accent: "#D7FF3A",
    accent2: "#FF4D2E",
    highlight: "#D7FF3A",
    surface: "rgba(255,255,255,0.06)",
    border: "rgba(255,255,255,0.14)",
    displayFont: SANS,
    bodyFont: SANS,
    displayWeight: 900,
    tracking: "-0.045em",
    transition: "slide",
    transitionSeconds: 0.3,
    camera: "drift",
    cameraIntensity: 1.2,
    textAnim: "pop",
    stagger: 1.6,
    radius: 10,
  },
  aurora: {
    id: "aurora",
    light: false,
    bg: "#060A1F",
    bg2: "#0E1433",
    fg: "#EEF2FF",
    muted: "#9AA3C7",
    accent: "#7C5CFF",
    accent2: "#22D3EE",
    highlight: "#22D3EE",
    surface: "rgba(255,255,255,0.07)",
    border: "rgba(255,255,255,0.16)",
    displayFont: SANS,
    bodyFont: SANS,
    displayWeight: 700,
    tracking: "-0.03em",
    transition: "fade",
    transitionSeconds: 0.6,
    camera: "drift",
    cameraIntensity: 0.8,
    textAnim: "rise",
    stagger: 1.2,
    radius: 24,
  },
  editorial: {
    id: "editorial",
    light: true,
    bg: "#F6F3EE",
    bg2: "#ECE6DC",
    fg: "#1C1B19",
    muted: "#6B665E",
    accent: "#0F766E",
    accent2: "#C2410C",
    highlight: "#0F766E",
    surface: "rgba(255,255,255,0.7)",
    border: "rgba(28,27,25,0.12)",
    displayFont: SERIF,
    bodyFont: SANS,
    displayWeight: 600,
    tracking: "-0.02em",
    transition: "fade",
    transitionSeconds: 0.6,
    camera: "push-in",
    cameraIntensity: 0.5,
    textAnim: "rise",
    stagger: 1,
    radius: 18,
  },
};

const shade = (color: string, amount: number) => {
  const m = /^#([0-9a-f]{6})$/i.exec(color);
  if (!m) return color;
  const n = parseInt(m[1], 16);
  const ch = (v: number) => Math.max(0, Math.min(255, Math.round(v + 255 * amount)));
  const [r, g, b] = [ch((n >> 16) & 255), ch((n >> 8) & 255), ch(n & 255)];
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
};

const onColor = (color: string) => {
  const m = /^#([0-9a-f]{6})$/i.exec(color);
  if (!m) return "#FFFFFF";
  const n = parseInt(m[1], 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#111111" : "#FFFFFF";
};

export const getTheme = (sb: Storyboard): Theme => {
  const base = PRESETS[sb.style] ?? PRESETS.keynote;
  const c = sb.brand.colors ?? {};
  const f = sb.brand.fonts ?? {};
  const fam = (x?: { family: string }) => (x ? `"${x.family}", ` : "");
  const accent = c.primary ?? base.accent;
  const accent2 = c.accent ?? base.accent2;
  const button = c.button ?? accent;
  return {
    ...base,
    accent,
    accent2,
    highlight: base.id === "aurora" ? c.accent ?? base.highlight : c.primary ?? base.highlight,
    button,
    onButton: onColor(button),
    bg: c.background ?? base.bg,
    bg2: c.background ? shade(c.background, base.light ? -0.05 : 0.04) : base.bg2,
    fg: c.text ?? base.fg,
    muted: c.muted ?? base.muted,
    displayFont: fam(f.display ?? f.body) + base.displayFont,
    bodyFont: fam(f.body ?? f.display) + base.bodyFont,
    displayWeight: sb.brand.displayWeight ?? base.displayWeight,
  };
};

/** Flip a theme to the requested tone for a single scene. */
export const withTone = (theme: Theme, tone: Tone | undefined, sb: Storyboard): Theme => {
  if (!tone || (tone === "light") === theme.light) return theme;
  const c = sb.brand.colors ?? {};
  if (tone === "dark") {
    const bg = c.dark ?? "#1E1E1E";
    return {
      ...theme,
      light: false,
      bg,
      bg2: shade(bg, 0.04),
      fg: "#F5F5F5",
      muted: "rgba(255,255,255,0.6)",
      surface: "rgba(255,255,255,0.06)",
      border: "rgba(255,255,255,0.12)",
      button: c.button && onColor(c.button) === "#FFFFFF" ? "#F5F5F5" : theme.button,
      onButton: c.button && onColor(c.button) === "#FFFFFF" ? "#111111" : theme.onButton,
    };
  }
  const bg = c.light ?? "#F3F3F3";
  return {
    ...theme,
    light: true,
    bg,
    bg2: shade(bg, -0.05),
    fg: "#111111",
    muted: "rgba(0,0,0,0.6)",
    surface: "rgba(255,255,255,0.75)",
    border: "rgba(0,0,0,0.10)",
  };
};

export const ThemeContext = createContext<{ theme: Theme; sb: Storyboard } | null>(
  null,
);

export const useTheme = () => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("ThemeContext missing");
  return ctx;
};

/** Layout unit: 1u = 1px on the short side of a 1080p frame. */
export const useUnit = () => {
  const { width, height } = useVideoConfig();
  const u = Math.min(width, height) / 1080;
  return { u, portrait: height > width, square: width === height, width, height };
};
