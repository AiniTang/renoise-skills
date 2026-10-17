import { Config } from "@remotion/cli/config";

// Audio-only exports (wav): the main config sets a CRF, which the wav codec rejects.
Config.setChromiumOpenGlRenderer("angle");
