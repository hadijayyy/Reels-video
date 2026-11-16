"""Generate Indonesian voiceover clips (gTTS), speed them up, and build the timeline."""
import json, subprocess, pathlib
from gtts import gTTS

ROOT = pathlib.Path(__file__).parent
TEMPO = 1.3           # gTTS is slow by default
LEAD, GAP, TAIL = 0.3, 0.16, 0.9

script = json.loads((ROOT / "script.json").read_text())
t = LEAD
clips = []
for ln in script["lines"]:
    raw = ROOT / "vo" / f"{ln['id']}.mp3"
    wav = ROOT / "vo" / f"{ln['id']}.wav"
    if not raw.exists():
        gTTS(ln["text"], lang="id").save(str(raw))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af",
        f"silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
        f"silenceremove=start_periods=1:start_threshold=-45dB,areverse,atempo={TEMPO}",
        "-ar", "44100", "-ac", "1", str(wav)], check=True)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "csv=p=0", str(wav)]))
    clips.append({**ln, "start": round(t, 3), "dur": round(dur, 3)})
    t += dur + GAP

# scenes span from their first clip to the next scene's first clip
scenes = []
for c in clips:
    if not scenes or scenes[-1]["name"] != c["scene"]:
        scenes.append({"name": c["scene"], "start": max(0, c["start"] - 0.18)})
scenes[0]["start"] = 0
total = round(t - GAP + TAIL, 3)
for i, s in enumerate(scenes):
    s["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else total
tl = {"fps": 30, "duration": total, "scenes": scenes, "clips": clips}
(ROOT / "timeline.json").write_text(json.dumps(tl, indent=1, ensure_ascii=False))
print(json.dumps({"duration": total, "scenes": scenes}, indent=1))
