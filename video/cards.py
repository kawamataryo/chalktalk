"""デモ動画のテロップ・カード・背景を PNG で描く（1920x1080）。

使い方: .venv/bin/python cards.py <出力ディレクトリ>
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "cards")
OUT.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("/System/Library/Fonts")
def font(name, size):
    for p in FONT_DIR.iterdir():
        if p.name.startswith(name):
            return ImageFont.truetype(str(p), size)
    raise FileNotFoundError(name)

import unicodedata
def nfd(s): return unicodedata.normalize("NFD", s)
def jfont(weight, size):
    target = nfd(f"ヒラギノ角ゴシック W{weight}.ttc")
    for p in FONT_DIR.iterdir():
        if nfd(p.name) == target:
            return ImageFont.truetype(str(p), size)
    raise FileNotFoundError(target)
def maru(size):
    for p in FONT_DIR.iterdir():
        if nfd(p.name).startswith(nfd("ヒラギノ丸ゴ")):
            return ImageFont.truetype(str(p), size)
    return jfont(6, size)

# 色（黒板の緑とチョークの黄を軸に）
BG = (243, 241, 233)
BOARD = (36, 68, 58)
CHALK = (238, 244, 238)
YELLOW = (233, 196, 106)
INK = (31, 42, 36)
MUTED = (93, 107, 99)
KID = (194, 65, 12)
KID_BG = (255, 241, 232)

# iPad の画面を置く場所（左）。録画は 2420x1668
IPAD_H = 940
IPAD_W = round(2420 / 1668 * IPAD_H)  # 1364
IPAD_X, IPAD_Y = 56, (H - IPAD_H) // 2
PANEL_X = IPAD_X + IPAD_W + 48  # 右のテロップ欄の左端
PANEL_W = W - PANEL_X - 48


def wrap(draw, text, fnt, width):
    import re
    lines, line = [], ""
    for ch in re.findall(r"[A-Za-z0-9.]+|.", text, re.S):  # 英単語は途中で折らない
        if ch == "\n":
            lines.append(line); line = ""; continue
        if draw.textlength(line + ch, font=fnt) > width:
            # 句読点を行頭に置かない
            if ch in "、。！？」）":
                line += ch; lines.append(line); line = ""; continue
            lines.append(line); line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines


def background():
    """セッション用の背景（iPad の枠と影）"""
    img = Image.new("RGB", (W, H), BG)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (IPAD_X - 14, IPAD_Y - 6, IPAD_X + IPAD_W + 14, IPAD_Y + IPAD_H + 22), 46, fill=(0, 0, 0, 70))
    img.paste(shadow.filter(ImageFilter.GaussianBlur(18)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((IPAD_X - 16, IPAD_Y - 16, IPAD_X + IPAD_W + 16, IPAD_Y + IPAD_H + 16), 44, fill=(28, 30, 32))
    img.save(OUT / "bg.png")


def panel(name, scene_no, title, telops=(), kid=None, note=None):
    """右のテロップ欄（透明 PNG）。scene_no は小さく、title を大きく、telops を黒板の札で"""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x, y = PANEL_X, IPAD_Y + 8
    if scene_no:
        d.text((x, y), scene_no, font=jfont(6, 22), fill=MUTED)
        y += 40
    for line in wrap(d, title, maru(42), PANEL_W):
        d.text((x, y), line, font=maru(42), fill=INK)
        y += 58
    y += 18
    for t in telops:
        f = jfont(6, 26)
        lines = wrap(d, t, f, PANEL_W - 40)
        h = 22 + 38 * len(lines)
        d.rounded_rectangle((x, y, x + PANEL_W, y + h), 12, fill=BOARD)
        for i, l in enumerate(lines):
            d.text((x + 20, y + 12 + 38 * i), l, font=f, fill=CHALK)
        y += h + 14
    if kid:
        f = jfont(4, 26)
        lines = wrap(d, kid, f, PANEL_W - 40)
        top = IPAD_Y + IPAD_H - (70 + 38 * len(lines))
        d.rounded_rectangle((x, top, x + PANEL_W, IPAD_Y + IPAD_H), 14, fill=KID_BG, outline=KID, width=2)
        d.text((x + 20, top + 12), "子ども（台本の台詞・字幕のみ）", font=jfont(6, 18), fill=KID)
        for i, l in enumerate(lines):
            d.text((x + 20, top + 44 + 38 * i), l, font=f, fill=INK)
    if note:
        f = jfont(3, 16)
        for i, l in enumerate(wrap(d, note, f, PANEL_W)):
            d.text((x, IPAD_Y + IPAD_H + 12 + 22 * i), l, font=f, fill=MUTED)
    img.save(OUT / f"{name}.png")


def title_card(name, lines, sub=None, dark=True):
    """全面のカード（黒板）"""
    img = Image.new("RGB", (W, H), BOARD if dark else BG)
    d = ImageDraw.Draw(img)
    fg = CHALK if dark else INK
    f = maru(64)
    total = 88 * len(lines) + (70 if sub else 0)
    y = (H - total) // 2
    for l in lines:
        w = d.textlength(l, font=f)
        d.text(((W - w) / 2, y), l, font=f, fill=fg)
        y += 88
    if sub:
        f2 = jfont(4, 30)
        w = d.textlength(sub, font=f2)
        d.text(((W - w) / 2, y + 30), sub, font=f2, fill=YELLOW if dark else MUTED)
    img.save(OUT / f"{name}.png")


def quotes_card(name, heading, quotes):
    """子どもの感想（黒板にチョークで書いたような）"""
    img = Image.new("RGB", (W, H), BOARD)
    d = ImageDraw.Draw(img)
    d.text((160, 170), heading, font=jfont(6, 34), fill=YELLOW)
    y = 280
    for q in quotes:
        d.text((160, y), f"「{q}」", font=maru(58), fill=CHALK)
        y += 150
    img.save(OUT / f"{name}.png")


def arch_card(name):
    """Claude の使い分けの図"""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((120, 90), "Claude の使い分け", font=maru(52), fill=INK)
    boxes = [
        ("Haiku", "会話", "文ごとにストリーミングして、すぐ読み上げる"),
        ("Sonnet", "読み取り・図・ふり返り", "撮った問題からヒントの段階と黒板の図を作る"),
        ("Jev", "速い判断", "話しかけたか・言い終わったかを、すぐに判断する"),
    ]
    x = 120
    for head, role, desc in boxes:
        d.rounded_rectangle((x, 220, x + 530, 520), 20, fill=(255, 255, 255), outline=(214, 221, 215), width=2)
        d.text((x + 34, 250), head, font=jfont(7, 46), fill=BOARD)
        d.text((x + 34, 320), role, font=jfont(6, 30), fill=INK)
        for i, l in enumerate(wrap(d, desc, jfont(4, 24), 460)):
            d.text((x + 34, 380 + 36 * i), l, font=jfont(4, 24), fill=MUTED)
        x += 570
    rows = [
        "話す前に AnswerLeakGuard で、答えが漏れていないかを検査（漢数字・分数・単位の言い換えまで）",
        "写真と声はどこにも保存しない。残すのは文字の要約だけ",
        "開発も Claude Code：issue → worktree → テスト → PR を、ハッカソン期間中に回した",
    ]
    y = 590
    for r in rows:
        d.rounded_rectangle((120, y, 1800, y + 96), 14, fill=BOARD)
        d.text((156, y + 30), r, font=jfont(6, 30), fill=CHALK)
        y += 116
    img.save(OUT / f"{name}.png")


if __name__ == "__main__":
    background()
    title_card("s1_title", ["一人の勉強に、", "声で話せる先生を。"], "AI家庭教師（仮）— Built with Claude: Japan 2026")
    title_card("s1_problem", ["勉強の時間はある。", "でも、そばに誰もいない。"])
    quotes_card("s9_quotes", "使ってみた長男（小5）の感想", [
        "励ましてくれるのが嬉しかった",
        "宇宙の話とかもできた",
        "ちょっと間違えることもあるけど、それも可愛い",
    ])
    arch_card("s9_arch")
    title_card("s9_end", ["一人じゃない勉強を、", "どの家庭にも。"], "github.com/kawamataryo/ai-home-teacher")
    print("ok")


def dashboard_parts():
    """シーン8：スマホの枠（中を透明に）と、横に並べる成長・週のまとめのカード"""
    R = Path("/Users/ryo/ghq/github.com/kawamataryo/ai-home-teacher/docs/screenshots/parent-report")
    PW, PH = 420, 860  # スマホの画面
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    px, py = 120, (H - PH) // 2
    # 枠の外を背景色で塗り、画面の所だけ抜く
    mask = Image.new("L", (W, H), 255)
    ImageDraw.Draw(mask).rounded_rectangle((px, py, px + PW, py + PH), 36, fill=0)
    bgfill = Image.new("RGBA", (W, H), BG + (255,))
    frame.paste(bgfill, (0, 0), mask)
    d.rounded_rectangle((px - 14, py - 14, px + PW + 14, py + PH + 14), 50, outline=(28, 30, 32), width=14)
    # 右のカード
    x = px + PW + 70
    for name, y in (("161-growth.png", py), ("162-weekly.png", py + 470)):
        im = Image.open(R / name).convert("RGB")
        im.thumbnail((560, 440))
        sh = Image.new("RGBA", (im.width + 40, im.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((20, 24, im.width + 20, im.height + 24), 16, fill=(0, 0, 0, 50))
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        frame.alpha_composite(sh, (x - 20, y - 20))
        frame.paste(im, (x, y))
    frame.save(OUT / "s8_frame.png")
    shot = Image.open(R / "158-parent-prompt.png").convert("RGB")
    shot = shot.resize((PW, round(shot.height * PW / shot.width)))
    shot.save(OUT / "s8_phone.png")
    print("phone", px, py, shot.size)


dashboard_parts()
