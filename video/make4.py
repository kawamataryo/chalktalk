"""ChalkTalk のプロモーション動画（第6試作）。

導入（Blender の部屋・リアル版）→ ロゴ（App Store 風のカード）→ iPad の紹介 → 機能 01〜07 → 長男の感想 → 締め。
子どもの発話はソラの声で入れ、その間は録画を止めて（静止）、話してから先生が返すようにする。
セリフはすべて字幕（子ども：オレンジの吹き出し、先生：紫の字幕）。
使い方: .venv/bin/python make4.py → out4/chalktalk_promo.mp4 と out4/audit.txt（ナレーションと場面の対応表）
環境変数: ONLY=3,5 でそのセグメントだけ作る / FRAMES=frames2（Blender の連番）
"""
import json, math, os, random, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont

V = Path(__file__).parent
sys.argv = [sys.argv[0], str(V / "cards")]
import cards as C  # noqa: E402

W, H, FPS = 1920, 1080, 30
OUT = V / "out4"; (OUT / "seg").mkdir(parents=True, exist_ok=True)
L = OUT / "layers"; L.mkdir(exist_ok=True)
A = V / "audio"; N4 = A / "n4"; I2 = V / "out2" / "intro2"; BL = V / "blender"
FR = BL / os.environ.get("FRAMES", "frames2")
CHALK_FONT = "/System/Library/Fonts/Supplemental/Chalkduster.ttf"
def chalkf(size): return ImageFont.truetype(CHALK_FONT, size)
BG_HEX = "0xF3F1E9"
NAME, TAG = "ChalkTalk", "話しかければ、そばに先生。"
KID_C, KID_BG = (214, 92, 24), (255, 245, 236)
MUNI_C = (104, 98, 196)
SPEAKER = {"session": "ムニ先生", "board": "ムニ先生", "research": "ムニ先生", "watch": "ムニ先生", "message": "ムニ先生"}

NARR_DIR = A / os.environ.get("NARR", "n4")  # ナレーションの声（n4: Azure の仮、n5: ElevenLabs）
def nv(key, fallback):
    p = NARR_DIR / f"{key}.mp3"
    return p if p.exists() else fallback

def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode: print(r.stderr[-3000:]); raise SystemExit(1)
_dur = {}
def dur_of(f):
    f = str(f)
    if f not in _dur:
        _dur[f] = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout)
    return _dur[f]
def rms_of(f):
    """音声の大きさ（1/30 秒ごと、0〜1）"""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    hop = 16000 // FPS; n = len(a) // hop
    r = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])
    return r / (r.max() + 1e-6)

# ---------- 黒板とチョーク ----------
def board_bg():
    p = L / "board_bg.png"
    if p.exists(): return p
    img = Image.new("RGB", (W, H), (34, 64, 54)); r = random.Random(1)
    sm = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(sm)
    for _ in range(26):
        x, y = r.uniform(-200, W), r.uniform(-100, H); w, h = r.uniform(300, 900), r.uniform(60, 220)
        d.ellipse((x, y, x + w, y + h), fill=(255, 255, 255, r.randint(5, 13)))
    img = Image.alpha_composite(img.convert("RGBA"), sm.filter(ImageFilter.GaussianBlur(40)))
    noise = Image.effect_noise((W, H), 18).convert("L")
    img = Image.composite(Image.new("RGBA", (W, H), (255, 255, 255, 255)), img, noise.point(lambda v: 10 if v > 150 else 0))
    vig = Image.new("L", (W // 4, H // 4), 0); ImageDraw.Draw(vig).ellipse((-60, -40, W // 4 + 60, H // 4 + 40), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(30)).resize((W, H))
    img = Image.composite(img, Image.new("RGBA", (W, H), (14, 30, 25, 255)), vig.point(lambda v: 90 + int(v * 165 / 255)))
    img.convert("RGB").save(p); return p

def chalky(layer):
    a = layer.getchannel("A")
    n = Image.effect_noise(layer.size, 60).convert("L").point(lambda v: 255 if v > 70 else 120).filter(ImageFilter.GaussianBlur(0.6))
    layer.putalpha(ImageChops.multiply(a, n)); return layer

def text_layer(name, items):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for s, f, col, x, y, ch in items:
        w = d.textlength(s, font=f); xx = (W - w) / 2 if x == "c" else x
        t = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(t).text((xx, y), s, font=f, fill=col)
        img = Image.alpha_composite(img, chalky(t) if ch else t)
    p = L / f"{name}.png"; img.save(p); return p

def rounded_icon(size):
    ic = Image.open(V / "cards" / "appicon.png").convert("RGBA").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), int(size * 0.225), fill=255)
    ic.putalpha(m); return ic

