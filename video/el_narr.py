"""ナレーションを ElevenLabs で作る（eleven_multilingual_v2。<break> でためを入れる）。
キーは環境変数 ELEVENLABS_API_KEY か、~/chalktalk-video-work/video/.env（export ELEVENLABS_API_KEY=...）から読む。値は表示しない。
使い方:
  .venv/bin/python el_narr.py voices            # 日本語のナレーション向けの声を一覧
  .venv/bin/python el_narr.py sample <voice_id>...  # 同じ文で聞き比べ（../elv/sample_<id>.mp3）
  .venv/bin/python el_narr.py build <voice_id>  # 全部のナレーションを audio/n5/ に作る
"""
import json, os, re, sys, urllib.request, urllib.parse, hashlib
from pathlib import Path
V = Path(__file__).parent

def key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k:
        for p in (V / ".env", Path.home() / "chalktalk-video-work" / "video" / ".env"):
            if p.exists():
                m = re.search(r"ELEVENLABS_API_KEY=['\"]?([^'\"\n]+)", p.read_text())
                if m: k = m.group(1).strip(); break
    if not k: raise SystemExit("ELEVENLABS_API_KEY がありません")
    return k

def api(path, body=None, params=None):
    url = "https://api.elevenlabs.io" + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, method="POST" if body is not None else "GET", data=json.dumps(body).encode() if body is not None else None,
                                 headers={"xi-api-key": key(), "content-type": "application/json", "User-Agent": "chalktalk-video/1.0"})
    return urllib.request.urlopen(req, timeout=120).read()

B = lambda s: f'<break time="{s}s" />'
# 読み違えやすい語はかなで書く（字幕は TEXTS の漢字のまま）
LINES = {
    "i_a": "小学ごねんの長男は、中学じゅけんの勉強中です。",
    "i_b2": f"ともばたらきの、わがや。{B(0.3)}親は仕事で、そばにいられません。",
    "i_c": f"わからない問題で、手が止まっても、{B(0.2)}聞ける人がいない。",
    "n1c": f"もし、{B(0.4)}話しかけられる先生が、{B(0.2)}そばにいたら。",
    "i_e": f"だから、{B(0.6)}作りました。",
    "logo": f"話しかければ、そばに先生。{B(0.5)}チョークトーク。",
    "ipad2": f"アイパッドに、話しかけるだけ。{B(0.3)}そばで一緒にがんばる、勉強のあいぼうです。",
    "f1": "声で話せる。", "f2": "こくばんで教える。", "f3": f"答えは言わない。{B(0.3)}できたら、ほめる。",
    "f4": f"見守って、{B(0.2)}声をかける。", "f5": "自分の先生を選べる。", "f6": "なんでも話せる。", "f7": "親とつながる。",
    "nm": f"すうちょくせんや、めんせきず、グラフ。{B(0.4)}メダカや植物、電気の回路まで、{B(0.2)}どんな形も、こくばんに自由にかきます。",
    "n8": f"今夜、{B(0.15)}どんな言葉をかければいいかが、親にとどきます。",
    "npriv": f"写真や声は保存せず、残すのは文字だけ。{B(0.4)}先生が覚えていることも、親が確かめて、けせます。",
    "kidq": "使ってみた、長男の感想です。",
    "close": f"ひとりじゃない勉強を、{B(0.3)}どの家庭にも。{B(0.8)}話しかければ、そばに先生。{B(0.4)}チョークトーク。",
}
# 字幕に使う文（漢字）
TEXTS = {
    "i_a": "小学5年の長男は、中学受検の勉強中です。", "i_b2": "共働きの、わが家。親は仕事で、そばにいられません。",
    "i_c": "わからない問題で、手が止まっても、聞ける人がいない。", "n1c": "もし、話しかけられる先生が、そばにいたら。",
}
SETTINGS = {"stability": 0.5, "similarity_boost": 0.8, "style": 0.2, "use_speaker_boost": True, "speed": 1.0}
VOICE = "XqU2UWV8Vx1jxIkWGuhk"

FAST = set()  # 速くすると不自然なので、どの文も速さ 1.0
# 「チョークトーク」は multilingual_v2 だと「ちょくとく」と縮むので、ブランド名を言う文は eleven_v3 で作る（ためは「……」）
V3_LINES = {
    "logo": "話しかければ、そばに先生。……チョークトーク。",
    "close": "ひとりじゃない勉強を、どの家庭にも。……話しかければ、そばに先生。……チョークトーク。",
}
def to_v3(text):
    """<break> を v3 のためにする（0.4 秒以上は「……」、それより短いのは「…」）"""
    return re.sub(r'<break time="([\d.]+)s" />', lambda m: "……" if float(m.group(1)) >= 0.4 else "…", text)
for k_ in LINES:
    V3_LINES.setdefault(k_, to_v3(LINES[k_]))

