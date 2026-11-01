# Handoff: W09R-D（Issue #49）— D 南の Meshy 素材の差し替え（M05 メリーゴーラウンドの屋根・中央の柱、M06 おばけ列車の先頭車）

親 #1 の Spec §13「各タスクの引き継ぎに必須の項目」。詳しい記録は `docs/p2-meshy-replacement.md` 15 章（以下「記録」）。方式と手順は同じ文書の 2・4 章（W09R #44）。

## 1. 対象工程・アセット

- 工程: P2 の後続の差し替え（Spec §12「最終版：P4の完了条件」の「採用するMeshyモデルが統合済み」に向けた作業）。残りの 7 素材の 5 件のうち 4 件目（順は C → A → B → D → E。2026-11-01 の利用者の決定）
- 対象: D 南・パンプキン遊園地の M05 メリーゴーラウンドの柱（`DAM_Carousel_001_M05_CenterCasing` → `M05_CenterCasing_001`）と屋根（`DAM_Carousel_001_M05_Canopy` → `M05_Canopy_001`）、M06 おばけ列車の先頭車（`DAM_GhostTrain_001_M06_EngineShell` → `M06_GhostTrainEngine_001`）。W05 の支柱 `DAM_Carousel_001_Poles` と前照灯の取付位置 `DAM_GhostTrain_001_Att_Headlamp`
- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ
- 所要時間: claim 06:14:49Z から PR の作成まで約 50 分（読み込みと前提の確認・Issue の更新 約 8 分、全キーのビルド（並行して読み込み）約 5 分、最初の diff 約 5 分、屋根の下面の計測と利用者の決定 約 5 分、実装（D・`replacements.py`・`export_meshy.py`・`verify_live.py`・テスト）約 12 分、export・diff・apply・実測・撮影 約 6 分、利用者の歩行の待ち・変異・記録 約 10 分）。GPT のレビューと保存・マージは PR の後

## 2. 今回完了したこと

1. 保存の後の最初の diff: 全 14 宣言で変更 0、資産の作り直し・重複なし（記録 15.1）
2. M05 を `received.json` の行ごとの 2 行（`M05_CenterCasing`・`M05_Canopy`）に分け、M05 の `.blend` から子 1 つだけの宣言を作る仕組み（`export_meshy.extract_part`）を足した（記録 15.2・15.4）
3. **利用者の決定（支柱「屋根まで伸ばす」）**: W05 の支柱 8 本を、支柱ごとに屋根の下面の 2 cm 上まで伸ばし（TurnRoot のローカルで 3.25 m → 3.97〜4.27 m）、上端の飾りの輪を 3 cm 下げた（記録 15.2・15.3）
4. 前照灯の取付位置を (0, 1.233, 1.498) → (0, 1.26, 1.39)（M06 のレンズの前面の 1.35 cm 前）へ移した。**利用者の決定**: 取付位置の目印（電球のように見える）はこのまま
5. M05・M06 を差し替えた。外接箱・原点・取付位置の差 0.0 m、M05 は東、M06 は北を向く。2 回目の apply は書き込み 0、全 17 宣言が変更 0 で収束（記録 15.6・15.7）
6. `verify_live.py` の取付位置の期待値に親の部品の位置を足した（直し）。屋根と柱の組み立て・支柱・前照灯の検査を足した。テスト 4 件（記録 15.4、9 章）
7. 撮影 14 枚。黒い面・反転・透けなし（記録 15.8）。利用者の歩行は「問題なし」、60 fps 前後
8. 後続の子のために、apply した 3 つのバンドルを Git の外の `p2_bundles/` に控えた（記録 15.5）

## 3. 変更ファイルと版

