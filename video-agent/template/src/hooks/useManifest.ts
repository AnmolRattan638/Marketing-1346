import manifest from "../../manifest.json";
import type { Manifest } from "../types";

// The manifest is statically imported so Remotion's bundler can pre-compute
// durations. Scene components call this hook to access the full manifest.
export function useManifest(): Manifest {
  return manifest as Manifest;
}
