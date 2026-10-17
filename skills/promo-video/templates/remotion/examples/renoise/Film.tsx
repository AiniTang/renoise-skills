import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useVideoConfig } from "remotion";
import { AudioLines, Brush, Clapperboard, DropletOff, Eraser, Expand, FolderOpen, Image, ImageUpscale, LayoutTemplate, Megaphone, MonitorUp, Sparkles, SquareTerminal, SwitchCamera } from "lucide-react";
import { useBrandFonts } from "./Promo";
import type { Storyboard } from "./types";
import { BrandProvider, brandFromStoryboard } from "./cinematic/brand";
import { EndCard, Opener } from "./cinematic/Logo3D";
import { PromptToVideo, promptCues, promptFrames, type PromptToVideoProps } from "./cinematic/PromptToVideo";
import { SoundCues, type Cue } from "./cinematic/sfx";
import { TemplateWall, templateWallCues, TEMPLATE_WALL_FRAMES, type TemplateCard } from "./cinematic/TemplateWall";
import { ToolBeats, toolBeatsCues, toolBeatsFrames, type ToolBeat } from "./cinematic/ToolBeats";
import { VideoMontage, montageCues, montageFrames, type MontageClip, type MontageWord } from "./cinematic/VideoMontage";

const BEAT = (30 * 60) / 120;
const snap = (frames: number) => Math.ceil(frames / BEAT) * BEAT;

const CLIPS: MontageClip[] = [
  { src: "video/hero-wan.mp4", from: 1.5, label: "Wan 3.0" },
  { src: "video/hero-seedance.mp4", from: 2, label: "Seedance 2.5 · 1080P" },
  { src: "video/jungle.mp4", from: 3.5, label: "Film & Story" },
  { src: "video/hero-gpt-image.mp4", from: 2.5, label: "GPT Image 2.5" },
  { src: "video/city.mp4", from: 6.5, label: "UGC & Social" },
  { src: "video/earbuds.mp4", from: 4.5, label: "Marketing & Ads" },
];
const WORDS: MontageWord[] = [
  { beat: 0, text: "Every" },
  { beat: 1, text: "top model." },
  { beat: 4, text: "Every", clear: true },
  { beat: 5, text: "style." },
  { beat: 8, text: "One", clear: true },
  { beat: 9, text: "studio.", accent: true },
];

const DEMO: PromptToVideoProps = {
  prompt: "A sea turtle glides over a sunlit coral reef, cinematic 4K",
  placeholder: "Describe your idea",
  models: [{ name: "Seedance 2.5 · 1080P", tag: "Hot" }, { name: "Kling 3.0 Omni" }, { name: "Wan 3.0" }, { name: "MiniMax H3" }, { name: "Grok Video" }],
  pick: 0,
  startModel: "Gemini Omni Flash",
  heroVideo: { src: "video/hero-wan.mp4", from: 0.5 },
  result: { src: "video/hero-seedance.mp4", from: 0.5, label: "Seedance 2.5 · 1080P" },
  nav: [
    { label: "Agent", icon: Sparkles },
    { label: "Video", icon: Clapperboard },
    { label: "Image", icon: Image },
    { label: "Audio", icon: AudioLines },
    { label: "Marketing", icon: Megaphone },
    { label: "Templates", icon: LayoutTemplate },
    { label: "Assets", icon: FolderOpen },
    { label: "CLI", icon: SquareTerminal },
  ],
  tools: [
    { label: "Video upscale", icon: MonitorUp },
    { label: "Video reshoot", icon: SwitchCamera },
    { label: "Image upscale", icon: ImageUpscale },
    { label: "Redraw", icon: Brush },
    { label: "Remove object", icon: Eraser },
    { label: "Expand image", icon: Expand },
    { label: "Remove watermark", icon: DropletOff },
  ],
  scenarios: [
    { title: "Marketing & Ads", img: "images/earbuds.jpg" },
    { title: "UGC & Social", img: "images/city.jpg" },
    { title: "Film & Story", img: "images/jungle.jpg" },
    { title: "Anime & Illustration", img: "images/monster.jpg" },
  ],
  mark: "brand/logo-mark.svg",
};

