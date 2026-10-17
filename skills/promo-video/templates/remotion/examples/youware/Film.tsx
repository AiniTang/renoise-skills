import React from "react";
import { Audio, interpolate, Sequence, staticFile, useVideoConfig } from "remotion";
import { useBrandFonts } from "./Promo";
import type { Storyboard } from "./types";
import { BrandProvider, brandFromStoryboard } from "./cinematic/brand";
import { Carousel3D } from "./cinematic/Carousel3D";
import { DeviceSwing } from "./cinematic/DeviceSwing";
import { Gallery3D, galleryFrames } from "./cinematic/Gallery3D";
import { EndCard, Opener } from "./cinematic/Logo3D";
import { FORMULA_TYPING, type ProofBeat, ProofBeats } from "./cinematic/ProofBeats";
import { type Cue, keyCues, SoundCues } from "./cinematic/sfx";
import { typingSchedule } from "./cinematic/motion";
import { AGENTS, agentDone, CHIP_AT, CLICK_AT, PROMPT, PROMPT_T, ProductUI, TOAST_AT, UI_FRAMES } from "./ProductUI";
import { TeamGrid } from "./TeamGrid";

const BPM = 122.3;
const B = (30 * 60) / BPM;
const FORMULA = "=C21/'DCF'!C26";
const PROOF_EACH = 42;

const PANELS = [
  { img: "images/capability-slide-decks.png", label: "Slide decks" },
  { img: "images/capability-research-reports.png", label: "Research reports" },
  { img: "images/capability-spreadsheets.png", label: "Spreadsheets" },
  { img: "images/capability-websites.png", label: "Websites" },
];
const SPECIALISTS = [
  { img: "images/head-3.png", name: "Project Manager", status: "Breaks the task down" },
  { img: "images/head-7.png", name: "Researcher", status: "Verifies every source" },
  { img: "images/head-2.png", name: "Data Analyst", status: "Shows the calculations" },
  { img: "images/head-4.png", name: "Writer & Designer", status: "Drafts and lays it out" },
  { img: "images/head-1.png", name: "Reviewer", status: "Flags what needs you" },
];
const TEAMS = [
  { label: "Financial Analysis", icon: "images/agent-financial-analysis.png" },
  { label: "Market Research", icon: "images/agent-market-research.png" },
  { label: "Competitive Analysis", icon: "images/agent-competitive-analysis.png" },
  { label: "Data Analytics", icon: "images/agent-data-analytics.png" },
  { label: "Business Review", icon: "images/agent-business-review.svg" },
  { label: "Product Strategy", icon: "images/agent-product-strategy.png" },
];
const PROOFS: ProofBeat[] = [
  {
    text: "Sources verified.",
    visual: {
      kind: "checklist",
      items: ["Market sizing · Industry report 2026", "Revenue table · Q2 filing", "Survey panel · 1,200 respondents"],
    },
  },
  {
    text: "Calculations shown.",
    visual: { kind: "formula", cell: "C22", formula: FORMULA, label: "Implied value / share", value: 230371 },
  },
  {
    text: "Your files stay yours.",
    visual: { kind: "lock", file: "Customer interviews.docx", note: "Used for this task only · never used for training" },
  },
];

const T = (() => {
  const opener = 0;
  const openerLen = 96;
  const ui = 88;
  const specialists = ui + UI_FRAMES - 2;
  const specLen = 12 + SPECIALISTS.length * 22 + 16;
  const teams = specialists + specLen - 6;
  const teamsLen = Math.round(B * 1.5 + B * TEAMS.length + B);
  const trust = teams + teamsLen - 6;
  const trustLen = PROOFS.length * PROOF_EACH + 8;
  const gallery = trust + trustLen - 6;
  const galleryLen = galleryFrames(PANELS.length);
  const device = gallery + galleryLen - 6;
  const deviceLen = 110;
  const end = device + deviceLen - 6;
  return { opener, openerLen, ui, specialists, specLen, teams, teamsLen, trust, trustLen, gallery, galleryLen, device, deviceLen, end, total: end + 80 };
})();

export const FILM_FRAMES = T.total;

