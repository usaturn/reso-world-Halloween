# P2 静的統合（W08、Issue #41）

Halloween Magical Carnival の P1 の成果（`world` と 5 地区）を、Meshy 素材の箇所は仮モデルのまま、Resonite のワールドへ静的に統合した記録。基本照明・スポーン・歩行用の当たり判定もここで作った。親 #1 の Spec §12「P2：統合の完了条件」の 1 つ目と、4 つ目のうち静的な側に当たる（Issue #41 の「W08 の完了と P2 全体の完了」）。

- 担当: Claude Code（Opus 5.5）、2026-10-31〜11-01（UTC）。apply したのはこのセッションだけ
- 着手前の確認事項の回答: #41 の issuecomment-6545243021（以下「回答 N」）
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1
- 入力: `main` の `5514cf3`（W07 のマージ）の P1 の成果と `docs/p1-handoff.md`
- 確認できたことと、確認していないこと（14 章）を分けて書く。ResoniteLink の ID と接続先のポートはセッション限りなので、この文書には恒久の値として書かない

## 1. 適用先

| 項目 | 値 | 確かめ方 |
|---|---|---|
| ワールド | 新しい専用のワールド「Halloween Magical Carnival」（回答 2。利用者が作成） | `resoloop discover --json` の候補が 1 件で、セッション名が一致 |
| 接続 | 作業のときの ResoniteLink（ローカル）。ポートはセッションごとに変わるので、次の作業でも `discover` から確かめる（回答 1） | `resoloop doctor --url <URL> --json` が ready |
| 公開範囲 | 利用者だけが入れる設定（回答 2。利用者の設定で、エージェントは設定画面を見ていない） | `Root` の直下の User は利用者の 1 人だけ（apply の前に観察） |
| W08 の root Slot | `Root/HalloweenMagicalCarnival`（位置 0・回転 0・拡縮 1） | `content/main.json` で作り、`resoloop inspect` で確かめてから地区の `--parent` にした |
| 所有範囲 | `Root/HalloweenMagicalCarnival` の下だけ（回答 3）。既定の物は 1.1 の 4 つを無効にしただけで、削除・その他の変更はしていない | 全 diff の対象を、パスで root の下か資産の取り込み（`$assets/...`）だけと確かめた（7 章） |
| ほかに apply する人・エージェント | いなかった（回答 7。利用者は W08 の root の下を手で変えない） | 作業の間、`Root` の直下の User は利用者だけ |

### 1.1 ワールドに最初からあった物

apply の前に `resoloop hierarchy --depth 2` で観察した `Root` の直下（回答 3 の「着手時に確かめる」）。

| Slot | 中身 | W08 の扱い |
|---|---|---|
| `Controllers` | `SimpleUserSpawn`・`CommonAvatarBuilder`、移動の方式 | 変えていない |
| `Roles` | 権限の設定 | 変えていない |
| `Clipboard Importer` | `ClipboardImporter` | 変えていない |
| `SpawnArea` | `CommonSpawnArea`（原点、半径 4 m の円） | **無効にした**。原点は中央の噴水と M02 の仮モデルの位置で、新しく入った人がその中に出てしまう。W08 のスポーン（4 章）に替えた |
| `Light` | 太陽の向きの `Directional` ライト（強さ 0.8、影あり） | **無効にした**。昼の光で、W08 の月光（3 章）と重なる |
| `Skybox` | 昼の `ProceduralSkyMaterial`、環境光（`AmbientLightSH2`）、反射プローブ | **無効にした**。W08 の夜の空と環境光（3 章）に替えた。夜の空を使う空にした後で無効にした |
| `Ground` | 高さ 0 の 1000 m 四方のグリッドの床と、厚さ 0 の `BoxCollider` | **無効にした**。島の上面（高さ 0〜0.07 m）と同じ高さで重なり、島の間の虚空にも見えない床ができる |
| `User ...`、`__TEMP` | 利用者のアバターと一時領域 | 触っていない |

無効にした 4 つは、変える前に `resoloop import <Slot>` で記録し、その記録の `existing.slotChanges` で `IsActive` を `false` にした（diff はそれぞれ 1 件の更新だけ）。記録と state は親の checkout のプロジェクトの `tmp/w08/05_default_<名前>_<UTC>/`（Git の対象外）にある。戻すときは同じ記録の `IsActive` を `true` にして diff・apply する。

