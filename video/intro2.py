"""導入（27秒）の第2版：絵の品質を上げ、課題を具体的にし、「そばにいたら」のあとに間を置いて「だから、作りました」につなぐ。

絵はすべて Pillow で描く（2倍で描いて縮め、線をなめらかにする）。動きは ffmpeg で重ねる。
使い方: .venv/bin/python intro2.py → out2/seg_intro.mp4（音なし）と out2/intro_voice.json
"""
import json, math, random, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops

V = Path(__file__).parent
sys.argv = [sys.argv[0], str(V / "cards")]
import cards as C  # noqa: E402

W, H, FPS, DUR = 1920, 1080, 30, 27.0
S = 2  # 2 倍で描く
L = V / "out2" / "intro2"; L.mkdir(parents=True, exist_ok=True)

# 時刻（秒）
T_PARENT, T_Q, T_FAST, T_IF, T_PAUSE, T_SO, T_ON = 5.6, 11.0, 13.6, 16.9, 20.4, 22.3, 24.2

def canvas(): return Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
def P(*xy): return [v * S for v in xy]
def done(img, name, blur_px=0):
    img = img.resize((W, H), Image.LANCZOS)
    if blur_px: img = img.filter(ImageFilter.GaussianBlur(blur_px))
    p = L / f"{name}.png"; img.save(p); return p
def glow(img, r): return img.filter(ImageFilter.GaussianBlur(r * S))

def bezier(pts, n=24):
    """[(x,y), ...] を 3 次ベジェの連続（p0, c1, c2, p1, c1, c2, p2 ...）として点列に"""
    out = []
    for i in range(0, len(pts) - 1, 3):
        p0, p1, p2, p3 = pts[i:i + 4]
        for k in range(n):
            t = k / n
            x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
            y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]
            out.append((x * S, y * S))
    out.append((pts[-1][0] * S, pts[-1][1] * S))
    return out

def vgrad(d, box, top, bottom):
    x0, y0, x1, y1 = box
    for y in range(int(y0 * S), int(y1 * S)):
        a = (y - y0 * S) / max(1, (y1 - y0) * S)
        d.line((x0 * S, y, x1 * S, y), fill=tuple(int(top[i] + (bottom[i] - top[i]) * a) for i in range(len(top))))

# 色
WALL_T, WALL_B = (46, 50, 68), (30, 33, 46)
SIL, SIL2 = (13, 15, 22), (24, 27, 38)
WARM, COOL = (255, 190, 115), (150, 195, 255)
WOOD, WOOD_D, WOOD_L = (104, 72, 50), (78, 53, 37), (138, 98, 68)

# 配置
WX0, WY0, WX1, WY1 = 300, 130, 700, 500       # 窓
IX0, IY0, IX1, IY1 = 960, 410, 1450, 748       # iPad
SX0, SY0, SX1, SY1 = IX0 + 18, IY0 + 18, IX1 - 18, IY1 - 18
DESK_Y = 752

