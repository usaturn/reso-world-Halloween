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

全作業は以下の 19 キー（`M01`〜`M08` の 8 キーは 1 行にまとめた）に分割して管理し、1 タスク＝1 キーの所有範囲で編集する。担当は親 Issue #1 のボード `halloween-p0p1` の子キーである（W01A で揃えた）。

| キー (`key`) | 担当 | ビルダスクリプト | Blender ファイル | レビュー画像 | レイアウト JSON | マニフェスト JSON |
| --- | --- | --- | --- | --- | --- | --- |
| `probe` | W00 | `modeling/probe/build.py` | `blender/probe/probe.blend` | `review/probe/*.png` | `modeling/probe/probe_layout.json` | `modeling/probe/probe_manifest.json` |
| `world` | W01 | `modeling/world/build.py` | `blender/world/world.blend` | `review/world/*.png` | `layout/world_layout.json` | `assets/manifest/world.json` |
| `common` | W01 | `modeling/common/build.py` | `blender/common/common.blend` | `review/common/*.png` | （各エリアの `Common_Placement`） | `assets/manifest/common.json` |
| `A_plaza` | W02 | `modeling/A_plaza/build.py` | `blender/A_plaza/A_plaza.blend` | `review/A_plaza/*.png` | `layout/areas/A_plaza.json` | `assets/manifest/A_plaza.json` |
| `B_mansion` | W03 | `modeling/B_mansion/build.py` | `blender/B_mansion/B_mansion.blend` | `review/B_mansion/*.png` | `layout/areas/B_mansion.json` | `assets/manifest/B_mansion.json` |
| `C_candy` | W04 | `modeling/C_candy/build.py` | `blender/C_candy/C_candy.blend` | `review/C_candy/*.png` | `layout/areas/C_candy.json` | `assets/manifest/C_candy.json` |
| `D_amusement` | W05 | `modeling/D_amusement/build.py` | `blender/D_amusement/D_amusement.blend` | `review/D_amusement/*.png` | `layout/areas/D_amusement.json` | `assets/manifest/D_amusement.json` |
| `E_forest` | W06 | `modeling/E_forest/build.py` | `blender/E_forest/E_forest.blend` | `review/E_forest/*.png` | `layout/areas/E_forest.json` | `assets/manifest/E_forest.json` |
| `overview` | W07 | `modeling/overview/build.py` | `blender/overview/overview.blend` | `review/overview/*.png` | `layout/world_layout.json`（参照） | `assets/manifest.json`（統合出力） |
| `meshy` | W09 | `modeling/meshy/`（受領した素材の検査と仕上げの共通処理） | （作る場合）`blender/meshy/meshy.blend` | `review/meshy/*.png` | — | —（受領台帳は `assets/meshy/received.json`） |
| `M01`〜`M08`（`<M>`） | W09-M01〜W09-M08 | `modeling/<M>/build.py` | `blender/<M>/<M>.blend` | `review/<M>/*.png` | — | `assets/manifest/<M>.json` |
| `p2_static` | W08 | `modeling/p2_static/`（`content/main.json` の生成・P2 の export と当たり判定・実測の検査） | — | `review/p2_static/*.jpg` | — | —（`content/main.json`、`exports/p2_static/`） |
| `p2_meshy` | W09R | `modeling/p2_meshy/`（Meshy の仕上げた素材への差し替えの設定・宣言の作成・実測の検査） | —（`blender/<M>/<M>.blend` を使う） | `review/p2_meshy/*.jpg` | — | —（`exports/p2_meshy/`） |
| `p3_gimmicks` | W10 | `modeling/p3_gimmicks/`（P3 の自動ギミックの定義・地区の宣言への駆動の追加・P3 の宣言と ProtoGraph の生成・配備・実測の検査） | — | `review/p3_gimmicks/*.jpg` | — | —（`content/p3_gimmicks.json`、`flux/P3PlazaDance.pg`・`flux/p3_plaza_dance.flux.json`、W10-A の `flux/P3FountainGlow.pg`・`flux/p3_fountain_glow.flux.json`、W10-B の `flux/P3MansionMotion.pg`・`flux/p3_mansion_motion.flux.json`） |

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
   - `B_mansion`: `BMN_<AssetName>_<NNN>`
   - `C_candy`: `CCD_<AssetName>_<NNN>`
   - `D_amusement`: `DAM_<AssetName>_<NNN>`
   - `E_forest`: `EFR_<AssetName>_<NNN>`
   - `meshy`: `MSH_<AssetName>_<NNN>`
   - `M01`〜`M08`: キーと同じ接頭辞 `<M>_<AssetName>_<NNN>`（例：`M03_HauntedMansion_001`）
   - マテリアル: `MAT_<Prefix>_<Name>`（例：`MAT_P0_AsymSign`, `MAT_CMN_WarmWood`）