## 2. Slot の構成

```text
Root/HalloweenMagicalCarnival            # W08 の root（content/main.json、ObjectRoot）
├─ Environment
│  ├─ NightSky                           # 夜の空・環境光・反射プローブ（3 章）
│  ├─ MoonLight                          # 月光（Directional、影あり）
│  └─ KeyLights/<6 個>                    # 主要ライト（Point、影なし）
├─ SouthEntranceSpawn                    # スポーン（4 章）
├─ world                                 # 各地区のバンドル（exports/p2_static/<key>-<UTC>/p2.apply.json）
├─ A_plaza
├─ B_mansion
├─ C_candy
├─ D_amusement
└─ E_forest
```

- 地区の root（`world`・`A_plaza` など）の下は、P1 の `.blend` の階層そのまま（`--preserve-hierarchy`）。アセットの root（P1 の `asset_root`）、可動部品の root（`motion_root`）、見た目（`visual_root`）、取付位置（`attachment_points`）は P1 のオブジェクト名がそのまま Slot 名になる。Spec §6.3 の `AssetRoot / MotionRoot / VisualRoot / AttachmentPoints` は、この P1 の階層をそのまま使う（W08 で Slot 名を付け替えていない）
- `FixedCollisionRoot` に当たるのは、Meshy の仮モデルの静的な部分の兄弟に置いた `<仮モデルの Slot 名>_FixedCollision`（5 章）。通路などの当たり判定は、その物の見た目の Slot の上にある（差し替えない物なので）
- `ObjectRoot` を、W08 の root、地区の root、地区の root の直下の物（Blender_Providers と FixedCollision を除く）に付けた（`resonite-build` スキル）。resoloop がそれぞれに `AI_GeneratedContent` を自動で足す
- 後続が Slot を探すときは、ResoniteLink の ID ではなく、パス（例 `Root/HalloweenMagicalCarnival/B_mansion/BMN_MansionPlaceholder_001`）か、state ファイルと `$slot:<key>`（キーはバンドルの `slot.key`。例 `object_BMN_MansionPlaceholder_001_<8 桁>`）を使う

## 3. 照明と空

`modeling/p2_static/build_content.py` が `content/main.json` に書く。Spec §11 のとおり、ランタンなどの小さな光は P1 の発光の材質だけで表し、実ライトは 7 個（影は月光だけ）にした。

| 物 | Component | 値 | 理由 |
|---|---|---|---|
| 夜の空 | `Skybox` ＋ `ProceduralSkyMaterial` | `SkyTint` (0.62, 0.30, 0.60)、`GroundColor` (0.07, 0.05, 0.11)、`Exposure` 0.35、`AtmosphereThickness` 0.6、太陽 = 月光（`SunSize` 0.03 で月の円盤） | `layout/world_layout.json` の `lighting_preset`（`halloween_dusk_purple_amber`）と `sky_moon` の紫の夕闇。最初の `SkyTint` (0.42, 0.26, 0.60) は青く見えたので、撮影を見て 1 回だけ直した |
| 環境光・反射 | `ReflectionProbe`（空だけ、空の材質が変わったときに描く）→ `ReflectionProbeSH2` → `ValueCopy<SphericalHarmonicsL2<colorX>>` → `AmbientLightSH2` | ワールドの既定の空と同じ形 | `SphericalHarmonicsL2` の値は resoloop が書けない（`VALUE_TYPE_UNSUPPORTED`）ので、参照だけでつないで夜の空から作らせた。空の色を変えたとき環境光も暗く変わったことを撮影で確かめた |
| 月光 | `Light`（Directional） | 強さ 0.45、色 (0.72, 0.74, 1.0)、影 Soft・強さ 0.8。向きは `sky_moon` の方位 25°・高度 38° から（`moon_light_rotation`） | 夜の主な光。影を付けるのはこれだけ |
| 主要ライト 6 個 | `Light`（Point、影なし） | 中央広場のカボチャの上 (0, 0, 9.5)、南の入口 (0, -42.5, 5.0)、B の玄関 (0.7, 34.5, 4.6)、C のアーチ (33, 0, 5.6)、D の回転木馬 (-10.5, -32, 7.0)、E の時計塔 (-35, 0, 6.5)。Blender の座標（Resonite は (x, z, y)）。範囲 12〜20 m、強さ 1.3〜1.6 | 5 つのランドマークと入口を夜の中で見分けられるようにする。C のアーチの位置は `layout/areas/C_candy.json` の `Light_Anchor` の `LA_C_CandyArchCrown_001`。C のほかの 4 つの候補と各地区の取付位置は使っていない（P3 の演出の範囲） |
| 霧 | なし | — | **未実装**。Resonite にワールド全体の霧の Component が無い（Reflection の検索で見つかるのは箱の範囲の材質 `FogBoxVolumeMaterial` だけ）。箱の霧は透過の重なりになり、Spec §11 の「濃い霧を控える」とも合わないので使っていない。遠景は空の暗い地平で表した |

