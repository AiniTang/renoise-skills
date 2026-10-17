import React from "react";
import { AbsoluteFill } from "remotion";
import { useFontManifest } from "../cinematic/type";

/** Holds the frame until every face in public/fonts/fonts.json is loaded. */
export const LabFonts: React.FC<{ children: React.ReactNode; bg?: string }> = ({ children, bg = "#111" }) => {
  const faces = useFontManifest();
  if (!faces) return <AbsoluteFill style={{ background: bg }} />;
  return <>{children}</>;
};
