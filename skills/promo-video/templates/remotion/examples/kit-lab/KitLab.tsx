import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { useBrandFonts } from "./Promo";
import type { Storyboard } from "./types";
import { BrandProvider, brandFromStoryboard } from "./cinematic/brand";
import { PaperCut3D, paperCutCues } from "./cinematic/PaperCut3D";
import { SoundCues } from "./cinematic/sfx";
import { ReportBuild, reportCues, reportFrames, type ReportProps } from "./cinematic/ReportBuild";

const REPORT: ReportProps = {
  kicker: "Quarterly business review",
  title: "Northline Home: Q2 performance",
  meta: "Prepared by YouWare · 12 sources · July 2026",
  sections: [
    {
      heading: "Revenue grew 18% on repeat buyers",
      paragraphs: [
        "Q2 revenue reached $4.2M, up 18% quarter over quarter. Repeat customers drove 62% of the gain, led by the spring home refresh campaign and faster two-day delivery in the Northeast.",
      ],
      chart: { title: "Revenue by month ($K)", labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"], values: [610, 640, 655, 690, 760, 842] },
    },
    {
      heading: "Where margin moved",
      table: {
        head: ["Category", "Revenue", "Margin", "QoQ"],
        rows: [
          ["Furniture", "$1.9M", "34%", "+21%"],
          ["Lighting", "$1.1M", "41%", "+16%"],
          ["Textiles", "$0.8M", "38%", "+12%"],
        ],
      },
      insight: "Lighting carries the best margin: expand it before the Q3 promotion.",
    },
  ],
};

const PAPER = 140;
export const KITLAB_FRAMES = PAPER + reportFrames(REPORT);

export const KitLab: React.FC<Storyboard> = (sb) => {
  useBrandFonts(sb);
  return (
    <BrandProvider brand={brandFromStoryboard(sb, { ink: "#141414" })}>
      <AbsoluteFill>
        <Sequence durationInFrames={140}>
          <PaperCut3D title="Built layer by layer." subtitle="Every draft, checked and refined." />
        </Sequence>
        <Sequence from={PAPER}>
          <ReportBuild {...REPORT} />
        </Sequence>
        <SoundCues cues={[...paperCutCues(0), ...reportCues(REPORT, PAPER)]} />
      </AbsoluteFill>
    </BrandProvider>
  );
};