- 夜の空と環境光をワールドで使うものにするのは、`Skybox` と `AmbientLightSH2` の `SetActive`（Reflection で確かめたメソッド）。`content/main.json` の probe のテストに書いてあり、`resoloop test content/main.json --state <p2_root.json> --probe --yes` で実行した（2 つとも `verified`）。ワールドを開き直して空が昼に戻っていたら、同じコマンドをもう一度実行する（P4 の保存・再読込の確認で見る）
- 既定の空に戻すときは、`Root/Skybox` を有効にして、その `Skybox`・`AmbientLightSH2` の `SetActive` を呼ぶ
- 見え方（撮影 12 章）: 全景・5 エリア・入口・橋で、通路の縁の街灯とランタン、入口の門、橋の手すり、5 つのランドマーク（中央のカボチャ・B の屋敷・C のアーチ・D の回転木馬・E の時計塔）が見分けられる。黒い面・同じ高さの面のちらつき・透けは撮影では見つからなかった

## 4. スポーン

| 項目 | 値 |
|---|---|
| Slot | `Root/HalloweenMagicalCarnival/SouthEntranceSpawn` |
| 位置 | Blender (0, -44, 0.08) = Resonite (0, 0.08, -44)。W01 の `spawn` の位置で、床（A の入口の舗装の上面 z 0.072）の 8 mm 上 |
| 向き | 回転 0。Slot の +Z（Blender の +Y = 北）を向く。`CommonSpawnArea.OrientUser` true |
| 範囲 | `CirclePointGenerator` の半径 2.0 m |
| 既定のスポーン | `Root/SpawnArea` を無効にした（1.1） |

8 章の 13（南の入口のベンチ 2 脚がスポーンの空き半径に入る）の解消:

- ベンチの内側の縁はスポーンから 2.86 m。ベンチは動かさず、W01 の `layout/world_layout.json` の空き半径を実際に空いている範囲に合わせて 3.0 m（`spawn`）・3.5 m（`Spawn_South_Entrance_Gate`）から 2.8 m にした（`modeling/world/layout_data.py`。12 章）
- 実際に出る範囲は半径 2.0 m の円にした。アバターの幅を見込んでもベンチまで 0.8 m 以上空く
- W07 の検査（`review/overview/checks.json` の `spawns`）を作り直し、半径 2.8 m の中の障害物が 2・6 から 0 になった
- 実機: 利用者がリスポーンして、南の入口に床の上・北向きでベンチに重ならずに出ることを確かめた（9 章）

## 5. 歩行用の当たり判定

`modeling/p2_static/colliders.py` が、export したバンドル（`model.apply.json`）から `p2.apply.json` を作るときに足す。export の出力そのものは変えない。

### 5.1 方針

