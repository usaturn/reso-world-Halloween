# P2 Meshy 素材の差し替え（W09R、Issue #44）

仮モデルを Meshy の仕上げた素材に差し替える方式と、最初の素材 M02 巨大ジャック・オー・ランタンの差し替えの記録。残りの 7 素材の子は、この文書の 2・4 章の手順と `handoff/W09R.md` を使う。後続の子の記録は 12 章から（W09R-C #46 の M04・M08 は 12 章、W09R-A #47 の M01 は 13 章）。

- 担当: Claude Code（Opus 5.5）、2026-10-31（UTC）。apply したのはこのセッションだけ
- 着手前の確認事項: W08 #41 の回答（issuecomment-6545243021）をそのまま使う（2026-10-31 の利用者の決定）

## 1. 適用先と版

- ワールド「Halloween Magical Carnival」（`resoloop discover` の候補 1 件）。W08 の root `Root/HalloweenMagicalCarnival` の下だけを変えた
- Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1（W08 と同じ）
- 着手時の W08 の root: Slot 674・Component 1,612（W08 の記録と同じ）。スナップショットは親の checkout の `tmp/w09r/01_snapshot_before_20261031T164029Z/`（Git の対象外）

## 2. 方式

### 2.1 決めたこと

| 項目 | 決めたこと | 理由 |
|---|---|---|
| 仕上げた素材の置き場 | 地区のバンドルとは別の宣言（`exports/p2_meshy/<M>-<UTC>/p2m.apply.json`、state は `p2m_<M>.json`）にし、仮モデルの見た目の Slot（`visual_root`。M02 は `APL_GiantJackProxy_001_Body`）の子に置く | 差し替えの範囲（Spec §6.3 の `VisualRoot`）の中だけに作る。地区の宣言の Slot・ID・可動部品・取付位置を作り直さない。素材ごとに diff・apply・巻き戻しができる |
| 仮モデルの見た目 | 地区の宣言（`p2.apply.json`）で、仮モデルの `MeshRenderer` を `Enabled = false` にする（Slot・メッシュは残す）。`modeling/p2_static/export_p2.py` が `colliders.compose` の後に `modeling/p2_meshy/replacements.py` の `hide_placeholders` を呼ぶ | Component を消さない（`--prune` が要らず、すぐ戻せる）。地区を export し直しても、仮モデルが再び表示されない（W08 の手順のまま再 apply できる） |
| 取付位置の目印 | M02 は取付位置 3 つが `_Body` の子なので、Slot と位置は残し、目印のメッシュの描画だけ止める | 目印（半径 4 cm の発光の部品）が M02 の顔の目の間と鼻の上に出ていた（5.3）。P3 は Slot の位置を使うので影響しない |
| 置き方 | バンドルの root Slot に、`visual_root` のローカルでの位置・回転を書く（`replacements.py` の `position_local`・`rotation_z_deg`。回転 = `received.json` の `placement_hint.rotation_z_deg` − 仮モデルのアセットの root の世界の回転）。素材の Slot 自体は変換なし | 素材の Slot の変換をアセット一覧（原点 0・回転なし）と同じに保つ。M02 は 180 − 0 = 180° |
| 当たり判定 | 仮モデルの形の `FixedCollision`（W08 が `visual_root` の兄弟に置いた物）をそのまま使い、仕上げた素材には当たり判定を付けない | M02 の外接箱は仮モデルと同じ（W07 の差 0.000）で、本体は器の上（高さ 1.6 m 以上）にあり歩いて触れない。仮モデルは 932 三角形で、30,792 三角形の `MeshCollider` より軽い。利用者の実機の確認で問題なし（5.5） |
| 画像 | `--pack-pbr` で金属・粗さを 1 枚に詰め、apply は `--texture-transfer data`（`docs/environment.md` 4.2）。解像度は W09-M02 の仕上げのまま（色 2048、詰めた PBR 1024） | Windows の Resonite はコンテナのパスを開けない。解像度は W09-M02 が決めた値 |
| state | 親の checkout の `.resoloop/state/p2m_<M>.json`（W08 の `p2_<key>.json` と同じ場所） | worktree を消しても残す（W08 の回答 5） |

### 2.2 採らなかった方法

- 地区の `.blend` の中で仮モデルのメッシュを仕上げた素材に入れ替え、地区ごと export し直す: 地区の宣言に素材のメッシュ・画像・材質が入り、素材ごとに戻せない。W09-M0N の `.blend` を地区のビルドに持ち込むので、W02〜W06 の所有ファイルを大きく変える
- 地区の宣言から仮モデルの `MeshRenderer` を外して `--prune --yes` で消す: 削除が要り、戻すには作り直しになる。`Enabled = false` で同じ見た目になる
- 仮モデルの Slot（`_Body`）を無効にする: 宣言の Slot には有効・無効の項目が無い（`resoloop schema describe slot`）。M02 では取付位置が `_Body` の子なので、子も消える
- 当たり判定を仕上げた素材のメッシュから作る: 3 万三角形の `MeshCollider` になり、歩いて触れない所では効果が無い。形が大きく違う素材（M03 の建物など）は後続の子が素材ごとに決める（`handoff/W09R.md` 6 章）

## 3. 保存の後の最初の再 apply

W08 の後に利用者が保存したワールドへの最初の diff（16:41:10Z、何も変える前。A は仮モデルの描画を止める宣言で取った）:

| 宣言 | 操作 |
|---|---|
| `content/main.json` | 0 |
| `world`・`B_mansion`・`C_candy`・`D_amusement`・`E_forest`（この子で export し直した `p2.apply.json`） | 0 |
| `A_plaza` | 更新 1（`APL_GiantJackProxy_001_Body` の `MeshRenderer` の `Enabled` だけ）。資産の作成・更新は 0 |

- 資産の作り直し・重複は無かった。`APPLY_ASSET_MIGRATION_UNVERIFIED` も出なかった
- 資産の URL は、保存の後もまだ `local://` だった（`StaticMesh.URL` の観察。W08 の記録 13 章と同じ）。ワールドを開き直していないため。`resdb:///` に変わった後の再 apply は未確認（P4）
- この子で `.blend` を作り直して export し直した 6 キーの宣言とメッシュは、W08 の宣言と同じだった（diff 0。W08 の再 export の結果と同じ）

## 4. 手順

プロジェクト（worktree）のディレクトリ。`ST` は親の checkout の `.resoloop/state`、`T` は親の checkout の `tmp/w09r/`（スナップショットと diff・apply の報告）、`URL` は確かめた接続先。

```sh
resoloop blender run modeling/<M>/build.py --json                     # 仕上げた素材の .blend（M02 は約 50 秒）
uv run python modeling/p2_static/export_p2.py --url "$URL" --key <地区>  # 仮モデルの描画を止めた p2.apply.json
uv run python modeling/p2_meshy/export_meshy.py --url "$URL" --meshy <M>  # p2m.apply.json（validate はオフライン・--strict）
resoloop import Root/HalloweenMagicalCarnival --output "$T/<新しいディレクトリ>" --url "$URL" --json   # apply の前のスナップショット
resoloop diff <p2m.apply.json> --state "$ST/p2m_<M>.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply <p2m.apply.json> --state "$ST/p2m_<M>.json" --texture-transfer data --url "$URL" --json
resoloop diff <地区の p2.apply.json> --state "$ST/p2_<地区>.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply <地区の p2.apply.json> --state "$ST/p2_<地区>.json" --url "$URL" --json
# 同じ diff・apply をもう 1 回行い、変更 0・書き込み 0 を確かめる
uv run python modeling/p2_meshy/verify_live.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p2_meshy/live_checks.json
resoloop capture <p2m.apply.json> --camera <名前> --output review/p2_meshy/<名前>.jpg --width 1600 --height 900 --url "$URL" --json
```

