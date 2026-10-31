# 制作規約・データ形式・コマンド仕様 (`docs/conventions.md`)

本ドキュメントは `reso-world-Halloween` における座標系、命名規約、原点方針、データ形式、1 キー単位の再生成コマンド、および検査コマンドの共通仕様を定義する。後続タスク（W01〜W08）は本仕様を基準として実装・検証を行う。

---

## 1. 単位・座標系・変換規約

| 項目 | 仕様 |
| --- | --- |
| 長さ単位 | `1 unit = 1.0 m` (`METRIC`, `scale_length = 1.0`) |
| Blender 座標系 | 右手系：`+X` = 右（東）、`+Y` = 奥／前方（北）、`+Z` = 上、地面基準高 `z = 0.0` |
| Resonite 変換対応 | `resoloop blender export --preserve-hierarchy` により Blender `(x, y, z)` は Resonite `(x, z, y)`（左手系：`+X` 右、`+Y` 上、`+Z` 前方）へ自動変換される。UV は無変換で維持される |
| スケール規約 | 全オブジェクト（Mesh / Empty）のローカルおよびワールドスケールは `(1.0, 1.0, 1.0)` に統一する。負スケール（`< 0`）、非一様スケール（`sx != sy` 等）、および親子回転＋非一様スケールに起因する shear（非直交基底）は禁止 |
| メッシュ・法線・UV | 外向き法線（`bmesh.ops.recalc_face_normals`）、UV レイヤー名 `UVMap`、1 オブジェクト＝1 メッシュ（後から Resonite インスペクターで操作しやすい粒度） |

---

## 2. キー一覧とファイル配置

全作業は以下の 9 キーに分割して管理し、1 タスク＝1 キーの所有範囲で編集する。

| キー (`key`) | 担当 | ビルダスクリプト | Blender ファイル | レビュー画像 | レイアウト JSON | マニフェスト JSON |
| --- | --- | --- | --- | --- | --- | --- |
| `probe` | W00 | `modeling/probe/build.py` | `blender/probe/probe.blend` | `review/probe/*.png` | `modeling/probe/probe_layout.json` | `modeling/probe/probe_manifest.json` |
| `world` | W01 / W07 | `modeling/world/build.py` | `blender/world/world.blend` | `review/world/*.png` | `layout/world_layout.json` | `assets/manifest/world.json` |
| `common` | W02 | `modeling/common/build.py` | `blender/common/common.blend` | `review/common/*.png` | （各エリアの `Common_Placement`） | `assets/manifest/common.json` |
| `A_plaza` | W01 / W03 | `modeling/A_plaza/build.py` | `blender/A_plaza/A_plaza.blend` | `review/A_plaza/*.png` | `layout/areas/A_plaza.json` | `assets/manifest/A_plaza.json` |
| `B_alley` | W01 / W04 | `modeling/B_alley/build.py` | `blender/B_alley/B_alley.blend` | `review/B_alley/*.png` | `layout/areas/B_alley.json` | `assets/manifest/B_alley.json` |
| `C_park` | W01 / W05 | `modeling/C_park/build.py` | `blender/C_park/C_park.blend` | `review/C_park/*.png` | `layout/areas/C_park.json` | `assets/manifest/C_park.json` |
| `D_mansion` | W01 / W06 | `modeling/D_mansion/build.py` | `blender/D_mansion/D_mansion.blend` | `review/D_mansion/*.png` | `layout/areas/D_mansion.json` | `assets/manifest/D_mansion.json` |
| `E_forest` | W01 / W07 | `modeling/E_forest/build.py` | `blender/E_forest/E_forest.blend` | `review/E_forest/*.png` | `layout/areas/E_forest.json` | `assets/manifest/E_forest.json` |
| `overview` | W08 | `modeling/overview/build.py` | `blender/overview/overview.blend` | `review/overview/*.png` | `layout/world_layout.json`（参照） | `assets/manifest.json`（統合出力） |

---

## 3. ID・オブジェクト名・コレクション名・マテリアル名規約