| 対象 | 当たり判定 | 理由 |
|---|---|---|
| 静的なメッシュ（地形・道・橋・広場・前庭・台地・坂・階段・建物・柵・手すり・崖の柵・街灯・ベンチ・木・岩など） | その Slot に `MeshCollider` を 1 つ。参照するメッシュはその Slot の `StaticMesh`。`Type` Static、`CharacterCollider` true、`Sidedness` DualSided | 見た目と同じ形で歩ける面と通れない物を一度に作れる。坂・階段・円い道も形どおりになる。片面だけの面でも両側から止まるように DualSided にした |
| Meshy の仮モデルの静的な部分（M01 の門のアーチ、M02 の巨大カボチャ、M03 の屋敷、M04 の工房、M07 の時計塔の本体） | 仮モデルの Slot と同じ親・同じ変換の兄弟 Slot `<名前>_FixedCollision` に、同じメッシュの資産を参照する自分の `StaticMesh` と `MeshCollider` | Spec §6.3 の `FixedCollisionRoot`。差し替えの子が見た目（`visual_root`）を替えても当たり判定は残る |
| 可動部品（アセット一覧の `motion_roots` とその子孫。78 個） | なし | Spec §8・§11（動く物には当たり判定・剛体を付けない）。回転床・座席・扉・列車・カップ・針・鐘・おばけなど |
| 取付位置（`attachment_points`） | なし | 小さな目印のメッシュ |
| `WLD_FloatingIslets_001` | なし | 遠景の浮き岩。歩いて届かない |
| `CCD_WitchPatrolLoop_001_GuideRing`、`CCD_M08_FlyingWitchProxy_001` | なし | 高さ 10 m の空中の目印と、空を飛ぶ M08 の仮モデル |
| `CCD_MagicCauldron_001_Liquid`、`EFR_Pond_001_Water` | なし | 液面・水面。器と池の底に当たり判定がある |
| `EFR_ClockTower_001_Dial` | なし | 高さ 8 m の仮の文字盤（M07 の差し替えの範囲）。手が届かない |
| E の茂み・小さなキノコの群れ・中くらいのキノコ（`EFR_Bush_*`・`EFR_MushroomCluster_*`・`EFR_MushroomMedium_*`。発光の部品を含む） | なし | W06 が `assets/manifest/E_forest.json` に書いた `collider_policy` の `none` に従った |

E の `collider_policy` のほかの値（`box`・`convex_hull`・`mesh_static`・`separate_fixed_collision`）は、すべて上の `MeshCollider` で作った（`box` の木道は坂の両端を、`convex_hull` の木は樹冠の下を形どおりにするため）。`separate_fixed_collision` の時計塔は M07 の本体を兄弟の `FixedCollision` にし、顔のある木は動く枝・目に付けず幹にだけ付けた。ほかのキーには `collider_policy` の記録が無いので、この表を W08 の方針とする（アセット一覧の `collider_policy` は書き換えていない）。

### 5.2 数（`exports/p2_static/<key>-<UTC>/colliders.json`）

| キー | メッシュの Slot | `MeshCollider`（見た目の Slot） | `FixedCollision` | なし |
|---|---|---|---|---|
| `world` | 21 | 20 | 0 | 1 |
| `A_plaza` | 110 | 40 | 2（M01 のアーチ・M02） | 68 |
| `B_mansion` | 45 | 27 | 1（M03） | 17 |
| `C_candy` | 42 | 26 | 1（M04） | 15 |
| `D_amusement` | 58 | 30 | 0 | 28 |
| `E_forest` | 115 | 58 | 1（M07） | 56 |
| 合計 | 391 | 201 | 5 | 185 |

`colliders.json` の `objects` に、メッシュの Slot ごとの方針と理由がある。

### 5.3 西の主動線の床と時計塔の台座（8 章の 5）

W01 の西の森の道（`WLD_WestBridge_001` の森の部分）は x -42.25 まで伸びて、時計塔（`EFR_ClockTower_001_Body`、x -42.289〜-34.711）の下を通っていた。床を時計塔の東の面 x -34.711 で止めた（`modeling/world/build.py`。12 章）。Resonite での実測で、床の西の端と時計塔の東の面はどちらも x -34.711（`review/p2_static/live_checks.json` の `dimensions`）。重なりは床の上面 0.05 m の時計塔の中に隠れた部分だけだったので、見た目は変わらない。W07 の動線の検査（`checks.json` の `routes`）も変わらず問題 0。

## 6. export と validate

`uv run python modeling/p2_static/export_p2.py --url <URL>`。キーごとに新しい `exports/p2_static/<key>-<UTC>/` へ、確かめた `Root/HalloweenMagicalCarnival` を `--parent` にして export した（`exports/p1/` の試験用のバンドルは使っていない）。2 回行い（`...T153958Z` と `...T155217Z`）、2 回目の宣言・メッシュは 1 回目とバイト単位で同じだった。

