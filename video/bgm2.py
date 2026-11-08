"""BGM を合成する（権利の心配がないよう、すべて NumPy で作る）。場面に合わせて4つの部分に分ける。

  導入（〜logo）  : 静かなピアノとパッド。Am → F → C → G（少しさみしい）
  ロゴ〜機能の前  : 明るく転じる。C → G → Am → F、ピアノのアルペジオとパッドが広がる
  機能（feat〜）  : やわらかいベースと軽いリズム（キック・シェイカー）、短いメロディ
  感想・締め      : リズムを抜いて、ピアノとパッドでやさしく。最後は C で終わる
使い方: .venv/bin/python bgm2.py <全体の秒> <出力.wav> <ロゴの秒> <機能の秒> <感想の秒> <締めの秒>
"""
import sys, wave
import numpy as np

SR = 48000
dur, out = float(sys.argv[1]), sys.argv[2]
T_LOGO, T_FEAT, T_FEED, T_END = (float(x) for x in sys.argv[3:7])
BPM = 84; BEAT = 60 / BPM; BAR = BEAT * 4
N = int((dur + 4) * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(3)

def hz(n): return 440 * 2 ** ((n - 69) / 12)

def put(sig, start, pan=0.5, gain=1.0):
    i = int(start * SR)
    if i >= N: return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * np.cos(pan * np.pi / 2)
    R[i:i + len(sig)] += sig * gain * np.sin(pan * np.pi / 2)

def piano(n, length=2.5, vel=1.0):
    """ピアノ風：倍音ごとに減衰を変え、少しずらした2本で温かく"""
    t = np.arange(int(length * SR)) / SR; f = hz(n); s = np.zeros_like(t)
    for h, (a, dk) in enumerate([(1.0, 1.6), (0.45, 2.6), (0.22, 3.8), (0.12, 5.5), (0.06, 7.0), (0.03, 9.0)], start=1):
        fh = f * h * (1 + 0.0004 * h * h)
        s += a * np.exp(-t * dk * (0.6 + f / 900)) * (np.sin(2 * np.pi * fh * t) + 0.6 * np.sin(2 * np.pi * fh * 1.0015 * t))
    att = np.minimum(1, t / 0.004); rel = np.minimum(1, (length - t) / 0.3)
    return s * att * rel * vel * 0.18

def pad(notes, length, vel=1.0):
    """パッド：のこぎり波を6倍音までに抑え、ゆっくり出入りさせる"""
    t = np.arange(int(length * SR)) / SR; s = np.zeros_like(t)
    for n in notes:
        for det in (-0.12, 0.0, 0.12):
            f = hz(n + det)
            for h in range(1, 7):
                s += np.sin(2 * np.pi * f * h * t + rng.uniform(0, 6.28)) / (h * 1.6)
    env = np.minimum(1, t / 1.2) * np.minimum(1, (length - t) / 1.4)
    return s * env * vel * 0.012 / max(1, len(notes))

def bass(n, length):
    t = np.arange(int(length * SR)) / SR; f = hz(n)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return s * np.minimum(1, t / 0.02) * np.exp(-t * 1.2) * np.minimum(1, (length - t) / 0.1) * 0.16

def kick():
    t = np.arange(int(0.35 * SR)) / SR
    f = 50 + 70 * np.exp(-t * 25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.22

def shaker():
    t = np.arange(int(0.09 * SR)) / SR
    n = rng.standard_normal(len(t)); n = n - np.convolve(n, np.ones(6) / 6, mode="same")  # 高い音だけ
    n = np.convolve(n, np.ones(3) / 3, mode="same")  # 耳に痛い一番上は丸める
    return n * np.exp(-t * 45) * np.minimum(1, t / 0.008) * 0.035

INTRO = [[57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62]]   # Am F C G
MAIN = [[48, 55, 64], [55, 59, 62], [57, 60, 64], [53, 57, 60]]    # C G Am F
ROOT_I = [45, 41, 48, 43]; ROOT_M = [36, 43, 45, 41]

# 導入：2小節ごとにゆっくり。ピアノは和音をほどいて、すき間を多く
t = 0.4; k = 0
while t < T_LOGO - 0.5:
    ch = INTRO[k % 4]
    put(pad([n + 12 for n in ch], BAR * 2 + 1.5, 0.8), t, 0.5)
    for j, (dt, n) in enumerate([(0, ch[0] + 12), (BEAT * 1.5, ch[2] + 12), (BEAT * 3, ch[1] + 24), (BAR + BEAT, ch[2] + 12)]):
        put(piano(n, 3.0, 0.7), t + dt, 0.35 + 0.1 * j)
    t += BAR * 2; k += 1

# ロゴ〜：明るく。アルペジオが広がる
def main_bar(t, k, rhythm, melody, vel=1.0):
    ch = MAIN[k % 4]
    put(pad([n + 12 for n in ch], BAR + 1.4, 0.9 * vel), t, 0.5)
    pat = [0, 1, 2, 1, 2, 1, 0, 2]
    for j in range(8):
        put(piano(ch[pat[j]] + 24, 1.6, 0.42 * vel), t + j * BEAT / 2, 0.3 if j % 2 else 0.7)
    if rhythm:
        put(bass(ROOT_M[k % 4], BEAT * 2), t, 0.5); put(bass(ROOT_M[k % 4], BEAT * 2), t + BEAT * 2, 0.5, 0.8)
        put(kick(), t, 0.5); put(kick(), t + BEAT * 2, 0.5, 0.8)
        for j in range(8): put(shaker(), t + j * BEAT / 2 + 0.01, 0.65, 1.0 if j % 2 else 0.6)
    if melody:
        mel = {0: [(0, 76), (1.5, 79), (3, 76)], 1: [(0, 74), (2, 71)], 2: [(0, 72), (1, 76), (2.5, 79)], 3: [(0, 77), (2, 76), (3, 74)]}[k % 4]
        for b, n in mel: put(piano(n, 2.2, 0.55), t + b * BEAT, 0.55)

t = T_LOGO; k = 0
while t < T_FEAT - 0.3:
    main_bar(t, k, rhythm=False, melody=False, vel=min(1.0, 0.5 + 0.25 * k)); t += BAR; k += 1
# 機能：リズムとメロディ（8小節ごとにメロディを休む）
t = T_FEAT; k = 0
while t < T_FEED - 0.3:
    main_bar(t, k, rhythm=True, melody=(k // 4) % 2 == 1); t += BAR; k += 1
# 感想：リズムを抜く
t = T_FEED; k = 0
while t < T_END - 0.3:
    main_bar(t, k, rhythm=False, melody=True, vel=0.85); t += BAR; k += 1
# 締め：C を長く鳴らして終わる
put(pad([60, 64, 67, 72], dur - T_END + 2.0, 1.0), T_END, 0.5)
for j, n in enumerate([48, 55, 60, 64, 67, 72, 76]):
    put(piano(n, 5.0, 0.6), T_END + 0.25 + j * 0.12, 0.3 + 0.07 * j)

# 残響（減衰するノイズを畳み込む）
def reverb(x, secs=2.2, mix=0.28):
    ir_t = np.arange(int(secs * SR)) / SR
    ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2); ir = ir - np.convolve(ir, np.ones(40) / 40, mode="same") * 0.5
    ir /= np.abs(ir).sum() / 6
    n = len(x) + len(ir); nfft = 1 << (n - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
    return x * (1 - mix) + wet * mix
L = reverb(L); R = reverb(R)
tt = np.arange(N) / SR
fade = np.minimum(1, tt / 2.0) * np.clip((dur - tt) / 3.0, 0, 1)
st = np.stack([L * fade, R * fade], axis=1)[: int(dur * SR)]
st /= max(1e-9, np.abs(st).max()) / 0.6
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
print(out, dur)
