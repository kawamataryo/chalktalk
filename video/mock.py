"""見守り → 「見て」→ 撮影 → ヒント、の画面のイメージ（モック）を作る。
Simulator にはカメラがないので、撮影から先は絵で作る（実機の機能：spec §②）。
使い方: from mock import mock_frame, notebook（make4.py から使う）
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
V = Path(__file__).parent
sys.argv = [sys.argv[0], str(V / "cards")]
import cards as C  # noqa: E402
KLEE = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/81e879dcb4d596ab140f7cffcd5ccaaf8108519b.asset/AssetData/Klee.ttc"
def klee(size):
    try: return ImageFont.truetype(KLEE, size, index=1)
    except Exception: return C.jfont(3, size)

def notebook():
    """子どものノート（問題と、途中まで書いた式）"""
    w, h = 900, 620
    im = Image.new("RGB", (w, h), (250, 248, 240)); d = ImageDraw.Draw(im)
    for y in range(70, h, 46): d.line((0, y, w, y), fill=(196, 214, 232), width=2)
    d.line((70, 0, 70, h), fill=(232, 170, 170), width=2)
    pr = C.jfont(4, 30)
    d.text((90, 26), "【問題】クラスの人数は30人です。そのうち40％が", font=pr, fill=(60, 60, 64))
    d.text((90, 72), "サッカーが好きです。サッカーが好きな人は何人？", font=pr, fill=(60, 60, 64))
    hf = klee(54)
    d.text((110, 200), "30 ÷ 0.4 = 75", font=hf, fill=(40, 44, 70))
    d.text((110, 300), "答え　75人", font=hf, fill=(40, 44, 70))
    # 消しゴムのあと
    d.rounded_rectangle((560, 400, 820, 470), 10, fill=(240, 238, 230))
    # 写真っぽく：少し暗く、ふちを落とす
    vig = Image.new("L", (w, h), 0); ImageDraw.Draw(vig).ellipse((-200, -160, w + 200, h + 160), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(80))
    im = Image.composite(im, Image.new("RGB", (w, h), (196, 190, 176)), vig)
    return im

NB = None
def photo_card(scale):
    global NB
    if NB is None: NB = notebook()
    w = int(NB.width * scale); h = int(NB.height * scale)
    card = Image.new("RGBA", (w + 16, h + 16), (255, 255, 255, 255)); card.paste(NB.resize((w, h), Image.LANCZOS), (8, 8))
    return card

def mock_frame(t, base_a, base_b, eye):
    """iPad の画面（1364x940）を返す。t は撮影の瞬間からの秒"""
    if t < 1.7:
        scr = base_a.copy()
    else:
        scr = base_b.copy(); scr.alpha_composite(eye, (0, 0))
    d = ImageDraw.Draw(scr)
    # 撮った写真：大きく出て、黒板の左下に収まる
    if t >= 0.15:
        k = min(1.0, max(0.0, (t - 0.9) / 0.8)); k = k * k * (3 - 2 * k)
        s = 0.95 + (0.36 - 0.95) * k
        card = photo_card(s).rotate(-3 * k, expand=True, resample=Image.BICUBIC)
        cx0, cy0 = 682 - card.width / 2, 470 - card.height / 2
        cx1, cy1 = 64, 520
        x = int(cx0 + (cx1 - cx0) * k); y = int(cy0 + (cy1 - cy0) * k)
        sh = Image.new("RGBA", scr.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rectangle((x + 8, y + 12, x + card.width + 8, y + card.height + 12), fill=(0, 0, 0, 90))
        scr.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10))); scr.alpha_composite(card, (x, y))
        if t >= 1.7:
            d = ImageDraw.Draw(scr); d.rounded_rectangle((x + 10, y - 34, x + 190, y - 4), 15, fill=(240, 200, 110))
            d.text((x + 26, y - 31), "撮ったノート", font=C.jfont(6, 20), fill=(36, 50, 44))
    # 読んでいる間の札
    if 0.4 <= t < 1.7:
        d = ImageDraw.Draw(scr); f = C.jfont(6, 22); s_ = "ノートを読んでいるよ…"
        d.rounded_rectangle((960, 130, 960 + d.textlength(s_, font=f) + 60, 172), 21, fill=(255, 255, 255, 235))
        d.text((990, 138), s_, font=f, fill=(60, 64, 80))
    # ヒント：1 枚目のカードを光らせる
    if t >= 2.0:
        a = int(min(1.0, (t - 2.0) / 0.4) * 255)
        gl = Image.new("RGBA", scr.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle((50, 190, 1046, 268), 14, outline=(255, 214, 90, a), width=6)
        scr.alpha_composite(gl.filter(ImageFilter.GaussianBlur(1.2)))
    # シャッターの白い光
    if t < 0.35:
        fl = Image.new("RGBA", scr.size, (255, 255, 255, int(255 * (1 - t / 0.35))))
        scr.alpha_composite(fl)
    return scr