3. **コレクション名規約**
   - 各 `.blend` ファイルのルートコレクション名は対象キー名（`probe`, `world`, `common`, `A_plaza`, `B_mansion`, `C_candy`, `D_amusement`, `E_forest`, `overview`, `meshy`, `M01`〜`M08`）に一致させる。

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

W01 が作成する共通部品は、以下のいずれかの方法で各エリア（W02〜W06）から利用する。

1. **共通ビルダ関数の呼び出し（推奨）**
   - `modeling/lib/common_parts.py`（および W01 が公開する共通パーツ生成関数）をエリア側の `modeling/<area>/build.py` から import し、エリアのコレクション内にエリア固有プレフィックス付きの名前（例：`APL_LanternPost_001`）で生成する。
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
- `.blend` とテクスチャはコミットしないので（§8）、新しい checkout では、アセット一覧が参照する `.blend`・画像が無く、終了コード `1`（`blend_file does not exist on disk`）になる。先に各キーの §7.1 を実行してから検査する（全キーの順序は `docs/p1-handoff.md`）。生成物を作らずにデータの形だけを確かめるときは `--no-file-check` を付ける。

### 7.3 `.blend` 検査コマンド
```bash
# blender/*/*.blend を一括検査
uv run python tools/check_blend.py

# 特定キーまたは特定ファイルを検査
uv run python tools/check_blend.py --key <key>
uv run python tools/check_blend.py blender/<key>/<key>.blend
```
- 正常時は終了コード `0`、未解決の外部画像／ライブラリ・負スケール・非一様スケール・shear・`.001` 名や既定名検出時は終了コード `1` を返す。
- `.blend` に内包した画像（§8 の `pack_images=True`）は、参照パスの先にファイルが無くても失敗にしない（参照パスは `.blend` を作った worktree の絶対パスなので、その worktree を消すと先が無くなる。内包した画像は `.blend` から読めるので困らない）。内包していない画像の参照切れは失敗にする。

### 7.4 レビュー画像の出力方法
- `modeling.lib.render.render_review_images(views, ...)` を使用し、Headless 環境で動作する `CYCLES` (`CPU`, 24〜32 samples) で `review/<key>/` 配下に PNG を出力する。
- レビュー用の一時カメラ・一時ライト・一時ワールドは `render_review_images` の `finally` ブロックで自動削除され、保存される `.blend` にはアセット以外のオブジェクトを残さない。

