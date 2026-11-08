# デモ動画（ChalkTalk のプロモーション動画）の作り方

できあがりは [docs/demo/demo.mp4](../docs/demo/demo.mp4)（2分51秒）。YouTube に上げる完成版。経緯と試行錯誤は #170。

録画・声・3D の連番・素材は大きいので、リポジトリには入れていない（`.gitignore`）。このフォルダには作り方のスクリプトだけを置く。

## 流れ

| 場面 | 作り方 |
|---|---|
| 導入（3D の部屋） | `blender/scene2.py`（Blender 5.2、Eevee）。家具と質感は Poly Haven の CC0 素材を `phget.py` で `ph/dl/` に取る |
| ロゴ・機能の見出し・感想・締め | `make4.py` が Pillow で絵を作り、ffmpeg で動かす |
| アプリの画面 | 専用の Simulator（iPad Pro 11、横向き）を `xcrun simctl io recordVideo` で録画（`session.sh` / `rec.sh`） |
| 先生と子どもの声 | 録画には声が入らないので、`voices.py` が記録の「話し始めた」時刻に合わせて Worker の `/v1/tts/azure` で作り直す。子どもの声は同い年の仲間キャラ・ソラの声 |
| ナレーション | `el_narr.py`（ElevenLabs の `eleven_v4`。声は `XqU2UWV8Vx1jxIkWGuhk`）。読み違えやすい語はかなで書き、`verify` で全部の文を文字起こし（Scribe）して台本と照らし合わせる。仮のナレーションは `narr.py`（Azure） |
| 見守りのあとの撮影〜ヒント | Simulator にカメラがないので `mock.py` で画面のイメージを作る（画面に注記あり） |
| BGM | `bgm2.py`（NumPy で合成。導入 → ロゴ → 機能 → 感想・締めで曲調を変える） |

## 撮影用の起動引数

- `-autoSessionDemo`（`-boardScript` / `-researchScript`）：台本の発話でセッションを流す。先生の返事は本番の Worker と Claude
- `-autoWatchDemo`：見守りの自己テストを、ふだんのセッション画面で流す
- `-demoParentMessage "お母さん|本文"`：本番の D1 を通さずに、端末の中だけで親の伝言を渡す（伝えても「伝えた」と記録しない）

`session.sh` は、子どもが「終わり」と言う直前にアプリを止める。ふり返りを本番に保存しないため。

## 完成版の書き出し

```sh
cd video
.venv/bin/python el_narr.py verify          # 読みの確認と、語ごとの時刻（図の一覧の絵を出す時刻に使う）
FINAL=1 NARR=n6 FRAMES=frames3 .venv/bin/python make4.py
```

`FINAL=1` のときの設定：1920×1080、30fps、H.264（`crf 16`、`preset slow`）。音は AAC 320kbps、48kHz。音量は -14 LUFS、ピークは -1 dB（YouTube の基準）。

## 確かめ方

`make4.py` は、全部の声の始まりと終わりを場面の範囲と比べた表（`out4/audit.txt`）を書き出す。はみ出しや重なりがあれば知らせる。`check.py` は、ナレーションの頭と終わりのコマに文を書き込んで並べた一覧（`out4/check_*.jpg`）を作る。

## 秘密情報

`voices.py` と `narr.py` は `video/.env`（`WORKER_BASE_URL` と `FAMILY_TOKEN`。gitignore 済み）を読む。値は `ios/Config/Secrets.xcconfig` と同じ。`el_narr.py` は `ELEVENLABS_API_KEY` を環境変数か `.env` から読む。共有ライブラリの声を API で使うには、ElevenLabs の有料プランが要る
