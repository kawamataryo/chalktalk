"""静かな BGM を合成する（権利の心配がないよう、すべて NumPy で作る）。

やわらかいパッドの和音（C → Am → F → G）と、ゆっくりした木琴風のアルペジオ。テンポ 84。
使い方: .venv/bin/python bgm.py <秒> <出力.wav>
"""
import sys, wave
import numpy as np

SR = 48000
dur = float(sys.argv[1]) if len(sys.argv) > 1 else 150
out = sys.argv[2] if len(sys.argv) > 2 else "audio/bgm.wav"
bpm = 84
beat = 60 / bpm
bar = beat * 4

def hz(n):  # MIDI 番号 → Hz
    return 440 * 2 ** ((n - 69) / 12)

chords = [[60, 64, 67, 72], [57, 60, 64, 69], [53, 57, 60, 65], [55, 59, 62, 67]]
t = np.arange(int(dur * SR)) / SR
left = np.zeros_like(t); right = np.zeros_like(t)

# パッド：和音ごとに、ゆっくり立ち上がって消える
for i in range(int(dur / bar) + 1):
    start = i * bar
    seg = (t >= start) & (t < start + bar + 1.0)
    tt = t[seg] - start
    env = np.minimum(1, tt / 0.8) * np.exp(-np.maximum(0, tt - bar) * 3)
    for k, n in enumerate(chords[i % 4]):
        f = hz(n - 12 if k == 0 else n)
        tone = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt + 0.3)
        pan = 0.35 + 0.1 * k
        left[seg] += 0.05 * env * tone * (1 - pan)
        right[seg] += 0.05 * env * tone * pan

# アルペジオ：8 分音符、減衰の速い音（木琴風）
pattern = [0, 1, 2, 3, 2, 1, 2, 3]
for i in range(int(dur / (beat / 2))):
    start = i * beat / 2
    chord = chords[int(start / bar) % 4]
    n = chord[pattern[i % 8]] + 12
    seg = (t >= start) & (t < start + 1.2)
    tt = t[seg] - start
    env = np.exp(-tt * 6) * np.minimum(1, tt / 0.005)
    f = hz(n)
    tone = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 4 * f * tt) * np.exp(-tt * 20)
    pan = 0.3 if i % 2 else 0.7
    left[seg] += 0.035 * env * tone * (1 - pan)
    right[seg] += 0.035 * env * tone * pan

# 頭と終わりをフェード
fade = np.minimum(1, t / 2.0) * np.minimum(1, (dur - t) / 3.0)
stereo = np.stack([left * fade, right * fade], axis=1)
stereo /= max(1e-9, np.abs(stereo).max()) / 0.5
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((stereo * 32767).astype("<i2").tobytes())
print(out, dur)