- 置き方・光源・カメラだけを変えるときは、export し直さずに `export_meshy.py --meshy <M> --recompose <既存のバンドル>` で宣言だけを作り直す。export し直すと、メッシュの接線が 1.8e-7 だけ変わり（Blender の export のたびに変わる。W09-M02 の handoff と同じ）、apply がメッシュの資産を取り込み直す（Slot・Component は増えず、`StaticMesh.URL` の更新 1 と資産の取り込み 1。5.2）
- `resoloop capture` は `<名前>.scene.json` も書く。作業ツリーの絶対パスを含むのでコミットしない
- `verify_live.py` は `REPLACEMENTS` のすべての素材のバンドル（`exports/p2_meshy/<M>-*/p2m.apply.json` とメッシュ）を読む。バンドルはコミットしないので、新しい worktree では、前の子が Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/p2_bundles/<M>-<UTC>/` に控えた物（`SHA256SUMS` で確かめる）を、同じ名前の出力先へ写してから実行する（W09R-C で追加。12.4）
- 可動部品を持つ素材（M01 の門扉。W09R-A で追加、13.2）は、1 素材で宣言が複数になる。素材の宣言 `p2m.apply.json`（state `p2m_<M>.json`）と、部品ごとの `p2m_<部品>.apply.json`（state `p2m_<M>_<部品>.json`。M01 は `DoorLeft`・`DoorRight`）を、上と同じ形で diff・apply する（素材の宣言を先に。資産は `--texture-transfer data`）
- コミットするのは `exports/p2_meshy/<M>-<UTC>/` の `report.json`・`validate.json`・`placement.json`（`exports/p2_meshy/.gitignore`）、地区の出力先の `report.json`・`validate.json`・`colliders.json`・`replacements.json`、`review/p2_meshy/` の撮影と `live_checks.json`

## 5. M02 の差し替えの結果

### 5.1 export と validate

| 出力先 | 内容 | validate（オフライン・`--strict`） |
|---|---|---|
| `exports/p2_meshy/M02-20261031T164004Z` | 最初の export（`--parent` は M02 の `visual_root`、`--preserve-hierarchy --pack-pbr`） | issues 0 |
| `exports/p2_meshy/M02-20261031T164338Z` | export し直し（5.2 の確認）。その後、光源とカメラを足して `--recompose` した宣言を apply した | issues 0 |
| `exports/p2_static/A_plaza-20261031T163858Z` | 仮モデルの本体の描画を止めた A | issues 0 |
| `exports/p2_static/A_plaza-20261031T164856Z` | 本体と取付位置の目印 3 つの描画を止めた A（apply した版） | issues 0 |
| `exports/p2_static/<key>-20261031T163858Z`（5 キー） | 3 章の確認に使った world・B〜E | issues 0 |

M02: 三角形 30,792、頂点 27,007、材質 1、描画の区切り 1、画像 2（色 2048×2048、詰めた PBR 1024×1024。RGBA8 とミップの見積もり 合計 約 28 MB）、警告 0。

### 5.2 diff と apply

| 時刻（UTC） | 宣言 | diff | apply |
|---|---|---|---|
| 16:41:47 | M02（最初） | 作成 15（資産 3、Slot 6、Component 6。すべて `_Body` の下） | Slot 6・Component 6・資産 3 を作成 |
| 16:42:22 | A（本体の描画を止める） | 更新 1 | Component の更新 1 |
| 16:42:41 | M02・A の 2 回目 | 変更 0（no-op 15・655） | 書き込み 0 |
| 16:43:49 | M02（export し直した宣言） | 作成 1（メッシュの資産。接線の差） | `StaticMesh` の更新 1・資産の取り込み 1。Slot・Component は増えない |
| 16:44:19 | M02 の 2 回目 | 変更 0 | — |
| 16:49:05 | A（目印 3 つの描画も止める） | 更新 3 | Component の更新 3 |
| 16:49:42 | A の 2 回目 | 変更 0（no-op 655） | 書き込み 0 |
| 16:59:45 | M02（光源を足した宣言。6 章） | 作成 2（Slot 1・Component 1） | Slot 1・Component 1 を作成 |
| 17:01:04 | M02 の 2 回目と、全 8 宣言（`content/main.json`・6 キー・M02） | すべて変更 0 | M02 は書き込み 0 |

- `--prune` は使っていない。削除・名前の変更・作り直しは 0
- apply の前のスナップショット: `tmp/w09r/01_snapshot_before_*`（W08 の root 全体）、`12_snapshot_jack_before_markers_*`・`18_snapshot_jack_before_light_*`（`APL_GiantJackProxy_001`）

### 5.3 実測（`review/p2_meshy/live_checks.json`、`modeling/p2_meshy/verify_live.py`）

期待値は実測から求めず、データ（W07 の `review/overview/checks.json` の `frame_origin_world`、`received.json` の `placement_hint`、アセット一覧）から求める（GPT のレビューの指摘で、親ごと動いた状態を成功と判定しないように直した。10 章）。

| 検査 | 結果 |
|---|---|
| 仮モデルの見た目の Slot の位置 | `_Body` の世界の原点 (0, 1.6, 0) が、W07 の `frame_origin_world` と差 0.0 m |
| 外接箱 | 世界で x -3.1011〜3.1014、高さ 1.6001〜7.6001、z -2.9351〜2.935（6.2025 × 6.0 × 5.8701 m）。アセット一覧の寸法を `_Body` の位置と 180° で置いた値との差 0.0 m |
| 正面と鏡像 | 素材の前方（拡縮を含む変換で求めた向き）は Resonite の (0, 0, -1)（南。スポーンの向き +Z の逆で、入口から顔が見える）。祖先の拡縮はすべて正 |
| 描画 | 仮モデルの本体と目印 3 つの `MeshRenderer.Enabled` が false。M02 は Slot と祖先が有効で、`MeshRenderer` が有効、同じ Slot の `StaticMesh` と、色の画像（URL のある `StaticTexture2D`）を持つ `PBS_Metallic` を参照する |
| 取付位置 | `_EyeLightAttach` (0, 3.917, -2.676)、`_MouthReactionAttach` (0, 2.972, -2.806)、`_InteriorLightAttach` (0, 2.581, 2.409)。アセット一覧の `origin_world` と `pivot_local` の位置との差 0.0 m（差し替えの前と同じ） |
| 当たり判定 | `APL_GiantJackProxy_001_Body_FixedCollision` が有効で `_Body` と同じ変換。`MeshCollider` が有効・`Static`・`CharacterCollider` で、同じ Slot の `StaticMesh`（`_Body` と同じメッシュの資産）を参照する。M02 の下に当たり判定は無い |
| 数 | A の Slot 173・Component 386（W08 の 166・379 に、A のすべての差し替えの宣言（今は M02 だけ。Slot 7・Component 6 と自動の `AI_GeneratedContent` 1）を足した値と一致）。W08 の root の下は Slot 681・Component 1,619（W08 から +7・+7） |

ID・部品名・可動部品は変えていない。`APL_GiantJackProxy_001` の名前（Proxy）は ID なので残した。

### 5.4 撮影（`review/p2_meshy/`、1600×900、カメラは `replacements.py` の `cameras`）

`m02_front`・`m02_front_close`（正面）、`m02_oblique_se`（南東の斜め上）、`m02_back`（北）、`m02_eyes_low`・`m02_eyes_low_side`（器の縁の近くの下から。6 章）、`area_A_plaza`（W08 と同じ A の全景）、`overview_south`（W08 と同じ全景）。

- 黒い面・反転・透け・ちらつきは見つからない。顔は南を向き、本体の底は器の上に乗る
- 帽子は Blender では紫、帯は青緑だが、Resonite では茶色寄り・暗い緑に見える。材質の値は正常（金属 約 0、滑らかさ 約 0.4）で、広場の真上 (0, 9.5, 0) の橙色の主要ライト `PlazaPumpkinLight`（W08、色 (1.0, 0.62, 0.28)）を受けた色と合う。照明は W08 の宣言でこの子の範囲外なので、利用者の決定で記録して後続（P3・P4 の照明の調整）に回した
- M02 の手前 (0, 4.8, -3.8) に見える水色の小さな部品は、W02 の定期ショーの取付位置の目印 `APL_PeriodicShowRig_001_GhostOrbitAttach_S`。差し替えの前からあり、範囲外なので変えていない（`handoff/W09R.md` 6 章の要望）

### 5.5 実機の確認（利用者、デスクトップ）

- 2026-10-31: 噴水の器と台座のまわりを歩き、当たり判定は基本的に問題なし。要望として「かぼちゃの中の光源を調整して、近くの下から見ても目が光って見えるようにしてほしい」（6 章で対応）
- 光源を足した後の見え方を利用者が見て「このままでよい」

### 5.6 保存（確認事項 4）

- GPT のレビューへの対応（10 章）の後に、エージェントの依頼で利用者が Resonite で 1 回保存した（2026-10-31、17:31Z より前）。保存の後は apply していない
- 保存の後に読み取りだけで確かめた（17:31:50Z）: M02 と A の diff は変更 0（no-op 17・655）。M02 のメッシュと画像 2 つの資産の URL はまだ `local://`（ワールドを開き直していない。`resdb:///` に変わった後の再 apply は未確認）