# ---------- 空 ----------
def sky(night):
    img = canvas(); d = ImageDraw.Draw(img)
    if night:
        vgrad(d, (WX0, WY0, WX1, WY1), (14, 20, 52, 255), (58, 50, 98, 255))
        r = random.Random(7); stars = canvas(); d0 = d; d = ImageDraw.Draw(stars)
        for _ in range(70):
            x, y = r.uniform(WX0 + 8, WX1 - 8), r.uniform(WY0 + 8, WY0 + 230); s = r.choice([1.2, 1.6, 2.4])
            d.ellipse(P(x - s, y - s, x + s, y + s), fill=(255, 250, 230, r.randint(150, 255)))
        img = Image.alpha_composite(img, stars); d = ImageDraw.Draw(img)
        g = canvas(); ImageDraw.Draw(g).ellipse(P(560, 160, 680, 280), fill=(255, 240, 200, 90)); img = Image.alpha_composite(img, glow(g, 18))
        d = ImageDraw.Draw(img); d.ellipse(P(595, 195, 645, 245), fill=(252, 244, 214, 255))
        d.ellipse(P(606, 208, 618, 220), fill=(232, 222, 190, 255)); d.ellipse(P(624, 222, 632, 230), fill=(232, 222, 190, 255))
    else:
        vgrad(d, (WX0, WY0, WX1, WY1), (250, 170, 110, 255), (140, 92, 140, 255))
        g = canvas(); ImageDraw.Draw(g).ellipse(P(380, 330, 560, 510), fill=(255, 220, 150, 200)); img = Image.alpha_composite(img, glow(g, 30))
        c = canvas(); cd = ImageDraw.Draw(c)
        for x, y, w in [(330, 190, 160), (470, 230, 200), (560, 170, 140)]:
            cd.ellipse(P(x, y, x + w, y + 34), fill=(255, 210, 190, 150))
        img = Image.alpha_composite(img, glow(c, 6))
    d = ImageDraw.Draw(img)
    # 遠い山と街並み
    d.polygon([(x * S, y * S) for x, y in [(WX0, 440), (380, 400), (450, 425), (540, 385), (630, 420), (WX1, 400), (WX1, WY1), (WX0, WY1)]],
              fill=(60, 52, 90, 255) if night else (150, 100, 130, 255))
    r = random.Random(3)
    x = WX0
    while x < WX1:
        w, h = r.randint(36, 70), r.randint(40, 120)
        d.rectangle(P(x, WY1 - h, x + w, WY1), fill=(26, 28, 44, 255) if night else (70, 50, 70, 255))
        if night:
            for yy in range(WY1 - h + 10, WY1 - 8, 16):
                for xx in range(x + 6, x + w - 8, 12):
                    if r.random() < 0.45:
                        d.rectangle(P(xx, yy, xx + 6, yy + 8), fill=r.choice([(255, 214, 130, 255), (255, 236, 190, 255), (180, 210, 255, 255)]))
        x += w + r.randint(0, 6)
    m = Image.new("L", img.size, 0); ImageDraw.Draw(m).rectangle(P(WX0, WY0, WX1, WY1), fill=255)
    out = canvas(); out.paste(img, (0, 0), m)
    return out