def store_card(name, y):
    """App Store の製品ページ風のカード（Apple の公式バッジは使わない）。まだ公開前なので「近日公開」"""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cw, ch = 820, 150; x = (W - cw) // 2
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((x, y + 10, x + cw, y + ch + 10), 34, fill=(0, 0, 0, 90))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(img); d.rounded_rectangle((x, y, x + cw, y + ch), 34, fill=(250, 250, 252, 250))
    img.alpha_composite(rounded_icon(110), (x + 22, y + 20))
    d.text((x + 156, y + 26), "ChalkTalk", font=C.jfont(6, 42), fill=(20, 20, 24))
    d.text((x + 158, y + 84), "教育　・　iPad 向けアプリ", font=C.jfont(4, 26), fill=(110, 112, 120))
    bw, bh = 196, 62; bx, by = x + cw - bw - 30, y + (ch - bh) // 2
    d.rounded_rectangle((bx, by, bx + bw, by + bh), bh // 2, fill=(226, 228, 234))
    f = C.jfont(6, 28); t = "近日公開"; d.text((bx + (bw - d.textlength(t, font=f)) / 2, by + 13), t, font=f, fill=(96, 100, 112))
    f2 = C.jfont(3, 21); t2 = "※ 開発中のため、App Store ではまだ公開していません（画面はイメージ）"
    d.text(((W - d.textlength(t2, font=f2)) / 2, y + ch + 22), t2, font=f2, fill=(214, 226, 218, 230))
    p = L / f"{name}.png"; img.save(p); return p

def logo_layers():
    f = chalkf(190); d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w = d.textlength(NAME, font=f); x0 = (W - w) / 2 - 40; y0 = 230
    name = text_layer("logo_name", [(NAME, f, (248, 246, 238, 255), x0, y0, True)])
    b = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
    bx, by = x0 + w + 20, y0 + 10
    bd.rounded_rectangle((bx, by, bx + 130, by + 96), 40, outline=(240, 200, 110, 255), width=9)
    bd.polygon([(bx + 26, by + 88), (bx + 10, by + 128), (bx + 58, by + 92)], fill=(240, 200, 110, 255))
    for k in range(3):
        bd.ellipse((bx + 30 + k * 30, by + 40, bx + 46 + k * 30, by + 56), fill=(240, 200, 110, 255))
    bub = L / "logo_bubble.png"; chalky(b).save(bub)
    tag = text_layer("logo_tag", [(TAG, C.maru(60), (255, 236, 190, 255), "c", 520, False)])
    card = store_card("logo_store", 680)
    return name, bub, tag, card, x0, w

def feature_card_layers(no, title, sub):
    num = text_layer(f"fnum{no}", [(f"0{no}", chalkf(230), (240, 200, 110, 255), 230, 330, True)])
    ttl = text_layer(f"fttl{no}", [(title, C.maru(96), (250, 248, 240, 255), 620, 370, False)])
    sb = text_layer(f"fsub{no}", [(sub, C.jfont(4, 38), (214, 228, 220, 255), 626, 520, False)])
    line = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(line).line((626, 500, 1640, 500), fill=(250, 248, 240, 160), width=4)
    lp = L / f"fline{no}.png"; chalky(line).save(lp)
    return num, ttl, sb, lp

def wrap_nice(d, text, f, width):
    """折り返し。最後の行が短すぎるときは、幅を少し狭めて均す"""
    lines = C.wrap(d, text, f, width)
    w = width
    while len(lines) > 1 and len(lines[-1]) <= 3 and w > width * 0.6:
        w -= 12; lines = C.wrap(d, text, f, w)
    return lines

# ---------- 右の欄 ----------
def panel(name, no, title, telops=(), image=None):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x, y = C.PANEL_X, C.IPAD_Y + 4
    d.text((x, y - 8), f"0{no}", font=chalkf(64), fill=(194, 140, 40)); y += 86
    for line in wrap_nice(d, title, C.maru(40), C.PANEL_W):
        d.text((x, y), line, font=C.maru(40), fill=C.INK); y += 56
    y += 14
    for t in telops:
        for fs in (25, 24, 23, 22, 21):
            f = C.jfont(6, fs); lines = C.wrap(d, t, f, C.PANEL_W - 40)
            if len(lines) == 1 or len(lines[-1]) > 3: break
        h = 22 + 37 * len(lines)
        d.rounded_rectangle((x, y, x + C.PANEL_W, y + h), 12, fill=C.BOARD)
        for i, l in enumerate(lines):
            d.text((x + 20, y + 12 + 37 * i), l, font=f, fill=C.CHALK)
        y += h + 12
    if image is not None:
        im = image; img.alpha_composite(im, (x, y + 6))
    p = L / f"{name}.png"; img.save(p); return p

def note(name, s):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); f = C.jfont(3, 16)
    for i, l in enumerate(C.wrap(d, s, f, C.PANEL_W)):
        d.text((C.PANEL_X, C.IPAD_Y + C.IPAD_H - 48 + 22 * i), l, font=f, fill=C.MUTED)
    p = L / f"{name}.png"; img.save(p); return p

def caption(name, s, color=(250, 246, 236), size=50, y=54):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); f = C.maru(size); d = ImageDraw.Draw(img)
    w = d.textlength(s, font=f); x = (W - w) / 2
    d.rounded_rectangle((x - 44, y - 20, x + w + 44, y + size + 30), 22, fill=(8, 10, 16, 165))
    d.text((x, y), s, font=f, fill=color + (255,))
    p = L / f"{name}.png"; img.save(p); return p

# ---------- セリフの字幕（1 コマずつ描いて、透明つきの動画にする） ----------
def mic(d, cx, cy, r, color):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color); w = r * 0.36
    d.rounded_rectangle((cx - w, cy - r * 0.55, cx + w, cy + r * 0.15), w, fill=(255, 255, 255))
    d.arc((cx - r * 0.55, cy - r * 0.45, cx + r * 0.55, cy + r * 0.35), 0, 180, fill=(255, 255, 255), width=max(2, int(r * 0.09)))
    d.line((cx, cy + r * 0.35, cx, cy + r * 0.55), fill=(255, 255, 255), width=max(2, int(r * 0.09)))