| キー | Slot（export / 当たり判定を足した後） | `.blend` のオブジェクト | 三角形 | 頂点 | 材質 | 描画の区切り | 画像 | 警告 | validate（`model` / `p2`、オフライン・`--strict`） |
|---|---|---|---|---|---|---|---|---|---|
| `world` | 40 / 40 | 21 | 12,088 | 25,731 | 17 | 67 | 0 | 2 | すべて終了コード 0・issues 0 |
| `A_plaza` | 164 / 166 | 141 | 18,448 | 40,149 | 21 | 240 | 0 | 2 | 同上 |
| `B_mansion` | 87 / 88 | 66 | 7,540 | 17,783 | 19 | 112 | 0 | 2 | 同上 |
| `C_candy` | 79 / 80 | 53 | 12,116 | 29,226 | 24 | 151 | 0 | 2 | 同上 |
| `D_amusement` | 98 / 98 | 76 | 15,628 | 37,719 | 20 | 194 | 0 | 2 | 同上 |
| `E_forest` | 189 / 190 | 146 | 57,978 | 146,714 | 41 | 285 | 0 | 3 | 同上 |

- export の Slot 数は `docs/p1-export-report.md` 2 章と同じ。当たり判定を足した後の差は `FixedCollision` の Slot
- 警告は P1 と同じ性能の目安（材質 8 超、描画の区切り 16 超、E の三角形 5 万超）。Issue の範囲外なので記録だけ（10 章）
- 画像は 0 のまま（P1 のキーは画像を使わない）
- コミットするのは各出力先の `report.json`・`validate.json`・`colliders.json`。バンドル本体（`*.apply.json`・`*.mesh.json`）はコミットしない

## 7. apply の手順と結果

state ファイルは回答 5 のとおり、親の checkout の `/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/state/` にキーごとに置いた（worktree の中には置かない）。

| 宣言 | state |
|---|---|
| `content/main.json` | `p2_root.json` |
| `exports/p2_static/<key>-<UTC>/p2.apply.json` | `p2_<key>.json`（`p2_world.json`・`p2_A_plaza.json` など） |

手順（プロジェクトのディレクトリ。`ST` は上の state の場所、`URL` は確かめた接続先）:

```sh
uv run python modeling/p2_static/build_content.py
resoloop diff content/main.json --state "$ST/p2_root.json" --brief --report <新しいファイル> --url "$URL" --json
resoloop apply content/main.json --state "$ST/p2_root.json" --url "$URL" --json
resoloop test content/main.json --state "$ST/p2_root.json" --probe --yes --url "$URL" --json   # 夜の空と環境光の SetActive
uv run python modeling/p2_static/export_p2.py --url "$URL"
for k in world A_plaza B_mansion C_candy D_amusement E_forest; do
  B=$(ls -d exports/p2_static/$k-* | tail -1)
  resoloop diff "$B/p2.apply.json" --state "$ST/p2_$k.json" --brief --report <新しいファイル> --url "$URL" --json
  resoloop apply "$B/p2.apply.json" --state "$ST/p2_$k.json" --url "$URL" --json
done
uv run python modeling/p2_static/verify_live.py --url "$URL" --raw-out <Git の外> --output review/p2_static/live_checks.json
```

- apply の前には毎回、`resoloop import <W08 の root の ID> --output <新しいディレクトリ>` でスナップショットを取った（回答 4）。置き場は親の checkout のプロジェクトの `tmp/w08/`（Git の対象外）。最初の apply の前は root が無かったので、`Root` の直下の観察（`00_root_hierarchy_before_w08_<UTC>.json`）を残した
- diff の対象: 1 回目の diff の操作（`content/main.json` 29、地区 184〜780）は、すべて `Root/HalloweenMagicalCarnival/` の下の作成か、メッシュの資産の取り込みだった。更新・名前の変更・作り直し・削除は 0。`--prune` は使っていない
- 数の要約は `review/p2_static/apply_summary.json`