## 6. 目の光（利用者の要望）

- `M02` の宣言に、空洞の中の点光源 `M02_InteriorGlow`（`FrooxEngine.Light`、Point、色 (1.0, 0.55, 0.15)、強さ 3.0、範囲 5.0 m、影なし）を足した。位置は M02 のローカル（Blender）(0, 0.8, 1.6)、世界で (0, 3.2, -0.8)
- M02 の内側の壁は空洞の中心を向いているので、中から照らすと目・鼻・口の奥が光る（`m02_eyes_low` と光源の前の比較で確かめた）。顔の穴から漏れた光として、帽子のつばの裏と器の縁が少し橙色になる
- 材質の発光は使っていない（本体の材質を光らせると全体が光る。`handoff/W09-M02.md` 8 章）
- P3 の I03（目の発光の反応）は、この Light の `Intensity` を動かせる（`$component:m02_interior_glow_light`、state は `p2m_M02.json`）。I03 の範囲（反応の演出）は P3

## 7. 負荷

- 利用者の測定（W08 と同じ端末、3440×1440・Ryzen 7 5700G・RTX 4070 Ti SUPER、デスクトップ）: 広場の中央から M02 を見て「たまに 54 FPS ぐらい」。W08 の基準は 60 fps
- 差し替えで増えた物: 三角形 30,792（仮モデル 932 は描画を止めた）、画像 2（約 28 MB の見積もり）、点光源 1（影なし）
- 低下の原因（素材・画像・光源のどれか、測定の揺れか）は切り分けていない（未確認。P4 で通常時・ショー時と比べる）

## 8. 全素材の状態（Spec §12「P2」の 3 つ目、2026-10-31。M04・M08 の行は 2026-11-01 に W09R-C が、M01 の行は同日に W09R-A が更新）

受領は W09 #13（`assets/meshy/received.json`、PR #26）。どの素材も未着ではない。採用しない物は、利用者が作り直す前の版（各ディレクトリの `size_over/`）と、M07 の `NG/`（針が塔に溶接されていた）だけで、確定版で置き換えた。

| 素材 | 受領 | 仕上げ（子・PR） | Resonite への投入 | 確認 | 採用 |
|---|---|---|---|---|---|
| M01 入場ゲート | 済（約 3.0 万三角形） | 済（W09-M01 #14・PR #29。門扉を切り離し両面化） | **済（W09R-A #47。門扉は仮モデルの門扉の Slot の下に別の宣言）** | **Resonite で実測・撮影・利用者の実機**（13 章） | 採用 |
| M02 巨大ジャック・オー・ランタン | 済（約 3.1 万） | 済（W09-M02 #15・PR #27） | **済（この子）** | **Resonite で実測・撮影・利用者の実機**（5 章） | 採用 |
| M03 幽霊屋敷の外観 | 済（約 3.0 万） | 済（W09-M03 #16・PR #35。入口の開口） | 未（`BMN_MansionPlaceholder_001`） | Blender・export・validate まで | 採用 |
| M04 魔女のお菓子工房の外観 | 済（約 3.1 万） | 済（W09-M04 #17・PR #39。窓の発光） | **済（W09R-C #46）** | **Resonite で実測・撮影・利用者の実機**（12 章） | 採用 |
| M05 メリーゴーラウンドの屋根 | 済（約 4.2 万） | 済（W09-M05 #18・PR #34） | 未（`DAM_Carousel_001_M05_Canopy`） | Blender・export・validate まで | 採用 |
| M05 メリーゴーラウンドの中央の柱 | 済（約 3.2 万） | 済（同上） | 未（`DAM_Carousel_001_M05_CenterCasing`） | Blender・export・validate まで | 採用 |
| M06 おばけ列車の先頭車外装 | 済（約 1.5 万） | 済（W09-M06 #19・PR #38） | 未（`DAM_GhostTrain_001_M06_EngineShell`） | Blender・export・validate まで | 採用 |
| M07 魔法の時計塔 | 済（約 3.1 万。針の無い作り直しの版） | 済（W09-M07 #20・PR #32。文字盤の計測） | 未（`EFR_ClockTower_001_Body`・`_Dial`） | Blender・export・validate まで | 採用（`NG/` の版は不採用） |
| M08 ほうきに乗った魔女 | 済（約 3.1 万） | 済（W09-M08 #21・PR #37） | **済（W09R-C #46。点光源 2 つ）** | **Resonite で実測・撮影・利用者の実機**（12 章） | 採用 |