class Talk:
    """クリップの中のセリフ（時刻はクリップの頭から）"""
    def __init__(self, area):
        self.area = area  # (x0, x1, bottom)
        self.kids, self.teachers = [], []
    def kid(self, t0, text, audio):
        self.kids.append(dict(t0=t0, text=text, dur=dur_of(audio), rms=rms_of(audio)))
    def teacher(self, t0, text, d, who="ムニ先生"):
        self.teachers.append(dict(t0=t0, text=text, dur=d, who=who))

    def frame(self, t):
        x0, x1, bottom = self.area
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        # いま話している先生
        cur_t = next((e for e in self.teachers if e["t0"] <= t < e["t0"] + e["dur"] + 0.15), None)
        # 子ども：話している間は大きな吹き出し、先生が返し始めたら上の小さな札に
        last_kid = None
        for e in self.kids:
            if e["t0"] <= t: last_kid = e
        if last_kid:
            e = last_kid; prog = (t - e["t0"]) / max(0.1, e["dur"] * 0.92)
            answered = any(te["t0"] >= e["t0"] + e["dur"] * 0.5 and te["t0"] <= t for te in self.teachers)
            if not answered:
                self._kid_big(d, img, e, t, min(1.0, prog), x0, x1, bottom)
            else:
                self._kid_small(d, e, x0, x1)
        if cur_t:
            self._teacher(d, img, cur_t, t, x0, x1, bottom)
        return img

    def _kid_big(self, d, img, e, t, prog, x0, x1, bottom):
        f = C.maru(44); pad = 28; mw = 110
        lines = wrap_nice(d, e["text"], f, x1 - x0 - mw - pad * 2)
        h = 70 + 58 * len(lines); top = bottom - h
        # 出てくるときに少し持ち上がる
        k = min(1.0, (t - e["t0"]) / 0.25); top += int(24 * (1 - k)); alpha = int(250 * k)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle((x0, top, x1, top + h), 30, fill=KID_BG + (alpha,), outline=KID_C + (alpha,), width=5)
        ld.polygon([(x0 + 60, top + h - 2), (x0 + 30, top + h + 34), (x0 + 110, top + h - 2)], fill=KID_BG + (alpha,))
        ld.line([(x0 + 60, top + h + 1), (x0 + 30, top + h + 34), (x0 + 110, top + h + 1)], fill=KID_C + (alpha,), width=5)
        img.alpha_composite(lay); d = ImageDraw.Draw(img)
        mic(d, x0 + pad + 40, top + 72, 40, KID_C)
        d.text((x0 + mw + pad, top + 14), "長男が声で話しかける", font=C.jfont(6, 22), fill=KID_C)
        # 声の波（実際の音の大きさ）
        i = int((t - e["t0"]) * FPS)
        if 0 <= i < len(e["rms"]):
            bx = x0 + mw + pad + 270
            for j in range(9):
                v = e["rms"][max(0, i - j)] if i - j >= 0 else 0
                hh = 4 + 26 * v
                d.rounded_rectangle((bx + j * 12, top + 27 - hh / 2, bx + j * 12 + 6, top + 27 + hh / 2), 3, fill=KID_C)
        n = math.ceil(len(e["text"]) * prog); shown = e["text"][:n]
        y = top + 50
        for line in lines:
            take = shown[:len(line)]; shown = shown[len(line):]
            d.text((x0 + mw + pad, y), take, font=f, fill=C.INK); y += 58

    def _kid_small(self, d, e, x0, x1):
        f = C.maru(30); t = f"「{e['text']}」"
        while d.textlength(t, font=f) > x1 - x0 - 120 and len(t) > 6: t = t[:-2] + "」"
        w = d.textlength(t, font=f); top = C.IPAD_Y + 18
        d.rounded_rectangle((x0, top, x0 + w + 110, top + 62), 31, fill=KID_BG + (245,), outline=KID_C, width=3)
        mic(d, x0 + 34, top + 31, 21, KID_C)
        d.text((x0 + 70, top + 13), t, font=f, fill=C.INK)

    def _teacher(self, d, img, e, t, x0, x1, bottom):
        f = C.maru(40); lines = wrap_nice(d, e["text"], f, x1 - x0 - 80)
        h = 62 + 54 * len(lines); top = bottom - h
        k = min(1.0, (t - e["t0"]) / 0.1)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle((x0, top, x1, top + h), 26, fill=MUNI_C + (int(255 * k),))
        img.alpha_composite(lay); d = ImageDraw.Draw(img)
        d.text((x0 + 36, top + 12), e["who"], font=C.jfont(6, 22), fill=(225, 223, 255))
        y = top + 44
        for line in lines:
            d.text((x0 + 36, y), line, font=f, fill=(255, 255, 255)); y += 54

def render_talk(talk, dur, path):
    """字幕の動画（透明つき）を書き出す"""
    n = int(round(dur * FPS))
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "qtrle", "-pix_fmt", "argb", str(path)], stdin=subprocess.PIPE)
    cache_key, cache = None, None
    for i in range(n):
        t = i / FPS
        img = talk.frame(t)
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()

# ---------- 公的な統計：共働き世帯（総務省「労働力調査」、JILPT 図12） ----------
STAT_Y = list(range(1980, 2026))
STAT_W = [614,645,664,708,721,722,720,748,771,783,823,877,914,929,943,908,927,949,956,929,942,951,951,949,961,988,977,1013,1011,995,1012,987,1054,1069,1082,1120,1136,1188,1224,1251,1247,1257,1262,1278,1300,1333]
STAT_H = [1114,1082,1096,1038,1054,952,952,933,946,930,897,888,903,915,930,955,937,921,889,912,916,890,894,870,875,863,854,851,825,831,797,773,787,748,723,692,668,641,608,584,574,569,539,517,508,476]
def stat_frame(t, t0=0.4, td=1.8):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = min(1.0, max(0.0, (t - 0.0) / 0.4))
    x0, y0, cw, ch = 50, 470, 900, 560
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle((x0, y0, x0 + cw, y0 + ch), 22, fill=(10, 14, 26, int(200 * a)))
    img.alpha_composite(lay); d = ImageDraw.Draw(img)
    if a < 1: return img
    d.text((x0 + 34, y0 + 24), "共働きの家庭は、40年で2倍以上に", font=C.maru(42), fill=(255, 240, 210))
    gx, gy, gw, gh = x0 + 70, y0 + 110, cw - 290, 330
    d.line((gx, gy + gh, gx + gw, gy + gh), fill=(150, 160, 180), width=2)
    for yr in (1980, 2000, 2025):
        xx = gx + gw * (yr - 1980) / 45; d.text((xx - 30, gy + gh + 10), str(yr), font=C.jfont(4, 24), fill=(190, 198, 214))
    k = min(1.0, max(0.0, (t - t0) / td)); n = max(2, int(len(STAT_Y) * k))
    def pts(vals): return [(gx + gw * (STAT_Y[i] - 1980) / 45, gy + gh - gh * vals[i] / 1400) for i in range(n)]
    for vals, col, lab in ((STAT_H, (150, 172, 214), "専業主婦世帯"), (STAT_W, (250, 196, 90), "共働き世帯")):
        p_ = pts(vals); d.line(p_, fill=col, width=7, joint="curve")
        ex, ey = p_[-1]; d.ellipse((ex - 9, ey - 9, ex + 9, ey + 9), fill=col)
        if k >= 1.0:
            d.text((ex + 20, ey - 46), lab, font=C.jfont(6, 26), fill=col)
            d.text((ex + 20, ey - 14), f"{vals[-1]:,}万", font=C.jfont(6, 44), fill=col)
    d.text((x0 + 34, y0 + ch - 38), "出典：総務省「労働力調査」（労働政策研究・研修機構「専業主婦世帯と共働き世帯」）", font=C.jfont(3, 19), fill=(170, 178, 196))
    return img

def fade_out(img, k):
    if k >= 1: return img
    a = img.getchannel("A").point(lambda v: int(v * max(0.0, k))); img.putalpha(a); return img

class FnAnim:
    def __init__(self, fn): self.fn = fn
    def frame(self, t): return self.fn(t)

# ---------- セグメント ----------
segments = []
def seg(**k): segments.append(k)
def events(name): return json.loads((A / name / "events.json").read_text())
NOTE = note("note_session", "子どもの声は合成音声（同い年の仲間キャラ・ソラの声）。先生の返事は本番の Claude。録画に声が入らないため、先生と同じ声をあとで重ねた")
IPAD_AREA = (C.IPAD_X + 40, C.IPAD_X + C.IPAD_W - 40, C.IPAD_Y + C.IPAD_H - 34)