| 宣言 | 1 回目の apply（Slot / Component / 資産） | 2 回目の diff | 2 回目の apply | 再 export 後の diff・apply |
|---|---|---|---|---|
| `content/main.json` | 12 / 17 / 0 | 変更 0（no-op 29） | 書き込み 0 | — |
| `world` | 40 / 123 / 21 | 変更 0（no-op 184） | 書き込み 0（資産 21 は変わらず） | 変更 0・書き込み 0 |
| `A_plaza` | 166 / 379 / 110 | 変更 0（655） | 書き込み 0 | 変更 0・書き込み 0 |
| `B_mansion` | 88 / 200 / 45 | 変更 0（333） | 書き込み 0 | 変更 0・書き込み 0 |
| `C_candy` | 80 / 196 / 42 | 変更 0（318） | 書き込み 0 | 変更 0・書き込み 0 |
| `D_amusement` | 98 / 222 / 58 | 変更 0（378） | 書き込み 0 | 変更 0・書き込み 0 |
| `E_forest` | 190 / 475 / 115 | 変更 0（780） | 書き込み 0 | 変更 0・書き込み 0 |

- `content/main.json` は 1 回目の後に空の色を 1 回直した（diff は `sky_material` の更新 1 件だけ、apply は Component の更新 1）。その後の 2 回目の diff・apply が上の表
- W08 の root の下の数（実測）: Slot 674（root の宣言 12、地区 662）、Component 1,612（root 17、地区 1,595）。地区の Component は宣言 1,365 と、resoloop が自動で足す `AI_GeneratedContent` 230 の和

## 8. Resonite での実測

`review/p2_static/live_checks.json`（`modeling/p2_static/verify_live.py`）。`resoloop hierarchy --under Root/HalloweenMagicalCarnival` の 1 回の観察から、W08 の root からローカルの変換を順にかけて世界の座標を求めた。再 export 後の apply の後に取り直して、すべて問題 0。

| 検査 | 結果 |
|---|---|
| Slot・Component の数 | 6 キーとも、実測が宣言（＋自動の `AI_GeneratedContent`）と一致 |
| `.blend` のオブジェクト | 6 キーの 503 オブジェクトが、すべて同じ階層・名前の Slot としてある（キーごとの数は `docs/p1-export-report.md` 2 章と同じ） |
| 可動部品 78 個の原点 | `checks.json` の `motion_parts` の `pivot_world` を (x, z, y) に直した値との差は最大 0.66 mm（1 cm 以内）。78 個とも別の Slot のままで、下に当たり判定は無い |
| Meshy の仮モデル 9 行 | 位置の差 0。M01・M02・M03・M04・M07 の静的な部分の `FixedCollision` がある |
| ランドマーク 5 つ | 建てた物（`checks.json` の `landmarks` の `built_origin`）との位置の差 0 |
| 取付位置 | `attachment_points` に当たり判定は無い。Slot として残っている（オブジェクトの照合に含む） |
| `MeshCollider` の数 | 20 / 42 / 28 / 27 / 30 / 59（`colliders.json` の見た目の Slot と `FixedCollision` の和と一致） |
| 寸法（取り込んだメッシュの頂点 × 観察した変換） | M03 の仮モデルの幅 15.0 m・高さ 10.607 m、時計塔の高さ 14.0 m、北・東の主動線の幅 4.0 m、M01 の仮モデルの幅 11.0 m、西の床の西の端と時計塔の東の面 x -34.711（すべて期待値と一致） |

向き: 南の上からの全景（`review/p2_static/01_overview_south.jpg`）で、手前（-Z）に南の D と入口、右（+X）に東の C、左に西の E、奥に北の B が写り、`review/overview/01_world_aerial_from_south.png`（Blender）と同じ配置。上下・前後・左右の反転は無い。M03 の仮モデルは z 36.39〜46.61 にあり、正面（玄関）は南（-Z）を向く。スポーンからの撮影（`03_spawn_view.jpg`）は北（+Z）を向き、入口の門・南の主動線・中央のカボチャが正面に見える。

撮影（`review/p2_static/`、`resoloop capture content/main.json --camera <名前>`、1280×720）: `01_overview_south`・`02_overview_northwest`（全景）、`03_spawn_view`（スポーン）、`04_entrance_gate`（南の入口）、`05_area_A_plaza`〜`09_area_E_forest`（5 エリア）、`10_bridge_NE`・`11_bridge_NW`（北の台地への連絡橋）。カメラの位置は `content/main.json` の `cameras`。

