# Handoff: W09R-C（Issue #46）— C 東の Meshy 素材の差し替え（M04 お菓子工房・M08 ほうきに乗った魔女）

親 #1 の Spec §13「各タスクの引き継ぎに必須の項目」。詳しい記録は `docs/p2-meshy-replacement.md` 12 章（以下「記録」）。方式と手順は同じ文書の 2・4 章（W09R #44）。

## 1. 対象工程・アセット

- 工程: P2 の後続の差し替え（Spec §12「最終版：P4の完了条件」の「採用するMeshyモデルが統合済み」に向けた作業）。残りの 7 素材の 5 件のうち最初（順は C → A → B → D → E。2026-11-01 の利用者の決定）
- 対象: C 東・キャンディストリートの M04 魔女のお菓子工房の外観（`CCD_M04_CandyWorkshopProxy_001` → `M04_WitchCandyWorkshop_001`）と M08 ほうきに乗った魔女（`CCD_M08_FlyingWitchProxy_001` → `M08_FlyingWitch_001`）
- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ

## 2. 今回完了したこと

1. 保存の後の最初の diff: 全宣言で資産の作り直し・重複なし。資産の URL が `resdb:///` に移った後の再 apply も no-op（W09R で未確認だった項目。記録 12.1）
2. M04・M08 を W09R の方式で差し替えた。外接箱・原点・正面が期待値と差 0.0 m、2 回目の diff・apply は変更 0・書き込み 0、全 10 宣言が変更 0 で収束（記録 12.5・12.6）
3. `verify_live.py` を、当たり判定を付けない素材・`placement_hint` に回転が無い素材・発光の画像を持つ素材に対応させた（記録 12.3。テスト 1 件）
4. 利用者の確認「暗くて見えにくい」に対応して、M08 に影なしの点光源 2 つを足した（利用者が「このままでよい」）
5. 利用者がデスクトップで M04 のまわりを歩き、当たり判定に問題なし。fps は 60 前後（W08 の基準と同じ）
6. 後続の子のために、apply した M04・M08 のバンドルを Git の外の `p2_bundles/` に控えた

## 3. 変更ファイルと版

- 基点: `main` の `b07d52a`
- 変更: `modeling/p2_meshy/replacements.py`（M04・M08 の行）、`modeling/p2_meshy/verify_live.py`（記録 12.3）、`tests/test_p2_meshy_verify.py`（1 件）、`review/p2_meshy/live_checks.json`（M02・M04・M08 の実測）、`docs/p2-meshy-replacement.md`（冒頭・4 章・8 章の M04・M08 の行・11 章・12 章）
- 追加: `exports/p2_meshy/M04-20261101T022427Z/`・`M08-20261101T022537Z/` と `exports/p2_static/<key>-20261101T022203Z/`（6 キー）の記録（`report.json`・`validate.json`・`placement.json`・`colliders.json`・`replacements.json`）、`review/p2_meshy/` の撮影 10 枚、この文書
- 閉じた子の所有ファイル（W04・W09-M04・W09-M08・W08）は変えていない
- state: 親の checkout の `/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state/` に `p2m_M04.json`・`p2m_M08.json` を足し、`p2_C_candy.json` を更新した。消すと次の apply が同じ物をもう一度作るので消さない
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1
- 保存（確認事項 4）: 〔保存の後に記入〕

## 4. 再実行手順

記録 4 章。この子で使った形:

```sh
for key in world common A_plaza B_mansion C_candy D_amusement E_forest M04 M08; do
  resoloop blender run modeling/$key/build.py --json || exit 2      # D_amusement・E_forest は --arg=--no-render で速くなる
done
uv run python modeling/p2_static/export_p2.py --url "$URL"           # 6 キー（C は M04・M08 の描画を止める）
uv run python modeling/p2_meshy/export_meshy.py --url "$URL" --meshy M04
uv run python modeling/p2_meshy/export_meshy.py --url "$URL" --meshy M08
# 光源・カメラだけを変えるときは --recompose exports/p2_meshy/M08-<UTC>
# スナップショット → diff → apply（素材は --texture-transfer data）→ 2 回目の diff・apply（記録 4 章）
cp <p2_bundles/M02-20261031T164338Z の追跡していないファイル> exports/p2_meshy/M02-20261031T164338Z/   # verify_live の前（記録 4 章）
uv run python modeling/p2_meshy/verify_live.py --url "$URL" --raw-out <Git の外> --output review/p2_meshy/live_checks.json
```

- 作り直した追跡中の `.blend`・確認画像と、ビルドが `export_result` を `unexported` に戻した `assets/manifest/M04.json`・`M08.json` は、コミットの前に `git restore` で戻した（形は変えていない）

## 5. 確認した内容と結果

