import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { V } from "./cinematic/brand";
import { E, mix, seg } from "./cinematic/motion";

export type TeamItem = { label: string; icon: string };

/** Official team icons on a product-page grid. One card takes focus per beat. */
export const TeamGrid: React.FC<{ items: TeamItem[]; beat: number; title: string; subtitle: string }> = ({
  items,
  beat,
  title,
  subtitle,
}) => {
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const intro = beat * 1.5;
  const active = f < intro ? -1 : Math.min(items.length - 1, Math.floor((f - intro) / beat));
  const fade = seg(f, 0, 8, E.linear) * (1 - seg(f, durationInFrames - 6, 6, E.linear));
  return (
    <AbsoluteFill style={{ background: V.paper, opacity: fade }}>
      <div style={{ position: "absolute", left: 100, top: 72 }}>
        <div style={{ fontFamily: V.body, fontSize: 20, letterSpacing: "0.18em", color: V.accent, opacity: seg(f, 2, 10) }}>DEDICATED TEAMS</div>
        <div
          style={{
            fontFamily: V.display,
            fontWeight: 500,
            fontSize: 56,
            color: V.ink,
            marginTop: 12,
            letterSpacing: "-0.02em",
            opacity: seg(f, 4, 12),
            transform: `translateY(${(1 - seg(f, 4, 16)) * 20}px)`,
          }}
        >
          {title}
        </div>
        <div style={{ fontFamily: V.body, fontSize: 26, color: "rgba(0,0,0,0.5)", marginTop: 8, opacity: seg(f, 8, 12) }}>{subtitle}</div>
      </div>
      <div style={{ position: "absolute", left: 100, right: 100, top: 280, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 22 }}>
        {items.map((it, i) => {
          const on = i === active;
          const land = seg(f, 10 + i * 3, 14, E.out);
          const hit = on ? seg((f - intro) % beat, 0, 8, E.out) : 1;
          return (
            <div
              key={it.label}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 22,
                padding: "28px 28px",
                borderRadius: 24,
                background: on ? "#fff" : "rgba(255,255,255,0.55)",
                border: on ? `2px solid ${V.accent}` : "1px solid rgba(0,0,0,0.06)",
                boxShadow: on ? "0 18px 40px rgba(243,100,64,0.16)" : "0 8px 20px rgba(0,0,0,0.04)",
                opacity: land * (on ? 1 : 0.72),
                transform: `translateY(${(1 - land) * 24}px) scale(${mix(1, 1.03, on ? hit : 0)})`,
              }}
            >
              <Img src={staticFile(it.icon)} style={{ width: 72, height: 72, objectFit: "contain", flexShrink: 0 }} />
              <div style={{ fontFamily: V.display, fontWeight: 500, fontSize: 28, color: V.ink, letterSpacing: "-0.02em", lineHeight: 1.2 }}>{it.label}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
