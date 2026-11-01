# Handoff: W09R-E（Issue #50）— E 西の Meshy 素材の差し替え（M07 魔法の時計塔）

親 #1 の Spec §13「各タスクの引き継ぎに必須の項目」。詳しい記録は `docs/p2-meshy-replacement.md` 16 章（以下「記録」）。方式と手順は同じ文書の 2・4 章（W09R #44）。

## 1. 対象工程・アセット

- 工程: P2 の後続の差し替え（Spec §12「最終版：P4の完了条件」の「採用するMeshyモデルが統合済み」に向けた作業）。残りの 7 素材の 5 件のうち 5 件目で、差し替えの子の最後（順は C → A → B → D → E。2026-11-01 の利用者の決定）
- 対象: E 西・魔法の森の M07 魔法の時計塔（`EFR_ClockTower_001_Body` → `M07_ClockTower_001`）と、仮の文字盤 `EFR_ClockTower_001_Dial`（描画を止めた）。針・鐘・鐘の腕木は W06 の部品のまま
- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ
- 所要時間: claim 07:23:56Z から PR の作成まで約 50 分（Issue の更新・読み込みと前提の確認 約 10 分、全キーのビルド（並行して読み込み）約 6 分、形の照らし合わせと利用者の決定 約 5 分、最初の diff 約 3 分、実装（`replacements.py`・`verify_live.py`・テスト）約 12 分、export・diff・apply・実測・撮影 約 8 分、変異・記録 約 10 分）。利用者の確認・GPT のレビュー・保存・マージは PR の後

## 2. 今回完了したこと

1. 保存の後の最初の diff: 全 17 宣言で変更 0、資産の作り直し・重複なし（記録 16.1）
2. 仮の本体（今の当たり判定と同じ形）と M07 の形を Blender で照らし合わせた。正面の階段で最大約 0.8 m 浮き、壁・台座のまわりに 0.4〜1.3 m の見えない壁が出る（記録 16.2）
3. **利用者の決定（当たり判定「M07 のメッシュにする」）**: M07 のメッシュに `MeshCollider`、仮の本体の `FixedCollision` は `MeshCollider` だけ止めた（W09R-B の M03 と同じ形）
4. 仮の文字盤 `_Dial`（`_Body` の兄弟）の描画を止めた。`hide` の範囲は、地区の持ち主（W06）がアセット一覧の `replacement_slot.hide_on_replacement` に書いた兄弟にだけ広げた（`replacements.owner_hide_on_replacement`）
5. M07 を差し替えた。外接箱・原点の差 0.0 m、正面は東。2 回目の apply は書き込み 0、M07・E とも変更 0 で収束（記録 16.5・16.6）
6. `verify_live.py` に針の検査（`check_dial_hands`。回転軸と針の Slot が文字盤の中心の軸の上で軸と平行、針が回る範囲に M07 の面が無い）と、兄弟の `hide` の確認を足した。M01〜M08 の全 9 行で合格。テスト 3 件（記録 16.3、9 章）
7. GPT のレビュー（確認事項 7）: Major 3 件・Minor 2 件のうち、Major 2 件（大きな三角形が針の回る範囲を横切るのを見落とす、針の Slot のずれ・軸の傾きを見落とす）と Minor 1 件（8 章の表と 16.7 の食い違い）を採用して直した。採用しない 2 件の理由は記録 16.8
8. 利用者の実機: 時計塔のまわりと台座で当たり判定、文字盤と針の見え方とも「すべて問題ありません」、60 fps
9. 撮影 10 枚。黒い面・反転・透けなし、針は文字盤の中心の前（記録 16.7）
10. 後続の作業のために、apply したバンドルを Git の外の `p2_bundles/M07-20261101T073451Z` に控えた（記録 16.4）
11. これで採用する 8 素材（`received.json` の 9 行）の差し替えが終わった（記録 8 章の表）

## 3. 変更ファイルと版

- 基点: `main` の `7f2ffbf`
- 変更（差し替え）: `modeling/p2_meshy/replacements.py`（M07 の行、`owner_hide_on_replacement`、`hide_placeholders` の範囲）、`modeling/p2_meshy/verify_live.py`（記録 16.3）、`tests/test_p2_meshy_replacements.py`（1 件）、`tests/test_p2_meshy_verify.py`（2 件）、`review/p2_meshy/live_checks.json`（全 9 行の実測）、`docs/p2-meshy-replacement.md`（冒頭・4 章・8 章の M07 の行・11 章・16 章）
- 変更（閉じた子 W09-M07 の記録。記録 16.3）: `review/M07/checks.json` の `dial.w06`（W06 の今の針の軸との照合）と `review/M07/M07_dial_textured.png`。M07 のビルドの出力をそのまま。形は変えていない
- 追加: `exports/p2_meshy/M07-20261101T073451Z/` と `exports/p2_static/<key>-20261101T073124Z/`（6 キー）・`E_forest-20261101T073434Z/` の記録（`report.json`・`validate.json`・`placement.json`・`colliders.json`・`replacements.json`）、`review/p2_meshy/` の撮影 10 枚、この文書
- W06 の `E_forest`、W08 の `modeling/p2_static/`、W09-M07 の `modeling/M07/`・`assets/manifest/M07.json` は変えていない
- state: 親の checkout の `/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state/` に `p2m_M07.json` を足し、`p2_E_forest.json` を更新した。消すと次の apply が同じ物をもう一度作るので消さない
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1
- 保存（確認事項 4）: （記入待ち）