# 1. 導入（Blender 0〜22 秒）
T = dict(PARENT=5.6, Q=11.0, FAST=13.6, IF=16.9, PAUSE=20.4)
INTRO_TXT = {"i_a": "小学5年の長男は、中学受検の勉強中です。", "i_b2": "共働きの、わが家。親は仕事で、そばにいられません。",
             "i_c": "わからない問題で、手が止まっても、聞ける人がいない。", "n1c": "もし、話しかけられる先生が、そばにいたら。"}
INTRO_AT = {"i_a": 0.6, "i_b2": T["PARENT"] - 0.2, "i_c": 11.5, "n1c": T["IF"]}
intro_caps = []
for k_, at_ in INTRO_AT.items():
    f_ = nv(k_, A / f"{k_}.mp3"); end_ = at_ + dur_of(f_) + 0.5
    if k_ == "n1c": end_ = T["PAUSE"] + 1.2
    intro_caps.append((caption(f"icap_{k_}", INTRO_TXT[k_], size=46) if os.environ.get("NARR", "n4") != "n4" else I2 / {"i_a": "c1.png", "i_b2": "c2.png", "i_c": "c3.png", "n1c": "c4.png"}[k_], at_ - 0.1, end_))
seg(kind="frames", start=1, n=660, dur=22.0, layers=[*intro_caps, 
    (I2 / "vig95.png", T["IF"] + 1.2, 99)],
    anims=[(FnAnim(lambda t: fade_out(stat_frame(t - 5.8), (12.4 - t) / 0.5) if 5.8 <= t < 12.4 else Image.new("RGBA", (W, H), (0, 0, 0, 0))), 0)],
    voice=[(nv("i_a", A / "i_a.mp3"), 0.6), (nv("i_b2", N4 / "i_b2.mp3"), T["PARENT"] - 0.2), (nv("i_c", A / "i_c.mp3"), INTRO_AT["i_c"]), (nv("n1c", A / "n1c.mp3"), T["IF"])], fade_out=0.6)

# 2. ロゴ
name, bub, tag, card, lx, lw = logo_layers()
seg(kind="logo", dur=max(6.6, 3.0 + dur_of(nv("logo", A / "logo.mp3")) + 0.4), name=name, bub=bub, tag=tag, card=card, lx=lx, lw=lw, voice=[(nv("i_e", A / "i_e.mp3"), 0.3), (nv("logo", A / "logo.mp3"), 3.0)])

# 3. iPad の紹介（Blender 22〜29.5 秒）：子どもが話しかける → iPad が光ってあいさつ
tk = Talk((150, 1770, 1030))
tk.kid(0.4, "ねえ先生、ただいま！", N4 / "kid_tadaima.mp3")
tk.teacher(2.58, "おかえり！", dur_of(A / "session" / "000.mp3"))
seg(kind="frames", start=661, n=225, dur=max(9.0, 3.8 + dur_of(nv("ipad2", N4 / "ipad2.mp3")) + 0.4), talk=tk, crop=(286, 215, 1477, 831), layers=[(caption("cap_ipad", "iPad に話しかけるだけ。そばで一緒にがんばる、勉強の相棒です。", (255, 226, 150), y=950), 3.8, 99)],
    voice=[(N4 / "kid_tadaima.mp3", 0.4), (A / "session" / "000.mp3", 2.58), (nv("ipad2", N4 / "ipad2.mp3"), 3.8)], fade_out=0.4)

def fcard(no, title, sub, voice):
    num, ttl, sb, ln = feature_card_layers(no, title, sub)
    seg(kind="fcard", dur=max(2.9, dur_of(voice) + 1.5), layers=[(num, 0.3, "wipe"), (ln, 0.7, "wipe"), (ttl, 0.55, "up"), (sb, 0.9, "up")], voice=[(voice, 0.6)])

def clip(src, t_in, t_out, pnl, kids=(), extra=(), layers=(), teachers=None, who="ムニ先生", note_layer=True):
    """録画の一部。kids の子どもの発話（録画の時刻）で、声の長さだけ画面を止める"""
    ev = events(src) if (A / src / "events.json").exists() else []
    kid_ev = [e for e in ev if e["who"] == "kid" and t_in - 0.05 <= e["t"] < t_out and e["text"] in kids]
    freezes = []
    for e in kid_ev:
        ft = e["t"] - 0.05
        nxt = [x["t"] for x in ev if x["who"] == "teacher" and x["t"] > e["t"]]
        skip = max(0.0, min(nxt[0] - 0.5 - ft, t_out - ft - 0.5)) if nxt else 0.0  # 先生が考えている間は詰める
        freezes.append((ft, dur_of(e["file"]) + 0.35, skip, e))
    def mt(t):  # 録画の時刻 → クリップの時刻
        return t - t_in + sum(fd for ft, fd, sk, _ in freezes if ft <= t) - sum(min(sk, t - ft) for ft, fd, sk, _ in freezes if ft <= t)
    total = (t_out - t_in) + sum(fd - sk for _, fd, sk, _ in freezes)
    talk = Talk(IPAD_AREA); voice = []
    for ft, fd, sk, e in freezes:
        at = ft - t_in + sum(x - y for z, x, y, _ in freezes if z < ft) + 0.05
        talk.kid(at, e["text"], e["file"]); voice.append((Path(e["file"]), at))
    for e in (ev if teachers is None else []):
        if e["who"] == "teacher" and t_in - 0.05 <= e["t"] and e["t"] + dur_of(e["file"]) <= t_out + 0.25:
            talk.teacher(mt(e["t"]), e["text"], dur_of(e["file"]), who); voice.append((Path(e["file"]), mt(e["t"])))
    for f, at, cut, text, spk in extra:
        talk.teacher(at - t_in, text, cut or dur_of(A / f), spk); voice.append((A / f, at - t_in, cut))
    lay = list(layers) + ([(NOTE, 0, None)] if note_layer else [])
    seg(kind="video", src=src, t_in=t_in, t_out=t_out, freezes=[(ft, fd, sk) for ft, fd, sk, _ in freezes], dur=total, panel=pnl,
        layers=lay, talk=talk, voice=voice)

