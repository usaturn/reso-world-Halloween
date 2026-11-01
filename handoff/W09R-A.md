# Handoff: W09R-A（Issue #47）— A 中央広場の Meshy 素材の差し替え（M01 入場ゲート）

親 #1 の Spec §13「各タスクの引き継ぎに必須の項目」。詳しい記録は `docs/p2-meshy-replacement.md` 13 章（以下「記録」）。方式と手順は同じ文書の 2・4 章（W09R #44）。

## 1. 対象工程・アセット

- 工程: P2 の後続の差し替え（Spec §12「最終版：P4の完了条件」の「採用するMeshyモデルが統合済み」に向けた作業）。残りの 7 素材の 5 件のうち 2 件目（順は C → A → B → D → E。2026-11-01 の利用者の決定）
- 対象: A 中央広場の入口の M01 ハロウィン入場ゲート（`APL_EntranceGateProxy_001` → `M01_EntranceGate_001`。アーチ `M01_GateArch_001` と門扉 2 枚 `M01_GateLeafLeft_001`・`M01_GateLeafRight_001`）
- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ
- 所要時間: claim 03:27:56Z から PR の作成まで約 1 時間 30 分（読み込みと前提の確認 約 15 分、全キーのビルドと最初の diff 約 15 分（利用者への確認の待ちを含む）、門扉の置き方の調査と利用者の決定 約 10 分、実装（`replacements.py`・`export_meshy.py`・`verify_live.py`）約 20 分、export・diff・apply・実測・撮影 約 10 分、利用者の実機の確認 約 5 分、テストと変異の確認 約 5 分、記録 約 10 分）

## 2. 今回完了したこと

1. 保存の後の最初の diff: 全 10 宣言で変更 0、資産の作り直し・重複なし（記録 13.1）
2. M01 を差し替えた。resoloop の宣言は 1 つの親の下にしか置けないので、アーチ（`_Arch` の下）と門扉 2 枚（`_DoorLeft`・`_DoorRight` の下）を 3 つの宣言に分けた（記録 13.2）
3. **利用者の決定**で、仮モデルの門扉の Slot を M01 の蝶番へ動かし（左 15.3 cm・右 12.9 cm）、回転を ±88° → ±90° にした。Slot・ID・階層は作り直していない。P3 はこの Slot を閉 0°〜開 ±90° で回す（記録 13.2）
4. 外接箱は期待値と差 0.2 mm、門扉の Slot と門扉の原点は M01 の蝶番と差 0.0 m、正面は南。2 回目の diff・apply は変更 0・書き込み 0、全 13 宣言が変更 0 で収束（記録 13.5・13.6）
5. `verify_live.py` を、メッシュが素材の子にある素材と、可動部品（門扉）に対応させた。テスト 4 件（記録 13.3）
6. 利用者がデスクトップでゲートをくぐり、柱・袖の壁・門扉のまわりを歩いて「問題なし」。fps は 60 前後（W08 の基準と同じ）
7. 後続の子のために、apply した M01 のバンドルを Git の外の `p2_bundles/M01-20261101T042541Z` に控えた

## 3. 変更ファイルと版

- 基点: `main` の `b8c3ee0`
- 変更: `modeling/p2_meshy/replacements.py`（M01 の行、`moving_parts`・`moving_part_poses`・`repose_motion_roots`、`hide` の範囲）、`modeling/p2_meshy/export_meshy.py`（部品ごとの宣言）、`modeling/p2_meshy/verify_live.py`（記録 13.3）、`tests/test_p2_meshy_verify.py`（4 件）、`review/p2_meshy/live_checks.json`（M01・M02・M04・M08 の実測）、`review/p2_meshy/overview_south.jpg`（撮り直し）、`docs/p2-meshy-replacement.md`（冒頭・4 章・8 章の M01 の行・11 章・13 章）
- 追加: `exports/p2_meshy/M01-20261101T042541Z/` と `exports/p2_static/<key>-20261101T041730Z/`（6 キー）・`A_plaza-20261101T042531Z/` の記録（`report.json`・`validate.json`・`placement.json`・`colliders.json`・`replacements.json`）、`review/p2_meshy/` の M01 の撮影 8 枚、この文書
- 閉じた子の所有ファイル（W02・W09-M01・W08）は変えていない
- state: 親の checkout の `/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state/` に `p2m_M01.json`・`p2m_M01_DoorLeft.json`・`p2m_M01_DoorRight.json` を足し、`p2_A_plaza.json` を更新した。消すと次の apply が同じ物をもう一度作るので消さない
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1
- 保存（確認事項 4）: 記録 13.10