1. **命名正規表現**
   - アセット ID (`asset_id`)、パーツ ID (`part_id`)、オブジェクト名、マテリアル名、動線 ID (`route_id`)、配置 ID (`placement_id`) はすべて次の正規表現に一致させる：
     ```text
     ^[A-Za-z0-9]+(_[A-Za-z0-9]+)+$
     ```
   - Blender が自動付与する重複サフィックス（`.001`, `.002` 等、`\.[0-9]{3}$`）は一切禁止する。
   - Blender の既定名（`Cube`, `Cylinder`, `Sphere`, `Plane`, `Empty`, `Camera`, `Light`, `Material`, `Collection` 等）は禁止する。
2. **プレフィックス規約**
   - `probe`: `P0_<AssetName>_<NNN>`（例：`P0_MeterRef_001`, `P0_PivotGate_001`）
   - `world`: `WLD_<AssetName>_<NNN>`
   - `common`: `CMN_<AssetName>_<NNN>`
   - `A_plaza`: `APL_<AssetName>_<NNN>`
   - `B_alley`: `BAL_<AssetName>_<NNN>`
   - `C_park`: `CPK_<AssetName>_<NNN>`
   - `D_mansion`: `DMN_<AssetName>_<NNN>`
   - `E_forest`: `EFR_<AssetName>_<NNN>`
   - マテリアル: `MAT_<Prefix>_<Name>`（例：`MAT_P0_AsymSign`, `MAT_CMN_WarmWood`）
3. **コレクション名規約**
   - 各 `.blend` ファイルのルートコレクション名は対象キー名（`probe`, `world`, `common`, `A_plaza`, `B_alley`, `C_park`, `D_mansion`, `E_forest`, `overview`）に一致させる。

---

## 4. 原点規約 (`origin_policy`) とパーツ階層 (`role`)

### 4.1 原点方針 (`origin_policy`)

| `origin_policy` | 適用対象 | ローカル原点 `(0, 0, 0)` の位置 |
| --- | --- | --- |
| `ground_center` | 建築物・小道具・樹木・街灯などの接地アセット | 接地底面の中央（底面が `z = 0.0`） |
| `hinge_pivot` | 扉・門扉・揺れる看板・回転遊具などの可動部品 | 回転軸またはヒンジ支点の位置 |
| `attachment_point` | ランタン吊り下げフック・ガーランド接続点 | 接続・吊り下げ基準点の位置 |
| `world_origin` | ワールド全体地形・境界・空ドーム | ワールド原点 `(0.0, 0.0, 0.0)` |

### 4.2 パーツ役割 (`role`) と階層構造

後続の ProtoFlux 実装や Resonite インスペクターでの調整を容易にするため、複合アセットや可動ギミックは以下の役割を明示して親子階層を構成する。

- `asset_root`: アセット全体の配置基準（`ground_center` または `world_origin`）
- `static_part`: 支柱・枠・土台など動かないメッシュ部品（親：`asset_root`）
- `motion_root`: 回転・移動の基準となるピボット（`hinge_pivot`。親：`asset_root`）
- `visual_root`: 実際に描画されるメッシュ部品（親：`asset_root` または `motion_root`）
- `attachment_point`: ランタンや装飾を吊るす接続点（`attachment_point`）

> **注意（P0 検証結果に基づく重要仕様）**:
> `resoloop blender export --preserve-hierarchy` は、子孫に `MESH` オブジェクトを持たない末端の `Empty` を Resonite Slot 出力から省略する。一方、`MESH` オブジェクトを子に持つ親 `Empty`（`asset_root` や `motion_root`）はそのまま Resonite Slot として出力される。したがって、Resonite 側にも Slot を残したい `attachment_point` には小メッシュ（フック金具等）を持たせるか、メッシュオブジェクト自身として作成する。

---

## 5. データ形式仕様

スキーマ定義ファイルは以下に配置されている。
- ワールド全体レイアウト: [`layout/schema/world_layout.schema.json`](../layout/schema/world_layout.schema.json)（記入例：[`layout/schema/world_layout.example.json`](../layout/schema/world_layout.example.json)、解説：[`layout/README.md`](../layout/README.md)）
- エリア別レイアウト: [`layout/schema/area_layout.schema.json`](../layout/schema/area_layout.schema.json)
- アセットマニフェスト: [`assets/schema/manifest.schema.json`](../assets/schema/manifest.schema.json)（解説：[`assets/README.md`](../assets/README.md)）