# 01 声で話せる
fcard(1, "声で話せる", "画面に触らない。「ねえ先生」と話しかけるだけ", nv("f1", N4 / "f1.mp3"))
p1 = panel("p1", 1, "声で話せる", ["画面に触らず、話しかけるだけ", "わからない言葉も、その場で聞ける"])
clip("session", 32.5, 41.75, p1, kids=["ねえ先生、もとにする量ってなに？"])
# 02 黒板で教える
fcard(2, "黒板で教える", "話に合わせて、図を1つずつ書いていく", nv("f2", N4 / "f2.mp3"))
p2 = panel("p2", 2, "黒板で教える", ["話しながら、黒板に図を書く", "線分図で「もとにする量」を見せる"])
clip("session", 41.75, 47.7, p2)
mont = []
tiles = ["m0.png", "m1.png", "m2.png", "f_drawing_fish.png", "f_drawing_flower.png", "f_drawing_circuit.png"]
for i_, fn in enumerate(tiles):
    im = Image.open(V / "montage" / fn).convert("RGB"); im = im.crop((0, int(im.height * 0.105), im.width, int(im.height * 0.80)))
    im = im.resize((540, int(540 * im.height / im.width)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); x = 150 + (i_ % 3) * 570; y = 300 + (i_ // 3) * 390
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((x + 4, y + 12, x + im.width + 4, y + im.height + 12), 16, fill=(0, 0, 0, 60))
    lay = Image.alpha_composite(lay, sh.filter(ImageFilter.GaussianBlur(10))); lay.paste(im, (x, y))
    pth = L / f"mont{i_}.png"; lay.save(pth); mont.append((pth, 0.5 + i_ * 0.75, "up"))
WJ = NARR_DIR / "words.json"
if WJ.exists():
    ws = json.loads(WJ.read_text())["nm"]; txt = "".join(w["w"] for w in ws)
    def at_word(word):
        i0 = txt.find(word); n_ = 0
        for w in ws:
            if n_ >= i0: return w["t"]
            n_ += len(w["w"])
        return None
    for j_, word in enumerate(["数直線", "面積", "グラフ", "メダカ", "植物", "回路"]):
        t_ = at_word(word)
        if t_ is not None: mont[j_] = (mont[j_][0], round(0.3 + t_ - 0.15, 2), "up")
    print("montage at", [m_[1] for m_ in mont])
hm = text_layer("hm", [("決まった図も、自由な絵も", C.maru(52), C.INK + (255,), 150, 70, False),
                       ("決まった図：数直線・面積図・グラフ・線分図・ベン図・表 など11種類", C.jfont(6, 26), C.MUTED + (255,), 154, 150, False),
                       ("自由に描く：どんな形も、線と曲線で描ける（いちばん新しい機能）", C.jfont(6, 26), (46, 125, 106, 255), 154, 190, False)])
rowlab = text_layer("rowlab", [("決まった図", C.jfont(6, 26), (194, 140, 40, 255), 150, 258, False), ("自由に描く", C.jfont(6, 26), (46, 125, 106, 255), 150, 648, False)])
seg(kind="card", bg="paper", dur=round(dur_of(nv("nm", N4 / "nm.mp3")) + 0.9, 2), layers=[(hm, 0.1, "fade"), (rowlab, 0.4, "fade"), *mont], voice=[(nv("nm", N4 / "nm.mp3"), 0.3)])
# 03 答えは言わない。できたら、ほめる
fcard(3, "答えは言わない", "まちがえても次のヒント。できたら、いっしょに喜ぶ", nv("f3", N4 / "f3.mp3"))
p3 = panel("p3", 3, "答えは言わない。できたら、ほめる", ["「おしい、いいところまで来てるよ」", "最後のひと言は子どもが言う"])
clip("session", 75.2, 79.0, p3, kids=["ねえ先生、じゃあ10平方センチかな？"])
clip("session", 88.5, 92.1, p3, kids=["ねえ先生、わかった！24平方センチだ！"])
# 04 見守って、声をかける
fcard(4, "見守って、声をかける", "手が止まったら、先生のほうから「どこか考え中？」", nv("f4", N4 / "f4.mp3"))
p4 = panel("p4", 4, "見守って、声をかける", ["カメラで手の動きだけを見る（映像は送らず、保存もしない）", "止まったら、先生から声をかける", "「見て」でノートを読んでヒント"])
eye = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ed = ImageDraw.Draw(eye)
ed.rounded_rectangle((128, 108, 520, 152), 22, fill=(46, 125, 106, 240)); ed.text((146, 115), "← 見守り中（手の動きだけを見る）", font=C.jfont(6, 22), fill=(255, 255, 255))
eye_p = L / "eye_lbl.png"; eye.save(eye_p)
stop_lbl = caption("cap_stop", "手が止まって、しばらく…", (255, 226, 150), size=40, y=C.IPAD_Y + 150)
clip("watch", 21.0, 26.75, p4, kids=["うん、見て"], layers=[(stop_lbl, 0.1, 1.4), (eye_p, 0.2, None)])
mt_ = Talk(IPAD_AREA); mt_.teacher(1.9, "ここまで書けたね！30と0.4、どっちが「もとにする量」かな？", dur_of(N4 / "hint.mp3"))
seg(kind="mock", dur=7.3, panel=p4, talk=mt_, note=note("note_mock", "撮影からヒントまでは画面のイメージ（実機では「見て」でノートを撮って読む。Simulator にはカメラがないため）"),
    voice=[(N4 / "hint.mp3", 1.9)])
# 05 自分の先生を選べる
fcard(5, "自分の先生を選べる", "見た目も声も性格も違う8人", nv("f5", N4 / "f5.mp3"))
p5 = panel("p5", 5, "自分の先生を選べる", ["触ると、その先生の声で自己紹介", "選ぶと、次の勉強からその先生に"])
# リカの自己紹介は、長さに収めるため外した（8人の一覧は画面に映る）
clip("picker2", 19.4, 25.7, p5, extra=[("n4/boru_intro.mp3", 20.15, None, "ピピッと来たよ！ボルです。ほめ言葉を練習中で、合ってた？って聞いちゃうんだ。", "ボル先生")], note_layer=False)
# 06 なんでも話せる
fcard(6, "なんでも話せる", "好きな話にもつきあう。調べて、写真を見せる", nv("f6", N4 / "f6.mp3"))
p6 = panel("p6", 6, "なんでも話せる", ["わからないことは調べて確かめる", "本物の写真を黒板に出す"])
clip("research", 44.4, 51.6, p6, kids=["ねえ先生、オオカミってどんな見た目なの？写真見せて"])
# 07 親とつながる
fcard(7, "親とつながる", "伝言を先生が届ける。今夜の声かけが親に届く", nv("f7", N4 / "f7.mp3"))
def parent_note_card():
    """親が書いた伝言（ダッシュボードの「先生にことづける」から）"""
    w = C.PANEL_W; im = Image.new("RGBA", (w, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 290), 18, fill=(255, 255, 255, 255), outline=(214, 208, 196), width=2)
    d.text((22, 18), "親のダッシュボードから", font=C.jfont(6, 20), fill=(46, 125, 106))
    d.text((22, 50), "先生にことづける", font=C.jfont(6, 28), fill=C.INK)
    y = 100
    for line in C.wrap(d, "今日もがんばってるね。終わったら、いっしょにおやつ食べよう！", C.jfont(4, 26), w - 44):
        d.text((22, y), line, font=C.jfont(4, 26), fill=C.INK); y += 38
    d.text((22, 236), "お母さんから", font=C.jfont(3, 20), fill=C.MUTED)
    return im
p7 = panel("p7", 7, "親とつながる", ["親の伝言を、先生が勉強の始めに伝える"], image=parent_note_card())
clip("message", 11.7, 18.3, p7)
T_PRIV = max(4.5, 0.6 + dur_of(nv("n8", N4 / "n8.mp3")) + 0.4)  # 今夜の声かけを言い終えてから、プライバシーの話
seg(kind="dash", dur=T_PRIV + dur_of(nv("npriv2", N4 / "npriv.mp3")) + 1.2, t_priv=T_PRIV, voice=[(nv("n8", N4 / "n8.mp3"), 0.6), (nv("npriv2", N4 / "npriv.mp3"), T_PRIV)],
    panel=panel("p7b", 7, "親とつながる", ["今夜の声かけ", "自分で解けるようになってきた変化", "週のまとめ"]))
def privacy_layer():
    """プライバシー：先生が覚えていること（親が消せる）＋ 守っていること"""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(img).rectangle((590, 0, C.PANEL_X - 20, H), fill=(243, 241, 233, 255))
    mem = Image.open(V / "cards" / "mem.png").convert("RGBA"); mem = mem.resize((int(mem.width * 0.78), int(mem.height * 0.78)), Image.LANCZOS)
    x, y = 640, 120
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((x + 4, y + 10, x + mem.width + 4, y + mem.height + 10), 20, fill=(0, 0, 0, 50))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(12))); img.alpha_composite(mem, (x, y))
    d = ImageDraw.Draw(img); cy = y + mem.height + 30; cw = 700
    d.rounded_rectangle((x, cy, x + cw, cy + 250), 20, fill=C.BOARD)
    # 鍵の印
    lx, ly = x + 34, cy + 30
    d.rounded_rectangle((lx, ly + 22, lx + 44, ly + 58), 7, fill=(240, 200, 110)); d.arc((lx + 7, ly, lx + 37, ly + 40), 180, 360, fill=(240, 200, 110), width=6)
    d.text((x + 96, cy + 30), "子どものプライバシーを守る", font=C.maru(34), fill=(250, 248, 240))
    for k, t in enumerate(["写真と声は保存しない。残すのは文字だけ", "見守りのカメラ映像は、端末の外に出さない", "先生が覚えていることは、親が確かめて消せる"]):
        d.text((x + 40, cy + 98 + k * 46), "・" + t, font=C.jfont(4, 27), fill=(226, 236, 228))
    p = L / "privacy.png"; img.save(p); return p
