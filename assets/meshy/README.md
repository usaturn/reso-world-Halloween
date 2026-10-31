# Meshy 素材の受領台帳（キー `meshy`、W09）

`received.json` は、利用者が Meshy で作った M01〜M08 の原本と、W09（#13）が確定した寸法・正面・原点・削減の目標・分離と取付位置・両面の扱いを、素材ごとに 1 行で記録する。M05 は屋根（`M05_Canopy`）と中央の柱（`M05_CenterCasing`）の 2 行で、全 9 行。

- 書く人: W09。W02〜W06 と W09-M01〜W09-M08 は読むだけで、変えたい点は自分の handoff に要望として書く（親 #1「共有インターフェースと所有」）
- 原本と仕上げた 3D モデルは Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/` にある（3D モデルはコミットしない）。検査と理由は `docs/meshy-intake.md`

## 作り直し方

| ブロック | 書き方 |
|---|---|
| `source`・`decided`・`budget`・`split_and_attach`・`double_sided` | 手で書く（W09 の判断） |
| `measured`・`derived` | `resoloop blender run modeling/meshy/intake_inspect.py --json` が書き直す（実測と、`decided` から計算した値） |

`decided` を変えたら、必ず `intake_inspect.py` を実行し直す（`tests/test_meshy_received.py` が、`derived` の点が `decided` から計算した値と食い違うと失敗する）。確認画像は `resoloop blender run modeling/meshy/review_views.py --json` で `review/meshy/<row_id>_views.png` に作り直す。

## 上部の項目

| 項目 | 内容 |
|---|---|
| `confirmed_set` | 利用者が一式を確定した #13 のコメント。一式が変わったら、最新のコメントの一式で `source` から作り直す |
| `store` | Git の外の原本置き場、全ファイルの `SHA256SUMS`、コピーしなかった物（`size_over/`・`NG/`・Windows の `*:Zone.Identifier`）。コピーは読み取り専用 |
| `conventions` | 軸、変換の式、正面の約束（置いた後の正面は +Y = Resonite の +Z）、点の測り方と誤差 |

## 行（`assets[]`）の項目

| 項目 | 内容 |
|---|---|
| `row_id`・`key`・`name_ja`・`finishing_child` | 行の名前、素材のキー（`M01`〜`M08`）、仕上げを担当する子 |
| `source` | 元のパス（`tmp/` の下）、コピー先のパス、SHA-256、バイト数、受領日、付属資料のコピー先と数 |
| `decided.scale`・`yaw_deg`・`origin_source` | 原本から置いた後への変換（`conventions.placement`） |
| `decided.origin_policy`・`origin_note` | 原点の種類（`docs/conventions.md` §4）と位置の説明 |
| `decided.size_basis` | 寸法の決め方と、Spec §7 の目安との違い |
| `decided.front_local`・`front_meaning` | 置いた後の正面（+Y）と、それが原本のどの面か |
| `decided.area_id`・`used_by` | 置く地区と、この値を使う子 |
| `decided.placement_hint` | ワールドでの位置と向きの推奨（W01 の配置データからの推奨。最終は地区の子が決める。`null` は地区の子が決める） |
| `decided.points_source` | 開口・蝶番・文字盤・回転軸などの点（原本の座標）。置いた後の座標は `derived.points_local_m` |
| `budget` | 見る距離、三角形数の上限、色の画像と金属・粗さの画像の解像度の上限、その根拠（`derived.texels_per_m`） |
| `split_and_attach` | 部品ごとの実測（`measured`）と判断（`decision`）、守る空き（`keep_clear`） |
| `double_sided` | 両面の扱い（利用者に確認済み）と、片面で透ける所 |
| `measured` | GLB の JSON（`doubleSided`・画像の種類）、外接箱、三角形数、頂点数（取り込み時と溶接後）、メッシュ数、素材と画像、UV の使用率、穴（`boundary_loops`）・浮いた破片・裏返った法線（`topology`）、高さ方向の外形、正面と側面の開口、裏面を消したときに透ける割合（`backface_check`） |
| `derived` | 置いた後の外形寸法・外接箱・点の座標（m）、表面積、画像の解像度ごとの 1 m あたりの画素数 |
