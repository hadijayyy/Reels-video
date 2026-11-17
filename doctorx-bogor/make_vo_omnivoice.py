"""Generate the voiceover with OmniVoice (the engine behind VoiceStudio), verified by Whisper.

Each line is synthesised with voice design, transcribed with faster-whisper, and retried with
another seed if the transcript drifts from the script. Output: vo/<id>.ov.wav

Needs a VoiceStudio checkout (https://github.com/debpalash/VoiceStudio) on PYTHONPATH and a Python
env with torch, torchaudio, transformers>=5.10, soundfile, pydub, psutil, faster-whisper.
"""
import difflib, json, pathlib, re, subprocess, sys
import numpy as np, torch
from omnivoice.models.omnivoice import OmniVoice
from omnivoice.utils.audio import save_audio
from faster_whisper import WhisperModel

ROOT = pathlib.Path(__file__).parent
VOICE = "male, young adult, moderate pitch"
SPEED = 1.1
SEEDS = [7, 1234, 42, 99, 2026, 5, 11, 314]
MIN_SCORE = 0.88
NUM = {"0": "nol", "1": "satu", "2": "dua", "3": "tiga", "11": "sebelas"}

def norm(s):
    s = s.lower().replace("dr.", "doktor").replace("doctor", "doktor").replace("shooting", "syuting")
    s = re.sub(r"\d+", lambda m: NUM.get(m.group(), m.group()), s)
    return re.sub(r"[^a-z ]", " ", s).split()

MUST = {"what": ["dokter"], "loc": ["cariu"], "cta": ["menurut"]}   # words the voice tends to get wrong


def score(lid, a, b):
    ja, jb = "".join(norm(a)), "".join(norm(b))           # spaceless: "di tumpukan" == "ditumpukan"
    sc = difflib.SequenceMatcher(None, ja, jb).ratio()
    return sc if all(w in jb for w in MUST.get(lid, [])) else min(sc, 0.5)

def asr(m, path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = m.transcribe(np.frombuffer(raw, np.int16).astype(np.float32) / 32768, language="id", beam_size=5)
    return " ".join(s.text.strip() for s in segs)

only = set(sys.argv[1:])
tts = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu", dtype=torch.float32)
stt = WhisperModel("small", device="cpu", compute_type="int8")
report = {}
for ln in json.loads((ROOT / "script.json").read_text())["lines"]:
    if only and ln["id"] not in only:
        continue
    out, best = ROOT / "vo" / f"{ln['id']}.ov.wav", None
    for seed in SEEDS:
        torch.manual_seed(seed)
        a = tts.generate(text=ln.get("tts", ln["text"]),   # "tts": phonetic respelling, if any
                          language="id", instruct=VOICE, speed=SPEED, num_step=32)
        tmp = ROOT / "vo" / f"{ln['id']}.try.wav"
        save_audio(str(tmp), a[0], tts.sampling_rate)
        heard = asr(stt, tmp); sc = score(ln["id"], ln["text"], heard)
        print(f"{ln['id']:6s} seed={seed:<5d} score={sc:.2f}  {heard}", flush=True)
        if best is None or sc > best[0]:
            best = (sc, seed, heard); tmp.replace(out)
        else:
            tmp.unlink()
        if sc >= MIN_SCORE:
            break
    report[ln["id"]] = {"score": round(best[0], 3), "seed": best[1], "heard": best[2]}
rp = ROOT / "vo" / "asr_report.json"
report = {**(json.loads(rp.read_text()) if rp.exists() else {}), **report}
rp.write_text(json.dumps(report, indent=1, ensure_ascii=False))
bad = [k for k, v in report.items() if v["score"] < MIN_SCORE]
print("LOW SCORE:", bad if bad else "none")