- 基点: `main` の `66c4839`
- 変更（差し替え）: `modeling/p2_meshy/replacements.py`（3 行と新しい項目 `source`・`export_root`・`assembly_with`・`poles`・`lens_attachment`）、`modeling/p2_meshy/export_meshy.py`（`extract_part`・`_providers_for`）、`modeling/p2_meshy/verify_live.py`（記録 15.4）、`tests/test_p2_meshy_verify.py`（4 件）、`review/p2_meshy/live_checks.json`（全 8 行の実測）、`docs/p2-meshy-replacement.md`（冒頭・4 章・8 章の M05・M06 の行・11 章・15 章）
- 変更（閉じた子 W05 の所有。記録 15.3）: `modeling/D_amusement/layout_data.py`（定数 3 つ）・`assets_rides.py`（支柱・飾りの輪・前照灯）、生成物の `assets/manifest/D_amusement.json`（`Att_Headlamp` の `pivot_local` だけ）・`review/D_amusement/*.png`
- 追加: `exports/p2_meshy/M05_CenterCasing-20261101T063625Z/`・`M05_Canopy-20261101T063625Z/`・`M06-20261101T063625Z/` と `exports/p2_static/<key>-20261101T062140Z/`（6 キー）・`D_amusement-20261101T063618Z/` の記録（`report.json`・`validate.json`・`placement.json`・`colliders.json`・`replacements.json`）、`review/p2_meshy/` の撮影 14 枚、この文書
- W09-M05・W09-M06 の `M05`・`M06`、W08 の `modeling/p2_static/` は変えていない
- state: 親の checkout の `/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state/` に `p2m_M05_CenterCasing.json`・`p2m_M05_Canopy.json`・`p2m_M06.json` を足し、`p2_D_amusement.json` を更新した（#49 の本文の `p2m_M05.json` ではなく行ごと）。消すと次の apply が同じ物をもう一度作るので消さない
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1
- 保存（確認事項 4）: 記録 15.10（PR の後に記録する）

## 4. 再実行手順

記録 4 章。この子で使った形:

```sh
for key in world common A_plaza B_mansion C_candy D_amusement E_forest M05 M06; do
  resoloop blender run modeling/$key/build.py --json || exit 2      # E_forest は --arg=--no-render で速くなる。全部で約 5 分
done
# Git の外の p2_bundles/<M>-<UTC>（M01・M02・M03・M04・M08、この子の M05_CenterCasing・M05_Canopy・M06）を SHA256SUMS で確かめ、同じ名前の exports/p2_meshy/ へ写す
uv run python modeling/p2_static/export_p2.py --url "$URL" --key D_amusement            # 支柱・前照灯を直し、3 つの仮モデルの描画を止めた D
uv run python modeling/p2_meshy/export_meshy.py --url "$URL" --meshy M05_CenterCasing --meshy M05_Canopy --meshy M06
# スナップショット → diff → apply（素材は --texture-transfer data、state p2m_<行>.json）→ D の diff・apply → 2 回目の diff・apply（記録 4 章）
uv run python modeling/p2_meshy/verify_live.py --url "$URL" --raw-out <Git の外> --output review/p2_meshy/live_checks.json
```

- 作り直して変わった追跡中の `.blend`・他のキーの確認画像と、ビルドが `export_result` を `unexported` に戻した `assets/manifest/M05.json`・`M06.json` は、コミットの前に `git restore` で戻した（形は変えていない）。D の確認画像は形を変えたのでコミットした
- `resoloop capture` の `<名前>.scene.json` は作業ツリーの絶対パスを含むので消した
- 屋根の下面の計測（記録 15.2）は、セッションの一時的なスクリプト（M05 の屋根のメッシュへの上向きのレイ）で行い、コミットしていない。同じ計測は `verify_live.py` の `check_poles` が毎回行う

## 5. 確認した内容と結果

