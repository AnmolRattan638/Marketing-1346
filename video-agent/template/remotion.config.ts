import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(false);
Config.setConcurrency(null); // use all cores
// Files the agent stages live under ./public/assets/run, and manifest paths
// look like "assets/run/narration/s1.mp3" (relative to ./public).
Config.setPublicDir("public");