### 5.1 `layout/world_layout.json` の必須項目
- `schema_version` (`"1.0"`), `project` (`"reso-world-Halloween"`), `unit` (`"m"`), `axes`, `world_origin` (`[0, 0, 0]`)
- `areas`: 各エリアの `area_id`, `key`, `name`, `center`, `bounds` (`min`/`max`), `ground_elevation_m`, `connections`
- `routes`: 動線 `route_id`, `from_area`, `to_area`, `kind`（`main_road`/`ring_road` は `width_m >= 3.0`、`bridge`/`side_path` は `width_m >= 2.0`）, `waypoints`, `max_slope_deg` (`<= 30.0`)
- `landmarks`: ランドマーク `landmark_id`, `area_id`, `position`, `height_m`, `visible_from_areas`, `target_point`
- `line_of_sight`: 視線抜け `los_id`, `from_area`, `from_point`, `to_area`, `to_point`, `corridor_width_m`, `description`
- `lighting_preset`, `sky_moon`, `fog`: 全体照明・空・満月・霧の方針パラメータ
- `spawn`: 初期出現位置 `area_id`, `position`, `forward`, `clearance_radius_m` (`>= 1.5`)

### 5.2 `layout/areas/<area>.json` の必須項目
- 基本情報: `schema_version`, `area_id`, `key`, `name`, `theme`, `bounds`
- 空間構成 7 分類（すべて必須）:
  1. `Anchor`: 中心建築・主役の座標・寸法・向き・役割
  2. `Circulation`: 主動線 ID・最小歩行幅 (`>= 2.0m`)・入口座標・回遊説明
  3. `Framing`: 左右フレーミング要素・視線誘導先・視野角
  4. `Story_Cluster`: 物語性のある小塊（カボチャ群・屋台・墓石群等）の配置リスト
  5. `Common_Placement`: 共通部品 (`CMN_*`) の利用箇所リスト
  6. `Hero_or_Gimmick`: 可動・主役要素の `asset_id` と `motion_roots` / `visual_roots` / `attachment_points`
  7. `Exclusions`: 視線確保・通行確保のための配置禁止矩形領域
- `placements`: 配置インスタンス一覧（`placement_id`, `asset_id`, `source_key`, `category`, `position`, `rotation_euler_deg`, `scale`（正の一様スケールのみ）, `origin_policy`, `clearance_radius_m`）

### 5.3 `assets/manifest/<key>.json` および `assets/manifest.json` の必須項目
各アセット要素は以下の全項目を持つ：
- `asset_id`, `key`, `category`, `area_id`, `collection`, `blend_file`, `script_file`
- `origin_policy`, `origin_world`, `dimensions_m` (`width`, `depth`, `height`), `bounds_local` (`min`, `max`)
- `parts` (`part_id`, `role`, `parent_part`, `origin_policy`, `pivot_local`)
- `hierarchy` (`asset_root`, `motion_roots`, `visual_roots`, `attachment_points`)
- `materials`, `textures`
- `metrics`:
  - **実測済みの場合**: `"measured": true`, `"measurement_source": "blender_scene"`（または `"resoloop_export_report"`）, `"triangles": <int>`, `"vertices": <int>`, `"materials_count": <int>`, `"objects_count": <int>`
  - **未計測の場合（推測値の記入は厳禁）**: `"measured": false`, `"triangles": null`, `"vertices": null`, `"materials_count": null`, `"objects_count": null`, `"unmeasured_reason": "<未計測の理由>"`
- `export_result`: `"status"` (`"unexported"` | `"exported"` | `"verified_resonite"`), `"bundle_dir"`, `"apply_plan"`, `"report_file"`
- `replacement`: `"is_placeholder"`, `"modifiable"`, `"notes"`, `"future_target"`

---

## 6. `common`（共通部品）をエリア側で使う方法

W02 が作成する共通部品は、以下のいずれかの方法で各エリア（W03〜W07）から利用する。

1. **共通ビルダ関数の呼び出し（推奨）**
   - `modeling/lib/common_parts.py`（および W02 が公開する共通パーツ生成関数）をエリア側の `modeling/<area>/build.py` から import し、エリアのコレクション内にエリア固有プレフィックス付きの名前（例：`APL_LanternPost_001`）で生成する。
   - エリアの `layout/areas/<area>.json` の `Common_Placement` には、元となった `common_asset_id`（例：`CMN_LanternPost_001`）と配置座標リストを記録する。