仕上げた物は Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/finished/<M>/`。各素材の差し替えの注意は `handoff/W09R.md` 6 章。

## 9. 直した閉じた子のファイル

| ファイル（所有） | 変更 | 理由 |
|---|---|---|
| `modeling/p2_static/export_p2.py`（W08） | `colliders.compose` の後に `replacements.hide_in_file` を呼び、止めた仮モデルを `replacements.json` に書く（6 行） | 地区を export し直しても、差し替えた仮モデルが再び表示されないようにする（2.1） |

- `A_plaza`（W02）と `M02`（W09-M02）の所有ファイルは変えていない。`.blend` を作り直して変わった追跡中の `.blend`・確認画像・`assets/manifest/M02.json`（`export_result` が `unexported` に戻る）はコミットしていない（形は変えていない）
- `docs/conventions.md` §2・§7.6 と `AGENTS.md` に、キー `p2_meshy` と差し替えの手順・state を足した

## 10. GPT のレビュー（確認事項 7）

- 起動: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（codex-cli 0.166.0、モデル gpt-6-astra）。対象は PR #45 の `fd6b0b0`。Resonite には接続させず、checkout も変更させていない。観点は、宣言の正しさ、diff の対象と収束、実測の検査、W08 のファイルの修正、テストの採用基準の 5 つ
- 結果: 実測の検査に Major 4 件・Minor 1 件、テストに Minor 1 件。宣言・diff・W08 の修正は指摘なし。全文は PR #45 のコメント

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| 1 | Major | 期待値を実測した親から求めるので、仮モデルごと動いても成功する | 採用 | 後続の子も受け入れの証拠に使う検査で、誤った状態を成功と報告するため。`frame_origin_world`・`placement_hint`・アセット一覧の `origin_world` から求めるように直した（祖先の回転を外接箱の期待値に入れていなかった点も、同じ直しで解消） |
| 2 | Major | 負の拡縮で正面が反転しても成功する | 採用 | 正面を拡縮を含む変換で求め、祖先の拡縮がすべて正であることを確かめる |
| 3 | Major | Slot が無効、`MeshRenderer` の参照が切れていても成功する | 採用 | 祖先を含む有効、`MeshRenderer` → `StaticMesh`・材質 → 色の画像の参照をたどる |
| 4 | Major | 当たり判定が無効・設定違い・参照切れ・位置ずれでも成功する | 採用 | `FixedCollision` の有効・変換、`MeshCollider` の有効・`Type`・`CharacterCollider`・参照を確かめる |
| 5 | Minor | 同じ地区に 2 素材あると数の検査を飛ばす | 採用 | 後続の M01 で A に 2 素材目が入るため。地区ごとに、すべての差し替えの宣言の数を足して比べる（`check_counts`） |
| 6 | Minor | 検査の誤判定をテストの採用基準の L として扱っている | 採用 | 「失敗を成功と報告する」は S。`tests/test_p2_meshy_verify.py` に、正しい状態で通る例と、1〜5 の守りの代表 1 件ずつ（計 6 件）を足し、各守りを外すと失敗することを確かめた |

直した検査で実際のワールドを観察し直し、すべて合格した（`review/p2_meshy/live_checks.json`）。ワールドへの書き込みは無い。

## 11. Resonite で未確認の項目

- 保存・再読込の後の状態（M02 の画像と光源が保存されるか）。P4。資産の URL が `resdb:///` に変わった後の再 apply は、W09R-C が確かめた（12.1。作り直し・重複なし）
- VR での見え方、二人以上
- 負荷の低下（60 → ときどき 54 fps）の原因（7 章）
- 帽子の色の照明による変化の調整（5.4。後続）
- `docs/p1-handoff.md` 8 章の 1〜3・6〜8（残りの素材の子）。4（入口の門扉の可動範囲）は W09R-A が門扉の Slot の基準姿勢を決めた（13.2）

## 12. W09R-C（#46）: C 東の M04 お菓子工房・M08 ほうきに乗った魔女

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ。着手前の確認事項は W08 #41 の回答（#46 の本文）
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1（W09R と同じ）
- スナップショットと diff・apply の報告は親の checkout の `tmp/w09r-c/`（Git の対象外）
- 閉じた子の所有ファイル（W04 の `C_candy`、W09-M04・W09-M08 の `M04`・`M08`、W08 の `modeling/p2_static/`）は変えていない

### 12.1 保存の後の最初の diff

- 着手時のスナップショット（`tmp/w09r-c/01_snapshot_before_20261101T022208Z`）は W08 の root の下が Slot 681・Component 1,619 で、W09R の完了時と同じ（利用者が手で変えた所は無い）
- 最初の diff（02:23:51〜02:24:16Z、何も変える前。C は M04・M08 の仮モデルの描画を止める宣言で取った）:

| 宣言 | 操作 |
|---|---|
| `content/main.json` | 0（no-op 29） |
| `world`・`A_plaza`・`B_mansion`・`D_amusement`・`E_forest`（この子で作り直して export した `p2.apply.json`） | 0（no-op 184・655・333・378・780） |
| `C_candy` | 更新 2（`CCD_M04_CandyWorkshopProxy_001`・`CCD_M08_FlyingWitchProxy_001` の `MeshRenderer` の `Enabled` だけ）。資産の作成・更新は 0 |
| M02（W09R が Git の外に控えたバンドル `p2_bundles/M02-20261031T164338Z`） | 0（no-op 17） |

- 資産の URL は、W09R の後の保存とワールドの開き直しで `resdb:///` に移っていた（W08 と M02 の 399 件）。resoloop は「asset URL was migrated to resdb by a world save; state will record the live URL」として no-op と判定し、資産の作り直し・重複は無かった。W09R で未確認だった「`resdb:///` に変わった後の再 apply」はこれで確かめた（画像・光源が保存されることの確認は P4）

### 12.2 設定（`modeling/p2_meshy/replacements.py`）

| 項目 | M04 | M08 |
|---|---|---|
| `visual_root` | `CCD_M04_CandyWorkshopProxy_001`（仮モデルのアセットの root がそのまま見た目。W04 の `hierarchy.visual_roots`） | `CCD_M08_FlyingWitchProxy_001`（C の root の直下。巡回の `CCD_WitchPatrolLoop_001_CarrierPivot` の子ではない） |
| `hide` | 仮モデル（`visual_root` 自身）の `MeshRenderer` | 同じ |
| 回転 | 0（`placement_hint` 90 − 仮モデルの root 90） | 0（`placement_hint` は null。仮モデルは回転 0 で正面 +Y） |
| 置き方 | 土台の下面の中央 = 仮モデルの原点（地面） | 飛行の動作中心 = 仮モデルの原点（巡回の点 0、(43.2, 0, 10.2)） |
| 当たり判定 | 仮モデルの形の `CCD_M04_CandyWorkshopProxy_001_FixedCollision`（C の root の下の兄弟）をそのまま使う。仮モデルと仕上げた素材の外接箱は同じで、利用者の歩行で問題なし（12.7） | 付けない（`collision: False`。空を飛ぶ、P3 の G11） |
| 発光・光源 | 窓の発光の画像（`PBS_Metallic` の `EmissiveMap`、`emissive: True`）。`EmissiveColor` は白のまま（昼も光る。夜の制御は P3） | 点光源 2 つ（`M08_FrontGlow` 前 (0, 1.3, 0.3)・`M08_UnderGlow` 足元の下 (0, 0.2, -1.1)、素材のローカル。色 (1.0, 0.8, 0.6)、強さ 3.0、範囲 3.0・2.8 m、影なし）。利用者の確認で足した（12.7） |

### 12.3 検査の拡張（`modeling/p2_meshy/verify_live.py`）