# ---------- 部屋 ----------
def room():
    img = canvas(); d = ImageDraw.Draw(img)
    vgrad(d, (0, 0, W, DESK_Y), WALL_T + (255,), WALL_B + (255,))
    # 窓（穴）・枠・窓台
    d.rectangle(P(WX0, WY0, WX1, WY1), fill=(0, 0, 0, 0))
    d.rectangle(P(WX0 - 18, WY0 - 18, WX1 + 18, WY1 + 18), outline=(92, 78, 70, 255), width=18 * S)
    d.rectangle(P(WX0 - 6, WY0 - 6, WX1 + 6, WY1 + 6), outline=(60, 50, 46, 255), width=6 * S)
    d.line(P((WX0 + WX1) / 2, WY0, (WX0 + WX1) / 2, WY1), fill=(92, 78, 70, 255), width=10 * S)
    d.line(P(WX0, (WY0 + WY1) / 2, WX1, (WY0 + WY1) / 2), fill=(92, 78, 70, 255), width=10 * S)
    d.rectangle(P(WX0 - 40, WY1 + 18, WX1 + 40, WY1 + 34), fill=(110, 94, 84, 255))
    # 窓台の鉢植え
    d.polygon([(x * S, y * S) for x, y in [(640, WY1 + 18), (676, WY1 + 18), (670, WY1 - 18), (646, WY1 - 18)]], fill=(150, 90, 60, 255))
    for a in (-0.9, -0.4, 0.1, 0.6):
        d.ellipse(P(658 + 34 * math.sin(a) - 12, WY1 - 50 - 20 * math.cos(a), 658 + 34 * math.sin(a) + 12, WY1 - 18 - 20 * math.cos(a)), fill=(70, 110, 80, 255))
    # カーテン（ひだのグラデーション）
    for x0, x1 in ((WX0 - 120, WX0 - 10), (WX1 + 10, WX1 + 120)):
        for k in range(int((x1 - x0) / 10)):
            shade = 0.75 + 0.25 * math.sin(k * 1.3)
            d.rectangle(P(x0 + k * 10, WY0 - 50, x0 + k * 10 + 10, WY1 + 70), fill=(int(120 * shade), int(70 * shade), int(76 * shade), 255))
        d.rectangle(P(x0 - 6, WY0 - 62, x1 + 6, WY0 - 50), fill=(70, 60, 56, 255))
    # 本棚（右の壁）
    bx0, by0 = 780, 150
    d.rectangle(P(bx0, by0, bx0 + 300, by0 + 230), fill=(70, 52, 40, 255))
    r = random.Random(11)
    for row in range(2):
        y1 = by0 + 108 + row * 112; d.rectangle(P(bx0, y1, bx0 + 300, y1 + 10), fill=(96, 72, 54, 255))
        x = bx0 + 10
        while x < bx0 + 280:
            w, h = r.randint(14, 26), r.randint(70, 96)
            col = r.choice([(150, 70, 60), (60, 100, 130), (200, 160, 80), (90, 120, 90), (120, 90, 140), (200, 200, 190)])
            if r.random() < 0.1:
                d.polygon([(x * S, y1 * S), ((x + h * 0.4) * S, (y1 - h) * S), ((x + h * 0.4 + w) * S, (y1 - h + 6) * S), ((x + w) * S, y1 * S)], fill=tuple(int(c * 0.7) for c in col) + (255,)); x += w + int(h * 0.4)
            else:
                d.rectangle(P(x, y1 - h, x + w, y1), fill=tuple(int(c * 0.7) for c in col) + (255,)); x += w + 2
    # 奥の部屋の戸口
    d.rectangle(P(1590, 240, 1866, DESK_Y), fill=(70, 60, 54, 255))
    d.rectangle(P(1606, 256, 1850, DESK_Y), fill=(52, 48, 50, 255))
    # 机（木目と手前の縁）
    vgrad(d, (0, DESK_Y, W, H), WOOD + (255,), WOOD_D + (255,))
    r = random.Random(5); grain = canvas(); gd = ImageDraw.Draw(grain)
    for _ in range(26):
        y = r.uniform(DESK_Y + 20, H); x = r.uniform(-200, W)
        gd.line(P(x, y, x + r.uniform(300, 700), y + r.uniform(-4, 4)), fill=(255, 220, 180, 22), width=2 * S)
    img = Image.alpha_composite(img, grain); d = ImageDraw.Draw(img)
    d.rectangle(P(0, DESK_Y, W, DESK_Y + 12), fill=WOOD_L + (255,))
    # 机の上：参考書の山、鉛筆立て、消しゴム、ノート
    d.rounded_rectangle(P(1480, DESK_Y - 70, 1536, DESK_Y + 30), 8 * S, fill=(90, 120, 110, 255))
    for k, col in enumerate([(240, 190, 60), (220, 80, 70), (80, 140, 220)]):
        d.line(P(1490 + k * 16, DESK_Y - 70, 1482 + k * 22, DESK_Y - 150 + k * 12), fill=col + (255,), width=8 * S)
    # ノート（開いたページと書きかけの式）
    d.polygon([(x * S, y * S) for x, y in [(380, 870), (760, 850), (800, 1040), (390, 1075)]], fill=(238, 234, 222, 255))
    d.line(P(580, 860, 595, 1058), fill=(200, 196, 186, 255), width=3 * S)
    for k in range(6):
        y = 892 + k * 28; d.line(P(400, y + 3, 575, y - 2), fill=(176, 186, 206, 255), width=2 * S); d.line(P(600, y - 3, 775, y - 9), fill=(176, 186, 206, 255), width=2 * S)
    f = C.jfont(4, 22 * S)
    d.text(P(410, 880), "12 ÷ 0.4 =", font=f, fill=(60, 60, 70, 255))
    d.text(P(410, 936), "40% → 12人", font=f, fill=(60, 60, 70, 255))
    d.text(P(620, 870), "？", font=C.jfont(6, 30 * S), fill=(200, 80, 70, 255))
    d.ellipse(P(820, 1000, 870, 1030), fill=(236, 236, 236, 255)); d.rectangle(P(820, 1006, 846, 1024), fill=(80, 120, 200, 255))
    return img