const cues = (): Cue[] => {
  const formulaT = typingSchedule(FORMULA, FORMULA_TYPING.start, FORMULA_TYPING.frames / FORMULA.length, () => 0.5);
  return [
    { at: 2, name: "whoosh", volume: 0.5 },
    { at: 30, name: "impact", volume: 0.35 },
    { at: 62, name: "whoosh", volume: 0.55 },
    ...keyCues(PROMPT, PROMPT_T.times, T.ui),
    ...CHIP_AT.map((at) => ({ at: T.ui + at, name: "pop", volume: 0.45 })),
    { at: T.ui + CLICK_AT, name: "click", volume: 0.9 },
    { at: T.ui + 92, name: "whoosh", volume: 0.5 },
    ...AGENTS.map((_, i) => ({ at: T.ui + agentDone(i), name: "done", volume: 0.25 })),
    { at: T.ui + TOAST_AT, name: "pop", volume: 0.6 },
    { at: T.ui + 244, name: "whoosh", volume: 0.7 },
    { at: T.specialists + 2, name: "impact", volume: 0.28 },
    ...SPECIALISTS.slice(1).map((_, k) => ({ at: T.specialists + 12 + k * 22 + 12, name: "swish-1", volume: 0.22 })),
    { at: T.teams, name: "whoosh", volume: 0.4 },
    ...TEAMS.map((_, k) => ({ at: T.teams + B * 1.5 + B * k, name: "tap", volume: 0.35 })),
    ...PROOFS.map((_, k) => ({ at: T.trust + k * PROOF_EACH, name: "whoosh", volume: 0.28 })),
    ...[0, 1, 2].map((k) => ({ at: T.trust + 20 + k * 5, name: "done", volume: 0.28 })),
    ...keyCues(FORMULA, formulaT.times, T.trust + PROOF_EACH, 0.5),
    { at: T.trust + PROOF_EACH + 26, name: "pop", volume: 0.45 },
    { at: T.trust + PROOF_EACH * 2 + 18, name: "click", volume: 0.85 },
    { at: T.gallery, name: "whoosh", volume: 0.45 },
    ...[0, 1, 2, 3].map((k) => ({ at: T.gallery + 14 + k * 22, name: "whoosh", volume: 0.26 })),
    { at: T.device, name: "whoosh", volume: 0.55 },
    { at: T.end - 36, name: "riser", volume: 0.45 },
    { at: T.end, name: "impact", volume: 0.85 },
  ];
};

export const Film: React.FC<Storyboard> = (sb) => {
  const { fps, durationInFrames } = useVideoConfig();
  useBrandFonts(sb);
  return (
    <BrandProvider brand={brandFromStoryboard(sb, { ink: "#141414" })}>
      <Sequence durationInFrames={T.ui + 10}>
        <Opener headline={["Your AI partner.", "Already on it."]} />
      </Sequence>
      <Sequence from={T.ui} durationInFrames={T.specialists - T.ui + 6}>
        <ProductUI />
      </Sequence>
      <Sequence from={T.specialists} durationInFrames={T.specLen}>
        <Carousel3D items={SPECIALISTS} step={22} title="A specialist for every step." />
      </Sequence>
      <Sequence from={T.teams} durationInFrames={T.teamsLen}>
        <TeamGrid items={TEAMS} beat={B} title="Dedicated teams." subtitle="Focused on your task." />
      </Sequence>
      <Sequence from={T.trust} durationInFrames={T.trustLen}>
        <ProofBeats beats={PROOFS} each={PROOF_EACH} eyebrow="Nothing ships unchecked" />
      </Sequence>
      <Sequence from={T.gallery} durationInFrames={T.galleryLen}>
        <Gallery3D panels={PANELS} title="Finished work, ready to share." aspect={1.577} />
      </Sequence>
      <Sequence from={T.device} durationInFrames={T.deviceLen}>
        <DeviceSwing
          image="images/mobile-edit.png"
          title={"Pick up where\nyou left off."}
          body="Desktop or mobile, your work comes with you."
        />
      </Sequence>
      <Sequence from={T.end}>
        <EndCard cta="Try for free →" url="youware.com" ctaAccent />
      </Sequence>
      <Audio
        src={staticFile("music/bgm.wav")}
        volume={(fr) =>
          0.5 *
          interpolate(fr, [0, fps * 0.35, durationInFrames - fps * 1.6, durationInFrames - 1], [0, 1, 1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })
        }
      />
      <SoundCues cues={cues()} />
    </BrandProvider>
  );
};