def tts_v3(text, voice, out):
    Path(out).write_bytes(api(f"/v1/text-to-speech/{voice}", {"text": text, "model_id": "eleven_v3", "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}},
                              {"output_format": "mp3_44100_128"}))

def tts(text, voice, out, settings=SETTINGS):
    audio = api(f"/v1/text-to-speech/{voice}", {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": settings,
                                                 "language_code": "ja"}, {"output_format": "mp3_44100_128"})
    Path(out).write_bytes(audio)

def trim(p):
    """前後の無音を削る"""
    import subprocess
    tmp = p.with_suffix(".tmp.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,apad=pad_dur=0.05",
                    "-b:a", "160k", str(tmp)], check=True)
    tmp.replace(p)

def scribe(p):
    """ElevenLabs の文字起こし（語ごとの時刻つき）"""
    import uuid
    bnd = uuid.uuid4().hex; data = Path(p).read_bytes()
    parts = []
    for k_, v_ in (("model_id", "scribe_v1"), ("language_code", "jpn"), ("timestamps_granularity", "word")):
        parts.append(f"--{bnd}\r\nContent-Disposition: form-data; name=\"{k_}\"\r\n\r\n{v_}\r\n".encode())
    parts.append(f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.mp3\"\r\nContent-Type: audio/mpeg\r\n\r\n".encode() + data + b"\r\n")
    body = b"".join(parts) + f"--{bnd}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", method="POST", data=body,
                                 headers={"xi-api-key": key(), "content-type": f"multipart/form-data; boundary={bnd}", "User-Agent": "chalktalk-video/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "voices":
        res = []
        for q in ({"language": "ja", "use_cases": "narrative_story"}, {"language": "ja", "use_cases": "informative_educational"}, {"language": "ja"}):
            d = json.loads(api("/v1/shared-voices", params={**q, "page_size": 40, "sort": "usage_character_count_1y"}))
            res += d.get("voices", [])
        seen = set()
        for v in res:
            if v["voice_id"] in seen: continue
            seen.add(v["voice_id"])
            print(v["voice_id"], "|", v.get("name"), "|", v.get("gender"), v.get("age"), v.get("accent"), v.get("use_case"), "|", (v.get("description") or "")[:80].replace("\n", " "))
    elif cmd == "sample":
        Path(V.parent / "elv").mkdir(exist_ok=True)
        for vid in sys.argv[2:]:
            tts(LINES["i_b2"] + B(0.6) + LINES["n1c"], vid, V.parent / "elv" / f"sample_{vid}.mp3"); print("ok", vid)
    elif cmd == "verify":  # 全部の文を文字起こしして、台本と並べる。語の時刻は audio/n5/words.json
        out = V / "audio" / "n5"; words = {}
        for k_, text in LINES.items():
            r = scribe(out / f"{k_}.mp3")
            words[k_] = [{"t": w["start"], "e": w["end"], "w": w["text"]} for w in r.get("words", []) if w.get("type") == "word"]
            print(f"[{k_}]\n  台本: {re.sub(r'<[^>]+>', '', text)}\n  聞き: {r.get('text')}")
        (out / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=1))
    elif cmd == "fix":  # 指定の文を、聞こえ方に期待する語が入るまで作り直す
        vid = VOICE; out = V / "audio" / "n5"
        for spec in sys.argv[2:]:
            k_, want = spec.split("=")
            for n_ in range(4):
                if k_ in V3_LINES: tts_v3(V3_LINES[k_], vid, out / f"{k_}.mp3")
                else: tts(LINES[k_], vid, out / f"{k_}.mp3")
                trim(out / f"{k_}.mp3")
                txt = scribe(out / f"{k_}.mp3").get("text", "")
                ok = all(w in txt for w in want.split("+"))
                print(k_, n_, "OK" if ok else "NG", txt)
                if ok: break
    elif cmd == "build3":  # 全部 eleven_v3 で作る
        vid = VOICE; out = V / "audio" / "n5"
        for k_ in LINES:
            p_ = out / f"{k_}.mp3"; tts_v3(V3_LINES[k_], vid, p_); trim(p_); print("made", k_, V3_LINES[k_])
    elif cmd == "build":
        vid = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else VOICE; out = V / "audio" / "n5"; out.mkdir(parents=True, exist_ok=True)
        meta_p = out / "meta.json"; meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
        only = sys.argv[3].split(",") if len(sys.argv) > 3 else None
        for k_, text in LINES.items():
            if only and k_ not in only: continue
            h = hashlib.sha1(f"{vid}|{text}|{json.dumps(SETTINGS, sort_keys=True)}|{k_ in FAST}|trim".encode()).hexdigest()
            p = out / f"{k_}.mp3"
            if meta.get(k_) != h or not p.exists():
                st = dict(SETTINGS, speed=1.12) if k_ in FAST else SETTINGS
                tts(text, vid, p, st); meta[k_] = h; print("made", k_)
                trim(p)
        meta_p.write_text(json.dumps(meta, indent=1))
