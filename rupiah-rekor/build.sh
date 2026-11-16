#!/usr/bin/env bash
# Rebuild the reel end to end: voiceover -> audio mix -> frames -> final MP4.
set -euo pipefail
cd "$(dirname "$0")"
[ -e node_modules/playwright ] || { mkdir -p node_modules; ln -sfn "$(npm root -g)/playwright" node_modules/playwright; }
python3 make_vo.py      # needs: pip install gTTS
python3 make_audio.py
node render.mjs
ffmpeg -y -loglevel error -i out/video.mp4 -i out/mix.wav \
  -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k -ar 44100 \
  -movflags +faststart -shortest rupiah-rekor-terlemah.mp4
echo "done -> rupiah-rekor-terlemah.mp4"