## 4. 再実行手順

記録 4 章。この子で使った形:

```sh
for key in world common A_plaza B_mansion C_candy D_amusement E_forest M01; do
  resoloop blender run modeling/$key/build.py --json || exit 2      # D_amusement・E_forest は --arg=--no-render で速くなる
done
uv run python modeling/p2_static/export_p2.py --url "$URL"           # 6 キー（A は M01・M02 の描画を止め、門扉の Slot を置き直す）
uv run python modeling/p2_meshy/export_meshy.py --url "$URL" --meshy M01   # p2m.apply.json と p2m_DoorLeft・p2m_DoorRight.apply.json
# カメラ・光源だけを変えるときは --recompose exports/p2_meshy/M01-<UTC>
# スナップショット → diff → apply（素材の 3 つの宣言は --texture-transfer data。state は p2m_M01.json・p2m_M01_DoorLeft.json・p2m_M01_DoorRight.json）
#   → A の diff・apply → 2 回目の diff・apply（記録 4 章）
cp <p2_bundles/<M>-<UTC> の追跡していないファイル> exports/p2_meshy/<M>-<UTC>/   # M02・M04・M08。verify_live の前（記録 4 章）
uv run python modeling/p2_meshy/verify_live.py --url "$URL" --raw-out <Git の外> --output review/p2_meshy/live_checks.json
```

- 作り直した追跡中の `.blend`・確認画像と、ビルドが `export_result` を `unexported` に戻した `assets/manifest/M01.json` は、コミットの前に `git restore` で戻した（形は変えていない）
- `resoloop capture` の `<名前>.scene.json` は作業ツリーの絶対パスを含むので消した

## 5. 確認した内容と結果

| 受け入れ基準 | 結果 |
|---|---|
| 保存の後の最初の diff | 全 10 宣言で 0。A の資産は `resdb` への移行の no-op（記録 13.1） |
| export・validate | M01 の 3 つの宣言と A がオフライン・`--strict` で issues 0（13.4） |
| M01 | 外接箱（アーチと門扉）の差 0.2 mm、正面は南 (0, 0, −1)。門扉は開いた形（±90°）。門扉の Slot の原点は M01 の蝶番と差 0.0 m。**差し替えの前の位置からは 15.3 cm・12.9 cm 動いた**（利用者の決定。本文の「差し替えの前と 1 cm 以内」は M01 の蝶番と両立しないので、着手のコメントで食い違いとして書いた） |
| 門扉 | 置き方（3 つの宣言）、基準姿勢（閉 0°、開 DoorLeft +90°・DoorRight −90°）、P3 が回す Slot（`_DoorLeft`・`_DoorRight`）を記録 13.2 に書いた |
| 見た目 | 撮影 8 枚。欠け・反転・黒い面・透けなし。仮モデルのアーチ・門扉・目印は表示されない。看板の裏の文字の鏡像は Meshy の画像のまま（13.7） |
| 取付位置と ID | 取付位置 3 つは差し替えの前と同じ位置（差 0.0 m）。ID・部品名は変えていない（門扉の Slot は位置と回転だけ） |
| 当たり判定 | アーチは仮モデルの形の `FixedCollision`（柱の内側の面は M01 と 1 cm 以内）、門扉には付けない。利用者の歩行で問題なし |
| 実測 | `verify_live.py` が M01・M02・M04・M08 で合格、A・C の数も一致（13.6） |
| 再適用 | M01 の 3 つの宣言と A の 2 回目の diff が 0、apply が書き込み 0。全 13 宣言が 0。Slot・Component は増えない |
| 所有範囲 | diff の対象は M01 の 3 つの親の下と資産、A の仮モデルのゲートの中（描画 6・門扉の Slot 2）だけ。ほかの宣言は 0 |
| 負荷 | 60 fps 前後。三角形 35,521、画像 2（約 28 MB の見積もり、3 つの宣言で同じ資産）、光源 0 |
| テスト | `uv run pytest` 87 件が通る（9 章） |

## 6. 次の子（W09R-B #48、M03 幽霊屋敷）への注意と要望

### 6.1 次の子への注意

