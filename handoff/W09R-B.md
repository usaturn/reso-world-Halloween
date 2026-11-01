# Handoff: W09R-B（Issue #48）— B 北の Meshy 素材の差し替え（M03 幽霊屋敷の外観）

親 #1 の Spec §13「各タスクの引き継ぎに必須の項目」。詳しい記録は `docs/p2-meshy-replacement.md` 14 章（以下「記録」）。方式と手順は同じ文書の 2・4 章（W09R #44）。

## 1. 対象工程・アセット

- 工程: P2 の後続の差し替え（Spec §12「最終版：P4の完了条件」の「採用するMeshyモデルが統合済み」に向けた作業）。残りの 7 素材の 5 件のうち 3 件目（順は C → A → B → D → E。2026-11-01 の利用者の決定）
- 対象: B 北・おばけ屋敷の M03 幽霊屋敷の外観（`BMN_MansionPlaceholder_001` → `M03_HauntedMansion_001`）と、W03 の扉 `BMN_MansionDoubleDoor_001`（G06）・玄関ホール `BMN_EntranceHall_001`・中庭の地面 `BMN_CourtyardGround_001`
- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ
- 所要時間: claim 05:07:29Z から（成果の提出の時刻と内訳は 3 章の最後）

## 2. 今回完了したこと

1. 保存の後の最初の diff: 全 13 宣言で変更 0、資産の作り直し・重複なし（記録 14.1）
2. M03 の仕上げた形を測り直し、本文の前提と違う 2 点を利用者に確かめた（記録 14.2、#48 のコメント）
   - **利用者の決定**: W03 のポーチの階段（上端 z 1.779）を外し、中庭の石畳を M03 自身の段の前まで延ばす（M03 の段 z 1.68 → ポーチ 1.870 で上がる）
   - **利用者の決定**: 当たり判定は M03 のメッシュ（29,801 三角形の `MeshCollider`）。仮モデルの `FixedCollision` は Slot を残して `MeshCollider` を止める
3. W03 の扉・玄関ホールを x +0.3725 m・z +0.091 m 動かし（蝶番は M03 の開口の蝶番の線 x -0.1015・1.5165、z 1.870）、扉の高さを 2.592 m にした。可動部品の旧 → 新は記録 14.2 の表
4. M03 を差し替えた。外接箱の差 0.0 m、正面は南、扉の蝶番とホールは M03 の開口と差 2.3 mm。2 回目の diff・apply は変更 0・書き込み 0、全 14 宣言が変更 0 で収束（記録 14.6・14.7）
5. `verify_live.py` に、素材のメッシュの当たり判定（`collision: "finished"`）と入口（扉の蝶番・ホール）の検査を足した。テスト 5 件（記録 14.4・9 章）
6. 撮影 11 枚。黒い面・反転・透けなし（記録 14.8）
7. 後続の子のために、apply した M03 のバンドルを Git の外の `p2_bundles/M03-20261101T052520Z` に控えた

## 3. 変更ファイルと版

- 基点: `main` の `4f2baa4`
- 変更（差し替え）: `modeling/p2_meshy/replacements.py`（M03 の行、`collision: "finished"`・`entrance`、`disable_fixed_collisions`）、`modeling/p2_meshy/export_meshy.py`（`add_mesh_colliders`）、`modeling/p2_meshy/verify_live.py`（記録 14.4）、`tests/test_p2_meshy_verify.py`（4 件）、`tests/test_p2_meshy_replacements.py`（1 件）、`review/p2_meshy/live_checks.json`（M01・M02・M03・M04・M08 の実測）、`review/p2_meshy/overview_south.jpg`（撮り直し）、`docs/p2-meshy-replacement.md`（冒頭・4 章・8 章の M03 の行・11 章・14 章）
- 変更（閉じた子 W03 の所有。記録 14.3）: `modeling/B_mansion/layout_data.py`・`build.py`、生成物の `layout/areas/B_mansion.json`・`assets/manifest/B_mansion.json`・`review/B_mansion/*.png`
- 追加: `exports/p2_meshy/M03-20261101T052520Z/` と `exports/p2_static/<key>-20261101T051336Z/`（6 キー）・`B_mansion-20261101T052512Z/` の記録（`report.json`・`validate.json`・`placement.json`・`colliders.json`・`replacements.json`）、`review/p2_meshy/` の M03 の撮影 10 枚と `area_B_mansion.jpg`、この文書
- W09-M03 の `M03`、W08 の `modeling/p2_static/` は変えていない
- state: 親の checkout の `/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state/` に `p2m_M03.json` を足し、`p2_B_mansion.json` を更新した。消すと次の apply が同じ物をもう一度作るので消さない
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1
- 保存（確認事項 4）: （記録待ち）