## 9. 実機での歩行（回答 6）

- 歩いた人・端末: 利用者、デスクトップ（2026-10-31、作業のセッションの中）
- 経路: リスポーン → 南の主動線 → A（環状道路を一周）→ 北の主動線（坂）→ B → 北東の連絡橋（坂）→ C → 南東の連絡橋 → D → 南西の連絡橋 → E → 北西の連絡橋（坂）→ B → A → 東の主動線 → C → A → 西の主動線 → E（時計塔の手前）→ A → スポーン
- 結果: **全経路で問題なし**（利用者の回答）。スポーンの位置・向き、床の抜け・落下、段差や見えない壁での引っかかり、通れない狭さ、坂の上り下り、橋・崖際・台地の縁からの落下を見てもらった
- 確認していないこと: VR での歩行（回答 6 で W08 の範囲外）、二人以上でのすれ違い（8 章の 15 の有効幅 3.30 m・2.38 m。一人で歩いたので未確認）

## 10. 負荷の基準（回答 8）

| 項目 | 値 |
|---|---|
| 時点 | 静的ワールドが完成した時点（6 キーと照明・スポーン・当たり判定の apply の後） |
| 条件 | デスクトップ、利用者一人、歩行の確認と同じ PC、スポーンで北を向いたとき |
| 解像度 | 3440×1440 |
| FPS | 60（利用者の読み取り） |
| フレーム時間 | 約 16.7 ms（60 fps から求めた値。直接は測っていない） |
| 端末（CPU・GPU）・メモリ | 未記録 |

- 60 fps は画面の更新の上限に張り付いている可能性がある（上限の設定は記録していない）。最適化はしていない（回答 8）。P4（W12）で通常時とショー時を比べるときの基準にする
- export の警告（材質・描画の区切り・E の三角形）は記録だけ（6 章）。当たり判定は `MeshCollider` 206 個（三角形の合計は見た目と同じ形）で、物理の負荷は測っていない

## 11. 管理範囲（静的な apply と P3 の動作）

- 静的な apply（地区の `p2.apply.json`）は、全 Slot の名前・位置・回転・拡縮と、メッシュ・材質・当たり判定・`ObjectRoot` の Component を管理する。可動部品の root の位置・回転も **基準姿勢（P1 の rest pose）として管理している**。同じ宣言を apply し直すと、宣言の値に戻す
- P3 が可動部品を動かすとき（例: 扉・回転床・針の `Rotation`、おばけ・キャンディの `Position`）は、静的な apply がその値を戻さないようにする必要がある（Spec §6.3）。次のどちらかで行う
  - 動かす Slot を可動部品の root の子に分け、P3 の駆動はその子に付ける（静的な apply は root の基準姿勢だけを管理する）
  - 可動部品の root の宣言に `"managedFields": ["scale"]` を付け、位置・回転を作成時の初期値だけにする（resoloop の `managedFields`。`colliders.py` と同じ位置で宣言を作り直す処理を足す）
- 当たり判定は動作の対象外（可動部品の下に付けていない）。照明（`content/main.json`）と当たり判定は静的
- 発光: P1 の発光の材質（`PBS_Metallic` の `EmissiveColor`）はバンドルの材質の Slot（地区の root の `Blender_Providers` の下）にある。P3 で発光を変えるときは、材質が地区の中で共有されていること（同じ材質を使う物がすべて変わる）に注意する（Spec §11）

## 12. 直した P1 のファイル

#41 の「P1 のキーの所有ファイルの最小限の修正」。W01〜W07 はすべて閉じている。