- `verify_live.py` は `REPLACEMENTS` の全素材のバンドルを読む。新しい worktree では、Git の外の `p2_bundles/M02-20261031T164338Z`・`M04-20261101T022427Z`・`M08-20261101T022537Z`・`M01-20261101T042541Z` を `SHA256SUMS` で確かめてから、同じ名前の出力先へ写す。M01 は宣言が 3 つ（`p2m.apply.json`・`p2m_DoorLeft.apply.json`・`p2m_DoorRight.apply.json`）で、state も 3 つ。最初の diff と全宣言の diff には 3 つとも入れる（M03 を足す前で全 13 宣言）
- resoloop 0.2.0 の宣言は 1 つの親の下にしか置けない（子の `parent` は無視される）。M03 の扉・玄関ホール（W03 の `BMN_MansionDoubleDoor_001`・`BMN_EntranceHall_001`）を M03 の開口へ動かす（`docs/p1-handoff.md` 8 章の 1）ときは、地区の宣言の Slot の位置を後処理で変える `repose_motion_roots` と同じ形が使える（今の関数は `moving_parts` の門扉のための物で、visual_root と同じ親の motion_root だけを扱う）
- `moving_parts` は「Meshy 素材の子を、仮モデルの可動部品の Slot の下に別の宣言で置く」ための項目。M05（屋根と中央の柱が別の visual_root）・M07（塔と文字盤）のように 1 素材が複数の親に分かれる素材にも、宣言を分ける形として使える（その場合、可動部品でない部品の置き方は `moving_part_poses` の前提（蝶番・角度）に合わないので、別の項目を考える）
- A は M01・M02 の 2 素材。`check_counts` は A のすべての差し替えの宣言（M01 は 3 つ）を足して比べる

### 6.2 要望（他の所有。この子は直していない）

- W02 の `A_plaza`（`assets/manifest/A_plaza.json` の `APL_EntranceGateProxy_001` の `parts` の `pivot_local`・`motion.door_*_hinge_local` と、`modeling/A_plaza/gimmicks.py` の門扉の位置 ±2.18・角度 ±88°）: ワールドの門扉の Slot は M01 の蝶番・±90° に置き直してあり、A のデータと違う（記録 13.2。差し替え側の `repose_motion_roots` が A の宣言を後処理している）。P3 が門扉を動かすときは、A のデータではなく記録 13.2 の値を使う。A のデータを M01 の蝶番に揃えるかは統合役か P3 が決める
- プロジェクトの `AGENTS.md`（統合役）: state の説明「差し替えた素材は `p2m_<M>.json`」に、可動部品の宣言の `p2m_<M>_<部品>.json` を足す
- P3（W10・W11）: A の宣言は門扉の Slot の回転（開いた形）を書いているので、P3 が回した後に A を再 apply すると開いた形に戻る（記録 13.2 の注意）

## 7. 未確認・未解決

- 保存の後の状態は記録 13.10。再読込の後に M01 の画像が保たれるかは P4
- 門扉の開閉の動きと、閉じた形の見え方（P3）。VR、二人以上

## 8. 次に触ってよい範囲と、上書きしてはいけない範囲

- 次に触ってよい: 後続の差し替えの子は `REPLACEMENTS` への自分の素材の行の追加と、その差し替えに要る検査の拡張。P3 は `_DoorLeft`・`_DoorRight` の Slot の回転（閉 0°〜開 ±90°）
- 上書きしてはいけない: 利用者が決めた門扉の Slot の位置（M01 の蝶番）と開いた角度（±90°）、前の子の素材の光源（M02・M08）。W08 の root の外、`Root` の直下の既定の物

## 9. テストの要否

- 足したテスト（`tests/test_p2_meshy_verify.py`、どれも S。検査が誤った状態を成功と報告すると、気付かないまま確認済みとして記録され、P3 が誤った軸で門扉を回す）:
  - `test_moving_part_motion_root_off_the_hinge_is_detected`: motion_root（P3 が回す Slot）が蝶番から外れている。正しい状態で通ることも確かめる
  - `test_moving_part_that_is_not_in_the_opened_pose_is_detected`: 門扉が開いた形でない
  - `test_moving_part_that_is_not_drawn_is_detected`: 門扉の `MeshRenderer` が無効（素材の Slot だけを見ていた検査では見落とす）
  - `test_collider_under_a_moving_part_is_detected`: 門扉の宣言の下に当たり判定がある
  - それぞれ守りを外すと、そのテストだけが失敗することを確かめた（古い pyc を避けて `PYTHONPYCACHEPREFIX` を変異ごとに分けた）
- 書かなかったもの: `repose_motion_roots` の拒否（visual_root と motion_root の親が違う・visual_root が原点でない）と `export_meshy.split_part` の拒否（export の部品の位置・回転がアセット一覧と違う）は、壊れると門扉が蝶番からずれた所に置かれるが、`verify_live.py` の蝶番の検査（上のテスト）が同じ損害を失敗として見つける（D）。部品の宣言に材質・画像が欠ければ validate が失敗する（L）。`REPLACEMENTS` の値は設定の写し（F）
