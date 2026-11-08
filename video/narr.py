"""ナレーションと単発の声を Azure で作る（仮のナレーション：KeitaNeural）。
使い方: .venv/bin/python narr.py  → audio/n4/<key>.mp3（文が変わったら作り直す）
"""
import json
READINGS = {"量": "りょう", "受検": "じゅけん"}  # 読み上げの読み違いを避ける（字幕は漢字のまま）
def reading(t):
    for k_, v_ in READINGS.items(): t = t.replace(k_, v_)
    return t
import json, re, urllib.request, hashlib
from pathlib import Path
V = Path(__file__).parent
env = dict(re.findall(r"export (\w+)=(.*)", (V / ".env").read_text()))
base, token = env["WORKER_BASE_URL"].strip("'"), env["FAMILY_TOKEN"].strip("'")
NARR = "ja-JP-KeitaNeural"; KID = "ja-JP-AoiNeural"; MUNI = "ja-JP-MayuNeural"
LINES = {
    "ipad2": (NARR, "iPadに話しかけるだけ。そばで一緒にがんばる、勉強の相棒です。"),
    "f1": (NARR, "声で話せる。"),
    "f2": (NARR, "黒板で教える。"),
    "f3": (NARR, "答えは言わない。できたら、ほめる。"),
    "f4": (NARR, "見守って、声をかける。"),
    "f5": (NARR, "自分の先生を選べる。"),
    "f6": (NARR, "なんでも話せる。"),
    "f7": (NARR, "親とつながる。"),
    "nm": (NARR, "数直線や面積図、グラフ。メダカや花、電気の回路まで、どんな形も黒板に自由に描きます。"),
    "n8": (NARR, "今夜どんな言葉をかければいいかが、親に届きます。"),
    "npriv": (NARR, "写真や声は保存せず、残すのは文字だけ。先生が覚えていることも、親が確かめて消せます。"),
    "kidq": (NARR, "使ってみた、長男の感想です。"),
    "close": (NARR, "一人じゃない勉強を、どの家庭にも。話しかければ、そばに先生。チョークトーク。"),
    "kid_tadaima": (KID, "ねえ先生、ただいま！"),
    "boru_intro": ("ja-JP-DaichiNeural", "ピピッと来たよ！ボルです。ほめ言葉を練習中で、合ってた？って聞いちゃうんだ。"),
    "i_b2": (NARR, "共働きが当たり前の今。わが家も、親は仕事でそばにいられません。"),
    "hint": (MUNI, "ここまで書けたね！30と0.4、どっちが「もとにする量」かな？"),
    "f3_ok": (MUNI, "うん、見せて！"),
}
out = V / "audio" / "n4"; out.mkdir(parents=True, exist_ok=True)
meta_p = out / "meta.json"; meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
for k, (voice, text) in LINES.items():
    h = hashlib.sha1(f"{voice}|{text}".encode()).hexdigest()
    p = out / f"{k}.mp3"
    if meta.get(k) != h or not p.exists():
        req = urllib.request.Request(f"{base}/v1/tts/azure", method="POST", data=json.dumps({"text": reading(text), "voice": voice}).encode(),
            headers={"Authorization": f"Bearer {token}", "content-type": "application/json", "User-Agent": "home-teacher-demo-video"})
        p.write_bytes(urllib.request.urlopen(req, timeout=30).read()); meta[k] = h
meta_p.write_text(json.dumps(meta, indent=1)); (out / "texts.json").write_text(json.dumps({k: t for k, (v, t) in LINES.items()}, ensure_ascii=False, indent=1))
print("ok")
