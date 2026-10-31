# 配置データ仕様（`layout/`）

このディレクトリは、ワールド全体の枠組み（`layout/world_layout.json`）と各地区の配置データ（`layout/areas/<key>.json`）を管理する。

## 所有と編集範囲

- **W00（P0）**: `layout/README.md` および `layout/schema/`（スキーマ定義とサンプル）を作成・凍結する。`layout/world_layout.json` と `layout/areas/` の実ファイルは W00 では作成しない。
- **W01（P1）**: `layout/world_layout.json` と `layout/areas/world.json` を作成して凍結する。
- **W02〜W06（P1）**: それぞれ担当地区の `layout/areas/<key>.json`（`A_plaza`, `B_mansion`, `C_candy`, `D_amusement`, `E_forest`）を作成・更新する。`layout/world_layout.json` は読み取り専用とし、変更要望がある場合は `handoff/W0N.md` に記録する。
- **W07（P1 統合）**: W00〜W06 がすべて完了した後に限り、handoff の要望や検査結果に基づく最小限の調整を行ってよい。

## 座標系と単位

- 原点 `[0.0, 0.0, 0.0]`: 中央広場の中心（基準地面高さ `Z = 0`）
- 軸の向き（Blender 座標系）:
  - `+X`: 東（East）
  - `+Y`: 北（North）
  - `+Z`: 上（Up）
- 単位: メートル（`1.0 = 1m`）
- 正面方向（`forward_axis`）: 原則 `-Y`（南向き、Blender の Front View 正面）。配置に応じて `+Y`, `+X`, `-X` を明示できる。

## ファイル構成とスキーマ

### 1. `layout/world_layout.json`（スキーマ: `layout/schema/world_layout.schema.json`）

ワールド全体の領域・5 地区の枠・主動線・入口・スポーン候補を定義する。サンプルは `layout/schema/world_layout.example.json` を参照。

必須項目:
- `schema_version`: `"1.0"`
- `world_name`: `"Halloween Magical Carnival"`
- `coordinate_system`: `origin` (`[0,0,0]`), `east` (`"+X"`), `north` (`"+Y"`), `up` (`"+Z"`), `unit` (`"m"`)
- `play_area`: `size_m`（目安 `[100.0, 100.0]`）, `bounds_min`, `bounds_max`
- `central_plaza`: `center`, `diameter_m`（26〜30m 目安）, `ring_road_width_m`（3.0m 以上）
- `entrance`: 南側入口の位置・向き・幅（3.0m 以上）・対象地区キー
- `spawn_candidates`: スポーン候補の配列（`id`, `position`, `forward`, `radius_m`）
- `areas`: 5 地区（`A_plaza`, `B_mansion`, `C_candy`, `D_amusement`, `E_forest`）の定義
  - 各地区の `key`, `area_code` (`A`〜`E`), `name`, `direction`, `center`, `bounds_min`, `bounds_max`, `entrances`, `connection_points`
- `routes`: 地区間を結ぶ主動線・周回路・橋・脇道・スロープの配列
  - 主動線（`main_road`）・中央周回路（`ring_road`）は `width_m >= 3.0`（目安 3〜4m）
  - 橋（`bridge`）・脇道（`side_path`）・スロープ（`slope`）は原則 `width_m >= 2.0`

### 2. `layout/areas/<key>.json`（スキーマ: `layout/schema/area_layout.schema.json`）

各地区内の通路・巡回経路・オブジェクト配置を定義する。サンプルは `modeling/probe/probe_layout.json` を参照。

必須項目:
- `schema_version`: `"1.0"`
- `key`: 担当キー（`world`, `A_plaza`, `B_mansion`, `C_candy`, `D_amusement`, `E_forest`, `probe`）
- `area_code`: `W`, `A`, `B`, `C`, `D`, `E`, `P0`
- `center`, `bounds_min`, `bounds_max`: 地区の中心と境界（`world_layout.json` の当該地区の枠と整合すること）
- `entrances`: 地区の入口一覧（`id`, `position`, `width_m`, `connects_to`）
- `paths`: 地区内の通路・小橋・スロープ・巡回ルート（C 地区の魔女の飛行経路 `patrol_loop`、D 地区の列車周回コース `rail_loop` を含む）
- `placements`: 配置オブジェクト一覧（`placement_id`, `asset_id`, `position`, `rotation_euler_deg`, `scale`, `forward_axis`）

## 検査コマンド

```bash
uv run python tools/check_data.py
# 特定のキーだけ検査する場合:
uv run python tools/check_data.py --key A_plaza
```