const TEMPLATES: TemplateCard[] = [
  { src: "video/t-petpro.mp4", from: 9, title: "Pet Pro Max" },
  { src: "video/t-octagon.mp4", from: 2, title: "Octagon Champion" },
  { src: "video/t-giant.mp4", from: 1, title: "Giant in the City" },
  { src: "video/t-rose.mp4", from: 3, title: "The Last Rose" },
  { src: "video/t-magicpet.mp4", from: 4, title: "Magical Pet" },
];

const TOOLS: ToolBeat[] = [
  { src: "video/hero-seedance.mp4", from: 6, word: "Enhance to 4K.", effect: "upscale", badge: "4K" },
  { src: "video/city.mp4", from: 2, word: "Expand any frame.", effect: "expand" },
  { src: "video/jungle.mp4", from: 1, word: "Keep characters consistent.", effect: "consistent" },
  { src: "video/hero-canvas.mp4", from: 8, word: "Reshoot any shot.", effect: "reshoot" },
];

const T = (() => {
  const montage = 90;
  const demo = montage + montageFrames(CLIPS.length, BEAT);
  const templates = demo + snap(promptFrames(DEMO));
  const tools = templates + TEMPLATE_WALL_FRAMES;
  const end = tools + toolBeatsFrames(TOOLS.length, BEAT);
  return { montage, demo, templates, tools, end, total: end + 105 };
})();
export const FILM_FRAMES = T.total;

const cues = (): Cue[] => [
  { at: 2, name: "whoosh", volume: 0.5 },
  { at: 30, name: "impact", volume: 0.35 },
  { at: 62, name: "whoosh", volume: 0.7 },
  ...montageCues(CLIPS.length, BEAT, T.montage),
  ...promptCues(DEMO, T.demo),
  ...templateWallCues(T.templates),
  ...toolBeatsCues(TOOLS, BEAT, T.tools),
  { at: T.end - 36, name: "riser", volume: 0.45 },
  { at: T.end, name: "impact", volume: 0.6 },
];

export const Film: React.FC<Storyboard> = (sb) => {
  const { fps, durationInFrames } = useVideoConfig();
  useBrandFonts(sb);
  return (
    <BrandProvider brand={brandFromStoryboard(sb, { ink: "#141414" })}>
      <AbsoluteFill>
        <Sequence from={T.montage - 2} durationInFrames={T.demo - T.montage + 2}>
          <VideoMontage clips={CLIPS} beat={BEAT} words={WORDS} />
        </Sequence>
        <Sequence durationInFrames={98}>
          <Opener headline={["Your idea,", "on screen."]} />
        </Sequence>
        <Sequence from={T.demo} durationInFrames={T.templates - T.demo}>
          <PromptToVideo {...DEMO} />
        </Sequence>
        <Sequence from={T.templates} durationInFrames={T.tools - T.templates}>
          <TemplateWall templates={TEMPLATES} center={2} title="Trending templates." subtitle="Upload one image. Make it yours." cta="Make your own" upload={{ img: "images/t-rose.jpg", name: "my-cat.jpg", hint: "Upload one character image" }} />
        </Sequence>
        <Sequence from={T.tools} durationInFrames={T.end - T.tools}>
          <ToolBeats items={TOOLS} beat={BEAT} />
        </Sequence>
        <Sequence from={T.end}>
          <EndCard cta="Start creating →" url="renoise.ai" ctaAccent />
        </Sequence>
      </AbsoluteFill>
      <Audio
        src={staticFile("music/bgm.wav")}
        volume={(f) =>
          0.55 *
          interpolate(f, [0, fps * 0.3, durationInFrames - fps * 1.5, durationInFrames - 1], [0, 1, 1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })
        }
      />
      <SoundCues cues={cues()} />
    </BrandProvider>
  );
};

export const TIMELINE = T;
