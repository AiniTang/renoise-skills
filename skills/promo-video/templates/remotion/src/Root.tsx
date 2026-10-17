import React from "react";
import { Composition } from "remotion";
import type { CalculateMetadataFunction } from "remotion";
import storyboard from "../storyboard.json";
import { Promo } from "./Promo";
import { getDimensions, getTotalFrames } from "./timing";
import type { Storyboard } from "./types";

const calculateMetadata: CalculateMetadataFunction<Storyboard> = ({ props }) => ({
  ...getDimensions(props),
  fps: props.format.fps,
  durationInFrames: getTotalFrames(props),
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Promo"
    component={Promo}
    defaultProps={storyboard as unknown as Storyboard}
    calculateMetadata={calculateMetadata}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={300}
  />
);