def lamp():
    img = canvas(); d = ImageDraw.Draw(img)
    d.polygon([(x * S, y * S) for x, y in [(90, 560), (230, 560), (820, H), (-260, H)]], fill=WARM + (60,))
    img = glow(img, 46)
    pool = canvas(); ImageDraw.Draw(pool).ellipse(P(60, 820, 900, 1120), fill=WARM + (70,)); img = Image.alpha_composite(img, glow(pool, 60))
    d = ImageDraw.Draw(img)
    metal = (66, 66, 74, 255)
    d.ellipse(P(10, 738, 130, 770), fill=metal)
    d.line(P(70, 752, 46, 610), fill=metal, width=12 * S); d.ellipse(P(36, 600, 58, 622), fill=metal)
    d.line(P(46, 610, 150, 520), fill=metal, width=12 * S); d.ellipse(P(140, 510, 162, 532), fill=metal)
    d.polygon([(x * S, y * S) for x, y in [(120, 470), (200, 462), (250, 560), (70, 572)]], fill=(214, 116, 70, 255))
    d.polygon([(x * S, y * S) for x, y in [(120, 470), (200, 462), (210, 482), (114, 490)]], fill=(236, 150, 100, 255))
    b = canvas(); ImageDraw.Draw(b).ellipse(P(90, 540, 230, 600), fill=(255, 240, 200, 255)); img = Image.alpha_composite(img, glow(b, 8))
    return img

def clock():
    img = canvas(); d = ImageDraw.Draw(img); cx, cy, r = 1360, 230, 84
    sh = canvas(); ImageDraw.Draw(sh).ellipse(P(cx - r - 6, cy - r + 4, cx + r + 14, cy + r + 18), fill=(0, 0, 0, 90)); img = Image.alpha_composite(img, glow(sh, 6))
    d = ImageDraw.Draw(img)
    d.ellipse(P(cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10), fill=(120, 86, 60, 255))
    d.ellipse(P(cx - r, cy - r, cx + r, cy + r), fill=(240, 234, 218, 255))
    for k in range(60):
        a = k * math.pi / 30; L0 = r - (14 if k % 5 == 0 else 7)
        d.line(P(cx + L0 * math.sin(a), cy - L0 * math.cos(a), cx + (r - 4) * math.sin(a), cy - (r - 4) * math.cos(a)), fill=(60, 60, 66, 255), width=(4 if k % 5 == 0 else 1) * S)
    a = math.radians(5.5 * 30)
    d.line(P(cx, cy, cx + 44 * math.sin(a), cy - 44 * math.cos(a)), fill=(40, 40, 46, 255), width=8 * S)
    return img