## 4. 再実行手順

記録 4 章。この子で使った形:

```sh
for key in world common A_plaza B_mansion C_candy D_amusement E_forest M03; do
  resoloop blender run modeling/$key/build.py --json || exit 2      # D_amusement・E_forest は --arg=--no-render で速くなる
done
# Git の外の p2_bundles/<M>-<UTC>（M01・M02・M04・M08・M03）を SHA256SUMS で確かめ、同じ名前の exports/p2_meshy/ へ写す
uv run python modeling/p2_static/export_p2.py --url "$URL"                # 6 キー（B は扉・ホールを動かし、仮モデルの描画と当たり判定を止める）
uv run python modeling/p2_meshy/export_meshy.py --url "$URL" --meshy M03  # p2m.apply.json（M03 のメッシュに MeshCollider）
# スナップショット → diff → apply（M03 は --texture-transfer data、state p2m_M03.json）→ B の diff・apply → 2 回目の diff・apply（記録 4 章）
uv run python modeling/p2_meshy/verify_live.py --url "$URL" --raw-out <Git の外> --output review/p2_meshy/live_checks.json
```

- 作り直して変わった追跡中の `.blend`・他のキーの確認画像と、ビルドが `export_result` を `unexported` に戻した `assets/manifest/M03.json` は、コミットの前に `git restore` で戻した（形は変えていない）。B の確認画像は形を変えたのでコミットした
- `resoloop capture` の `<名前>.scene.json` は作業ツリーの絶対パスを含むので消した
- M03 の形の測り直し（記録 14.2）は、セッションの一時的なスクリプト（M03 の `.blend` に対するレイと断面）で行い、コミットしていない。値は記録 14.2 にある

## 5. 確認した内容と結果

| 受け入れ基準 | 結果 |
|---|---|
| 保存の後の最初の diff | 全 13 宣言で 0。world・B・D・E・M02 の資産は `resdb` への移行の no-op（記録 14.1） |
| export・validate | M03 と B がオフライン・`--strict` で issues 0（14.5） |
| M03 | 外接箱の差 0.0 m（15.0001 × 10.6069 × 10.2206 m）、正面は南 (0, 0, −1) |
| 入口 | 扉の蝶番 2 つとホールの原点が M03 の開口と差 2.3 mm（1 cm 以内）、扉の面は壁と平行（14.7）。開口の縁は扉の枠が覆い、隙間・透けなし（撮影）。ポーチの段から入口まで: （利用者の実機の確認待ち）。**本文と違う点**: 本文の「ポーチの階段の上端を z 1.870」は M03 の形と合わないので、利用者の決定で W03 の階段を外し、M03 自身の段で上がる形にした（14.2） |
| 見た目 | 撮影 11 枚。画像の欠け・反転・黒い面・透けなし。仮モデルは表示されない。W03 の窓のおばけ（G08）の窓枠が M03 の窓と合わない（P3 の範囲。6.2） |
| 取付位置と ID | 仮モデルに取付位置は無い。動かしたのは本文で書いた扉・ホール（とホールの子の `_ChandelierHook`）だけ。ID・部品名・階層は変えていない |
| 当たり判定 | 方針: M03 のメッシュ（利用者の決定、14.2）。実測で仮モデルの当たり判定が無効・M03 の当たり判定が有効を確認。利用者の実機: （記録待ち） |
| 実測 | `verify_live.py` が M01・M02・M03・M04・M08 で合格、A・B・C の数も一致（14.7） |
| 再適用 | M03・B の 2 回目の diff が 0、apply が書き込み 0。全 14 宣言が 0。Slot・Component は増えない |
| 所有範囲 | diff の対象は M03 の `visual_root` の下と資産、B の扉・ホール・中庭の地面・仮モデルの描画と当たり判定だけ。ほかの宣言は 0 |
| 負荷 | （記録待ち）。三角形 29,801、画像 2（約 112 MB の見積もり）、`MeshCollider` 1（29,801 三角形）、光源 0 |
| テスト | `uv run pytest` 94 件が通る（9 章） |

