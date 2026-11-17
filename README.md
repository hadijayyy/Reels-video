# Reels-video

Short vertical videos (TikTok / Reels / Shorts) built entirely in code.

| Video | Topic | Length |
|---|---|---|
| [`rupiah-rekor/rupiah-rekor-terlemah.mp4`](rupiah-rekor/rupiah-rekor-terlemah.mp4) | Rupiah hits a record low of Rp18.270/US$ (16 Nov 2026) | 44.7 s, 1080×1920, 30 fps |
| [`doctorx-bogor/doctor-x-syuting-bogor.mp4`](doctorx-bogor/doctor-x-syuting-bogor.mp4) | Viral: K-drama *Doctor X* allegedly filmed in Cariu, Bogor (17 Nov 2026). Voice: OmniVoice (VoiceStudio) | 35.3 s, 1080×1920, 30 fps |

Each video folder holds the script (`script.json`), voiceover and music generators (`make_vo.py`, `make_audio.py`), the canvas animation (`reel.html`), the frame renderer (`render.mjs`), and `build.sh` to rebuild everything. Requires ffmpeg, Node with Playwright + Chromium, Python with numpy and gTTS. Caption, hashtags and sources are in `CAPTION.md`.