| 受け入れ基準 | 結果 |
|---|---|
| 保存の後の最初の diff | C の更新 2（仮モデルの描画）のほかは全宣言で 0。`resdb` への移行も no-op（記録 12.1） |
| export・validate | M04・M08・C ともオフライン・`--strict` で issues 0（12.4） |
| M04 | 外接箱の差 0.0 m、土台の下面が地面（高さ -0.0001）、正面は西 (-1, 0, 0)。窓の発光は窓だけ（`m04_front` など） |
| M08 | 外接箱の差 0.0 m（仮モデルの置き方で置いた値）、正面は北 (0, 0, 1)（巡回の点 0 の接線、W07 の `front_world`）。当たり判定なし |
| 見た目 | 撮影 10 枚。欠け・反転・黒い面・透けなし。仮モデルは表示されない |
| 取付位置と ID | M04・M08 に取付位置は無い。ID・部品名・可動部品は変えていない |
| 当たり判定 | M04 は仮モデルの形の `FixedCollision`（外接箱は同じ）。利用者の歩行で問題なし。M08 は付けない |
| 実測 | `verify_live.py` が M02・M04・M08 で合格、A・C の数も一致（12.6） |
| 再適用 | 2 回目の diff は全 10 宣言で 0、M04・M08・C の 2 回目の apply は書き込み 0。Slot・Component は増えない |
| 所有範囲 | diff の対象は M04・M08 の `visual_root` の下と資産、C の仮モデルの描画 2 件だけ。ほかの宣言は 0 |
| 負荷 | 60 fps 前後。三角形 61,832、画像 5（約 40.6 MB）、点光源 2 |
| テスト | `uv run pytest` が通る（記録の 9 章のテストの要否） |

## 6. 次の子（W09R-A #47、M01 入場ゲート）への注意と要望

### 6.1 次の子への注意

- `verify_live.py` は `REPLACEMENTS` の全素材のバンドルを読む。新しい worktree では、Git の外の `p2_bundles/M02-20261031T164338Z`・`M04-20261101T022427Z`・`M08-20261101T022537Z` を `SHA256SUMS` で確かめてから、同じ名前の出力先へ写す（バンドルと画像はコミットしない）
- 当たり判定を付けない素材は `collision: False`、`placement_hint` に回転が無い素材は W07 の `front_world` から向きを求める（M06 は W09R-D で使う）。M01 の門扉のように 1 素材で可動部品の下にも置く場合は、今の `REPLACEMENTS` の形（1 素材 = 1 `visual_root`）では足りないので、行の形を決める
- A は M02 に続く 2 素材目。`check_counts` は A の全素材の宣言を足して比べる
- 保存の後は資産の URL が `resdb:///` に移り、resoloop は no-op と判定する（12.1）。最初の diff で、作り直し・重複が無いことを確かめる
- 撮影のカメラは、手前の建物に遮られないかを撮ってから確かめる（`m08_from_street` は最初の位置で M04 の屋根に隠れた）

### 6.2 要望（他の所有。この子は直していない）

- W01 の `world`（`modeling/world/build.py` の `build_east_bridge`）: 東の連絡橋の床 `WLD_EastBridge_001` が工房の下を通って x 42.25 まで伸び、工房の裏（x 40.68）から 1.57 m・高さ 6 cm はみ出して見える（利用者の指摘、`m04_back`）。西の時計塔の同じ形は W08 が床を塔の東の面で止めて直した。東も床を工房の中（例 x 38）で止める。利用者の決定（2026-11-01）で、この子では記録だけにして後で直す（P4 の外観の確認などで、`world` を作り直して apply する）
- P3 の G11: M08 の光源 2 つ（`$component:m08_front_glow_light`・`m08_under_glow_light`、state `p2m_M08.json`）は M08 の Slot の子なので一緒に動く。航跡・発光を足すときは、光源の数と明るさを合わせて見直す
- P3: M04 の窓の発光は昼も光る（`EmissiveColor` が白）。夜だけ光らせるなら `EmissiveColor` を駆動する（`handoff/W09-M04.md` 8 章）

## 7. 未確認・未解決

- 保存（確認事項 4）の後の M04・M08 の状態（3 章の保存の記録）。再読込の後に画像・光源が保たれるかは P4
- M08 が巡回しているときの見え方（P3）、VR、二人以上
- 6.2 の東の床のはみ出し（記録だけ）

## 8. 次に触ってよい範囲と、上書きしてはいけない範囲

- 次に触ってよい: 後続の差し替えの子は `REPLACEMENTS` への自分の素材の行の追加と、その差し替えに要る検査の拡張。P3 は M04 の材質の `EmissiveColor`、M08 の光源の `Intensity`
- 上書きしてはいけない: 利用者が確かめた M08 の光源 2 つの位置・色・強さ（2026-11-01 に「このままでよい」）、W09R の M02 の光源。W08 の root の外、`Root` の直下の既定の物

## 9. テストの要否

- 足したテスト: `tests/test_p2_meshy_verify.py` の `test_replacement_without_collision_fails_while_the_placeholder_still_has_one`（S。`collision: False` は当たり判定の検査を飛ばすので、仮モデルに `FixedCollision` が残る素材に誤って付けると、壊れた当たり判定を確認済みとして記録してしまう）。正しい状態で通る例を含み、守りを外すと失敗することを確かめた
- 書かなかったもの: `placement_hint` が無い素材の向き（誤れば M04 か M08 の正面の検査が失敗して分かる。L）、発光の画像の参照（撮影で窓が光らないことで分かる。L）、`REPLACEMENTS` の値（設定の写しで F）
