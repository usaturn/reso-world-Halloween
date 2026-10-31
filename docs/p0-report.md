# P0 技術検証レポート (`W00` / Issue #2)

## 1. 概要

本レポートは `usaturn/reso-world-Halloween` の P0（`W00`: 制作基盤：環境・画像・規約・データ形式と小規模 export の確認）における技術検証結果を記録する。
小規模技術検証用アセット（`key = probe`）を Blender 4.0.2 で決定論的に生成し、レビュー用レンダリング・`resoloop blender export` によるバンドル出力・Resonite 実機（`ws://localhost:44608/`）への `validate` / `diff` / `apply` 2 回適用および一時 Slot のクリーンアップまで一通り確認した。

---

## 2. 検証対象アセット (`key = probe`)

| `asset_id` | 構成オブジェクト (`part_id` / `role`) | 寸法 (`width × depth × height`) | 配置座標 (Blender) | 検証目的 |
| --- | --- | --- | --- | --- |
| `P0_MeterRef_001` | `P0_MeterRef_001` (`asset_root` / Mesh) | `1.0m × 1.0m × 1.0m` | `(-1.5, 0.0, 0.0)` | 1m スケール基準・上下（`+Z`）・前後（`±Y`）・左右（`±X`）の非対称段差形状確認 |
| `P0_AsymSign_001` | `P0_AsymSign_001` (`asset_root` / Mesh) | `1.0m × 0.24m × 1.4m` | `(0.0, 0.0, 0.0)` | 非対称 PNG テクスチャ（`p0_asym_test.png`）による UV 上下左右・表裏・法線向き確認 |
| `P0_PivotGate_001` | `P0_PivotGate_001` (`asset_root` / Empty)<br>`P0_PivotGate_001_Post` (`static_part` / Mesh)<br>`P0_PivotGate_001_Hinge` (`motion_root` / Empty, `rotZ=+15°`)<br>`P0_PivotGate_001_Leaf` (`visual_root` / Mesh)<br>`P0_PivotGate_001_Hook` (`attachment_point` / Empty) | `1.0m × 0.35m × 1.3m` | `(1.5, 0.0, 0.0)` | 親子階層（`--preserve-hierarchy`）・ヒンジ pivot 回転（`hinge_pivot`）・末端 Empty の挙動確認 |

- 生成スクリプト: `modeling/probe/build.py`
- 保存 `.blend`: `blender/probe/probe.blend`
- レビュー画像: `review/probe/01_probe_overview.png`, `review/probe/02_probe_detail.png`
- エクスポートバンドル: `exports/probe/bundle/model.apply.json`, `exports/probe/bundle/report.json`

---

## 3. 検証項目と確認結果

### 3.1 スケール (`1 Blender unit = 1 meter`)

- **Blender 側設定**: `scene.unit_settings.system = "METRIC"`, `scale_length = 1.0`。全オブジェクトで `scale = (1.0, 1.0, 1.0)` を維持。
- **エクスポート結果**: `P0_MeterRef_001` の頂点座標は X `[-0.5, 0.5]`, Y(Resonite高さ) `[0.0, 1.0]`, Z `[-0.5, 0.5]` で出力され、Resonite 上でも `1.0m × 1.0m × 1.0m` の実寸として構築されることを確認した。

### 3.2 座標系変換（上下・前後・回転）

`resoloop blender export --preserve-hierarchy` による Blender（右手系 Z-up）から Resonite（左手系 Y-up）への変換挙動を `exports/probe/bundle/model.apply.json` および Resonite 実機 `resoloop hierarchy` で確認した。

| 項目 | Blender (Z-up) | Resonite (Y-up) | 実測値 (`probe`) |
| --- | --- | --- | --- |
| 位置変換 | `(x, y, z)` | `(x, z, y)` | `P0_PivotGate_001_Hinge`: Blender `(-0.4, 0.0, 0.1)` → Resonite `(-0.4, 0.1, 0.0)` |
| 上方向 | `+Z` | `+Y` | `ground_center` の底面 `z = 0` が Resonite `y = 0` に一致 |
| 前後方向 | `+Y` / `-Y` | `+Z` / `-Z` | 正面カメラ（`y < 0` から `+Y` を見る構図）が Resonite の `-Z` から `+Z` を見る向きに対応 |
| ヒンジ回転 | `+Z` 軸まわり `+15.0°` | `Y` 軸まわり `-15.0°` | `P0_PivotGate_001_Hinge` の Quaternion `(0, -0.1305262, 0, 0.9914449)` |

### 3.3 UV・テクスチャ向き・法線