priv_layer = privacy_layer()
# 長男の感想
q = [text_layer("q0", [("使ってみた長男（小5）の感想", C.jfont(6, 34), (240, 200, 110, 255), "c", 220, False)]),
     text_layer("q1", [("「励ましてくれるのが嬉しかった」", C.maru(60), (250, 248, 240, 255), "c", 360, False)]),
     text_layer("q2", [("「宇宙の話とかもできた」", C.maru(60), (250, 248, 240, 255), "c", 500, False)]),
     text_layer("q3", [("「ちょっと間違えることもあるけど、", C.maru(60), (250, 248, 240, 255), "c", 640, False),
                       ("それも可愛い」", C.maru(60), (250, 248, 240, 255), "c", 730, False)])]
seg(kind="card", bg="board", dur=7.2, layers=[(q[0], 0.2, "fade"), (q[1], 1.4, "up"), (q[2], 3.0, "up"), (q[3], 4.6, "up")], voice=[(nv("kidq", N4 / "kidq.mp3"), 0.2)])
# 締め
close_layer = text_layer("close", [("一人じゃない勉強を、どの家庭にも。", C.maru(46), (255, 236, 190, 255), "c", 130, False)])
T_CLOSE_B = 0.5 + dur_of(nv("close_a", N4 / "close.mp3")) + 0.7
seg(kind="logo", dur=T_CLOSE_B + dur_of(nv("logo", A / "logo.mp3")) + 1.0, name=name, bub=bub, tag=tag, card=card, lx=lx, lw=lw,
    voice=[(nv("close_a", N4 / "close.mp3"), 0.5), (nv("logo", A / "logo.mp3"), T_CLOSE_B)], end=True, close=close_layer)

# ---------- 書き出し ----------
def anim(base, k, t0, kind, t1=None, out_name=None):
    d = 0.45; o = out_name or f"o{k}"
    f = f"[{k}:v]format=rgba,fade=in:st={t0}:d={d}:alpha=1" + (f",fade=out:st={t1}:d=0.5:alpha=1" if t1 and t1 < 90 else "") + f"[l{k}]"
    if kind == "up":
        return f + f";[{base}][l{k}]overlay=x=0:y='if(lt(t,{t0}),40,if(lt(t,{t0 + d}),40*(1-(t-{t0})/{d}),0))'[{o}]"
    if kind == "slide":
        return f + f";[{base}][l{k}]overlay=x='if(lt(t,{t0 + d}),90*(1-clip((t-{t0})/{d},0,1)),0)':y=0[{o}]"
    return f + f";[{base}][l{k}]overlay=0:0[{o}]"