## 4. 再実行手順

記録 4 章。この子で使った形:

```sh
for key in world common A_plaza B_mansion C_candy D_amusement E_forest M07; do
  resoloop blender run modeling/$key/build.py --json || exit 2      # 全部で約 5 分
done
# Git の外の p2_bundles/<M>-<UTC>（M01〜M06・M08 の 8 つと、この子の M07）を SHA256SUMS で確かめ、同じ名前の exports/p2_meshy/ へ写す
uv run python modeling/p2_static/export_p2.py --url "$URL" --key E_forest            # 仮の本体・仮の文字盤・仮の当たり判定を止めた E
uv run python modeling/p2_meshy/export_meshy.py --url "$URL" --meshy M07
# スナップショット → diff → apply（素材は --texture-transfer data、state p2m_M07.json）→ E の diff・apply → 2 回目の diff・apply（記録 4 章）
uv run python modeling/p2_meshy/verify_live.py --url "$URL" --raw-out <Git の外> --output review/p2_meshy/live_checks.json
```

- 作り直して変わった追跡中の `.blend`・他のキーの確認画像と、ビルドが `export_result` を `unexported` に戻した `assets/manifest/M07.json` は、コミットの前に `git restore` で戻した（形は変えていない）
- `resoloop capture` の `<名前>.scene.json` は作業ツリーの絶対パスを含むので消した
- 形の照らし合わせ（記録 16.2）は、セッションの一時的なスクリプト（M07 の `.blend` に E の仮の本体を読み込み、上からと水平のレイを当てる）で行い、コミットしていない

## 5. 確認した内容と結果

| 受け入れ基準 | 結果 |
|---|---|
| 保存の後の最初の diff | 全 17 宣言で 0。world・E・M02 の資産は `resdb` への移行の no-op（記録 16.1） |
| export・validate | M07・E がオフライン・`--strict` で issues 0（16.4） |
| M07 | 世界の X × 高さ × Z で 7.578 × 14.000 × 8.239 m、`assets/manifest/M07.json` との差 0.0 m。正面は東（`placement_hint` -90）。仮の文字盤は描画なし（16.6） |
| 針 | 針・鐘・腕木の Slot の ID・親・原点・回転・拡縮は着手時と同じ（変えていない）。時針・分針の回転軸は文字盤の中心の軸の上（ずれ 0.0 m）、回る範囲に M07 の面は無く、後ろとの隙間は時針 1.25 cm（軸受け）・分針 4.65 cm。針の Slot は回転軸の Slot の原点にあり、向きは軸と平行。撮影でも針は文字盤の前（`m07_dial`・`m07_dial_oblique`）。利用者の実機でも問題なし |
| 全素材 | M01〜M08 の差し替えが済み、記録 8 章の表を更新した |
| 見た目 | 撮影 10 枚。画像の欠け・反転・黒い面・透けなし。仮の本体・仮の文字盤は表示されない（16.7） |
| 取付位置と ID | E の時計塔に取付位置は無い。仮モデルの Slot（`EFR_ClockTower_001` と子 10 個）は着手時と同じ位置・ID。アセットの ID・部品名は変えていない |
| 当たり判定 | 方針: M07 のメッシュ（利用者の決定、理由は記録 16.2）。利用者の実機（デスクトップ、時計塔のまわりと台座の階段）: 「すべて問題ありません」 |
| 実測 | `verify_live.py` が M01〜M08 の全 9 行で合格、A〜E の数も一致（16.6） |
| 再適用 | M07・E の 2 回目の apply が書き込み 0、2 回目の diff が 0。Slot・Component は増えない（W08 の root の下は 745・1,684 のまま） |
| 所有範囲 | diff の対象は M07 の `visual_root` の下と資産、E の仮の本体・仮の文字盤の描画と仮の本体の当たり判定だけ。ほかの宣言は 0 |
| 負荷 | 時計塔の近くで 60 fps（利用者の測定、W08 と同じ端末）。三角形 30,633、画像 2（色 2048・詰めた PBR 1024、約 28 MB の見積もり）、光源 0、当たり判定 1（M07 のメッシュ） |
| テスト | `uv run pytest` 107 件が通る（9 章） |

## 6. 次の子への注意と要望

差し替えの子はこれで最後（次の差し替えの子は無い）。P3・P4 と統合役への注意。

### 6.1 注意