| ファイル（所有） | 変更 | 旧 → 新 | 理由 |
|---|---|---|---|
| `modeling/world/build.py`（W01） | 西の森の道（`WLD_WestBridge_001` の森の部分）を時計塔の東の面で止めた | 道の範囲 ローカル x -25.0〜-3.0（世界 -42.25〜-20.25）→ -17.461〜-3.0（世界 -34.711〜-20.25） | 8 章の 5。床と時計塔の当たり判定が重ならないようにする。見た目は変わらない（重なっていた部分は時計塔の中） |
| `modeling/world/layout_data.py`（W01） → `layout/world_layout.json` | スポーンの空き半径 | `spawn` 3.0 → 2.8、`Spawn_South_Entrance_Gate` 3.5 → 2.8 | 8 章の 13。ベンチまで実際に空いている 2.86 m に合わせた |
| `assets/manifest/world.json`（W01、ビルドで再生成） | `WLD_WestBridge_001` の外寸 | 幅 28.11 → 20.571、`bounds_local` の min x -25.0 → -17.461 | 上の変更の結果 |
| `assets/manifest.json`・`review/overview/checks.json`（W07、`modeling/overview/build.py --arg=--no-render` で再生成） | `WLD_WestBridge_001` の外寸、スポーンの検査 | スポーン 2 つの半径 3.0・3.5 → 2.8、障害物 2・6 → 0 | 上の変更の結果。動線・可動部品・仮モデル・ランドマークの検査は変わらない |

- 作り直した後に `uv run python tools/check_data.py --key <key>`（7 キー）、`uv run python tools/check_blend.py`（9 ファイル、エラー 0）、`uv run pytest` が通り、E のビルドの `violations` は 0、E のデータは変わらなかった
- `modeling/E_forest/layout.py` の説明の「x = -42.25 まで」は W06 の文書なので直していない（13 章の要望）
- ID・部品名・可動部品の原点と階層は変えていない
- 作り直して変わった確認画像（`review/world/` など）と `.blend` はコミットしていない（見た目は変わらない）

## 13. 保存

回答 4 のとおり、全地区の apply と確認が終わった後に 1 回だけ、エージェントの依頼で利用者が Resonite で保存する。**この節は保存の後に書き足す。**

- 保存した後に apply し直すと、取り込んだ資産の URL が `local://` から `resdb:///` に変わっているので、最初の diff で資産の作り直しや重複が無いことを確かめる（`resonite-build` スキル）。W08 は保存の後に apply しない。保存の後の最初の再 apply は、Meshy 素材の差し替えの子で起きる（`handoff/W08.md`）
- 保存・再読込の後の確認（空・環境光が夜のままか、当たり判定・スポーンが残るか）は P4（W12）で行う

## 14. Resonite で未確認の項目

確認済みの項目（6〜10 章）と分けて書く。

- 保存・再読込の後の状態（13 章。P4）。とくに、夜の空と環境光が `SetActive` の後もワールドの空として保存されるか、既定の 4 つの無効が保存されるか
- VR での歩行と、二人以上でのすれ違い・途中参加（P4）
- 負荷の端末（CPU・GPU）・メモリ、FPS の上限の有無（10 章）
- 同じ高さの面の遠景でのちらつき（8 章の 14）は、撮影と利用者の歩行では見つからなかったが、視点を網羅して確かめてはいない
- 可動部品の回転の向き（Blender の Z 軸まわり +θ → Resonite の Y 軸まわり -θ）は、原点の位置だけを確かめた。動かして確かめるのは P3
- 霧（未実装。3 章）
- `docs/p1-handoff.md` 8 章の 1〜4・6〜8（Meshy 素材の差し替えの子の範囲）

## 15. 後続への引き継ぎ

- Meshy 素材の差し替えの子: `handoff/W08.md` の 3 章（仮モデルごとの Slot のパス、差し替えの範囲、取付位置、当たり判定の置き場、export と apply の手順、state ファイル、保存の後の最初の diff の注意）
- P3（W10・W11）: 8 章の可動部品の原点（`live_checks.json` の `motion_parts`）、11 章の管理範囲、3 章の照明
- P4（W12）: 13・14 章、10 章の負荷の基準
- `content/` に後続の子が宣言を足すとき: `content/main.json` は W08 の root・照明・スポーンの宣言で、`modeling/p2_static/build_content.py` から作る。後続は別のファイル（例 `content/<子のキー>.json`）に、別の ownership キーと state ファイルで、`Root/HalloweenMagicalCarnival` の下の自分の Slot だけを宣言する。地区のバンドルの中身を変えるときは、そのキーの export をやり直して `colliders.py` を通す