## 6. 次の子（W09R-D #49、M05 メリーゴーラウンド・M06 おばけ列車）への注意と要望

### 6.1 次の子への注意

- `verify_live.py` は `REPLACEMENTS` の全素材のバンドルを読む。新しい worktree では、Git の外の `p2_bundles/M02-20261031T164338Z`・`M04-20261101T022427Z`・`M08-20261101T022537Z`・`M01-20261101T042541Z`・`M03-20261101T052520Z` を `SHA256SUMS` で確かめてから、同じ名前の出力先へ写す。最初の diff と全宣言の diff は全 14 宣言（`content/main.json`・6 キー・M02・M04・M08・M01 の 3 つ・M03。state `p2m_M03.json`）
- `docs/p1-handoff.md` 8 章の値を信じる前に、仕上げた素材の実際の形を測る。この子では、M03 のポーチの床が仮モデルの前端まで来ている前提（「階段の上端を z 1.870」）が外れていた（M03 自身の段があり、前端は 0.67 m 奥）。M05 の支柱を屋根の下面まで伸ばす件（8 章の 2）も、屋根の下面の実際の高さを支柱の位置で測ってから決める
- 仮モデルの当たり判定が仕上げた形と大きく違うときは、`REPLACEMENTS` の `collision: "finished"` で素材のメッシュを当たり判定にできる（記録 14.4）。ただし可動部品（W08 は `motion_roots` の下に当たり判定を付けない）には使わない。M05・M06 は P3 で動く物なので、W08 の `colliders.json` で仮モデルに `FixedCollision` があるかを先に確かめる
- 閉じた子（W05）の配置を動かすときは、この子の B と同じく、値を定数にまとめて配置データとビルドの両方から使い、`verify_live.py` には素材の実測（`review/<M>/checks.json`）から求めた期待値の検査を足すと、配置の値の誤りを同じ値で合格にしない（記録 14.4 の `entrance`）
- W08 の `modeling/p2_static/verify_live.py` は W07 の `review/overview/checks.json` の `motion_parts` と比べるので、この子の後は G06 の蝶番の 2 行が 0.37 m ずれて失敗する（W09R-A の門扉と同じく、W07 のデータは直していない。6.2）。W08 の検査を実行し直すときは、この 2 行を記録 14.2 の値で読む

### 6.2 要望（他の所有。この子は直していない）

