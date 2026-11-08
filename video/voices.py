"""自己テストの記録から「話し始めた」文と子どもの発話を取り出し、先生の文を Azure で合成する。

使い方: python3 voices.py <名前>（raw/<名前>.selftest.txt と raw/<名前>.mp4.start を読む）
出力: audio/<名前>/NNN.mp3 と audio/<名前>/events.json（t は録画の先頭からの秒）
"""
import json
READINGS = {"量": "りょう", "受検": "じゅけん"}  # 読み上げの読み違いを避ける（字幕は漢字のまま）
def reading(t):
    for k_, v_ in READINGS.items(): t = t.replace(k_, v_)
    return t
import json, os, re, sys, urllib.request
from pathlib import Path

V = Path(__file__).parent
name = sys.argv[1]
voice = sys.argv[2] if len(sys.argv) > 2 else "ja-JP-MayuNeural"
start = float((V / "raw" / f"{name}.mp4.start").read_text())
env = dict(re.findall(r"export (\w+)=(.*)", (V / ".env").read_text()))
base, token = env["WORKER_BASE_URL"].strip("'"), env["FAMILY_TOKEN"].strip("'")
out = V / "audio" / name
out.mkdir(parents=True, exist_ok=True)

events = []
for line in (V / "raw" / f"{name}.selftest.txt").read_text().splitlines():
    m = re.search(r"\[(\d+\.\d+)\]\s+(.*)", line)
    if not m:
        continue
    t, body = float(m.group(1)) - start, m.group(2)
    if s := re.match(r"· 話し始めた(?:\[\w+\])?: (.*)", body):
        events.append({"t": round(t, 3), "who": "teacher", "text": s.group(1)})
    elif s := re.match(r"子ども: 「(.*)」", body):
        events.append({"t": round(t, 3), "who": "kid", "text": s.group(1)})

KID_VOICE = "ja-JP-AoiNeural"  # 子どもの声は、同い年の仲間ソラの声を借りる
def tts(text, v, path):
    if not path.exists():
        req = urllib.request.Request(f"{base}/v1/tts/azure", method="POST",
            data=json.dumps({"text": reading(text), "voice": v}).encode(),
            headers={"Authorization": f"Bearer {token}", "content-type": "application/json", "User-Agent": "home-teacher-demo-video"})
        path.write_bytes(urllib.request.urlopen(req, timeout=30).read())
n = k = 0
for e in events:
    if e["who"] == "teacher":
        path = out / f"{n:03d}.mp3"; tts(e["text"], voice, path); n += 1
    else:
        if e["text"] == "終わり": continue
        path = out / f"kid_{k:03d}.mp3"; tts(e["text"], KID_VOICE, path); k += 1
    e["file"] = str(path)
(out / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=1))
for e in events:
    print(f'{e["t"]:7.2f} {e["who"]:7s} {e["text"]}')