- 向き: `received.json` の `placement_hint` に回転が無い素材（経路の上の M06・M08）は、W07 の `review/overview/checks.json` の `placeholders.<M>.front_world`（M08 は north(+Y) → 0°）から期待値を求める。どちらから求めたかを `front_source` に書く
- 当たり判定を付けない素材（`collision: False`）: `<visual_root>_FixedCollision` が無いこと、素材のバンドルの root とその子孫に `MeshCollider` が無いことを確かめる。仮モデルに `FixedCollision` があるのに `False` と書いたら設定の誤りとして失敗にする（当たり判定の検査を黙って飛ばさない）
- 発光（`emissive: True`）: 材質の `EmissiveMap` が URL のある画像を参照すること
- テスト: `tests/test_p2_meshy_verify.py` に 3 件（S。`collision: False` の素材は、仮モデルに `FixedCollision` が残っていれば失敗し、無ければ通る。バンドルの root の `MeshCollider` を見落とさない。`emissive` の素材は `EmissiveMap` が無ければ失敗し、あれば通る）。それぞれ守りを外すと失敗することを確かめた（後の 2 件は 12.9 の GPT のレビューで足した）
- 地区ごとの数の検査（`check_counts`）は W09R のまま、C の 2 素材の宣言を足した値で比べた

### 12.4 export と validate

| 出力先 | 内容 | validate（オフライン・`--strict`） |
|---|---|---|
| `exports/p2_meshy/M04-20261101T022427Z` | M04（`--parent` は M04 の `visual_root`、`--preserve-hierarchy --pack-pbr`） | issues 0 |
| `exports/p2_meshy/M08-20261101T022537Z` | M08。光源とカメラは `--recompose` で足した（3 回。最後は光源 2 つ） | issues 0 |
| `exports/p2_static/C_candy-20261101T022203Z` | M04・M08 の仮モデルの描画を止めた C（apply した版） | issues 0 |
| `exports/p2_static/<key>-20261101T022203Z`（5 キー） | 12.1 の確認に使った world・A・B・D・E | issues 0 |

- M04: 三角形 30,702、頂点 49,968、材質 1、描画の区切り 1、画像 3（色 2048×2048、詰めた PBR 1024×1024、発光 1024×1024。RGBA8 とミップの見積もり 合計 約 33.6 MB）、警告 0
- M08: 三角形 31,130、頂点 42,750、材質 1、描画の区切り 1、画像 2（色 1024×1024、詰めた PBR 512×512。合計 約 7.0 MB）、警告 0
- 後続の子のために、apply した M04・M08 のバンドルを Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/p2_bundles/M04-20261101T022427Z`・`M08-20261101T022537Z` に控えた（`SHA256SUMS`）。新しい worktree で `verify_live.py` を実行するときは、M02 と同じく同じ名前の出力先へ写す（4 章）

### 12.5 diff と apply

| 時刻（UTC） | 宣言 | diff | apply |
|---|---|---|---|
| 02:25:09 | M04（最初） | 作成 18（資産 4、Slot 7、Component 7。すべて M04 の `visual_root` の下） | Slot 7・Component 7・資産 4 を作成 |
| 02:25:47 | M08（最初） | 作成 15（資産 3、Slot 6、Component 6。すべて M08 の `visual_root` の下） | Slot 6・Component 6・資産 3 を作成 |
| 02:26:03 | C（仮モデルの描画を止める） | 更新 2 | Component の更新 2 |
| 02:26:09〜02:26:29 | 全 10 宣言（`content/main.json`・6 キー・M02・M04・M08）の 2 回目 | すべて変更 0 | — |
| 02:26:37〜02:26:42 | M04・M08・C の 2 回目 | — | 書き込み 0 |
| 02:37:23 | M08（光源 1 つ目） | 作成 2（Slot 1・Component 1） | Slot 1・Component 1 を作成 |
| 02:41:02 | M08（光源 2 つ目と、1 つ目の強さ） | 作成 2・更新 1 | Slot 1・Component 1 を作成、Component の更新 1 |
| 02:43:01〜02:43:29 | M08 の 2 回目の apply と、全 10 宣言の diff | すべて変更 0 | M08 は書き込み 0 |

- `--prune` は使っていない。削除・名前の変更・作り直しは 0
- apply の前のスナップショット: `tmp/w09r-c/01_snapshot_before_*`（W08 の root 全体）、`13_snapshot_m08_before_light_*`・`17_snapshot_m08_before_light2_*`（`CCD_M08_FlyingWitchProxy_001`）

### 12.6 実測（`review/p2_meshy/live_checks.json`）

| 検査 | M04 | M08 |
|---|---|---|
| `visual_root` の世界の原点 | (38, 0, 0)。W07 の `frame_origin_world` と差 0.0 m | (43.2, 10.2, 0)。差 0.0 m |
| 外接箱 | x 35.3166〜40.6833、高さ -0.0001〜7.6278、z -4.0003〜3.9998（5.3667 × 7.6278 × 8.0001 m）。期待値との差 0.0 m | x 42.5632〜44.1049、高さ 9.5881〜12.0882、z -1.2147〜0.9116（1.5417 × 2.5001 × 2.1262 m）。差 0.0 m |
| 正面と鏡像 | (-1, 0, 0)（西の広場。`placement_hint` から） | (0, 0, 1)（北。`front_world` から）。祖先の拡縮はすべて正 |
| 描画 | 仮モデルの `MeshRenderer.Enabled` が false。素材は有効で、色と発光の画像を持つ `PBS_Metallic` を参照 | 仮モデルの描画が false。素材は有効で、色の画像を参照 |
| 当たり判定 | `FixedCollision` が有効・`visual_root` と同じ変換・`Static`・`CharacterCollider`・仮モデルと同じメッシュ。素材の下に当たり判定なし | `FixedCollision` が無い（方針どおり）。素材の下に当たり判定なし |
| 数 | C の Slot 95・Component 211（W08 の実測 80・196 に、M04 の 7・7 と M08 の 8・8（光源 2 つを含む）を足した値と一致） | 同左 |

- W08 の root の下は Slot 696・Component 1,634（着手時の 681・1,619 から +15・+15）。M02 の検査と A の数も合格のまま
- ID・部品名・可動部品は変えていない。M04・M08 には取付位置が無い

### 12.7 撮影と実機の確認

撮影（`review/p2_meshy/`、1600×900）: `m04_front`・`m04_front_close`（正面）、`m04_oblique_nw`（北西の斜め上）、`m04_side_north`（右側面）、`m04_back`（裏）、`area_C_candy`（W08 と同じ C の全景）、`m08_side_west`・`m08_front`・`m08_oblique_back`、`m08_from_street`（M04 の南の通りから見上げる）。

- M04: 黒い面・反転・透け・ちらつきは見つからない。窓の発光は窓だけに出て、扉は西の広場を向く。入口の照明は建物にめり込まない
- M08: 正面は北を向き、ほうきは W04 の巡回の線（`CCD_WitchPatrolLoop_001_GuideRing` の発光の線）の上にある。光源を足す前は、空を背にした影に近い見え方だった
- 利用者の実機（2026-11-01、デスクトップ）:
  - M04 の正面と建物のまわりを歩いた。当たり判定の問題の報告は無し。「お店の裏側に道の出っ張りみたいなものはあります」: W01 の東の連絡橋の床 `WLD_EastBridge_001`（x 14.14〜42.25、上面 z 0.06）が工房の下を通り、裏（x 40.68）から 1.57 m はみ出したもの。仮モデルのときから同じ形で、西の時計塔の同じ形は W08 が床を塔の前で止めて直している（`modeling/world/build.py`）。`world` は W01 の所有でこの子の範囲外なので、利用者の決定で記録だけにした（`handoff/W09R-C.md` 6 章の要望）
  - M08: 「暗くて見えにくい」→ 前の光源 1 つ（強さ 2.0）で「まだ暗い」→ 足元の下の光源を足し、両方を強さ 3.0 にして「このままでよい」
- 負荷（利用者の測定、W08 と同じ端末）: C の地区から M04 を見て 60 fps 前後（W08 の基準と同じ）
- 増えた物: 三角形 61,832（M04 30,702・M08 31,130。仮モデル 410・230 は描画を止めた）、画像 5（約 40.6 MB の見積もり）、点光源 2（影なし）

### 12.8 Resonite で未確認の項目

- 保存（確認事項 4）: GPT のレビューへの対応の後に利用者が 1 回保存した（2026-11-01、03:02Z より前）。保存の後に読み取りだけで確かめた全 10 宣言の diff は変更 0。M04・M08 の資産の URL はまだ `local://`（ワールドを開き直していない）。再読込の後に M04・M08 の画像・光源が保たれるかは未確認（P4）
- M08 が巡回しているときの見え方と光源の当たり方（P3 の G11）
- 窓の発光の昼夜の制御（P3）、VR、二人以上

