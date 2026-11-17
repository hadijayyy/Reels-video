"""Synthesize the music bed + SFX in numpy, place the voiceover, duck, and write out/mix.wav."""
import json, pathlib, wave
import numpy as np

ROOT = pathlib.Path(__file__).parent
SR = 44100
tl = json.loads((ROOT / "timeline.json").read_text())
N = int(tl["duration"] * SR)
rng = np.random.default_rng(7)


def read_wav(p):
    with wave.open(str(p)) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a


def place(buf, sig, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf) or i < 0:
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig * gain


def env(n, a=0.005, d=0.3):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)




def one_pole(x, cutoff):
    # vectorised-ish one-pole lowpass via FFT (cheap, zero-phase)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / cutoff) ** 2), len(x))


# ---------- instruments ----------
def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)


def hat(open_=False):
    n = int((0.16 if open_ else 0.05) * SR)
    x = rng.standard_normal(n)
    x = x - one_pole(x, 7000)
    return x * env(n, 0.001, 0.05 if open_ else 0.012)


def clap():
    n = int(0.2 * SR)
    x = rng.standard_normal(n)
    x = one_pole(x, 5000) - one_pole(x, 900)
    t = np.arange(n) / SR
    e = np.exp(-t / 0.07) * (1 + 0.8 * np.sin(2 * np.pi * 70 * t) * (t < 0.03))
    return x * e


def bass(freq, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.35 * np.sign(np.sin(2 * np.pi * freq * t))
    x = one_pole(x, 220)
    return x * np.minimum(t / 0.01, 1) * np.exp(-t / (dur * 0.9))


def pad(freqs, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for det in (-0.004, 0, 0.004):
            ph = rng.random() * 6.28
            x += np.sin(2 * np.pi * f * (1 + det) * t + ph) + 0.3 * np.sin(2 * np.pi * 2 * f * (1 + det) * t + ph)
    e = np.minimum(t / 0.4, 1) * np.minimum((dur - t) / 0.4, 1)
    return one_pole(x, 1400) * e / (len(freqs) * 3)


def pluck(freq, dur=0.22):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5 + np.sin(2 * np.pi * freq * t)
    return one_pole(x, 2600) * env(n, 0.002, 0.07)


def impact():
    n = int(1.1 * SR); t = np.arange(n) / SR
    f = 38 + 90 * np.exp(-t / 0.05)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    noise = one_pole(rng.standard_normal(n), 1800) * np.exp(-t / 0.18) * 0.6
    return sub + noise


def whoosh(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    lo = one_pole(x, 900); hi = one_pole(x, 6000)
    mixv = (t / dur) ** 2
    return (lo * (1 - mixv) + (hi - lo) * mixv) * (t / dur) ** 2.2


def tick():
    n = int(0.03 * SR)
    return np.sin(2 * np.pi * 1900 * np.arange(n) / SR) * env(n, 0.001, 0.006)


def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 200 * 2 ** (2.2 * t / dur)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + (rng.standard_normal(n) - one_pole(rng.standard_normal(n), 3000)) * 0.3
    return x * (t / dur) ** 2


# ---------- music bed: 120 BPM, A minor ----------
BPM = 120
beat = 60 / BPM
music = np.zeros(N, dtype=np.float64)
roots = [55.0, 55.0, 43.65, 49.0]            # A  A  F  G
chords = [[220, 261.63, 329.63], [220, 261.63, 329.63], [174.61, 220, 261.63], [196, 246.94, 293.66]]
arp = [[440, 523.25, 659.25, 523.25], [440, 523.25, 659.25, 783.99], [349.23, 440, 523.25, 440], [392, 493.88, 587.33, 493.88]]
K, H, HO, C = kick(), hat(), hat(True), clap()
scene_start = {s["name"]: s["start"] for s in tl["scenes"]}
drop = scene_start["what"]                  # full drums enter after the hook
outro = scene_start["cta"]
nbars = int(tl["duration"] / (beat * 4)) + 1
for bar in range(nbars):
    t0 = bar * beat * 4
    ci = bar % 4
    place(music, pad(chords[ci], beat * 4 + 0.3), t0, 0.5)
    for b in range(4):
        tb = t0 + b * beat
        full = tb >= drop - 0.05
        place(music, K, tb, 0.95 if full else 0.55)
        if full:
            place(music, bass(roots[ci], beat * 0.48), tb + beat / 2, 0.75)
            if b in (1, 3):
                place(music, C, tb, 0.33)
            for s in range(4):
                place(music, HO if s == 2 else H, tb + s * beat / 4, 0.16 if s == 2 else 0.10)
            for s in range(2):
                place(music, pluck(arp[ci][(b * 2 + s) % 4]), tb + s * beat / 2, 0.13)
        else:
            place(music, H, tb + beat / 2, 0.10)

# ---------- SFX on the picture ----------
def beep(f=1046.5, dur=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * env(n, 0.002, 0.05)


sfx = np.zeros(N, dtype=np.float64)
for s in tl["scenes"]:
    if s["start"] > 0.5:
        place(sfx, whoosh(), s["start"] - 0.42, 0.5)
    place(sfx, impact(), s["start"] + 0.02, 0.8 if s["name"] in ("hook", "what", "fact") else 0.5)
clip = {c["id"]: c for c in tl["clips"]}
for k in range(4):                                                # heart-monitor beeps under the title
    place(sfx, beep(), 0.25 + k * 0.5, 0.35)
place(sfx, impact(), 1.15, 0.75)                                  # BOGOR? stamp
place(sfx, riser(drop - 2.2), 2.2, 0.3)
place(sfx, impact(), scene_start["what"] + clip["what"]["start"] - scene_start["what"] + 4.6, 0.45)  # LAGOTA
for cid in ("clue1", "clue2", "clue3"):
    place(sfx, impact(), clip[cid]["start"], 0.45)
    place(sfx, tick(), clip[cid]["start"], 0.5)
place(sfx, impact(), scene_start["loc"] + 1.55, 0.55)             # pin lands
for k in range(26):                                               # view counter roll
    place(sfx, tick(), scene_start["proof"] + 1.4 + k * 0.1 * (1 + k / 26), 0.22)
place(sfx, impact(), scene_start["fact"] + 0.55, 0.85)            # BELUM DIKONFIRMASI stamp

# ---------- voice ----------
vo = np.zeros(N, dtype=np.float64)
for c in tl["clips"]:
    place(vo, read_wav(ROOT / "vo" / f"{c['id']}.wav").astype(np.float64), c["start"])
vo = vo - one_pole(vo, 90)                                         # high-pass rumble
vo /= np.max(np.abs(vo)) + 1e-9

# duck the bed under the voice
level = one_pole(np.abs(vo), 6) * 9
duck = 1 - 0.62 * np.clip(level, 0, 1)
music = music / (np.max(np.abs(music)) + 1e-9)
sfx = sfx / (np.max(np.abs(sfx)) + 1e-9)
fade = np.ones(N)
fo = int(1.0 * SR)
fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
mix = vo * 1.0 + music * 0.42 * duck + sfx * 0.42 * (0.55 + 0.45 * duck)
mix *= fade
mix = np.tanh(mix * 1.25) * 0.93

# light stereo width: music slightly decorrelated
st = np.stack([mix, mix], axis=1)
pcm = (st * 32767).astype(np.int16)
(ROOT / "out").mkdir(exist_ok=True)
with wave.open(str(ROOT / "out" / "mix.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("audio ok", round(N / SR, 2), "s")
