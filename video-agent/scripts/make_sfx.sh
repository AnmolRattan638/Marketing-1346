#!/usr/bin/env bash
# Generates simple placeholder sound effects with ffmpeg so the pipeline works out of the box.
# They are synthesized here, so there is nothing to license. Replace them with better sounds
# (same file names) from Pixabay or Freesound once you have checked each license.
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)/assets/sfx"
mkdir -p "$OUT"
ff() { ffmpeg -y -loglevel error "$@"; }

# whoosh: filtered pink noise that swells and fades
ff -f lavfi -i "anoisesrc=d=0.7:c=pink:a=0.6" \
   -af "highpass=f=350,lowpass=f=5500,afade=t=in:d=0.28,afade=t=out:st=0.3:d=0.4,volume=2.0" \
   -b:a 128k "$OUT/whoosh.mp3"

# pop: short falling-pitch blip
ff -f lavfi -i "aevalsrc=0.9*sin(2*PI*(500+2200*exp(-45*t))*t)*exp(-22*t):s=44100:d=0.18" \
   -b:a 128k "$OUT/pop.mp3"

# click: very short bright noise tick
ff -f lavfi -i "anoisesrc=d=0.04:c=white:a=0.9" \
   -af "highpass=f=2500,afade=t=out:d=0.035,volume=1.5" -b:a 128k "$OUT/click.mp3"

# riser: noise that grows over 1.4 s, ends abruptly on the word it builds to
ff -f lavfi -i "anoisesrc=d=1.4:c=pink:a=0.5" \
   -af "highpass=f=300,afade=t=in:d=1.3:curve=exp,volume=2.5" -b:a 128k "$OUT/riser.mp3"

ls -l "$OUT"