| 受け入れ基準 | 結果 |
|---|---|
| 保存の後の最初の diff | 全 14 宣言で 0。world・D・E・M02 の資産は `resdb` への移行の no-op（記録 15.1） |
| export・validate | M05 の 2 行・M06・D がオフライン・`--strict` で issues 0（15.5） |
| M05 | 柱 1.861 × 3.400 × 1.907 m・屋根 9.314 × 6.387 × 9.512 m、期待値との差 0.0 m。TurnRoot の回転 0 で東（`placement_hint` -90）。屋根は柱の 2.964 m 上（差 0.0 m）。支柱 8 本の上端は屋根の下面の 2.0〜2.8 cm 上で、先は屋根の殻の中（15.7） |
| M06 | 1.211 × 1.875 × 3.000 m、差 0.0 m。正面は北（進む向き）。前照灯の取付位置はレンズの前面の 1.35 cm 前、レンズの中心の高さ |
| 動作の root | `TurnRoot`・`EngineRoot`（と親の `DAM_Carousel_001`・`DAM_GhostTrain_001`）の Slot の ID・位置・回転・拡縮が着手時のスナップショットと同じ |
| 見た目 | 撮影 14 枚。画像の欠け・反転・黒い面・透けなし。仮モデルは表示されない。排障器と線路の間に隙間（15.8） |
| 取付位置と ID | 取付位置 5 つが Slot として残り、差 0.0 m（`Att_Headlamp` は本文どおり動かした新しい位置と）。ID・部品名・階層は変えていない |
| 当たり判定 | 方針: 付けない（3 つの仮モデルとも可動部品の下で、W08 は `FixedCollision` を作っていない。15.2）。利用者の実機: メリーゴーラウンドと列車のまわりで「問題なし」 |
| 実測 | `verify_live.py` が M01〜M06・M08 の全 8 行で合格、A・B・C・D の数も一致（15.7） |
| 再適用 | 4 つの宣言の 2 回目の apply が書き込み 0。全 17 宣言の diff が 0。Slot・Component は増えない |
| 所有範囲 | diff の対象は 3 つの `visual_root` の下と資産、D の支柱のメッシュ・前照灯の取付位置・3 つの仮モデルの描画だけ。ほかの宣言は 0 |
| 負荷 | 遊園地の近くで 60 fps 前後（利用者の測定、W08 と同じ端末）。三角形 89,037（M05 74,233・M06 14,804）、画像 6（約 42 MB の見積もり）、光源 0、当たり判定 0 |
| テスト | `uv run pytest` 102 件が通る（9 章） |

## 6. 次の子（W09R-E #50、M07 魔法の時計塔）への注意と要望

### 6.1 次の子への注意

- `verify_live.py` は `REPLACEMENTS` の全行のバンドルを読む。新しい worktree では、Git の外の `p2_bundles/M02-20261031T164338Z`・`M04-20261101T022427Z`・`M08-20261101T022537Z`・`M01-20261101T042541Z`・`M03-20261101T052520Z`・`M05_CenterCasing-20261101T063625Z`・`M05_Canopy-20261101T063625Z`・`M06-20261101T063625Z` を `SHA256SUMS` で確かめてから、同じ名前の出力先へ写す。最初の diff と全宣言の diff は全 17 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M08）。この子の後の W08 の root の下は Slot 739・Component 1,677
- **`pivot_local` の基準は地区（作ったビルド）で違う**: W05（D）は親の部品からの位置（`Att_M05_Canopy` は TurnRoot から 3.154）だが、W06（E）の時計塔の針・鐘は親（`_HourHandPivot` など）と同じ値で、アセットの root からの位置に見える。`verify_live.py` の取付位置の期待値（`pivot_in_asset`）は親の部品の位置を足すので、親が root でない部品を E で検査に足すときは、基準を確かめてから使う（E の時計塔の取付位置は親が root なので、今の検査には影響しない）
- `REPLACEMENTS` の `source`・`export_root`・`asset_id`（`export_meshy.extract_part`）で、1 つの素材の子だけを別の Slot の下に置ける。M07 の文字盤を別に扱う必要が出たときに使える（M07 は 1 つのメッシュなので、子に分けるには M07 の `.blend` の変更が要る）
- `_Dial` の描画を止めるには、`hide_placeholders` の範囲の守り（`visual_root` か `moving_parts` の `motion_root` の下だけ）を広げる必要がある（#50 の本文）。この子は前照灯の目印で同じ判断になり、利用者の決定で止めなかった
- 屋根の下面の計測（`verify_live.py` の `_up_hits`）は、素材のメッシュ（バンドルの `*.mesh.json`、Resonite の軸）へ鉛直の線を当てる。M07 の文字盤の面と針の隙間を測るときにも使える
- `resoloop capture` は Resonite が背面にあると真っ黒になる（約 23 KB の JPEG）。撮影の前に利用者に前面へ出してもらい、撮った後にファイルの大きさを見る