### 7.5 `resoloop blender export` コマンド
```bash
resoloop blender export blender/<key>/<key>.blend \
  --output <新しい出力先> \
  --parent <Slot> \
  --collection <key> \
  --preserve-hierarchy \
  --json
```
- 導入済みの resoloop 0.2.0 では `--parent` が必須で、W00 の版の `--root-path` は `OPTION_REQUIRED: --parent is required.` で止まる（W09 と W07 で確認。2026-10-31 に W07 が直した）。
- `--output` は存在しないディレクトリにする。P1 の地区ごとの出力は `exports/p1/<key>-<UTC 時刻>/`（`modeling/overview/export_p1.py`）。
- `--parent` は apply する Slot。Resonite に apply しない確認用の export では、`Root/ResoLoop_Test_<担当>_<key>` のような試験用のパスを渡し、apply の前に、ライブのワールドで確かめた Slot を `--parent` にして新しい出力先へ export し直す。
- 金属・粗さの画像を持つ素材（Meshy の仕上げなど）は `--pack-pbr` を付ける。`--pack-pbr` が作る `pbr_*.png` は §8 の除外の規則に当たらないので、その出力先の `.gitignore` で除く（`exports/M01/.gitignore` など）。
- 出力をオフラインで確かめるときは `resoloop validate <出力先>/model.apply.json --json`（`--strict` を付けない。`--strict` はライブの Reflection と照合する）。

### 7.6 P2 の export と apply（W08）

- export: `uv run python modeling/p2_static/export_p2.py --url <URL>`。確かめた `Root/HalloweenMagicalCarnival` を `--parent` にして新しい `exports/p2_static/<key>-<UTC>/` へ出し、歩行用の当たり判定を足した `p2.apply.json` を作る。apply するのは `model.apply.json` ではなく `p2.apply.json`
- apply: キーごとに `resoloop diff <出力先>/p2.apply.json --state <親の checkout>/.resoloop/state/p2_<key>.json --brief --report <新しいファイル> --json` で対象を確かめてから `resoloop apply`。apply の前に W08 の root のスナップショットを `resoloop import` で親の checkout のプロジェクトの `tmp/` に取る。詳細は `docs/p2-static-integration.md` 7 章
- コミットするのは `exports/p2_static/<key>-<UTC>/` の `report.json`・`validate.json`・`colliders.json`（バンドル本体は §8 のとおり除く）
- Meshy の仕上げた素材への差し替え（W09R）: 仕上げた素材は `uv run python modeling/p2_meshy/export_meshy.py --url <URL> --meshy <M>` で、仮モデルの見た目の Slot の子に置く別の宣言（`exports/p2_meshy/<M>-<UTC>/p2m.apply.json`、state は `p2m_<M>.json`）にする。差し替えた仮モデルの描画は `export_p2.py` が地区の `p2.apply.json` で止める（`modeling/p2_meshy/replacements.py` の `REPLACEMENTS`）。apply は `--texture-transfer data`。コミットするのは `exports/p2_meshy/<M>-<UTC>/` の `report.json`・`validate.json`・`placement.json` と、地区の出力先の `replacements.json`。詳細は `docs/p2-meshy-replacement.md`
- P3 の自動ギミック（W10）: P3 が動かす可動部品は、`export_p2.py` が地区の `p2.apply.json` に `managedFields` と駆動（G13 の `Spinner`、G01 の中継の `ValueMultiDriver`）を足す（`modeling/p3_gimmicks/district.py`）。外から変えられる値と ProtoFlux の配備先は `content/p3_gimmicks.json`（`uv run python modeling/p3_gimmicks/build_content.py` で作る。state は `p3_gimmicks.json`）、ProtoFlux は `uv run python modeling/p3_gimmicks/deploy_flux.py --url <URL> --report <新しいファイル>` で配備する（W10-A の G03 は `--manifest flux/p3_fountain_glow.flux.json`。発光を変える物は、共有の材質を写した専用の材質を `district.add_g03_material` のように足し、その物の MeshRenderer だけを付け替える。W10-B の G05・G06 は `--manifest flux/p3_mansion_motion.flux.json`。回転だけを駆動する蝶番は、中継を回転の 1 つにし `managedFields` を `["position", "scale"]` にする）。コミットするのは地区の出力先の `p3_drivers.json` と `review/p3_gimmicks/`。詳細は `docs/p3-gimmicks.md`

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