### 12.9 GPT のレビュー（確認事項 7）

- 起動: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（codex-cli 0.166.0、モデル gpt-6-astra）。対象は PR #51 の `4e42888`。Resonite には接続させず、checkout も変更させていない。観点は、宣言の正しさ、実測の検査の拡張、diff の対象と収束・所有範囲、テストの採用基準、記録の正確さの 5 つ
- 結果: Major 1 件・Minor 2 件。宣言の正しさと diff・所有範囲は指摘なし。全文は PR #51 のコメント

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| 1 | Major | `collision: False` の検査が、素材のバンドルの root 自身にある `MeshCollider` を見落とす | 採用 | 失敗を成功と報告する経路のため。走査の範囲にバンドルの root を含めた |
| 2 | Minor | 素材の下の当たり判定の拒否と、発光の画像の参照の検査にテストが無い。撮影で分かるので L とした分類は、検査の偽陽性を S とする基準に合わない | 採用 | 代表 1 件ずつ（計 2 件）を足し、それぞれ守りを外すと失敗することを確かめた。`handoff/W09R-C.md` 9 章の分類も直した |
| 3 | Minor | C の数が「Slot 93・Component 209」で、`live_checks.json` の 95・211 と食い違う | 採用 | 光源を足す前の値を写していた。12.6 を 95・211 に直した |

直した検査でワールドを観察し直し、すべて合格した（`review/p2_meshy/live_checks.json` は同じ内容）。ワールドへの書き込みは無い。

## 13. W09R-A（#47）: A 中央広場の M01 入場ゲート

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ。着手前の確認事項は W08 #41 の回答（#47 の本文）
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1（W09R・W09R-C と同じ）
- スナップショットと diff・apply の報告は親の checkout の `tmp/w09r-a/`（Git の対象外）
- 閉じた子の所有ファイル（W02 の `A_plaza`、W09-M01 の `M01`、W08 の `modeling/p2_static/`）は変えていない。門扉の Slot の置き直しは、差し替え側（`modeling/p2_meshy/replacements.py`）で A の宣言を後処理した

### 13.1 保存の後の最初の diff

- 着手時のスナップショット（`tmp/w09r-a/01_snapshot_before_20261101T041854Z`）は W08 の root の下が Slot 696・Component 1,634 で、W09R-C の完了時と同じ（利用者が手で変えた所は無い）
- 最初の diff（04:19:27Z、何も変える前。M01 の行を足す前の `REPLACEMENTS` で 6 キーを export した宣言）: 全 10 宣言（`content/main.json`・6 キー・M02・M04・M08）が変更 0（no-op 29・184・655・333・318・378・780・17・18・19）。資産の作り直し・重複は無い
- A の資産 110 件は `resdb:///` に移った後の no-op（「asset URL was migrated to resdb by a world save」）。M04・M08 の資産は「source hash and imported URL match state」（W09R-C の保存の後、ワールドを開き直していないので `local://` のまま）

### 13.2 決めたこと

| 項目 | 決めたこと | 理由 |
|---|---|---|
| 宣言の分け方 | M01 を親ごとに 3 つの宣言にする: アーチ `p2m.apply.json`（親 `_Arch`、state `p2m_M01.json`）、左の門扉 `p2m_DoorLeft.apply.json`（親 `_DoorLeft`、state `p2m_M01_DoorLeft.json`）、右の門扉 `p2m_DoorRight.apply.json`（親 `_DoorRight`、state `p2m_M01_DoorRight.json`）。export は 1 回で、`export_meshy.py` が宣言を分ける | resoloop 0.2.0 の宣言は、子の Slot に `parent` を書いても無視して宣言の root の下に作る（試しの宣言の `diff` で確かめた）。1 つの宣言は 1 つの親の下にしか置けない。門扉を可動部品の Slot（Spec §6.3 の `MotionRoot`）の下に置かないと、P3 が門扉を回せない |
| 門扉の Slot（**利用者の決定**、2026-11-01） | 仮モデルの `_DoorLeft`・`_DoorRight` を M01 の蝶番へ動かし、回転を ±88° → ±90° にする。Slot・ID・階層・Component は作り直さず、A の宣言の位置と回転だけを変える（`replacements.repose_motion_roots`） | M01 の蝶番は柱の裏にあり、仮モデルの蝶番（A のアセットの root のローカルで x ∓2.18、奥行き 0）から左 15.3 cm・右 12.9 cm 離れている。Slot を動かさないと、P3 が Slot を回したときに門扉が蝶番からずれた軸で回り、閉じると柱にめり込む。動かさない案（Slot の中で門扉を補正して置き、P3 は素材の中の Slot を回す）は Spec §6.3 の差し替えと動作の分離に反する |
| 基準姿勢（P3 が使う値） | P3 が回すのは `APL_EntranceGateProxy_001_DoorLeft`・`_DoorRight` の Slot の回転（Blender の Z 軸 = Resonite のローカルの Y 軸まわり）。閉 0°、開いた形（今の置き方）は DoorLeft +90°・DoorRight −90°（Blender の Z 軸まわり。Resonite の四元数で DoorLeft (0, −0.7071, 0, 0.7071)・DoorRight (0, 0.7071, 0, 0.7071)）。開く向きは北（広場の側） | M01 のアセット一覧の `leaves`（回転 0 で閉、左 +90°・右 −90° で開く）を、仮モデルの Slot の回転に移した。門扉の宣言の root は 180° で、その下の門扉の Slot は回転・移動なしの閉じた形なので、P3 は素材の中を回さない |
| 門扉の Slot の位置 | DoorLeft (−2.18, 0, 0) → (−2.2562, 0, 0.1328)、DoorRight (2.18, 0, 0) → (2.2498, 0, 0.1088)（Resonite の軸、A のアセットの root のローカル。世界では (−2.2562, 0, −39.8672)・(2.2498, 0, −39.8912)） | M01 の `leaves.pivot_local` を `received.json` の 180° で置いた値 |
| 仮モデルの見た目 | A の宣言で、アーチ・門扉 2 枚と、アーチの子の取付位置の目印 3 つ（`_BannerAttach`・`_LanternAttachLeft`・`_LanternAttachRight`）の `MeshRenderer` を `Enabled = false` にする | 目印は発光の部品で、M01 の柱と看板の前（奥行き −0.65 m）に出る。Slot と位置は残す（M02 と同じ） |
| 画像 | 3 つの宣言がそれぞれ同じ画像 2 枚と材質を持つ（宣言の外の Component は参照できないので、`Blender_Providers` のうち門扉の材質が参照する物を写す） | apply の後の `StaticTexture2D.URL` は 3 つの宣言で同じで、Resonite の中では同じ資産を使う（画像の読み込みは 1 回分） |
| 当たり判定 | アーチは仮モデルの形の `APL_EntranceGateProxy_001_Arch_FixedCollision` のまま。門扉には付けない | 仮モデルのアーチは W09 の外形・開口（幅 4.36 m・高さ 3.973 m）で作った箱で、柱の内側の面（x ±2.18）は、ゲートの面の前（奥行き 0.85 m）の M01 の柱の内側（±2.172〜2.174。M01 の `passage`）と 1 cm 以内。ゲートの面（蝶番の窪み）では M01 の開口が片側 2.213・2.355 m まで広く、当たり判定が見た目より最大 17 cm 内側にあるが、そこは開いた門扉の付け根で歩く所ではない。利用者の歩行で問題なし（13.7）。開いた門扉は通路側へ最大約 21 cm（ゲートの面の奥で x ±1.94〜1.97）出るが、当たり判定を付けると通路が 3.909 m に狭まる（`handoff/W09-M01.md` 8 章） |