- `blender/probe/textures/p0_asym_test.png`（256×256 RGBA）を生成し、4 象限の色分け（左上: オレンジ、右上: ティール、左下: パープル、右下: グリーン）および上辺ゴールド帯・左辺マゼンタ帯・「F」字型の非対称マーカーを配置した。
- 各ボックス面を外向き反時計回り（CCW）の頂点順＋`bmesh.ops.recalc_face_normals` で構築し、UV `(0,0)→(1,0)→(1,1)→(0,1)` を割り当てた。
- `review/probe/01_probe_overview.png` と `02_probe_detail.png` の目視確認、および `exports/probe/bundle/tex_p0_asym_test_png_color_2a547446.png` の `StaticTexture2D` インポートにより、上下反転・左右反転・裏面透過（法線反転）が無いことを確認した。

### 3.4 マテリアルとテクスチャの変換

- Blender の Principled BSDF マテリアル 4 個（`MAT_P0_MeterRef`, `MAT_P0_AsymSign`, `MAT_P0_GateIron`, `MAT_P0_GateLeaf`）がすべて `[FrooxEngine]FrooxEngine.PBS_Metallic` コンポーネントとして `Assets/Materials` スロット配下に変換された。
- `MAT_P0_AsymSign` の Base Color テクスチャは `Assets/Textures` スロット配下の `[FrooxEngine]FrooxEngine.StaticTexture2D` に変換され、`AlbedoTexture` フィールドへ参照接続された。

### 3.5 原点・ピボット・親子階層の保持と末端 Empty の注意点

- `--preserve-hierarchy` 指定時、メッシュを子孫に持つ Empty（`P0_PivotGate_001` および `P0_PivotGate_001_Hinge`）は Resonite 上でも親 Slot として保持され、ローカル座標・回転ピボットがそのまま機能する。
- **注意点（後続タスクへの重要事項）**: 子孫に Mesh を持たない末端 Empty（`P0_PivotGate_001_Hook` のような `attachment_point`）は、`resoloop blender export` の出力（`model.apply.json`）では省略される。
  - `.blend` 側および `assets/manifest/<key>.json` の `parts` / `hierarchy.attachment_points` には正確なローカル座標（例: `[0.72, 0.0, 0.88]`）を記録しておき、Resonite 上でも空 Slot として残す必要がある場合は微小なダミーメッシュを持たせるか apply plan 側で Slot を補うこと。

### 3.6 再実行時のべき等性（重複防止）

- `modeling/probe/build.py` を新規シーン（`resoloop blender run modeling/probe/build.py --json`）と既存 `.blend`（`resoloop blender run modeling/probe/build.py --blend blender/probe/probe.blend --json`）に対して連続実行し、どちらも `objects_count = 7`, `meshes_count = 4`, `materials_count = 4`, `images_count = 1` で完全に一致することを確認した。

---

## 4. Resonite 実機検証結果 (`ws://localhost:44608/`)

- **接続先**: `ws://localhost:44608/`（Resonite `2026.10.29.1239` / ResoniteLink `0.13.1.0`）
- **検証用一時ルート Slot**: `Root/ResoLoop_Test_P0_Probe`（Slot ID: `Reso_8006`）

1. **オフライン・オンライン検証 (`resoloop validate`)**:
   - `resoloop validate exports/probe/bundle/model.apply.json --offline --brief` → `valid: true, slots: 13, components: 13, references: 14, issueCount: 0`
   - `resoloop validate exports/probe/bundle/model.apply.json --url ws://localhost:44608 --brief` → `valid: true, slots: 13, components: 13, references: 14, issueCount: 0`
2. **初回 `diff` / `apply`**:
   - `resoloop diff` → `creates: 32, updates: 0, noOps: 0`
   - `resoloop apply` → `created: true, slotsCreated: 13, componentsAdded: 14, assetsImported: 5`（4 メッシュ + 1 テクスチャが標準の `file` モードで正常にインポート完了）
3. **2 回目 `diff` / `apply`（べき等収束確認）**:
   - 2 回目 `resoloop diff` → `creates: 0, updates: 0, renames: 0, deletes: 0, noOps: 32`
   - 2 回目 `resoloop apply` → `created: false, slotsCreated: 0, slotsUpdated: 0, slotsUnchanged: 13, componentsAdded: 0, componentsUpdated: 0, componentsUnchanged: 14, assetsImported: 0, assetsUnchanged: 5`
4. **バックアップと一時 Slot 削除**:
   - `resoloop import Reso_8006 --output tmp/backup_p0_probe --url ws://localhost:44608 --json` でスナップショット取得を確認（注意: `resoloop import Root` は `IMPORT_ROOT_FORBIDDEN` のため、必ず `Root` 直下の対象 Slot ID を指定する）。
   - `resoloop slot delete Reso_8006 --yes --url ws://localhost:44608 --json` で削除し、`resoloop find --name ResoLoop_Test_P0_Probe --exact` が `[]`（0 件）であることを確認した。
