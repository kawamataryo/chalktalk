"""ナレーションと場面が合っているかを見る一覧（out4/check_*.jpg）。
ナレーションの頭（+0.3 秒）と終わり（-0.3 秒）のコマに、その文を書き込んで並べる。
"""
import json, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
V = Path(__file__).parent
sys.argv = [sys.argv[0], str(V / "cards")]
import cards as C  # noqa: E402
OUT = V / "out4"; MOV = OUT / "chalktalk_promo.mp4"
texts = json.loads((V / "audio" / "n4" / "texts.json").read_text())
texts.update({"i_a": "小学5年の長男は、中学受検の勉強をしています。", "i_b": "共働きのわが家。その時間、親は仕事で、そばにいられません。",
              "i_c": "わからない問題で手が止まっても、聞ける人がいない。時間だけが、過ぎていきます。", "n1c": "もし、話しかけられる先生が、そばにいたら。",
              "i_e": "だから、作りました。", "logo": "話しかければ、そばに先生。チョークトーク。", "end": "話しかければ、そばに先生。チョークトーク。"})
rows = []
for line in (OUT / "audit.txt").read_text().splitlines()[1:]:
    m = re.match(r"(\d+) (\w+)\s+([\d.]+)-\s*([\d.]+) .*\) (\S+)", line)
    if not m: continue
    key = m.group(5).replace(".mp3", "")
    if key in texts and not key.startswith("kid_"):
        rows.append((float(m.group(3)), float(m.group(4)), texts[key]))
tiles = []
for a, b, t in rows:
    for when, lab in ((a + 0.3, "頭"), (b - 0.3, "終わり")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{when:.2f}", "-i", str(MOV), "-frames:v", "1", "-vf", "scale=640:360", "/tmp/_c.png"])
        im = Image.open("/tmp/_c.png").convert("RGB"); d = ImageDraw.Draw(im)
        d.rectangle((0, 300, 640, 360), fill=(0, 0, 0)); d.text((8, 304), f"{when:6.1f}s {lab}", font=C.jfont(6, 16), fill=(255, 220, 120))
        d.text((8, 326), t[:38], font=C.jfont(4, 16), fill=(255, 255, 255))
        tiles.append(im)
for k in range(0, len(tiles), 12):
    sheet = Image.new("RGB", (640 * 4, 360 * 3), (0, 0, 0))
    for j, im in enumerate(tiles[k:k + 12]):
        sheet.paste(im, ((j % 4) * 640, (j // 4) * 360))
    sheet.save(OUT / f"check_{k // 12}.jpg", quality=85)
print(len(tiles), "tiles")