- P3 への注意: A の宣言は門扉の Slot の回転（開いた形）を書いているので、P3 が回した後に A を再 apply すると開いた形に戻る（Spec §6.3「動作値を静的モデルの再適用で戻さない」）。P3 は、動作中に A を再 apply しない運用にするか、回転を宣言の管理から外す方法を決める（宣言の Slot には `managedFields` の項目がある（`resoloop schema describe slot`）が、この子では使っておらず未確認）

### 13.3 実装（`modeling/p2_meshy/`）

- `replacements.py`: M01 の行。新しい項目 `moving_parts`（素材の子のうち、仮モデルの motion_root の下に別の宣言で置く部品と、宣言の名前）。`moving_part_poses` が M01 のアセット一覧の `leaves` から motion_root の位置・回転と門扉の宣言の root の回転を求め、`repose_motion_roots` が A の宣言の motion_root を置き直す（`hide_in_file` から呼ぶので、W08 の `export_p2.py` は変えていない。置き直した前後の値は `replacements.json` に書く）。visual_root と motion_root が同じ親の子でなかったり、visual_root が親のローカルで回転・移動なしでなかったりすれば止める。`hide` の対象は motion_root の下も認める
- `export_meshy.py`: `moving_parts` の部品を素材の宣言から外し、部品ごとの宣言（ownership のキーは素材の宣言のキーに `_doorleft` などを付けた物）を作る。export の部品の位置・回転がアセット一覧の蝶番・開いた角度と違えば止める。3 つの宣言をそれぞれオフラインと `--strict` で validate する
- `verify_live.py`: 外接箱を素材のすべてのメッシュ（アーチと門扉 2 枚）を合わせた物にし、motion_root と門扉の原点が蝶番と 1 cm 以内か、motion_root の回転と門扉の世界の向きが開いた形か、門扉ごとの外接箱が門扉のメッシュをデータの蝶番・向きで置いた物と 1 cm 以内か（13.9 の指摘 1）、門扉の宣言にメッシュがあるか（同 2）、門扉が描画されるか、門扉の下に当たり判定が無いかを確かめる。期待値はアセット一覧の `leaves` と `received.json` の向きから直接求め、`moving_part_poses` の計算を通さない（置き方の計算の誤りを、同じ計算の期待値で合格にしないため）
- テスト: `tests/test_p2_meshy_verify.py` に 6 件（S。motion_root が蝶番から外れている、門扉が閉じている、門扉が描画されない、門扉の下に当たり判定がある、門扉の縮尺が違う、門扉の宣言にメッシュが無い、をそれぞれ失敗にする。1 件目は正しい状態で通ることも確かめる。後の 2 件は 13.9 の GPT のレビューで足した）。それぞれ守りを外すと、そのテストだけが失敗することを確かめた

### 13.4 export と validate

| 出力先 | 内容 | validate（オフライン・`--strict`） |
|---|---|---|
| `exports/p2_meshy/M01-20261101T042541Z` | M01（`--parent` はアーチの `visual_root`、`--preserve-hierarchy --pack-pbr`）。正面のカメラ 2 つは `--recompose` で柵の内側へ移した（宣言の中身はカメラだけが変わり、門扉の 2 つの宣言はバイト単位で同じ） | `p2m.apply.json`・`p2m_DoorLeft.apply.json`・`p2m_DoorRight.apply.json` とも issues 0 |
| `exports/p2_static/A_plaza-20261101T042531Z` | M01 の仮モデルの描画 6 つを止め、門扉の Slot 2 つを置き直した A（apply した版） | issues 0 |
| `exports/p2_static/<key>-20261101T041730Z`（6 キー） | 13.1 の確認に使った world・A〜E（M01 の行を足す前） | issues 0 |