def minute_hand():
    img = Image.new("RGBA", (360, 360), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.line((180, 180, 180, 180 - 140), fill=(40, 40, 46, 255), width=8); d.ellipse((168, 168, 192, 192), fill=(200, 80, 60, 255))
    img = img.resize((180, 180), Image.LANCZOS); p = L / "minute.png"; img.save(p); return p

def parent():
    """奥の部屋：パソコンに向かう親の横顔（左向き）と、マグの湯気"""
    img = canvas(); d = ImageDraw.Draw(img)
    d.rectangle(P(1606, 256, 1850, DESK_Y), fill=(150, 126, 100, 110))
    lg = canvas(); ImageDraw.Draw(lg).ellipse(P(1560, 520, 1720, 690), fill=COOL + (110,)); img = Image.alpha_composite(img, glow(lg, 24))
    d = ImageDraw.Draw(img)
    d.rectangle(P(1606, 676, 1850, 690), fill=(54, 42, 36, 255))                     # 机
    d.rectangle(P(1800, 560, 1812, 760), fill=SIL2 + (255,))                          # 椅子の背
    body = bezier([(1752, 556), (1790, 560), (1806, 600), (1800, 676), (1790, 700), (1740, 700), (1712, 676),
                   (1700, 640), (1712, 590), (1752, 556)])
    d.polygon(body, fill=SIL + (255,))
    d.polygon(bezier([(1730, 600), (1700, 620), (1676, 650), (1650, 672), (1660, 680), (1690, 664), (1716, 640)]) + [(1736 * S, 610 * S)], fill=SIL + (255,))  # 腕
    d.ellipse(P(1722, 480, 1788, 552), fill=SIL + (255,))                             # 頭
    d.polygon(bezier([(1726, 506), (1716, 512), (1714, 520), (1722, 526)]), fill=SIL + (255,))  # 鼻
    d.ellipse(P(1772, 486, 1806, 520), fill=SIL + (255,))                             # まとめた髪
    d.polygon([(1650 * S, 676 * S), (1600 * S, 676 * S), (1596 * S, 682 * S), (1656 * S, 682 * S)], fill=(80, 84, 96, 255))  # キーボード
    d.polygon([(1608 * S, 676 * S), (1620 * S, 600 * S), (1628 * S, 600 * S), (1618 * S, 676 * S)], fill=(205, 228, 255, 255))  # 画面（横から）
    rim = canvas(); ImageDraw.Draw(rim).ellipse(P(1718, 482, 1740, 548), fill=COOL + (160,)); img = Image.alpha_composite(img, glow(rim, 3))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(P(1776, 650, 1800, 676), 4 * S, fill=(200, 200, 196, 255)); d.arc(P(1794, 654, 1808, 668), 270, 90, fill=(200, 200, 196, 255), width=3 * S)
    st = canvas(); sd = ImageDraw.Draw(st)
    for k in range(2):
        sd.line(bezier([(1784 + k * 8, 646), (1778 + k * 8, 630), (1792 + k * 8, 620), (1786 + k * 8, 602)]), fill=(255, 255, 255, 90), width=2 * S)
    img = Image.alpha_composite(img, st)
    return img

def child_shape():
    """机に向かう子どもの後ろ姿（パーカー、はねた髪、机に置いたひじ）"""
    m = Image.new("L", (W * S, H * S), 0); d = ImageDraw.Draw(m)
    # 体（肩から下）
    d.polygon(bezier([(420, H + 10), (430, 990), (500, 920), (620, 900), (680, 892), (840, 892), (900, 900),
                      (1010, 916), (1080, 980), (1100, H + 10)]), fill=255)
    # 左のひじ（机に置いている）
    d.polygon(bezier([(470, 960), (420, 960), (380, 990), (390, 1030), (420, 1050), (500, 1040), (520, 1010)]), fill=255)
    # フード（首の後ろのふくらみ）
    d.polygon(bezier([(640, 900), (650, 850), (870, 850), (880, 900)]), fill=255)
    # 首と頭（少し右に傾ける）
    d.rounded_rectangle(P(705, 820, 815, 900), 30 * S, fill=255)
    d.ellipse(P(624, 590, 900, 860), fill=255)
    d.ellipse(P(604, 712, 646, 784), fill=255); d.ellipse(P(878, 704, 920, 776), fill=255)
    r = random.Random(4)
    for k in range(30):  # 髪のはね
        a = math.radians(-172 + k * (164 / 29)); cx, cy = 762, 725
        bx, by = cx + 128 * math.cos(a), cy + 128 * math.sin(a)
        L1 = r.uniform(26, 62) * (1.0 if -150 < math.degrees(a) < -30 else 0.6); w = r.uniform(12, 22)
        tip = (bx + (L1) * math.cos(a + r.uniform(-0.3, 0.3)), by + L1 * math.sin(a + r.uniform(-0.3, 0.3)))
        nx, ny = -math.sin(a) * w, math.cos(a) * w
        d.polygon([((bx - nx) * S, (by - ny) * S), (tip[0] * S, tip[1] * S), ((bx + nx) * S, (by + ny) * S)], fill=255)
    return m

def child(rim_color, side, strength):
    m = child_shape()
    base = canvas(); base.paste(Image.new("RGBA", base.size, SIL + (255,)), (0, 0), m)
    # 内側の陰影（フードの線と服のしわ）
    d = ImageDraw.Draw(base)
    d.line(bezier([(640, 900), (700, 930), (820, 930), (880, 900)]), fill=SIL2 + (255,), width=4 * S)
    d.line(bezier([(560, 1000), (600, 1040), (640, 1060), (660, H)]), fill=SIL2 + (255,), width=3 * S)
    d.line(bezier([(960, 990), (930, 1030), (900, 1060), (890, H)]), fill=SIL2 + (255,), width=3 * S)
    # 縁の光（片側にずらした差分）
    dx = -9 * S if side == "left" else 9 * S
    shifted = ImageChops.offset(m, dx, -4 * S)
    edge = ImageChops.subtract(m, shifted)
    rim = Image.new("RGBA", base.size, rim_color + (0,)); rim.putalpha(edge.point(lambda v: int(v * strength)))
    out = Image.alpha_composite(base, glow(rim, 1.2))
    return out

def ipad(lit):
    img = canvas(); d = ImageDraw.Draw(img)
    if lit:
        g = canvas(); ImageDraw.Draw(g).rounded_rectangle(P(IX0 - 70, IY0 - 70, IX1 + 70, IY1 + 70), 90 * S, fill=COOL + (120,)); img = glow(g, 50)
        pool = canvas(); ImageDraw.Draw(pool).ellipse(P(IX0 - 120, DESK_Y - 30, IX1 + 120, DESK_Y + 120), fill=COOL + (70,)); img = Image.alpha_composite(img, glow(pool, 40))
        d = ImageDraw.Draw(img)
    sh = canvas(); ImageDraw.Draw(sh).ellipse(P(IX0 + 40, DESK_Y - 8, IX1 - 40, DESK_Y + 22), fill=(0, 0, 0, 120)); img = Image.alpha_composite(img, glow(sh, 8)); d = ImageDraw.Draw(img)
    d.polygon([(x * S, y * S) for x, y in [(1150, DESK_Y + 2), (1260, DESK_Y + 2), (1240, 700), (1170, 700)]], fill=(54, 56, 62, 255))
    d.rounded_rectangle(P(IX0, IY0, IX1, IY1), 28 * S, fill=(22, 24, 28, 255))
    d.rounded_rectangle(P(IX0 + 2, IY0 + 2, IX1 - 2, IY1 - 2), 26 * S, outline=(70, 72, 80, 255), width=2 * S)
    if lit:
        d.rounded_rectangle(P(SX0, SY0, SX1, SY1), 12 * S, fill=(0, 0, 0, 0))
    else:
        d.rounded_rectangle(P(SX0, SY0, SX1, SY1), 12 * S, fill=(9, 10, 14, 255))
        ref = canvas(); ImageDraw.Draw(ref).polygon([(x * S, y * S) for x, y in [(SX0 + 30, SY0), (SX0 + 140, SY0), (SX0 + 40, SY1), (SX0 - 70, SY1)]], fill=(255, 255, 255, 10))
        m = Image.new("L", img.size, 0); ImageDraw.Draw(m).rounded_rectangle(P(SX0, SY0, SX1, SY1), 12 * S, fill=255)
        ref.putalpha(ImageChops.multiply(ref.getchannel("A"), m)); img = Image.alpha_composite(img, ref)
    return img

def thought():
    img = canvas(); d = ImageDraw.Draw(img)
    sh = canvas(); sd = ImageDraw.Draw(sh)
    for box in [(540, 400, 720, 540), (600, 548, 636, 580), (576, 590, 596, 610)]:
        sd.ellipse(P(box[0] + 4, box[1] + 8, box[2] + 4, box[3] + 8), fill=(0, 0, 0, 80))
    img = Image.alpha_composite(img, glow(sh, 6)); d = ImageDraw.Draw(img)
    for box in [(540, 400, 720, 540), (600, 548, 636, 580), (576, 590, 596, 610)]:
        d.ellipse(P(*box), fill=(252, 250, 244, 255))
    d.text(P(592, 400), "？", font=C.maru(110 * S), fill=(206, 80, 62, 255))
    return img

def caption(name, s, color=(250, 246, 236), size=52):
    img = canvas(); d = ImageDraw.Draw(img); f = C.maru(size * S)
    w = d.textlength(s, font=f) / S; x = (W - w) / 2; y = 54
    pad = canvas(); ImageDraw.Draw(pad).rounded_rectangle(P(x - 44, y - 20, x + w + 44, y + size + 30), 22 * S, fill=(8, 10, 16, 165))
    img = Image.alpha_composite(img, glow(pad, 2)); d = ImageDraw.Draw(img)
    d.text(P(x, y), s, font=f, fill=color + (255,))
    return done(img, name)

def big(name, s, color):
    img = canvas(); d = ImageDraw.Draw(img); f = C.maru(84 * S)
    w = d.textlength(s, font=f) / S
    g = canvas(); ImageDraw.Draw(g).text(P((W - w) / 2, 200), s, font=f, fill=color + (200,)); img = Image.alpha_composite(img, glow(g, 14))
    d = ImageDraw.Draw(img); d.text(P((W - w) / 2, 200), s, font=f, fill=(255, 250, 238, 255))
    return done(img, name)

def vignette(strength):
    m = Image.new("L", (W // 4, H // 4), 0); d = ImageDraw.Draw(m)
    d.ellipse((-W // 16, -H // 10, W // 4 + W // 16, H // 4 + H // 10), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(40)).resize((W, H), Image.LANCZOS)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); img.putalpha(m.point(lambda v: int((255 - v) * strength)))
    p = L / f"vig{int(strength * 100)}.png"; img.save(p); return p

layers = {
    "dusk": done(sky(False), "dusk"), "night": done(sky(True), "night"), "room": done(room(), "room"),
    "lamp": done(lamp(), "lamp"), "clock": done(clock(), "clock"), "parent": done(parent(), "parent"),
    "ipad_off": done(ipad(False), "ipad_off"), "ipad_on": done(ipad(True), "ipad_on"),
    "child": done(child(WARM, "left", 0.9), "child"), "child_cool": done(child(COOL, "right", 0.9), "child_cool"),
    "q": done(thought(), "q"),
    "c1": caption("c1", "小5の長男。中学受検の勉強中。"),
    "c2": caption("c2", "親は、まだ仕事。"),
    "c3": caption("c3", "わからない問題で、手が止まる。"),
    "c3b": caption("c3b", "聞ける人はいない。時間だけが過ぎていく。"),
    "c4": caption("c4", "もし、話しかけられる先生が、そばにいたら。", (255, 226, 150)),
    "c5": caption("c5", "だから、作りました。", (255, 214, 130), size=72),
    "vig": vignette(0.55), "vig_dark": vignette(0.95),
}
hand = minute_hand()

# ---------- ffmpeg ----------
names = ["dusk", "night", "room", "lamp", "clock", "parent", "ipad_off", "ipad_on", "child", "child_cool", "q",
         "c1", "c2", "c3", "c3b", "c4", "c5", "vig", "vig_dark"]
idx = {n: i + 1 for i, n in enumerate(names)}
ins = ["-f", "lavfi", "-i", f"color=c=0x000000:s={W}x{H}:r={FPS}:d={DUR}"]
for n in names:
    ins += ["-loop", "1", "-t", f"{DUR}", "-i", str(layers[n])]
k_hand = len(names) + 1; ins += ["-loop", "1", "-t", f"{DUR}", "-i", str(hand)]
k_scr = k_hand + 1; ins += ["-ss", "4.6", "-t", f"{DUR - T_ON + 0.5}", "-i", str(V / "raw" / "session.mp4")]

def fio(n, st, d=0.6, out=None, od=0.5):
    s = f"[{idx[n]}:v]format=rgba,fade=in:st={st}:d={d}:alpha=1"
    if out is not None: s += f",fade=out:st={out}:d={od}:alpha=1"
    return s + f"[{n}]"

sw, sh = SX1 - SX0, SY1 - SY0
# 分針：ふだんはゆっくり、T_FAST から 3 秒で 1 周（時間が過ぎていく）
ang = f"PI+t*0.12+if(gt(t,{T_FAST}),min(t-{T_FAST},2.8)*2.2,0)"
fc = [
    f"[0:v][{idx['dusk']}:v]overlay=0:0[s0]", fio("night", 3.5, 5.0), "[s0][night]overlay=0:0[s1]",
    f"[s1][{idx['room']}:v]overlay=0:0[s2]", f"[s2][{idx['lamp']}:v]overlay=0:0[s3]", f"[s3][{idx['clock']}:v]overlay=0:0[s4]",
    f"[{k_hand}:v]format=rgba,rotate=a='{ang}':c=none:ow=180:oh=180[mh]", "[s4][mh]overlay=1360-90:230-90[s5]",
    fio("parent", T_PARENT, 1.0), "[s5][parent]overlay=0:0[s6]",
    f"[s6][{idx['ipad_off']}:v]overlay=0:0[s7]",
    f"[{k_scr}:v]fps={FPS},drawbox=x=2040:y=56:w=372:h=104:color=0xF5F0E4:t=fill,scale={sw}:{sh},setpts=PTS-STARTPTS+{T_ON}/TB,format=rgba,fade=in:st={T_ON}:d=0.4:alpha=1[scr]",
    f"[s7][scr]overlay={SX0}:{SY0}:enable='gte(t,{T_ON})'[s8]",
    fio("ipad_on", T_ON, 0.4), "[s8][ipad_on]overlay=0:0[s9]",
    f"[s9][{idx['child']}:v]overlay=0:0[s10]",
    fio("child_cool", T_ON + 0.1, 0.6), "[s10][child_cool]overlay=0:0[s11]",
    fio("q", T_Q, 0.3, out=T_IF + 2.0, od=0.8), f"[s11][q]overlay=x=0:y='if(lt(t,{T_Q}),24,if(lt(t,{T_Q + 0.3}),24*(1-(t-{T_Q})/0.3),0))'[s12]",
    f"[s12][{idx['vig']}:v]overlay=0:0[s13]",
    # 「ため」：画面を少し暗くして、だから作りました の前で戻す
    fio("vig_dark", T_IF + 1.2, 1.6, out=T_SO + 0.6, od=1.0), "[s13][vig_dark]overlay=0:0[s14]",
    fio("c1", 0.6, 0.5, out=4.9), "[s14][c1]overlay=0:0[s15]",
    fio("c2", T_PARENT - 0.2, 0.5, out=10.2), "[s15][c2]overlay=0:0[s16]",
    fio("c3", 10.7, 0.5, out=13.4), "[s16][c3]overlay=0:0[s17]",
    fio("c3b", 13.6, 0.5, out=16.4), "[s17][c3b]overlay=0:0[s18]",
    fio("c4", T_IF, 0.6, out=T_PAUSE + 1.2, od=0.9), "[s18][c4]overlay=0:0[s19]",
    fio("c5", T_SO, 0.7, out=DUR - 1.2, od=0.8), f"[s19][c5]overlay=x=0:y='if(lt(t,{T_SO}),20,if(lt(t,{T_SO + 0.7}),20*(1-(t-{T_SO})/0.7),0))'[s20]",
    f"[s20]noise=alls=5:allf=t,fade=in:st=0:d=1.0,fade=out:st={DUR - 0.5}:d=0.5[v]",
]
out = V / "out2" / "seg_intro.mp4"
r = subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-t", f"{DUR}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", str(out)],
                   capture_output=True, text=True)
if r.returncode: print(r.stderr[-3000:]); raise SystemExit(1)
voice = [["i_a.mp3", 0.6], ["i_b.mp3", T_PARENT - 0.2], ["i_c.mp3", 10.8], ["n1c.mp3", T_IF + 0.1], ["i_e.mp3", T_SO + 0.1],
         ["session/000.mp3", T_ON + (4.98 - 4.6)]]
(V / "out2" / "intro_voice.json").write_text(json.dumps({"dur": DUR, "voice": voice, "bgm_mute": [T_PAUSE - 0.6, T_ON - 0.2]}))
print(out)