2. **`blender/common/common.blend` からのローカル化コピー**
   - `bpy.data.libraries.load` で `blender/common/common.blend` から対象オブジェクトを取り込む場合は、必ず `make_local()` 等でローカルデータブロック化し、保存後の `.blend` に外部ライブラリ参照（`bpy.data.libraries`）を残さないこと。

---

## 7. 標準コマンド（再生成・検査・レビュー出力・Export）

### 7.1 1 キー単位の `.blend`・レビュー画像・マニフェスト再生成
```bash
resoloop blender run modeling/<key>/build.py --json
```
- 冪等性要件：`modeling/<key>/build.py` の先頭で `modeling.lib.scene.reset_scene(<key>)` を呼び出し、2 回連続で実行してもオブジェクト数・メッシュ数・マテリアル数が増加しないこと。

### 7.2 データ形式検査コマンド
```bash
# リポジトリ内の全レイアウト・マニフェストを検査
uv run python tools/check_data.py

# 特定キーのみを検査
uv run python tools/check_data.py --key <key>
```
- 正常時は終了コード `0`、スキーマ不一致・ID 重複・参照切れ・未計測メトリクスの数値偽装・ファイル欠損時は終了コード `1` を返す。

### 7.3 `.blend` 検査コマンド
```bash
# blender/*/*.blend を一括検査
uv run python tools/check_blend.py

# 特定キーまたは特定ファイルを検査
uv run python tools/check_blend.py --key <key>
uv run python tools/check_blend.py blender/<key>/<key>.blend
```
- 正常時は終了コード `0`、未解決の外部画像／ライブラリ・負スケール・非一様スケール・shear・`.001` 名や既定名検出時は終了コード `1` を返す。

### 7.4 レビュー画像の出力方法
- `modeling.lib.render.render_review_images(views, ...)` を使用し、Headless 環境で動作する `CYCLES` (`CPU`, 24〜32 samples) で `review/<key>/` 配下に PNG を出力する。
- レビュー用の一時カメラ・一時ライト・一時ワールドは `render_review_images` の `finally` ブロックで自動削除され、保存される `.blend` にはアセット以外のオブジェクトを残さない。

### 7.5 `resoloop blender export` コマンド
```bash
resoloop blender export blender/<key>/<key>.blend \
  --output exports/<key>/bundle \
  --root-path Root/<RootSlotName> \
  --preserve-hierarchy \
  --json
```

---

## 8. Git 管理とファイルサイズ制限

- 1 ファイルあたり **50 MB 未満** を厳守する（GitHub の 100 MB 制限に対する安全マージン）。
- 確認画像（`review/<key>/*.png`）は Git にコミットする。
- 3D モデル（`.blend`、GLB・glTF・FBX・OBJ などのモデルのファイル、export のバンドル）は Git にコミットしない（2026-10-31 の利用者の指示）。`.blend` は §7.1 の再生成コマンドで作り直す。Meshy の原本と仕上げた物は Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/` に置く。
- 2026-10-31 より前にコミットした `blender/probe/probe.blend`・`blender/world/world.blend`・`blender/common/common.blend` は残すが、最新とは限らない。作り直して変わってもコミットせず、コミットの前に `git restore` で戻す。
- `exports/` 配下は、検証・出力サマリである `exports/**/report.json` のみを Git にコミットし、`resoloop blender export` からいつでも再生成できるバンドル本体（`exports/**/*.apply.json`, `exports/**/*.mesh.json`, `exports/**/tex_*.png`）は `.gitignore` で除外する（リポジトリ肥大化防止、および `model.apply.json` 内の `"key": "<識別子>"` に対する Gitleaks `generic-api-key` 誤検出防止のため）。
- Blender のバックアップファイル（`*.blend1`, `*.blend2`）は `.gitignore` で除外し、コミットしない。
- テクスチャ画像は外部 PNG として保存したうえで `save_blend(..., pack_images=True)` により `.blend` 内にもパックし、参照パス切れを防ぐ。
- 作業中の一時ファイルは `/workspaces/reso-world/tmp/agents/` 配下のセッションディレクトリに置き、ワークツリー内に未追跡ファイルを残さない。
