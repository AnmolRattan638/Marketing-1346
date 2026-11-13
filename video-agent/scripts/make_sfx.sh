#!/usr/bin/env bash
# Regenerates the placeholder sound library (44 files, see make_sfx.py). Needs numpy, scipy and ffmpeg.
set -euo pipefail
exec python3 "$(dirname "$0")/make_sfx.py"