FINAL = os.environ.get("FINAL") == "1"  # YouTube に上げる完成版：高画質、音量 -14 LUFS
ENC = ["-c:v", "libx264", "-preset", "slow" if FINAL else "veryfast", "-crf", "16" if FINAL else "19", "-pix_fmt", "yuv420p", "-r", FPS,
       "-profile:v", "high", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-an"]
audio, files, Tg, audit = [], [], 0.0, []
ONLY = os.environ.get("ONLY")
for i, s in enumerate(segments):
    out = OUT / "seg" / f"{i:02d}.mp4"; d = s["dur"]
    # ナレーションや声が場面からはみ出さないか
    for v in s.get("voice", []):
        f, at = v[0], v[1]; cut = v[2] if len(v) > 2 else None
        dd = cut or dur_of(f)
        audit.append((i, s["kind"], Tg + at, Tg + at + dd, Tg + d, Path(f).name))
    if ONLY and str(i) not in ONLY.split(","):
        files.append(out); Tg += d
        for v in s.get("voice", []): audio.append((v[0], Tg - d + v[1], v[2] if len(v) > 2 else None))
        continue
    if s["kind"] == "frames":
        nfr = s["n"]; pad = d - nfr / FPS
        ins = ["-framerate", FPS, "-start_number", s["start"], "-i", FR / "f_%04d.png"]
        cr = s.get("crop"); crs = f",crop={cr[2]}:{cr[3]}:{cr[0]}:{cr[1]},scale={W}:{H}:flags=lanczos" if cr else ""
        fc, base = [f"[0:v]trim=end_frame={nfr}{crs},format=yuv420p,fps={FPS}" + (f",tpad=stop_mode=clone:stop_duration={pad:.3f}" if pad > 0.01 else "") + "[b0]"], "b0"
        k = 1
        for png, t0, t1 in s["layers"]:
            ins += ["-loop", "1", "-t", d, "-i", png]; fc.append(anim(base, k, t0, "fade", t1)); base = f"o{k}"; k += 1
        for j, an in enumerate(([s["talk"]] if s.get("talk") else []) + [a_ for a_, _ in s.get("anims", [])]):
            tp = OUT / "seg" / f"{i:02d}_anim{j}.mov"; render_talk(an, d, tp)
            ins += ["-i", tp]; fc.append(f"[{base}][{k}:v]overlay=0:0[o{k}]"); base = f"o{k}"; k += 1
        fc.append(f"[{base}]fade=in:st=0:d=0.4,fade=out:st={d - s.get('fade_out', 0.3)}:d={s.get('fade_out', 0.3)}[v]")
        run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-frames:v", int(round(d * FPS)), *ENC, out])
    elif s["kind"] == "logo":
        ins = ["-loop", "1", "-t", d, "-i", board_bg(), "-loop", "1", "-t", d, "-i", s["name"], "-loop", "1", "-t", d, "-i", s["bub"],
               "-loop", "1", "-t", d, "-i", s["tag"], "-loop", "1", "-t", d, "-i", s["card"]]
        x0, w = s["lx"], s["lw"]; t0 = 0.4 if not s.get("end") else 0.3; wd = 1.6
        if s.get("close"): ins += ["-loop", "1", "-t", d, "-i", s["close"]]
        fc = [f"[1:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(X,{x0}+({w}+40)*clip((T-{t0})/{wd},0,1)),alpha(X,Y),0)'[nm]",
              "[0:v][nm]overlay=0:0[a]", anim("a", 2, t0 + wd + 0.05, "up", out_name="b"), anim("b", 3, t0 + wd + 0.6, "up", out_name="c"),
              anim("c", 4, t0 + wd + 1.2, "up", out_name="e" if not s.get("close") else "e0")] + ([anim("e0", 5, 0.4, "fade", out_name="e")] if s.get("close") else []) + [f"[e]fade=in:st=0:d=0.3,fade=out:st={d - 0.5}:d=0.5[v]"]
        run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", d, *ENC, out])
    elif s["kind"] == "fcard":
        ins = ["-loop", "1", "-t", d, "-i", board_bg()]; fc, base = [], "0:v"
        for k, (png, t0, kind) in enumerate(s["layers"], start=1):
            ins += ["-loop", "1", "-t", d, "-i", png]
            if kind == "wipe":
                fc.append(f"[{k}:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(X,200+1500*clip((T-{t0})/0.5,0,1)),alpha(X,Y),0)'[l{k}];[{base}][l{k}]overlay=0:0[o{k}]")
            else:
                fc.append(anim(base, k, t0, kind))
            base = f"o{k}"
        fc.append(f"[{base}]fade=in:st=0:d=0.25,fade=out:st={d - 0.25}:d=0.25[v]")
        run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", d, *ENC, out])
    elif s["kind"] == "card":
        ins = (["-loop", "1", "-t", d, "-i", board_bg()] if s["bg"] == "board" else ["-f", "lavfi", "-i", f"color=c={BG_HEX}:s={W}x{H}:r={FPS}:d={d}"])
        fc, base = [], "0:v"
        for k, (png, t0, kind) in enumerate(s["layers"], start=1):
            ins += ["-loop", "1", "-t", d, "-i", png]; fc.append(anim(base, k, t0, kind)); base = f"o{k}"
        fc.append(f"[{base}]fade=in:st=0:d=0.3,fade=out:st={d - 0.3}:d=0.3[v]")
        run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", d, *ENC, out])
    elif s["kind"] == "video":
        src = V / "raw" / f"{s['src']}.mp4"
        bgc = "0xDCEAF8" if s["src"].startswith("picker") else "0xF5F0E4"
        hide = f"drawbox=x=0:y=0:w=1100:h=54:color={bgc}:t=fill,"
        if not s["src"].startswith("picker"):
            hide += "drawbox=x=2040:y=56:w=372:h=104:color=0xF5F0E4:t=fill,drawbox=x=800:y=1528:w=820:h=64:color=0xF5F0E4:t=fill,"
        pre = f"[0:v]fps={FPS},{hide}scale={C.IPAD_W}:{C.IPAD_H},setsar=1"
        # 子どもが話す間は止める：[再生][静止][再生]…をつなぐ
        pieces, cur = [], s["t_in"]
        for ft, fd, sk in s["freezes"]:
            pieces.append(("play", cur, ft)); pieces.append(("hold", ft, fd)); cur = ft + sk
        pieces.append(("play", cur, s["t_out"]))
        pieces = [p for p in pieces if not (p[0] == "play" and p[2] - p[1] < 0.02)]
        fc = [pre + f",split={len(pieces)}" + "".join(f"[s{j}]" for j in range(len(pieces)))]
        for j, (kind, a, b) in enumerate(pieces):
            if kind == "play":
                fc.append(f"[s{j}]trim=start={a - s['t_in']:.3f}:end={b - s['t_in']:.3f},setpts=PTS-STARTPTS[p{j}]")
            else:
                fc.append(f"[s{j}]trim=start={a - s['t_in']:.3f}:duration=0.04,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={b:.3f},trim=duration={b:.3f}[p{j}]")
        fc.append("".join(f"[p{j}]" for j in range(len(pieces))) + f"concat=n={len(pieces)}:v=1:a=0[ipad]")
        tp = OUT / "seg" / f"{i:02d}_talk.mov"; render_talk(s["talk"], d, tp)
        ins = ["-ss", s["t_in"], "-t", s["t_out"] - s["t_in"] + 0.1, "-i", src, "-loop", "1", "-t", d, "-i", V / "cards" / "bg.png",
               "-loop", "1", "-t", d, "-i", s["panel"]]
        fc += [f"[1:v][ipad]overlay={C.IPAD_X}:{C.IPAD_Y}:shortest=0[b0]", anim("b0", 2, 0.05, "slide", out_name="b1")]
        base, k = "b1", 3
        for png, t0, t1 in s["layers"]:
            ins += ["-loop", "1", "-t", d, "-i", png]; fc.append(anim(base, k, t0, "fade", t1)); base = f"o{k}"; k += 1
        ins += ["-i", tp]; fc.append(f"[{base}][{k}:v]overlay=0:0[o{k}]"); base = f"o{k}"
        fc.append(f"[{base}]fade=in:st=0:d=0.2:color={BG_HEX}[v]")
        run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-frames:v", int(round(d * FPS)), *ENC, out])
    elif s["kind"] == "mock":
        from mock import mock_frame
        ba = Image.open(V / "cards" / "mock_a.png").convert("RGBA"); bb = Image.open(V / "cards" / "mock_b.png").convert("RGBA"); eye_ = ba.crop((0, 0, 120, 110))
        bgimg = Image.open(V / "cards" / "bg.png").convert("RGBA"); pn = Image.open(s["panel"]).convert("RGBA"); nt_ = Image.open(s["note"]).convert("RGBA")
        pr = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", *[str(x) for x in ENC], str(out)], stdin=subprocess.PIPE)
        for fi in range(int(round(d * FPS))):
            tt = fi / FPS; fr = bgimg.copy()
            scr = mock_frame(tt, ba, bb, eye_).resize((C.IPAD_W, C.IPAD_H)); fr.alpha_composite(scr, (C.IPAD_X, C.IPAD_Y))
            fr.alpha_composite(pn); fr.alpha_composite(nt_); fr.alpha_composite(s["talk"].frame(tt))
            pr.stdin.write(fr.tobytes())
        pr.stdin.close(); pr.wait()
    elif s["kind"] == "dash":
        ins = ["-f", "lavfi", "-i", f"color=c={BG_HEX}:s={W}x{H}:r={FPS}:d={d}", "-loop", "1", "-t", d, "-i", V / "cards" / "s8_phone_v2.png",
               "-loop", "1", "-t", d, "-i", V / "cards" / "s8_frame.png", "-loop", "1", "-t", d, "-i", s["panel"],
               "-loop", "1", "-t", d, "-i", priv_layer, "-loop", "1", "-t", d, "-i", note("note_dash", "画面は見本のデータ")]
        fc = ["[0:v][1:v]overlay=120:'110-min(109,max(0,t-1.5)*14)'[a]", "[2:v]format=rgba,fade=in:st=0:d=0.5:alpha=1[fr]",
              "[a][fr]overlay=x='if(lt(t,0.5),-60*(1-t/0.5),0)':y=0[b]", anim("b", 3, 0.2, "slide", out_name="c"),
              anim("c", 4, s.get("t_priv", 4.5) - 0.1, "fade", out_name="c2"), f"[c2][5:v]overlay=0:0,fade=in:st=0:d=0.3:color={BG_HEX}[v]"]
        run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", d, *ENC, out])
    for v in s.get("voice", []):
        audio.append((v[0], Tg + v[1], v[2] if len(v) > 2 else None))
    files.append(out)
    print(f"{i:02d} {Tg:6.2f}-{Tg + d:6.2f} {s['kind']} {s.get('src', '')}", flush=True)
    Tg += d
total = Tg

# 監査表：はみ出し・重なり
lines = [f"total {total:.2f}s"]
prev_end = -1
for (i, kind, a, b, segend, nm) in sorted(audit, key=lambda x: x[2]):
    flag = []
    if b > segend - 0.1: flag.append("はみ出し")
    if a < prev_end - 0.05: flag.append("重なり")
    lines.append(f"{i:02d} {kind:6s} {a:7.2f}-{b:7.2f} (場面の終わり {segend:7.2f}) {nm} {' '.join(flag)}")
    prev_end = max(prev_end, b)
(OUT / "audit.txt").write_text("\n".join(lines)); print("\n".join(l for l in lines if "はみ出し" in l or "重なり" in l) or "audit ok")
if ONLY: raise SystemExit(0)
(OUT / "concat.txt").write_text("".join(f"file '{f}'\n" for f in files))
run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", OUT / "concat.txt", "-c", "copy", OUT / "video.mp4"])
starts = []; acc = 0.0
for s_ in segments: starts.append((acc, s_)); acc += s_["dur"]
t_feat = next(a_ for a_, s_ in starts if s_["kind"] == "fcard")
t_feed = next(a_ for a_, s_ in starts if s_["kind"] == "card" and s_.get("bg") == "board")
t_end = [a_ for a_, s_ in starts if s_["kind"] == "logo"][-1]
subprocess.run([str(V / ".venv/bin/python"), str(V / "bgm2.py"), f"{total:.3f}", str(A / "bgm4.wav"), "22.0", f"{t_feat:.2f}", f"{t_feed:.2f}", f"{t_end:.2f}"], check=True, capture_output=True)
MUTE = [T["PAUSE"] - 0.6, 22.2]
inputs, parts = ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"], []
for k, (f, at, cut) in enumerate(audio, start=1):
    inputs += ["-i", str(f)]; ms = max(0, int(at * 1000))
    trim = f"atrim=0:{cut},afade=t=out:st={cut - 0.25}:d=0.25," if cut else ""
    parts.append(f"[{k}:a]{trim}aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{k}]")
b = len(audio) + 1; inputs += ["-i", str(A / "bgm4.wav")]
mix = ";".join(parts) + ";[0:a]" + "".join(f"[a{k}]" for k in range(1, b)) + \
      f"amix=inputs={b}:normalize=0:duration=first,asplit[voice][key];" + \
      f"[{b}:a]volume='0.22*max(clip(({MUTE[0]}-t)/0.6,0,1),clip((t-{MUTE[1]})/0.8,0,1))':eval=frame[bg];[bg][key]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[duck];" + \
      "[voice][duck]amix=inputs=2:normalize=0:duration=first,loudnorm=I=" + ("-14" if FINAL else "-16") + ":TP=-1.0:LRA=11,aresample=48000[out]"
run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", mix, "-map", "[out]", "-c:a", "aac", "-b:a", "320k" if FINAL else "160k", "-ar", "48000", OUT / "audio.m4a"])
run(["ffmpeg", "-y", "-v", "error", "-i", OUT / "video.mp4", "-i", OUT / "audio.m4a", "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", OUT / "chalktalk_promo.mp4"])
print(f"total {total:.1f}s, audio clips {len(audio)} -> {OUT / 'chalktalk_promo.mp4'}")
