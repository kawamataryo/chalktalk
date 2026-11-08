# デモ動画（ChalkTalk のプロモーション動画）の作り方

できあがりは [docs/demo/demo.mp4](../docs/demo/demo.mp4)（約2分53秒）。経緯と試行錯誤は #170。

録画・声・3D の連番・素材は大きいので、リポジトリには入れていない（`.gitignore`）。このフォルダには作り方のスクリプトだけを置く。

## 流れ

| 場面 | 作り方 |
|---|---|
| 導入（3D の部屋） | `blender/scene2.py`（Blender 5.2、Eevee）。家具と質感は Poly Haven の CC0 素材を `phget.py` で `ph/dl/` に取る |
| ロゴ・機能の見出し・感想・締め | `make4.py` が Pillow で絵を作り、ffmpeg で動かす |
| アプリの画面 | 専用の Simulator（iPad Pro 11、横向き）を `xcrun simctl io recordVideo` で録画（`session.sh` / `rec.sh`） |
| 先生と子どもの声 | 録画には声が入らないので、`voices.py` が記録の「話し始めた」時刻に合わせて Worker の `/v1/tts/azure` で作り直す。子どもの声は同い年の仲間キャラ・ソラの声 |
| ナレーション | `narr.py` |
| 見守りのあとの撮影〜ヒント | Simulator にカメラがないので `mock.py` で画面のイメージを作る（画面に注記あり） |
| BGM | `bgm.py`（NumPy で合成） |

## 撮影用の起動引数

- `-autoSessionDemo`（`-boardScript` / `-researchScript`）：台本の発話でセッションを流す。先生の返事は本番の Worker と Claude
- `-autoWatchDemo`：見守りの自己テストを、ふだんのセッション画面で流す
- `-demoParentMessage "お母さん|本文"`：本番の D1 を通さずに、端末の中だけで親の伝言を渡す（伝えても「伝えた」と記録しない）

`session.sh` は、子どもが「終わり」と言う直前にアプリを止める。ふり返りを本番に保存しないため。

## 確かめ方

`make4.py` は、全部の声の始まりと終わりを場面の範囲と比べた表（`out4/audit.txt`）を書き出す。はみ出しや重なりがあれば知らせる。`check.py` は、ナレーションの頭と終わりのコマに文を書き込んで並べた一覧（`out4/check_*.jpg`）を作る。

## 秘密情報

`voices.py` と `narr.py` は `video/.env`（`WORKER_BASE_URL` と `FAMILY_TOKEN`。gitignore 済み）を読む。値は `ios/Config/Secrets.xcconfig` と同じ。