- 8 素材の差し替えの宣言は全 18（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M07・M08）。新しい worktree で `verify_live.py` を実行するときは、Git の外の `p2_bundles/` の 9 つ（M01・M02・M03・M04・M05_CenterCasing・M05_Canopy・M06・M07・M08）を `SHA256SUMS` で確かめてから、同じ名前の出力先へ写す。W08 の root の下は Slot 745・Component 1,684
- 当たり判定を M07 のメッシュにした（M03 と同じ）。M07 の斜めの輪・浮かぶ球・吊りランタンにも当たり判定があるが、高さ 5 m 以上で歩いて触れない
- 時計の針（P3 の G20）: 回転軸は M07 の文字盤の中心にある（軸のずれ 0.0 m）。時針の後ろの面と M07 の軸受けの隙間は 1.25 cm で、針を軸に沿って後ろへ動かすと軸受けにめり込む。`verify_live.py` の `check_dial_hands` は回す位置によらずめり込みを確かめるので、針の形を変えたら実行する
- `hide` の範囲を `visual_root` の外へ広げられるのは、地区のアセット一覧の `replacement_slot.hide_on_replacement` に書いた兄弟だけ（`replacements.owner_hide_on_replacement`）。今これを持つのは E の時計塔の `_Dial` だけ
- `review/M07/checks.json` の `dial.w06` は、M07 のビルドのたびに W06 のアセット一覧の針の軸と照合し直す（W07 の直しの後は軸のずれ 0.0）

### 6.2 要望（他の所有。この子は直していない）

- W06 の `modeling/E_forest/clock_tower.py`（統合役か P3）: 鐘の腕木の板（`BellBracket`）は、北から見ると上の部分と M07 の鐘楼の壁の間に隙間がある（`review/p2_meshy/m07_bell_side.jpg`。下の端は M07 の正面の破風に乗る）。G20 で鐘を鳴らすときに、腕木を壁まで伸ばすか板を後ろへ足すかを決める（鐘の吊り点 `_BellPivot` は変えない）
- W06 の `modeling/E_forest/layout.py` の説明（統合役）: 「W01 の床は x = -42.25 まで」は W08 で x = -34.711 まで（`handoff/W08.md` の要望のまま）
- W06 の `handoff/W06.md` 6 章（統合役）: `_Dial` の扱いと時計塔の当たり判定は記録 16.2 で決めた
- 照明（P3・P4）: 文字盤が近くの照明で緑がかって見える（`m07_dial`）。照明の調整のときに見る

## 7. 未確認・未解決

- 再読込の後に M07 の画像と当たり判定が保たれるか（P4）
- 針・鐘を動かしたときの見え方（P3 の G20）、VR、二人以上

## 8. 次に触ってよい範囲と、上書きしてはいけない範囲

- 次に触ってよい: P3 は `_HourHandPivot`・`_MinuteHandPivot`・`_BellPivot` の動き、鐘の腕木（6.2）。P4 は保存と再読込の確認
- 上書きしてはいけない: 利用者が決めた時計塔の当たり判定（M07 のメッシュ）。針・鐘の回転軸の位置（W07 が M07 の文字盤の中心に合わせた値）。前の子の素材の光源（M02・M08）、M01 の門扉の Slot、M03 の当たり判定、M05 の支柱と前照灯の扱い。W08 の root の外、`Root` の直下の既定の物

## 9. テストの要否

- 足したテスト（どれも S。検査や処理が誤ると、気付かないまま物が消える・確認済みとして記録される）
  - `tests/test_p2_meshy_replacements.py::test_only_a_sibling_listed_by_the_district_owner_can_be_hidden`: 地区の持ち主が `hide_on_replacement` に書いた兄弟は描画を止められ、書いていない兄弟（針・鐘に当たる物）は拒否する。広げた範囲が書き間違いで針や鐘を黙って消さないための守り。正しく通る例を含む
  - `tests/test_p2_meshy_verify.py::test_hand_sunk_into_the_dial_is_detected`: 針の前後の範囲に文字盤の面（軸受け）が入る（めり込む）。GPT のレビューの反例（頂点・辺の中点・重心がどれも回る半径の外にある大きな三角形が、針の前後の範囲で円を横切る）も同じ守りの代表として含む。正しい位置で通り、隙間 1.5 cm を返すことも確かめる
  - `tests/test_p2_meshy_verify.py::test_hand_axis_off_the_dial_centre_is_detected`: 針の回転軸が文字盤の中心の軸から 3 cm ずれる。GPT のレビューの指摘 2 の、針の Slot が回転軸の Slot から 0.3 m ずれる・回転軸の向きが傾く場合も含む
  - それぞれ守りを外すと、そのテストだけが失敗することを確かめた（めり込みの判定・軸のずれの判定・回る範囲の面の選び方（点で選ぶ形に戻す）・針の Slot のずれ・軸の平行・兄弟の制限・範囲の広げ方の変異。変異ごとに `PYTHONPYCACHEPREFIX` を分けた）
- 書かなかったもの: `verify_live.py` で兄弟の `hide` を探す処理は、誤ると `_Dial` が見つからず検査が失敗する（L）。`owner_hide_on_replacement` がアセット一覧を読めないときは範囲が広がらず `hide_placeholders` がエラーで止まる（L）。M07 の行の値と撮影のカメラは設定の写し（F）で、実測の検査と撮影で確かめた