### 6.2 要望（他の所有。この子は直していない）

- W05 の `handoff/W05.md`（統合役）: 支柱の長さ（上端 3.25 m）と前照灯の取付位置 `[0.0, 1.233, 1.498]` の値が古い。記録 15.3 を参照するように注記する
- W08 の `handoff/W08.md` 3.1（統合役）: M06 の行の「前照灯は 8 章の 3」は対応済み（記録 15.2）
- W07 の `docs/p1-handoff.md` 8 章の 2・3（統合役）: この子で対応済み
- P3（W10・W11）:
  - G13 の回転: 支柱・屋根・柱はすべて `TurnRoot` の下で一緒に回る。支柱の上端の値は屋根の向き（-90°）で測った値なので、屋根だけを別に回すと支柱の先が屋根から出る
  - G15 の前照灯の光は `Att_Headlamp` に置く。目印（金色の八角形）は電球のように見えるので、光を付けるときに描画を止めるかを決める
  - 回転床（`TurnRoot` の `Floor`）には当たり判定が無い（W08 の方針。乗ると土台の上面 0.36 m に立ち、床の見た目 0.55 m より 19 cm 沈む）。座席に乗れるようにするときに決める

## 7. 未確認・未解決

- 再読込の後に M05・M06 の画像が保たれるか（P4）
- 回転床・座席・列車を動かしたときの見え方（P3）。VR、二人以上

## 8. 次に触ってよい範囲と、上書きしてはいけない範囲

- 次に触ってよい: 後続の差し替えの子は `REPLACEMENTS` への自分の素材の行の追加と、その差し替えに要る検査の拡張。P3 は `TurnRoot`・`SeatRoot_*`・`EngineRoot`・`CarRoot_001` の動き、前照灯の光
- 上書きしてはいけない: 利用者が決めた支柱の扱い（屋根の下面まで伸ばす。値は記録 15.3）と前照灯の目印の扱い（描画を止めない）。M05 の向き（-90°）と、屋根と柱の組み立て（2.964 m）。前の子の素材の光源（M02・M08）、M01 の門扉の Slot、M03 の当たり判定。W08 の root の外、`Root` の直下の既定の物

## 9. テストの要否

- 足したテスト（どれも S。検査が誤ると、気付かないまま確認済みとして記録される）: `tests/test_p2_meshy_verify.py`
  - `test_canopy_off_its_centre_casing_is_detected`: 屋根の仮モデルが柱の仮モデルと違う高さにある（それぞれの行の検査は自分の仮モデルとしか比べないので見落とす）。正しい状態で通ることも確かめる
  - `test_pole_ending_below_the_canopy_is_detected`: 支柱の上端が屋根の下面に届かない（宙で止まって見える）。屋根の殻に 2 cm 入った正しい状態で通ることも確かめる
  - `test_pole_poking_out_of_the_canopy_is_detected`: 支柱の先が屋根の上に突き抜ける
  - `test_headlamp_attachment_inside_the_lamp_is_detected`: 前照灯の取付位置が W05 の旧い位置（ランプの中）のまま。新しい位置で通り、隙間 1.25 cm を返すことも確かめる
  - それぞれ守りを外すと、そのテストだけが失敗することを確かめた（変異ごとに `PYTHONPYCACHEPREFIX` を分けた）
- 書かなかったもの: 取付位置の期待値の直し（親の部品の位置を足す）は、誤ると正しい配置を失敗にする方向で、実行でエラーとして現れる（L）。`extract_part` の、子が無い・位置が `pivot_local` と違う・回っているときの停止はエラーで分かる（L）。材質と画像の集め方の誤りは validate の参照切れで分かり（L）、`split_part` が同じ結果になることは M01・M03・M08 の宣言の作り直しで確かめた。支柱・前照灯の値（D の定数）と `REPLACEMENTS` の値は設定の写し（F）で、実測の検査と撮影で確かめた
