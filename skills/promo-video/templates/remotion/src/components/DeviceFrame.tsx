import React from "react";
import { useTheme } from "../theme";

export const DeviceFrame: React.FC<{
  kind: "browser" | "phone" | "none";
  width: number;
  u: number;
  url?: string;
  children: React.ReactNode;
}> = ({ kind, width, u, url, children }) => {
  const { theme } = useTheme();
  const light = theme.light;
  const chrome = light ? "#FFFFFF" : "#1C1C22";
  const shadow = `0 ${40 * u}px ${120 * u}px rgba(0,0,0,${light ? 0.18 : 0.5})`;

  if (kind === "phone") {
    return (
      <div
        style={{
          width,
          aspectRatio: "9 / 19.5",
          borderRadius: width * 0.14,
          padding: width * 0.035,
          background: "#0B0B0D",
          boxShadow: `${shadow}, inset 0 0 0 ${2 * u}px #2A2A30`,
          position: "relative",
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            borderRadius: width * 0.11,
            overflow: "hidden",
            position: "relative",
            background: theme.bg2,
          }}
        >
          {children}
          <div
            style={{
              position: "absolute",
              top: width * 0.03,
              left: "50%",
              transform: "translateX(-50%)",
              width: width * 0.3,
              height: width * 0.085,
              borderRadius: width,
              background: "#000",
            }}
          />
        </div>
      </div>
    );
  }

  if (kind === "none") {
    return (
      <div
        style={{
          width,
          borderRadius: theme.radius * u,
          overflow: "hidden",
          boxShadow: shadow,
        }}
      >
        {children}
      </div>
    );
  }

  const bar = 44 * u;
  return (
    <div
      style={{
        width,
        borderRadius: 16 * u,
        overflow: "hidden",
        background: chrome,
        boxShadow: `${shadow}, 0 0 0 ${1 * u}px ${theme.border}`,
      }}
    >
      <div
        style={{
          height: bar,
          display: "flex",
          alignItems: "center",
          gap: 8 * u,
          padding: `0 ${16 * u}px`,
          borderBottom: `${1 * u}px solid ${theme.border}`,
        }}
      >
        {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
          <div key={c} style={{ width: 12 * u, height: 12 * u, borderRadius: "50%", background: c }} />
        ))}
        <div
          style={{
            flex: 1,
            margin: `0 ${60 * u}px`,
            height: 26 * u,
            borderRadius: 8 * u,
            background: light ? "#F1F1F3" : "#2A2A31",
            color: theme.muted,
            fontFamily: theme.bodyFont,
            fontSize: 14 * u,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {url ?? ""}
        </div>
      </div>
      <div style={{ aspectRatio: "16 / 10", position: "relative", background: theme.bg2 }}>
        {children}
      </div>
    </div>
  );
};