- M01: 三角形 35,521、頂点 76,124、材質 1、描画の区切り 3（アーチ・門扉 2 枚）、画像 2（色 2048×2048、詰めた PBR 1024×1024。RGBA8 とミップの見積もり 合計 約 28 MB）、警告 0
- 後続の子のために、apply した M01 のバンドルを Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/p2_bundles/M01-20261101T042541Z`（`SHA256SUMS`）に控えた。新しい worktree で `verify_live.py` を実行するときは、M02・M04・M08 と同じく同じ名前の出力先へ写す

### 13.5 diff と apply

| 時刻（UTC） | 宣言 | diff | apply |
|---|---|---|---|
| 04:26:23 | M01 のアーチ | 作成 16（資産 3、Slot 7、Component 6。すべて `_Arch` の下） | — |
| 04:26:23 | M01 の左・右の門扉 | それぞれ作成 15（資産 3、Slot 6、Component 6。すべて `_DoorLeft`・`_DoorRight` の下） | — |
| 04:26:23 | A | 更新 8（`_DoorLeft`・`_DoorRight` の Slot の位置・回転 2、仮モデルの `MeshRenderer.Enabled` 6）。作成・削除 0 | — |
| 04:26:53〜04:27:14 | M01 のアーチ → 左 → 右 → A | — | アーチ: Slot 7・Component 6・資産 3 を作成。門扉: それぞれ Slot 6・Component 6・資産 3 を作成。A: Slot の更新 2・Component の更新 6 |
| 04:27:40〜04:27:51 | 同じ 4 宣言の 2 回目 | すべて変更 0（no-op 16・15・15・655） | 書き込み 0 |
| 04:29:58 | 全 13 宣言（`content/main.json`・6 キー・M02・M04・M08・M01 の 3 つ） | すべて変更 0 | — |

- `--prune` は使っていない。削除・名前の変更・作り直しは 0。diff の対象は M01 の 3 つの親の下と資産、A の仮モデルのゲートの中だけ（ほかの地区・`content/main.json`・前の素材の宣言は 0）
- apply の前のスナップショット: `tmp/w09r-a/01_snapshot_before_*`（W08 の root 全体。最初の diff の後、apply まで書き込みは無い）

### 13.6 実測（`review/p2_meshy/live_checks.json`）

| 検査 | 結果 |
|---|---|
| `visual_root` の世界の原点 | `_Arch` が (0, 0, −40)。W07 の `frame_origin_world` と差 0.0 m |
| 外接箱（アーチと門扉 2 枚を合わせた物） | x −5.4999〜5.4999、高さ −0.0001〜7.7392、z −41.311〜−37.6129（10.9999 × 7.7393 × 3.698 m。奥行きは開いた門扉を含む）。アセット一覧の `bounds_local` を 180° で置いた値との差 0.2 mm |
| 正面と鏡像 | 素材の前方は (0, 0, −1)（南。看板がスポーンを向く。`placement_hint` から）。祖先の拡縮はすべて正 |
| 門扉の Slot と門扉 | DoorLeft の原点 (−2.2562, 0, −39.8672)、DoorRight (2.2498, 0, −39.8912)。M01 の蝶番との差 0.0 m（差し替えの前の位置からは 15.3 cm・12.9 cm 動いた。13.2）。Slot の回転は閉 0° から +90°・−90°、門扉の世界の向きは開いた形（差 0.0） |
| 門扉ごとの外接箱 | 左 x −2.2896〜−1.9395・高さ 0.0051〜4.2・z −39.79〜−37.6395、右 x 1.9656〜2.311・高さ 0.0043〜4.2・z −39.82〜−37.6129。門扉のメッシュを蝶番・開いた形で置いた値との差 0.0 m |
| 描画 | 仮モデルのアーチ・門扉 2 枚・目印 3 つの `MeshRenderer.Enabled` が false。M01 のアーチと門扉 2 枚は有効で、色の画像を持つ `PBS_Metallic` を参照する |
| 取付位置 | `_LanternAttachLeft` (−2.45, 3.6, −40.65)、`_LanternAttachRight` (2.45, 3.6, −40.65)、`_BannerAttach` (0, 5.8, −40.65)。差し替えの前と同じ（差 0.0 m） |
| 当たり判定 | `APL_EntranceGateProxy_001_Arch_FixedCollision` が有効・`_Arch` と同じ変換・`Static`・`CharacterCollider`・仮モデルと同じメッシュ。M01 のアーチと門扉の下に当たり判定は無い |
| 数 | A の Slot 192・Component 404（W08 の実測 166・379 に、M02 の 7・7 と M01 の 3 つの宣言の 19・18 を足した値と一致）。W08 の root の下は Slot 715・Component 1,652（着手時の 696・1,634 から +19・+18） |

- M02・M04・M08 の検査と C の数も合格のまま。ID・部品名は変えていない（門扉の Slot は位置と回転だけを変えた）

### 13.7 撮影と実機の確認

撮影（`review/p2_meshy/`、1600×900）: `m01_front`・`m01_front_close`（正面。南の柵の内側から）、`m01_oblique_sw`（南西の斜め上）、`m01_back`（広場の側から）、`m01_leaves_inside`（開いた門扉を広場の側から）、`m01_hinge_left`（通路から左の蝶番の付近）、`area_A_entrance`（入口の全景）、`overview_south`（W08 と同じ全景。M01 の差し替えの後に撮り直した）。

- 黒い面・反転・透け・ちらつきは見つからない。看板の文字は南から読め、門扉は柱の裏の蝶番から北（広場の側）へ開き、地面に乗る。両面にした門扉は広場の側からも欠けない
- 広場の側から見た看板の裏は、文字が鏡像に見える（`m01_back`）。Meshy の画像のままで、アーチは片面（W09 の決定）。差し替えの不具合ではない
- 利用者の実機（2026-11-01、04:37Z ごろ、デスクトップ）: スポーンから北へ、広場から南へゲートをくぐり、柱・袖の壁・開いた門扉のまわりを歩いた。「問題なし」（引っかかる所・すり抜ける所・見た目の不具合なし）
- 負荷（利用者の測定、W08 と同じ端末）: ゲートの近くで 60 fps 前後（W08 の基準と同じ）
- 増えた物: 三角形 35,521（仮モデルのゲート 496 三角形は描画を止めた）、画像 2（約 28 MB の見積もり。3 つの宣言で同じ資産）、光源 0

### 13.8 Resonite で未確認の項目

- 再読込の後に M01 の画像が保たれるか（P4）。保存の後の状態は 13.10
- 門扉の開閉の動き（P3）。閉じた形（Slot の回転 0°）は、原本の門扉の位置（W09-M01 は閉じた形のメッシュを蝶番で回して開いた。`handoff/W09-M01.md` 2 章）だが、Resonite では閉じた形を置いて確かめていない
- VR での見え方、二人以上

### 13.9 GPT のレビュー（確認事項 7）

- 起動: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（codex-cli 0.166.0、モデル gpt-6-astra）。対象は PR #52 の `e796142`。Resonite には接続させず、checkout も変更させていない。観点は、宣言の正しさ、門扉の置き直し、実測の検査の拡張、diff の対象・所有範囲・記録の数値、テストの採用基準の 5 つ
- 結果: Major 2 件・Info 1 件。宣言の正しさ・門扉の置き直し（蝶番・軸・回転の符号・閉 0°／開 ±90°）・所有範囲と記録の数値は指摘なし。足したテスト 4 件は S として妥当（書きすぎの指摘なし）。全文は PR #52 のコメント

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| 1 | Major | 全体の外接箱はアーチともう一方の門扉で決まるので、門扉を半分に縮めても合格する | 採用 | 検査が誤った状態を成功と報告する経路のため。門扉ごとに、門扉のメッシュの頂点をデータの蝶番・向き（拡縮なし）で置いた外接箱と比べる。テスト 1 件（門扉の例の頂点を、縮尺で外接箱が変わる形にした） |
| 2 | Major | 検査する門扉のメッシュを門扉の宣言から集めるので、宣言からメッシュが欠けると検査の対象から消え、見えない門扉が合格する | 採用 | 同じ理由。部品ごとにメッシュを必須にし、部品の子の Slot にあるメッシュは検査が扱えないので失敗にする。テスト 1 件 |
| 3 | Info | 引き継ぎと記録が参照する 13.10（保存）が無い | 予定どおり | レビューの後に保存して 13.10 を書いた |

- 1・2 は、それぞれ守りを外すとそのテストだけが失敗することを確かめた。直した検査で実際のワールドを観察し直し、すべて合格した（`review/p2_meshy/live_checks.json`。門扉ごとの外接箱は 13.6）。ワールドへの書き込みは無い

### 13.10 保存（確認事項 4）

- GPT のレビューへの対応の後に、エージェントの依頼で利用者が Resonite で 1 回保存した（2026-11-01、04:52Z より前）。保存の後は apply していない
- 保存の後に読み取りだけで確かめた（04:52:25Z〜）: 全 13 宣言（`content/main.json`・6 キー・M02・M04・M08・M01 の 3 つ）の diff が変更 0。M01 の 3 つの宣言の資産は「source hash and imported URL match state」で、URL はまだ `local://`（ワールドを開き直していない。W09R-C と同じく、開き直すと `resdb:///` に移り、次の diff は no-op と判定する。12.1）
