# アセット一覧仕様（`assets/`）

このディレクトリは、各キーが作成するアセット一覧（`assets/manifest/<key>.json`）と、W07 が統合時に作成できる全体一覧（`assets/manifest.json`）のスキーマおよび規約を管理する。

## 所有と編集範囲

- **W00（P0）**: `assets/README.md` および `assets/schema/manifest.schema.json` を作成・凍結する。`assets/manifest/` 配下や `assets/manifest.json` は W00 では作成しない（`probe` の検証用マニフェストは `modeling/probe/probe_manifest.json` に置く）。
- **W01（P1）**: `assets/manifest/world.json` と `assets/manifest/common.json` を作成する。
- **W02〜W06（P1）**: それぞれ `assets/manifest/<key>.json`（`A_plaza`, `B_mansion`, `C_candy`, `D_amusement`, `E_forest`）を作成する。
- **W07（P1 統合）**: 各キーのマニフェストを検査し、必要に応じて `assets/manifest.json` に統合する。

## Spec §6.4 との対応項目

`assets/schema/manifest.schema.json` の各アセット要素（`assets[]`）は、親 Issue #1 Spec §6.4 の必須項目を以下のフィールドで記録する。

| Spec §6.4 の項目 | JSON フィールド | 内容・制約 |
|---|---|---|
| ID | `id` | `A_Pumpkin_001` 等の安定英数字 ID（`^[A-Za-z0-9]+(_[A-Za-z0-9]+)+$`、`.001` 禁止、全キー横断で一意） |
| 地区 | `area` | `"P0"`, `"W"`, `"CMN"`, `"A"`, `"B"`, `"C"`, `"D"`, `"E"`, `"OVW"` |
| 制作者・出典 | `author_source` | `author`, `source_type` (`blender_procedural` / `meshy_proxy` / `meshy_final` / `common_linked`), `meshy_id` (`"M01"`〜`"M08"` または `null`) |
| ファイルと版 | `file_and_version` | `blend_file`, `script_file`, `collection`, `version` |
| 仮モデルか完成素材か | `stage_status` | `"proxy"`（Meshy 仮モデル等）, `"final"`（Blender 本造形）, `"verification_probe"`（P0 検証用） |
| 単位と外形寸法 | `unit`, `dimensions_m` | `unit` は `"m"` 固定、`dimensions_m` は `[幅X, 奥行Y, 高さZ]`（すべて正の数） |
| 基準原点・正面 | `origin_and_facing` | `origin_policy` (`ground_center` / `hinge` / `rotation_center` / `clock_axis` / `motion_center` / `world_origin`), `origin_local`, `forward_axis`, `up_axis` (`"+Z"`) |
| 配置 | `placement` | `position` `[x,y,z]`, `rotation_euler_deg` `[rx,ry,rz]`, `scale` `[1,1,1]` |
| 部品名・親子関係 | `parts` | `[{"name": ..., "parent": nullまたは親部品名, "role": ...}]`（Spec §6.3 の `asset_root`, `motion_root`, `visual_root`, `attachment_point`, `fixed_collision`, `logic_root`, `static_part`, `movable_part`） |
| 可動軸・可動範囲・基準姿勢 | `motion` | 可動部品ごとの `part_name`, `gimmick_id` (`G01`〜`G20`, `I01`〜`I05` 等), `motion_type`, `pivot_local`, `axis`, `range` (`min`, `max`, `unit`), `rest_pose` |
| 取付位置 | `attachment_points` | エフェクト・音・照明・操作ボタン・定期ショー演出の取付位置（`name`, `purpose`, `local_position`, `gimmick_or_interaction_id`） |
| 差し替え先 | `replacement_slot` | Meshy 対象（M01〜M08）の場合に `meshy_id`, `visual_root_part`, `target_dimensions_m`, `forward_axis`, `keep_separate_parts` を記録。非対象は `null` |
| コライダー方針 | `collider_policy` | `"none"` / `"box"` / `"mesh_static"` / `"convex_hull"` / `"separate_fixed_collision"` |
| 材質・画像依存 | `material_and_textures` | `materials`（マテリアル名配列）と `textures`（`path`, `colorspace`, `dimensions_px`） |
| 三角形数・頂点数・材質数 | `metrics` | `measured` (`bool`), `triangles`, `vertices`, `materials` |
| 出力結果 | `export_result` | `status` (`not_exported` / `exported` / `failed`), `bundle_path`, `errors`, `warnings` |
| 確認状態 | `verification_status` | `blender_checked` (`bool`), `resonite_checked` (`verified` / `unverified` / `not_applicable`), `notes` |

## 未測定値の記録ルール（推測値の禁止）

Spec §6.4「三角形数・頂点数・材質数・画像寸法も記録するが、未測定値を推測で埋めない」に従い、次のように記録・検査する。

1. **未測定の場合**:
   ```json
   "metrics": {
     "measured": false,
     "triangles": null,
     "vertices": null,
     "materials": null
   }
   ```
   `measured: false` のときに `triangles`, `vertices`, `materials` に数値を入れることは検査コマンド（`tools/check_data.py`）でエラーとする。
2. **測定済みの場合**:
   Blender スクリプトまたは `resoloop blender export` の `report.json` から実測した 0 以上の整数を記録し、`measured: true` とする。
3. **画像寸法（`textures[].dimensions_px`）**:
   実画像のピクセル寸法 `[width, height]` を確認した場合は 2 要素の正整数配列、未確認の場合は `null` とする。

## 検査コマンド

```bash
uv run python tools/check_data.py
# 特定のマニフェストファイルを検査する場合:
uv run python tools/check_data.py --manifest assets/manifest/A_plaza.json
```