- W07（統合役）: `review/overview/checks.json` の `motion_parts` の `BMN_MansionDoubleDoor_001_HingeLeft`・`_HingeRight` の `pivot_world` と `assets/manifest.json` の B の値を、記録 14.2 の新しい値に揃える（W09R-A の門扉の Slot の置き直しと同じ扱いを決める）
- W03 の `handoff/W03.md` 6 章（統合役）: 扉・ホールの位置、ポーチの階段（外した）、ポーチの床の高さの値が古い。記録 14.2 を参照するように注記する
- P3（W10・W11）:
  - G08 の窓のおばけ（`BMN_WindowGhost_001`・`_002`、(±4.2, 37.35, 4.8)）の窓枠は仮モデルの窓に合わせた物で、M03 の窓と合わず手前に浮き、東の枠は張り出しの屋根に刺さる（`m03_front`・`m03_oblique_se`）。窓の顔出しを作るときに、M03 の窓の位置へ動かすか、窓枠の描画を止める
  - G06 の扉: B の宣言は蝶番の Slot の回転（閉 0°）を書いているので、P3 が開いた後に B を再 apply すると閉じた形に戻る（W09R-A の門扉と同じ）。扉を開いたときに開口の奥が玄関ホールで塞がれて見えるかは、Resonite では扉を閉じたまま確かめていない（ホールの箱の中に M03 の面が無いことは Blender で確かめた）
- W03 か P4: 中庭の石畳の北の端（y 36.4）と延長の東西の端に、W01 の台地との 6.5 cm の段が見える（仮モデルの台座が隠していた所。`m03_porch_steps`）。気になるなら、石畳を M03 の正面まで広げる

## 7. 未確認・未解決

- 再読込の後に M03 の画像と当たり判定が保たれるか（P4）
- 扉を開いたときの開口の奥の見え方（P3）。VR、二人以上

## 8. 次に触ってよい範囲と、上書きしてはいけない範囲

- 次に触ってよい: 後続の差し替えの子は `REPLACEMENTS` への自分の素材の行の追加と、その差し替えに要る検査の拡張。P3 は `_HingeLeft`・`_HingeRight` の Slot の回転（閉 0°〜内開き ±85°）と G08 の窓枠
- 上書きしてはいけない: 利用者が決めた当たり判定の方針（M03 のメッシュ、仮モデルの `FixedCollision` は無効）とポーチへの上がり方（W03 の階段を外し、M03 の段で上がる）。扉の蝶番の位置（M03 の開口の蝶番の線）。前の子の素材の光源（M02・M08）と M01 の門扉の Slot。W08 の root の外、`Root` の直下の既定の物

## 9. テストの要否

- 足したテスト（どれも S。検査や宣言の後処理が誤ると、気付かないまま確認済みとして記録されるか、当たり判定が黙って消える）:
  - `tests/test_p2_meshy_verify.py`
    - `test_placeholder_collider_left_enabled_is_detected_for_a_finished_asset_collision`: 仮モデルの `FixedCollision` の当たり判定が残っている（中央のアーチに見えない柱）。正しい状態で通ることも確かめる
    - `test_finished_asset_without_its_collider_is_detected`: M03 に当たり判定が無い（壁をすり抜ける）
    - `test_entrance_door_off_the_opening_is_detected`: 扉が P1 の位置（開口から 0.37 m）のまま。正しい状態で通ることも確かめる
    - `test_entrance_hall_off_the_opening_is_detected`: ホールが開口に付いてこない
  - `tests/test_p2_meshy_replacements.py`
    - `test_only_the_replacements_fixed_collision_is_disabled`: 地区の宣言で止めるのは、差し替えた仮モデルの `FixedCollision` の当たり判定だけ（地面やほかの仮モデルの当たり判定を止めると、実測の検査では見えずに落ちる・すり抜ける）
  - それぞれ守りを外すと、そのテストだけが失敗することを確かめた（変異ごとに `PYTHONPYCACHEPREFIX` を分けた）
- 書かなかったもの: `add_mesh_colliders` が当たり判定を付け損ねると、`verify_live.py` の `test_finished_asset_without_its_collider_is_detected` の守りが同じ損害を見つける（D）。`disable_fixed_collisions` の、Slot が無い・兄弟でない・`MeshCollider` が無いときの停止はエラーで分かる（L）。扉の面と壁の平行の検査は、扉の root が回れば蝶番の位置の検査で見つかる（D）。B の扉・ホールの位置・高さと中庭の地面の値は、配置データの写し（F）で、実測の入口の検査と撮影で確かめた。`REPLACEMENTS` の値は設定の写し（F）
