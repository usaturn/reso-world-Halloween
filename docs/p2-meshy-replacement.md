# P2 Meshy 素材の差し替え（W09R、Issue #44）

仮モデルを Meshy の仕上げた素材に差し替える方式と、最初の素材 M02 巨大ジャック・オー・ランタンの差し替えの記録。残りの 7 素材の子は、この文書の 2・4 章の手順と `handoff/W09R.md` を使う。後続の子の記録は 12 章から（W09R-C #46 の M04・M08 は 12 章、W09R-A #47 の M01 は 13 章、W09R-B #48 の M03 は 14 章、W09R-D #49 の M05・M06 は 15 章、W09R-E #50 の M07 は 16 章）。

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
- 当たり判定を素材のメッシュで作る素材（M03。W09R-B で追加、14.2）は、`REPLACEMENTS` の `collision: "finished"`。`export_meshy.py` が素材のメッシュに `MeshCollider` を付け、`export_p2.py` で地区を export し直すと、仮モデルの `<visual_root>_FixedCollision` の `MeshCollider` が `Enabled = false` になる（Slot は残す）。手順は上と同じ
- visual_root の兄弟の仮モデルの部品も隠す素材（M07 の仮の文字盤 `_Dial`。W09R-E で追加、16.2）は、`hide` にその Slot を書く。範囲の外の Slot は、地区のアセット一覧の `replacement_slot.hide_on_replacement` に書いてある兄弟だけ許される（`replacements.owner_hide_on_replacement`）。手順は上と同じ
- 1 つの素材を複数の visual_root に分けて置く素材（M05 の柱と屋根。W09R-D で追加、15.2）は、`received.json` の行ごとに `REPLACEMENTS` の行を作る。出力先は `exports/p2_meshy/<行>-<UTC>/`、state は `p2m_<行>.json`（M05 は `p2m_M05_CenterCasing.json`・`p2m_M05_Canopy.json`）。手順は上と同じ
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

## 8. 全素材の状態（Spec §12「P2」の 3 つ目、2026-10-31。M04・M08 の行は 2026-11-01 に W09R-C が、M01 の行は同日に W09R-A が、M03 の行は同日に W09R-B が、M05・M06 の行は同日に W09R-D が、M07 の行は同日に W09R-E が更新。これで 8 素材とも Resonite への投入が済んだ）

受領は W09 #13（`assets/meshy/received.json`、PR #26）。どの素材も未着ではない。採用しない物は、利用者が作り直す前の版（各ディレクトリの `size_over/`）と、M07 の `NG/`（針が塔に溶接されていた）だけで、確定版で置き換えた。

| 素材 | 受領 | 仕上げ（子・PR） | Resonite への投入 | 確認 | 採用 |
|---|---|---|---|---|---|
| M01 入場ゲート | 済（約 3.0 万三角形） | 済（W09-M01 #14・PR #29。門扉を切り離し両面化） | **済（W09R-A #47。門扉は仮モデルの門扉の Slot の下に別の宣言）** | **Resonite で実測・撮影・利用者の実機**（13 章） | 採用 |
| M02 巨大ジャック・オー・ランタン | 済（約 3.1 万） | 済（W09-M02 #15・PR #27） | **済（この子）** | **Resonite で実測・撮影・利用者の実機**（5 章） | 採用 |
| M03 幽霊屋敷の外観 | 済（約 3.0 万） | 済（W09-M03 #16・PR #35。入口の開口） | **済（W09R-B #48。当たり判定は M03 のメッシュ。W03 の扉・ホールを開口へ動かし、階段を外した）** | **Resonite で実測・撮影・利用者の実機**（14 章） | 採用 |
| M04 魔女のお菓子工房の外観 | 済（約 3.1 万） | 済（W09-M04 #17・PR #39。窓の発光） | **済（W09R-C #46）** | **Resonite で実測・撮影・利用者の実機**（12 章） | 採用 |
| M05 メリーゴーラウンドの屋根 | 済（約 4.2 万） | 済（W09-M05 #18・PR #34） | **済（W09R-D #49。柱と別の宣言で `DAM_Carousel_001_M05_Canopy` の下。W05 の支柱を屋根まで伸ばした）** | **Resonite で実測・撮影・利用者の実機**（15 章） | 採用 |
| M05 メリーゴーラウンドの中央の柱 | 済（約 3.2 万） | 済（同上） | **済（W09R-D #49。`DAM_Carousel_001_M05_CenterCasing` の下）** | **Resonite で実測・撮影・利用者の実機**（15 章） | 採用 |
| M06 おばけ列車の先頭車外装 | 済（約 1.5 万） | 済（W09-M06 #19・PR #38） | **済（W09R-D #49。前照灯の取付位置をレンズの前へ移した）** | **Resonite で実測・撮影・利用者の実機**（15 章） | 採用 |
| M07 魔法の時計塔 | 済（約 3.1 万。針の無い作り直しの版） | 済（W09-M07 #20・PR #32。文字盤の計測） | **済（W09R-E #50。当たり判定は M07 のメッシュ。仮の文字盤は描画を止め、針・鐘は W06 の部品のまま）** | **Resonite で実測・撮影・利用者の実機**（16 章） | 採用（`NG/` の版は不採用） |
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
- `docs/p1-handoff.md` 8 章の 6〜8 は記録のみ（各子が 5 章の表と `blender/<M>/<M>.blend`・`placement_hint` を使った）。5（西の主動線の床と時計塔の台座）は W08 が床を時計塔の東の面で止め、W09R-E が時計塔の当たり判定を M07 のメッシュにした（16.2）。2（M05 の支柱）と 3（M06 の前照灯）は W09R-D が対応した（15.2）。4（入口の門扉の可動範囲）は W09R-A が門扉の Slot の基準姿勢を決めた（13.2）。1（M03 の扉・玄関ホール）は W09R-B が対応した（14.2。階段は外した）

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

## 14. W09R-B（#48）: B 北の M03 幽霊屋敷の外観

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ。着手前の確認事項は W08 #41 の回答（#48 の本文）
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1（W09R〜W09R-A と同じ）
- スナップショットと diff・apply の報告は親の checkout の `tmp/w09r-b/`（Git の対象外）
- 閉じた子の所有ファイルのうち、W03 の `B_mansion`（扉・玄関ホール・中庭の地面）を最小限だけ直した（14.3）。W09-M03 の `M03`、W08 の `modeling/p2_static/` は変えていない

### 14.1 保存の後の最初の diff

- 着手時のスナップショット（`tmp/w09r-b/01_snapshot_before_20261101T051038Z`）は W08 の root の下が Slot 715・Component 1,652 で、W09R-A の完了時と同じ（利用者が手で変えた所は無い）
- 最初の diff（05:15:17〜05:15:45Z、何も変える前。M03 の行を足す前の `REPLACEMENTS` で 6 キーを export した宣言 `exports/p2_static/<key>-20261101T051336Z`）: 全 13 宣言（`content/main.json`・6 キー・M02・M04・M08・M01 の 3 つ）が変更 0（no-op 29・184・655・333・318・378・780・17・18・19・16・15・15）。資産の作り直し・重複は無い
- 資産の判定: world・B・D・E・M02 は「asset URL was migrated to resdb by a world save」（開き直しの後の保存で `resdb:///` に移っていた）。A・C・M01・M04・M08 は「source hash and imported URL match state」（W09R-A の保存の後、開き直していないので `local://` のまま）

### 14.2 決めたこと

M03 の仕上げた形を Blender で測り直し（ポーチの床の高さ、断面、正面の端。`modeling/M03/build.py` が作る `.blend` に対するレイと断面）、本文（と `docs/p1-handoff.md` 8 章の 1）の前提と違う 2 点を利用者に確かめた（#48 のコメント）。

| 項目 | 決めたこと | 理由 |
|---|---|---|
| ポーチへの上がり方（**利用者の決定**、2026-11-01） | W03 の 3 段の階段（上端 z 1.779、y 34.8〜36.39）と両脇の石を外し、中庭の石畳（上面 z 1.565）を M03 の段の前まで（x -1.1〜2.5、y 36.4〜37.12）延ばす。石畳から M03 自身の段（上面 z 1.68、+0.115 m）とポーチの床（z 1.870、+0.19 m）で上がる | M03 のポーチの床は奥の壁（y 39.95）から y 37.30 までで、その前に M03 自身の段が 1 つ（前端 y 37.03〜37.06、x -1.0〜2.4）ある。仮モデルの前端（y 36.39）とは 0.67 m 離れていて、間は W01 の台地（z 1.5）。本文の「階段の上端を z 1.870 にする」は M03 の床が仮モデルの前端まで来ている前提の値で、そのとおりにすると階段を 1.870 まで上がってから 0.37 m 下の台地に降りる |
| 当たり判定（**利用者の決定**、2026-11-01） | M03 のメッシュ（29,801 三角形）に `MeshCollider`（W08 と同じ `Static`・`CharacterCollider`・`DualSided`）を付ける。仮モデルの `BMN_MansionPlaceholder_001_FixedCollision` は Slot と `StaticMesh` を残し、`MeshCollider` を `Enabled = false` にする（`REPLACEMENTS` の `collision: "finished"`） | 仮モデル（314 三角形）は M03 と形が大きく違う: 中央のアーチの通路（M03 の柱の間 x 0.025〜1.39）に見えない柱（x 1.06〜1.54）が 0.33 m はみ出し、左のアーチもふさぐ。ポーチの床は 9.1 cm 低い。正面の張り出しの前に、高さ 0.28 m の見えない台座が 0.35〜2.5 m はみ出す（左の張り出しと玄関の間の奥まった所では 2.5 m）。M02・M04・M01 と違い、近くを歩いて触れる建物なので、形の一致を優先した。仮モデルの形を箱で M03 に合わせる案は、張り出しの斜めの面などを近似しきれない |
| 扉・玄関ホール | 本文どおり、W03 の `BMN_MansionDoubleDoor_001`・`BMN_EntranceHall_001` を x +0.3725 m・z +0.091 m 動かし、扉の高さを 2.683 → 2.592 m にする（枠のまぐさの下端 = 開口の上端 z 4.462）。幅・y・ID・部品名・階層・可動範囲は変えない | 開口は W09-M03 が中央のアーチに合わせて切った（`review/M03/checks.json` の `door_opening`）。枠の縦材（x ±0.809〜±0.94、y ±0.14）とまぐさが M03 の片面の壁（y 39.952）をまたいで切り口を覆い、ホール（奥行き 3.7 m、幅 3.3 m、天井 z 5.69）が開口の奥を塞ぐ。新しいホールの箱の中に M03 の頂点は無い（M03 の外へ突き出さない） |
| 仮モデルの形 | 変えない（P1 の開口・台座・柱のまま）。Resonite では描画も当たり判定も止めている | 差し替えの後は Slot と ID を残すだけの物。B の Blender の画像（`review/B_mansion/02_mansion_facade_and_doors.png`）では、動かした扉に仮モデルの壁と柱が重なって見える（アセット一覧の notes に書いた）。仮モデルに戻すときは、B の扉・ホール・中庭の地面もこの子の前に戻す |
| 墓地の縁石（利用者の歩行の報告の後、利用者の指示「推奨の判断で進めて」） | W03 の墓地の土の区画（x ±5.4〜±14、y 24.5〜35.8、高さ 0.08 m）の手前と奥の縁石 4 本（長さ 8.6 m、幅 0.25 m、高さ 0.2 m）を外す | 利用者の歩行（14.8）で「屋敷の周りの庭に謎の四角い棒が四本横たわっていて段差がある」。区画の 2 辺だけにある縁石で、北東・北西の橋から中庭へ歩くと手前の縁石（y 24.5）をまたぐ。中庭の地面のメッシュ（この子で既に変えている Component）の中の変更なので、diff の対象は増えない |
| 中庭の石畳の南端（同） | 石畳の始まりを y 20.2 → 20.25 にする（北の橋の床が平らに終わる所） | 石畳が橋の斜めの床（上面 z 約 1.52）の上から始まり、4 cm の段になっていた。20.25 からは W01 の道（z 1.56）の上なので 0.5 cm |
| 北の橋の支え（同） | 直さない（W01 の所有。要望として記録） | 利用者の「橋に謎の段」の主な原因は、W01 の `WLD_NorthBridge_001` の橋の下の支えの箱（ローカル y 1.6〜2.8・上端 z 1.3、世界 y 18.85〜20.05）が、斜めの床を y 18.85〜19.2 で最大 10 cm 突き抜けていること（`b_north_bridge_end`）。本文は B 以外の地区の宣言の diff を 0 にすると決めているので、この子では直さない（`handoff/W09R-B.md` 6.2） |

可動部品（Spec §6.1）の旧 → 新（`layout/areas/B_mansion.json` の `G06`。Blender の世界の座標）:

| 部品 | 旧（P1） | 新 | 変えない物 |
|---|---|---|---|
| `BMN_MansionDoubleDoor_001`（アセットの root） | (0.335, 39.95, 1.779) | (0.7075, 39.95, 1.870) | 回転 0、ID・階層 |
| `BMN_MansionDoubleDoor_001_HingeLeft`（`motion_root`） | (-0.474, 39.95, 1.779) | (-0.1015, 39.95, 1.870)（M03 の蝶番の線、正面から見て左） | `pivot_local` (-0.809, 0, 0)、Z 軸 0〜+85°（内開き）、基準姿勢 0（閉） |
| `BMN_MansionDoubleDoor_001_HingeRight`（`motion_root`） | (1.144, 39.95, 1.779) | (1.5165, 39.95, 1.870) | `pivot_local` (0.809, 0, 0)、Z 軸 -85〜0°、基準姿勢 0（閉） |
| `BMN_EntranceHall_001`（アセットの root） | (0.335, 41.80, 1.779) | (0.7075, 41.80, 1.870) | 取付位置 `_ChandelierHook` は root のローカル (0, 0, 3.45) のまま（世界では x +0.3725・z +0.091） |
| 扉の葉の高さ・枠 | 葉 2.66 m、縦材 2.75 m、まぐさ z 2.683〜2.92 | 葉 2.569 m、縦材 2.659 m、まぐさ z 2.592〜2.829（`DOOR_HEIGHT` から） | 幅 0.802 m・厚み、金具の位置 |

### 14.3 直した閉じた子のファイル（W03 の `B_mansion`）

| ファイル | 変更（旧 → 新） | 理由 |
|---|---|---|
| `modeling/B_mansion/layout_data.py` | 定数 `DOOR_ORIGIN`・`HALL_ORIGIN`・`DOOR_HEIGHT`・`DOOR_HALF_WIDTH`・`PORCH_FLOOR_Z` を足し、扉・ホールの配置、`m03_alignment`（ポーチの床 1.779 → 1.870、開口の中心 0.335 → 0.7075、高さ 2.683 → 2.592）、`G06` の `pivot_world`、除外範囲 `Excl_B_DoorSwingAndPorch`（x -1.35〜1.85 → -0.9775〜2.2225、下端 1.779 → 1.870）、説明の文をこれで書く | 14.2 |
| `modeling/B_mansion/build.py` | `build_courtyard_ground` の 3 段の階段と両脇の石（5 つの箱）を、石畳の延長（1 つの箱、x -1.1〜2.5・ローカル y 4.4〜5.12・上面 0.065）に替えた。利用者の歩行の後に、墓地の縁石 4 本を外し、石畳の南端をローカル y -11.8 → -11.75 にした（使わなくなった材質 `MAT_BMN_MansionStone` を中庭の地面から外した）。`build_mansion_double_door`・`build_entrance_hall` の位置と扉の高さを定数から作る。確認画像 02 のカメラの x を扉に合わせた。仮モデルのアセット一覧の notes に差し替えの後の扱いを足した | 14.2 |
| `layout/areas/B_mansion.json`・`assets/manifest/B_mansion.json`・`review/B_mansion/*.png` | 上の 2 つから作り直した（中庭の地面は 168 → 72 三角形、外接箱の奥行き 16.2 → 16.87 m・高さ 0.42 → 0.08 m。扉の高さ 2.92 → 2.829 m） | 生成物 |

- `uv run python tools/check_data.py --key B_mansion`・`tools/check_blend.py --key B_mansion` が 0。B を 2 回ビルドしても数は同じ（W03 と同じ）
- 他の子の記録で値が古くなった物（直していない。`handoff/W09R-B.md` 6.2 の要望）: `handoff/W03.md` 6 章（扉・ホール・階段の値）、W07 の `review/overview/checks.json`（`motion_parts` の G06 の蝶番。W08 の `modeling/p2_static/verify_live.py` はこの値と比べるので、G06 の 2 行は 0.37 m ずれて失敗する）と `assets/manifest.json`、`docs/p1-handoff.md` 8 章の 1（この子で対応済み）

### 14.4 実装（`modeling/p2_meshy/`）

- `replacements.py`: M03 の行（`visual_root` は仮モデルのアセットの root `BMN_MansionPlaceholder_001`、回転 0 = `placement_hint` 180 − 仮モデルの root 180）。新しい項目 `collision: "finished"` と `entrance`（検査用）。`disable_fixed_collisions` が地区の宣言の `<visual_root>_FixedCollision`（visual_root の兄弟）の `MeshCollider` を `Enabled = false` にする（`hide_in_file` から呼ぶので、W08 の `export_p2.py` は変えていない。止めた行は `replacements.json` に書く）
- `export_meshy.py`: `collision: "finished"` の素材は、素材のメッシュの Slot に `MeshCollider` を足す（`add_mesh_colliders`。`placement.json` の `colliders`）
- `verify_live.py`:
  - `collision: "finished"`: 仮モデルの `FixedCollision` が残っていて `MeshCollider.Enabled` が false、素材のすべてのメッシュの Slot に有効・`Static`・`CharacterCollider`・`Offset` 0 の `MeshCollider` があり同じ Slot の `StaticMesh` を参照する、素材のバンドルの中のそれ以外の Slot に当たり判定が無い
  - `entrance`: 地区の扉の蝶番の Slot の原点が M03 の開口の蝶番の線の下端と 1 cm 以内で、蝶番の Slot の前方が建物の奥を向く（閉じた扉が壁の面にある）。玄関ホールの原点が開口の中心の床から 1.85 m 奥と 1 cm 以内で、前方が建物の奥を向く。扉とホールのアセットの root から下のすべての Slot と祖先の拡縮が 1。期待値は `review/M03/checks.json` の `door_opening`（W09-M03 の実測）とデータの原点・向きから求め、B の配置データから求めない（B の値の誤りを、同じ値で合格にしないため）
- テスト: `tests/test_p2_meshy_verify.py` に 8 件（うち 4 件は 14.9 の GPT のレビューで足した）、`tests/test_p2_meshy_replacements.py` に 1 件（どれも S。`handoff/W09R-B.md` 9 章）。それぞれ守りを外すと、そのテストだけが失敗することを確かめた（変異ごとに `PYTHONPYCACHEPREFIX` を分けた）

### 14.5 export と validate

| 出力先 | 内容 | validate（オフライン・`--strict`） |
|---|---|---|
| `exports/p2_meshy/M03-20261101T052520Z` | M03（`--parent` は `BMN_MansionPlaceholder_001`、`--preserve-hierarchy --pack-pbr`）。`M03_HauntedMansion_001` に `MeshCollider` | issues 0 |
| `exports/p2_static/B_mansion-20261101T052512Z` | 扉・ホール・中庭の地面を直し、仮モデルの描画と `FixedCollision` の当たり判定を止めた B（最初に apply した版） | issues 0 |
| `exports/p2_static/B_mansion-20261101T060018Z` | 上に加えて、墓地の縁石を外し、石畳の南端をずらした B（利用者の歩行の後に apply した版） | issues 0 |
| `exports/p2_static/<key>-20261101T051336Z`（6 キー） | 14.1 の確認に使った world・A〜E（M03 の行と B の修正の前） | issues 0 |

- M03: 三角形 29,801、頂点 58,557、材質 1、描画の区切り 1、画像 2（色 4096×4096、詰めた PBR 2048×2048。RGBA8 とミップの見積もり 合計 約 112 MB）。警告 1（「Textures exceed 2048 px」。W09 が近景の 109.5 px/m のために決めた色 4096 の結果）
- 後続の子のために、apply した M03 のバンドルを Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/p2_bundles/M03-20261101T052520Z`（`SHA256SUMS`、42 MB）に控えた。新しい worktree で `verify_live.py` を実行するときは、ほかの素材と同じく同じ名前の出力先へ写す

### 14.6 diff と apply

| 時刻（UTC） | 宣言 | diff | apply |
|---|---|---|---|
| 05:26:00 | M03（最初） | 作成 16（資産 3、Slot 6、Component 7。すべて `BMN_MansionPlaceholder_001` の下。Component は `StaticMesh`・`MeshRenderer`・`MeshCollider`・`AI_GeneratedContent`・画像 2・材質） | — |
| 05:26:02 | B | 作成 4（扉の枠・葉 2 枚・中庭の地面のメッシュの資産）、更新 8（扉とホールの Slot の位置 2、`StaticMesh.URL` 4、仮モデルの `MeshRenderer.Enabled`、`FixedCollision` の `MeshCollider.Enabled`）。削除 0 | — |
| 05:26:12〜05:26:45 | M03 → B | — | M03: Slot 6・Component 7・資産 3 を作成。B: Slot の更新 2・Component の更新 6・資産の取り込み 4 |
| 05:27:01〜05:27:05 | M03・B の 2 回目 | — | 書き込み 0（資産は変更なし 3・45） |
| 05:27:09〜05:27:42 | 全 14 宣言（`content/main.json`・6 キー・M02・M04・M08・M01 の 3 つ・M03） | すべて変更 0（M03 は no-op 16、B は 333） | — |
| 06:00:31〜06:00:36 | B（縁石・石畳の南端。14.2） | 作成 1（中庭の地面のメッシュの資産）、更新 1（中庭の地面の `MeshRenderer` の作り直し。材質の一覧が 3 → 2 に減り、ResoniteLink は一覧の要素を消せないので resoloop が Component を消して作り直す。ほかに参照している物は無い） | Component の追加 1・更新 1（`StaticMesh.URL`）・削除 1、資産の取り込み 1。Slot は変わらない |
| 06:00:51〜06:01:18 | B の 2 回目の apply と、全 14 宣言の diff | すべて変更 0 | 書き込み 0 |
| 06:01:45 | M03（撮影のカメラ 2 つを足して `--recompose`） | 変更 0（no-op 16。カメラはワールドに書かない） | — |

- `--prune` は使っていない。削除・名前の変更は 0。作り直しは、中庭の地面の `MeshRenderer` の 1 つだけ（上の表）。diff の対象は M03 の `visual_root` の下と資産、B の扉・ホール・中庭の地面・仮モデルの描画と当たり判定だけ（ほかの地区・`content/main.json`・前の素材の宣言は 0）
- apply の前のスナップショット: `tmp/w09r-b/01_snapshot_before_*`（W08 の root 全体。最初の diff の後、apply まで書き込みは無い）、`10_snapshot_B_before_curbs_*`（B の root。縁石を外す前）

### 14.7 実測（`review/p2_meshy/live_checks.json`、05:27:50Z）

| 検査 | 結果 |
|---|---|
| `visual_root` の世界の原点 | (0, 1.5, 41.5)。W07 の `frame_origin_world` と差 0.0 m |
| 外接箱 | x -7.5005〜7.4996、高さ 1.5003〜12.1072、z 36.3899〜46.6104（15.0001 × 10.6069 × 10.2206 m）。アセット一覧の `bounds_local` を 180° で置いた値との差 0.0 m |
| 正面と鏡像 | (0, 0, -1)（南の中庭。`placement_hint` から）。祖先の拡縮はすべて正 |
| 描画 | 仮モデルの `MeshRenderer.Enabled` が false。M03 は有効で、色の画像を持つ `PBS_Metallic` を参照 |
| 入口 | `_HingeLeft` (-0.1015, 1.87, 39.95)・`_HingeRight` (1.5165, 1.87, 39.95)。M03 の蝶番の線（Resonite の z 39.9523）との差 2.3 mm、閉じた扉は壁の面にある（蝶番の前方が建物の奥を向く）。`BMN_EntranceHall_001` (0.7075, 1.87, 41.8)、開口の中心の 1.85 m 奥との差 2.3 mm（W03 の扉の面 y 39.95 と M03 の壁 39.9523 の差）で、前方は建物の奥。扉とホールの Slot の拡縮はすべて 1 |
| 当たり判定 | `BMN_MansionPlaceholder_001_FixedCollision` は残っていて `MeshCollider.Enabled` が false。`M03_HauntedMansion_001` の `MeshCollider` が有効・`Static`・`CharacterCollider`・`Offset` 0・同じ Slot の `StaticMesh` を参照。素材の中のほかの Slot に当たり判定は無い |
| 数 | B の Slot 94・Component 207（W08 の実測 88・200 に M03 の 6・7 を足した値と一致）。W08 の root の下は Slot 721・Component 1,659（着手時の 715・1,652 から +6・+7） |

- M01・M02・M04・M08 の検査と A・C の数も合格のまま。ID・部品名は変えていない（扉とホールは位置と扉の高さだけ）。仮モデルに取付位置は無い

### 14.8 撮影と実機の確認

撮影（`review/p2_meshy/`、1600×900）: `m03_front`（中庭から正面）、`m03_front_close`（ポーチと扉）、`m03_entrance`（段の前から開口と扉の枠）、`m03_door_edge_left`・`m03_door_edge_right`（開口の西・東の縁）、`m03_porch_steps`（石畳から M03 の段への上がり口）、`m03_oblique_se`・`m03_oblique_sw`（斜め上）、`m03_back`（北）、`area_B_mansion`（W08 と同じ B の全景）、`overview_south`（W08 と同じ全景。M03 の差し替えの後に撮り直した）、`b_graveyard_west`（縁石を外した墓地の区画）、`b_north_bridge_end`（北の橋の終わりと石畳の南端。手前に W01 の橋の支えの段が写る）。どれも利用者の歩行の後の B の直し（14.2）の後に撮り直した（06:0xZ）

- 黒い面・反転・透け・ちらつきは見つからない。ポーチは南を向き、扉の枠が開口の切り口を覆い、扉の合わせ目（1.4 cm）から奥のホールの明かりが見える。石畳の延長は M03 の段の前で止まり、段の下に隙間は無い
- 扉を開いたときの開口の奥（Resonite では扉を閉じたまま。P3 で開く）は Blender で確かめた: B の `.blend` に M03 を置き（回転 180°）、扉を ±85°（可動範囲の端）に開き、ポーチの 5 つの視点から開口の内側の格子（19 × 29）を通るレイ 2,755 本の最初の当たりは、玄関ホールの部屋 1,837・扉の葉 827・枠 36・シャンデリアの取付位置 55 で、M03 の内側の面と、何にも当たらないレイは 0 だった（保存しない一時的なスクリプト）
- 石畳の延長の東西の端と、石畳の北の端（y 36.4。仮モデルの台座が隠していた所）には、W01 の台地（z 1.5）との 6.5 cm の段が見える（`m03_porch_steps`）。中庭の石畳のほかの縁と同じ形で、歩行の妨げにはならない
- W03 の窓のおばけ（G08、`BMN_WindowGhost_001`・`_002`、(±4.2, 37.35, 4.8)）の窓枠は、仮モデルの窓に合わせた物で、M03 の窓と合わず手前に浮いて見え、東の枠は張り出しの屋根に刺さる（`m03_front`・`m03_oblique_se`）。窓の顔出しは P3 の範囲なので変えていない（`handoff/W09R-B.md` 6.2 の要望）
- 利用者の実機（2026-11-01、05:50Z ごろ、デスクトップ）: 中庭の石畳から M03 の段・ポーチ・アーチ・扉の前を歩き、「基本的に問題ありません」（引っかかる所・すり抜ける所・開口のまわりの見た目の報告なし）。ほかに 2 件の報告「橋に謎の段がある」「屋敷の周りの庭に謎の四角い棒が四本横たわっていて段差がある」があり、B の中の 2 つ（墓地の縁石、石畳の南端の 4 cm）を直し、W01 の北の橋の支えの段は要望として記録した（14.2）。直した後に利用者が歩き直して「問題なし」（06:05Z ごろ）
- 負荷（利用者の測定、W08 と同じ端末）: 屋敷の近くで 60 fps（W08 の基準と同じ）
- 増えた物: 三角形 29,801（仮モデルの 314 三角形は描画を止めた）、画像 2（約 112 MB の見積もり）、`MeshCollider` 1（29,801 三角形。仮モデルの 314 三角形の当たり判定は止めた）、光源 0

### 14.9 GPT のレビュー（確認事項 7）

- 起動: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（codex-cli 0.166.0、モデル gpt-6-astra）。対象は PR #53 の `d8b5112`。Resonite には接続させず、checkout も変更させていない。観点は、宣言の正しさ、B の修正、実測の検査の拡張、記録の正確さ、テストの採用基準の 5 つ
- 結果: Major 2 件・Minor 1 件・Info 1 件。宣言の正しさ（対象の取り違えなし、宣言の再生成は控えたバンドルと一致）、B の修正（値は記録と開口に整合、ID・階層は維持）、期待値の独立性、記録の数値は指摘なし。全文は PR #53 のコメント

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| 1 | Major | 入口の検査は蝶番とホールの原点しか見ないので、扉の縦の拡縮 0.5（扉・枠が半分の高さ）や、ホールの 180° の回転（奥の壁が入口をふさぐ）でも合格する | 採用 | 検査が誤った状態を成功と報告する経路のため。扉とホールのアセットの root から下のすべての Slot と祖先の拡縮が 1 であること、ホールの前方が建物の奥を向くことを確かめる。テスト 2 件 |
| 2 | Major | M03 の `MeshCollider.Offset` だけを (0.5, 0, 0) にすると、見た目から 50 cm ずれた当たり判定が合格する | 採用 | 同じ理由。`Offset` が 0 であることを確かめる。テスト 1 件 |
| 3 | Minor | 扉の面の向きの検査は位置の検査と重複しない（蝶番の Slot を +85° 回しても原点は動かない）のに、引き継ぎで D としてテストを書いていない | 採用 | 分類の誤り。向きの検査を「平行」から「建物の奥を向く」に強め（180° の回転も見つける）、テスト 1 件。`handoff/W09R-B.md` 9 章の分類を直した |
| 4 | Info | 8 章の表の M03 の行は「利用者の実機」を含むが、14.8 と引き継ぎは確認待ち | 予定どおり | 利用者の実機の確認の結果を 14.8 と引き継ぎに書いて揃えた |

- 1〜3 は、それぞれ守りを外すとそのテストだけが失敗することを確かめた。直した検査で実際のワールドを観察し直し、すべて合格した（`review/p2_meshy/live_checks.json`。扉とホールの前方は建物の奥、拡縮はすべて 1、`Offset` 0）。ワールドへの書き込みは無い

### 14.10 保存（確認事項 4）

- 利用者の歩行と直しの後に、エージェントの依頼で利用者が Resonite で 1 回保存した（2026-11-01、06:07Z より前）。保存の後は apply していない
- 保存の後に読み取りだけで確かめた（06:07:21〜06:07:55Z）: 全 14 宣言（`content/main.json`・6 キー・M02・M04・M08・M01 の 3 つ・M03）の diff が変更 0。M03 と B の資産は「source hash and imported URL match state」で、URL はまだ `local://`（ワールドを開き直していない。開き直すと `resdb:///` に移り、次の diff は no-op と判定する。12.1）

### 14.11 Resonite で未確認の項目

- 再読込の後に M03 の画像と当たり判定が保たれるか（P4）
- 扉を開いたときの開口の奥の Resonite での見え方（P3。Blender のレイでは塞がっている。14.8）、VR、二人以上

## 15. W09R-D（#49）: D 南の M05 メリーゴーラウンドの屋根・中央の柱、M06 おばけ列車の先頭車

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ。着手前の確認事項は W08 #41 の回答（#49 の本文）
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1（W09R〜W09R-B と同じ）
- スナップショットと diff・apply の報告は親の checkout の `tmp/w09r-d/`（Git の対象外）
- 閉じた子の所有ファイルのうち、W05 の `D_amusement`（支柱の長さと飾りの輪、前照灯の取付位置）を最小限だけ直した（15.3）。W09-M05・W09-M06 の `M05`・`M06`、W08 の `modeling/p2_static/` は変えていない

### 15.1 保存の後の最初の diff

- 着手時のスナップショット（`tmp/w09r-d/01_snapshot_before_20261101T062101Z`）は W08 の root の下が Slot 721・Component 1,659 で、W09R-B の完了時と同じ（利用者が手で変えた所は無い）
- 最初の diff（06:22:46〜06:23:11Z、何も変える前。M05・M06 の行を足す前の `REPLACEMENTS` で 6 キーを export した宣言 `exports/p2_static/<key>-20261101T062140Z`）: 全 14 宣言（`content/main.json`・6 キー・M02・M04・M08・M01 の 3 つ・M03）が変更 0（no-op 29・184・655・333・318・378・780・17・18・19・16・15・15・16）。資産の作り直し・重複は無い
- 資産の判定: world・D・E・M02 は「asset URL was migrated to resdb by a world save」、A・B・C・M01・M03・M04・M08 は「source hash and imported URL match state」（W09R-B の保存の後、開き直していないので `local://` のまま）

### 15.2 決めたこと

| 項目 | 決めたこと | 理由 |
|---|---|---|
| M05 の行の分け方 | `REPLACEMENTS` を `received.json` の行ごとに 2 行（`M05_CenterCasing`・`M05_Canopy`）にする。どちらも M05 の `.blend` を行ごとの出力先へ export し、`export_root`（`M05_PumpkinCarousel_001`）の子 1 つ（`asset_id`）だけを宣言の root の直下に置く（`export_meshy.extract_part`）。state は行ごとの `p2m_M05_CenterCasing.json`・`p2m_M05_Canopy.json`（#49 の本文の `p2m_M05.json` ではない） | 1 つの宣言は 1 つの親の下だけ（13.2）。W07 の `placeholders`・`received.json` の行・取付位置が行ごとなので、検査の期待値もそのまま行ごとに引ける。W09R-A の `moving_parts` は蝶番（`leaves`）が前提で、回らない子には使えない |
| 子の置き方 | 子の位置（組み立ての位置。屋根は柱の原点の 2.964 m 上）は visual_root の位置（TurnRoot の z 0.19 と 3.154）が受け持つので 0 にする。export の子の位置がアセット一覧の `pivot_local` と違えば止める。屋根が柱の上に組み立てどおりに乗っていることは実測で確かめる（15.4 の `assembly_with`） | 2 つの visual_root の差 2.964 m は W05 が M05 の確定値で置いた（`handoff/W09-M05.md` 6 章） |
| M05 の向き | `rotation_z_deg` -90（`placement_hint` の -90 − 仮モデルの visual_root 0）。顔と紋章は東（主動線の側）を向く | `received.json` の `placement_hint`。W05 の回転床の乗り口（土台の段）も東 |
| 支柱（2026-11-01 の利用者の決定「屋根まで伸ばす」） | W05 の支柱 8 本を、支柱ごとに屋根の下面の 2 cm 上まで伸ばす（TurnRoot のローカルで 3.25 m → 3.97〜4.27 m。先は屋根の閉じた殻の中）。上端の飾りの輪（3.08〜3.25 m）は 3 cm 下げて 3.05〜3.22 m にする。支柱・座席の位置は変えない | 屋根の下面は支柱の位置で 3.80〜4.25 m（支柱の太さの範囲の最も高い所。M05 の屋根のメッシュを -90° で置いて上向きのレイで測った）で、支柱の上端との間が 0.55〜1.0 m 空いていた（`docs/p1-handoff.md` 8 章の 2）。東西の 2 本（半径 3.35 m）では屋根の垂れ飾りの最下点が 3.236 m で、飾りの輪の上端 3.25 m と重なっていた。支柱の太さ（半径 0.055 m）の範囲は垂れ飾りに当たらない |
| 前照灯の取付位置 | W05 の `DAM_GhostTrain_001_Att_Headlamp` を EngineRoot のローカルで (0, 1.233, 1.498) → (0, 1.26, 1.39) に移す（M06 のレンズの前面の 1.35 cm 前、レンズの中心の高さ） | `docs/p1-handoff.md` 8 章の 3、`handoff/W09-M06.md` 6.5。旧い位置はレンズの上の縁の高さで、前面より 1.9 cm 奥（ランプの中） |
| 取付位置の目印 | 描画を止めない（2026-11-01 の利用者の決定「このまま」）。前照灯の目印（金色の八角形、半径 4 cm）はレンズの前で電球のように見える | P3 で前照灯の光を付ける場所の目印にもなる。止めるには、visual_root の外を止めない守り（`hide_placeholders`）を変える必要がある |
| 当たり判定 | 付けない（`collision: False`。3 行とも） | W08 の `colliders.json` で 3 つの仮モデルに `FixedCollision` が無い（可動部品 `TurnRoot`・`EngineRoot` の下。Spec §8・§11）。外周の当たり判定は W05 の土台（`DAM_Carousel_001_Base`）と柵のまま |

### 15.3 直した閉じた子のファイル（W05 の `D_amusement`）

| ファイル | 変更（旧 → 新） | 理由 |
|---|---|---|
| `modeling/D_amusement/layout_data.py` | 定数 `CAROUSEL_POLE_TOP_Z_M`（支柱ごとの上端、TurnRoot のローカル。3.97・4.25・4.00・4.27・3.98・4.27・4.00・4.27。支柱 k は角度 k × 45°）、`CAROUSEL_POLE_COLLAR_Z_M`（3.05〜3.22）、`GHOST_TRAIN_HEADLAMP_LOCAL`（(0, 1.26, 1.39)）を足した | 15.2 |
| `modeling/D_amusement/assets_rides.py` | 支柱の軸の上端 3.25 → 上の定数、飾りの輪 3.08〜3.25 → 3.05〜3.22、前照灯の取付位置 (0, 1.233, 1.498) → 定数 | 15.2 |
| `assets/manifest/D_amusement.json`・`review/D_amusement/*.png` | 上の 2 つから作り直した（アセット一覧の変更は `Att_Headlamp` の `pivot_local` だけ。`layout/areas/D_amusement.json` は変わらない） | 生成物 |

- `uv run python tools/check_data.py --key D_amusement`・`tools/check_blend.py --key D_amusement` が 0。`tests/test_D_amusement_layout.py`（座席の上下が屋根の飾りの下に収まる）も通る
- 支柱の上端の値は、M05 の屋根を -90° で置いたときの実測から決めた。屋根の向きや高さを変えるときは測り直す（`verify_live.py` の支柱の検査が、ずれを見つける。15.4）
- 他の子の記録で値が古くなった物（直していない。`handoff/W09R-D.md` 6.2 の要望）: `handoff/W05.md`（支柱・前照灯の値）、`handoff/W08.md` 3.1 の「前照灯は 8 章の 3」、`docs/p1-handoff.md` 8 章の 2・3（この子で対応済み）

### 15.4 実装（`modeling/p2_meshy/`）

- `replacements.py`: `M05_CenterCasing`・`M05_Canopy`・`M06` の行。新しい項目 `source`（素材のキー。`.blend`・アセット一覧・review の置き場）・`export_root`・`assembly_with`・`poles`（`M05_Canopy`）・`lens_attachment`（`M06`）
- `export_meshy.py`: `extract_part`（`export_root` の子 `asset_id` だけを置いた宣言にする。材質と画像は子が参照する物だけ）。材質と画像を集める処理を `_providers_for` にまとめ、W09R-A の `split_part` もこれを使う（M01・M03・M08 の宣言を作り直して、apply 済みの宣言と同じになることを確かめた）
- `verify_live.py`:
  - 素材の子 1 つだけを置く行: アセット一覧と review は `source` から読み、外接箱の期待値は `review/M05/checks.json` の `parts.<行>.bounds_m`（子のローカル）
  - 取付位置の期待値に、アセット一覧の親の部品の `pivot_local` を足す（**直し**。D の取付位置は `TurnRoot`・`EngineRoot` の子で、今までの式では 0.36 m・(0, 1.0, 0.14) ずれた位置と比べて失敗した。M01・M02 の取付位置の親は原点 0 なので結果は変わらない）
  - `assembly_with`（M05 の屋根）: この行の素材の原点と柱の行の素材の原点の差が、M05 のアセット一覧の `pivot_local` の差（2.964 m 上）を素材の向きで回した物と 1 cm 以内。それぞれの行の検査は自分の仮モデルとしか比べないので、仮モデルの間の高さの誤りを見落とす
  - `poles`（`check_poles`）: D の宣言の支柱のメッシュ（最新の `exports/p2_static/D_amusement-*`）を水平の距離で 8 本にまとめ、各支柱の上端の高さで、軸とまわりの 16 点（支柱の太さ）を屋根のローカルへ移し、屋根のメッシュ（素材のバンドル）に上向きのレイを当てる。どの点でも上端が屋根の下面以上（隙間が見えない）で、軸の上で上端より下にある屋根の面の数が奇数（先が閉じた殻の中にあり、上に突き抜けない）。期待値は D の定数ではなく 2 つのメッシュから求める
  - `lens_attachment`（`check_lens_attachment`）: D の `Att_Headlamp` を M06 のローカルへ移し、`review/M06/checks.json` の `headlamp.front_profile_x0`（x = 0 の断面の、高さごとの前面）から補間したレンズの前面の前 3 cm 以内、レンズの高さ（z 1.28〜1.50）、x 0 から 1 cm 以内
- テスト: `tests/test_p2_meshy_verify.py` に 6 件（うち 2 件は 15.9 の GPT のレビューで足した。どれも S。`handoff/W09R-D.md` 9 章）。それぞれ守りを外すと、そのテストだけが失敗することを確かめた（変異ごとに `PYTHONPYCACHEPREFIX` を分けた）

### 15.5 export と validate

| 出力先 | 内容 | validate（オフライン・`--strict`） |
|---|---|---|
| `exports/p2_meshy/M05_CenterCasing-20261101T063625Z` | M05 の柱（`--parent` は `DAM_Carousel_001_M05_CenterCasing`、`--preserve-hierarchy --pack-pbr`）。宣言は `M05_CenterCasing_001` と、その材質・画像だけ | issues 0 |
| `exports/p2_meshy/M05_Canopy-20261101T063625Z` | M05 の屋根（`--parent` は `DAM_Carousel_001_M05_Canopy`）。宣言は `M05_Canopy_001` と、その材質・画像だけ | issues 0 |
| `exports/p2_meshy/M06-20261101T063625Z` | M06（`--parent` は `DAM_GhostTrain_001_M06_EngineShell`）。撮影のカメラ `m06_back` を直して `--recompose` した（ワールドには書かない） | issues 0 |
| `exports/p2_static/D_amusement-20261101T063618Z` | 支柱・前照灯を直し、3 つの仮モデルの描画を止めた D | issues 0 |
| `exports/p2_static/<key>-20261101T062140Z`（6 キー） | 15.1 の確認に使った world・A〜E（M05・M06 の行と D の修正の前） | issues 0 |

- M05: 三角形は柱 32,414・屋根 41,819（`report.json` の 74,233 は 2 つの合計で、それぞれの宣言は自分の子だけを持つ）。画像は柱が色 1024・詰めた PBR 512、屋根が色 2048・詰めた PBR 1024（RGBA8 とミップの見積もり 合計 約 35 MB）。警告 1（「More than 50,000 triangles」。2 つの合計。W09 の判断で削減しない）
- M06: 三角形 14,804、画像 2（色 1024・詰めた PBR 512、約 7 MB）。警告なし
- 後続の子のために、apply した 3 つのバンドルを Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/p2_bundles/M05_CenterCasing-20261101T063625Z`・`M05_Canopy-20261101T063625Z`・`M06-20261101T063625Z`（`SHA256SUMS`、43 MB・43 MB・10 MB）に控えた。新しい worktree で `verify_live.py` を実行するときは、ほかの素材と同じく同じ名前の出力先へ写す

### 15.6 diff と apply

| 時刻（UTC） | 宣言 | diff | apply |
|---|---|---|---|
| 06:38:08〜06:38:12 | M05_CenterCasing・M05_Canopy・M06（最初） | それぞれ作成 15（資産 3、Slot 6、Component 6。すべて自分の `visual_root` の下。Component は `StaticMesh`・`MeshRenderer`・`AI_GeneratedContent`・画像 2・材質） | — |
| 06:38:06 | D | 作成 1（支柱のメッシュの資産）、更新 5（支柱の `StaticMesh.URL`、`Att_Headlamp` の Slot の位置、3 つの仮モデルの `MeshRenderer.Enabled`）。削除・名前の変更 0 | — |
| 06:38:21〜06:38:47 | M05_CenterCasing → M05_Canopy → M06 → D | — | 素材はそれぞれ Slot 6・Component 6・資産 3 を作成。D: Slot の更新 1・Component の更新 4・資産の取り込み 1 |
| 06:38:57〜06:39:04 | 4 つの 2 回目 | — | 書き込み 0（資産は変更なし 3・3・3・58） |
| 06:39:07〜06:39:36 | 全 17 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M08） | すべて変更 0（M05 の 2 つと M06 は no-op 15、D は 378） | — |

- `--prune` は使っていない。削除・名前の変更・Component の作り直しは 0。diff の対象は M05・M06 の 3 つの `visual_root` の下と資産、D の支柱のメッシュ・前照灯の取付位置・3 つの仮モデルの描画だけ（ほかの地区・`content/main.json`・前の素材の宣言は 0）
- apply の前のスナップショット: `tmp/w09r-d/01_snapshot_before_20261101T062101Z`（W08 の root 全体。最初の diff の後、apply まで書き込みは無い）

### 15.7 実測（`review/p2_meshy/live_checks.json`、06:39:44Z。15.9 の直しの後に 07:00:10Z に観察し直した）

| 検査 | M05_CenterCasing | M05_Canopy | M06 |
|---|---|---|---|
| `visual_root` の世界の原点（W07 の `frame_origin_world` との差） | (-10.5, 0.55, -32)、0.0 m | (-10.5, 3.514, -32)、0.0 m | (7.5, 0.14, -30.5)、0.0 m |
| 外接箱（世界の X × 高さ × Z、期待値との差） | 1.907 × 3.400 × 1.861 m、0.0 m（-90° で置くので、アセットの幅 1.861・奥行き 1.907 が入れ替わる） | 9.512 × 6.387 × 9.314 m、0.0 m | 1.211 × 1.875 × 3.000 m、0.0 m |
| 正面と鏡像 | (1, 0, 0)（東。`placement_hint` -90）。祖先の拡縮はすべて正 | 同左 | (0, 0, 1)（北、進む向き。W07 の `front_world`） |
| 描画 | 仮モデルの `MeshRenderer.Enabled` が false、素材は有効で色の画像を持つ材質を参照 | 同左 | 同左 |
| 取付位置 | `_Att_M05_CenterCasing`・`_Att_M05_Canopy` とも差 0.0 m | 同左 | `_Att_M06_Engine`・`_Att_CouplerRear`・`_Att_Headlamp`（新しい位置）とも差 0.0 m |
| 組み立て | — | 柱との差 (0, 2.964, 0)、期待値との差 0.0 m | — |
| 支柱 | — | 8 本とも上端が屋根の下面の 2.0〜2.8 cm 上（隙間なし）、先より下の屋根の面は 1（殻の中）。測った支柱と屋根のメッシュは、ワールドに表示されている物（URL が apply の state の記録と同じ、state の sourceHash がバンドルと同じ、描画が有効） | — |
| 前照灯 | — | — | M06 のローカルで (0, 1.26, 1.39)、レンズの前面 y 1.2465 の 1.35 cm 前 |
| 当たり判定 | 仮モデルに `FixedCollision` は無く、素材の中にも無い | 同左 | 同左 |

- 数: D の Slot 116・Component 240（W08 の実測に 3 つの宣言の 18・18 を足した値と一致）。W08 の root の下は Slot 739・Component 1,677（着手時の 721・1,659 から +18・+18）
- 動作の root: `DAM_Carousel_001`・`_TurnRoot`・`DAM_GhostTrain_001`・`_EngineRoot` の Slot の ID・位置・回転・拡縮は、着手時のスナップショットと同じ（TurnRoot は (0, 0.36, 0)、EngineRoot は (0, 0.14, 1.0)、どれも回転なし・拡縮 1）
- M01・M02・M03・M04・M08 の検査と A・B・C の数も合格のまま。アセットの ID・部品名・階層は変えていない（動かしたのは `Att_Headlamp` の位置だけ）

### 15.8 撮影と実機の確認

撮影（`review/p2_meshy/`、1600×900）: `m05_front`（東の主動線の側から顔と紋章）、`m05_oblique_se`、`m05_back`（西）、`m05_under_canopy`（回転床の縁から柱・支柱・屋根の下面）、`m05_pole_top`（東の支柱の先と垂れ飾り）、`m05_canopy_east`・`m05_canopy_top`（屋根）、`area_D_amusement`（W08 と同じ D の全景）、`m06_front`・`m06_oblique_nw`・`m06_side_west`・`m06_back`（先頭車の後面と客車）、`m06_headlamp`（前照灯のレンズと取付位置の目印）、`m06_plow_rail`（排障器と線路）

- 最初の撮影のうち 3 枚（`m05_front`・`m05_oblique_se`・`m05_back`）は Resonite が背面にあって真っ黒だった（利用者の指摘）ので、前面に出して撮り直した。`m06_back` は客車の屋根がカメラの前をふさいだので、カメラを西の後ろへ移して撮り直した
- 黒い面・反転・透け・ちらつきは見つからない。屋根は柱のハブの上に乗り、支柱は屋根の下面に入り（`m05_under_canopy`・`m05_pole_top`）、飾りの輪は垂れ飾りの下にある。仮モデルの見た目は表示されない
- M06 の排障器の下端と線路の上面の間に隙間が見える（`m06_plow_rail`。W09-M06 の 3 cm の持ち上げ）。W05 の車輪は M06 のアーチの中に収まる（`m06_side_west`）。前照灯の取付位置の目印（金色の八角形）はレンズの前で電球のように見える（`m06_headlamp`。15.2 の利用者の決定でこのまま）
- 利用者の実機（2026-11-01、06:45Z ごろ、デスクトップ）: メリーゴーラウンドと列車のまわりを歩き、見た目と外周の当たり判定は「問題なし」
- 負荷（利用者の測定、W08 と同じ端末）: 遊園地の近くで 60 fps 前後（W08 の基準と同じ）
- 増えた物: 三角形 89,037（M05 の 74,233 と M06 の 14,804。仮モデルの描画は止めた）、画像 6（約 42 MB の見積もり）、光源 0、当たり判定 0

### 15.9 GPT のレビュー（確認事項 7）

- 起動: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（codex-cli 0.166.0、モデル gpt-6-astra）。対象は PR #54 の `52a0309`。Resonite には接続させず、checkout も変更させていない。観点は、宣言の正しさ、W05 の修正、実測の検査の拡張、記録の正確さ、テストの採用基準の 5 つ
- 結果: Major 1 件・Minor 1 件。宣言の正しさ（`extract_part` の参照切れ・余分な資産なし、M01 の `split_part` は基点と同じ結果）、W05 の修正（名前・キー・階層の変更なし）、`source`・`export_root`・`pivot_in_asset`・前照灯・組み立ての期待値、足したテスト 4 件の採否は指摘なし。全文は PR #54 のコメント

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| 1 | Major | 支柱の検査は、支柱の形を最新のローカルのバンドルから取り、ワールドからは Slot の変換しか使わない。支柱のメッシュの更新を apply していない（旧い短い支柱が表示されている）状態や、支柱の描画を止めた・Slot を無効にした状態でも合格する（レビュアーが保存した観察の支柱の URL だけを戻して再現） | 採用 | 検査が誤った状態を成功と報告する経路のため。測った支柱と屋根のメッシュがワールドに表示されている物か（Slot と祖先が有効、`MeshRenderer` が有効で同じ Slot の `StaticMesh` を参照し、その URL が apply の state の記録と同じで、state の `sourceHash` がバンドルのファイルの SHA-256 と同じ）を確かめる（`check_measured_mesh_is_shown`。state の置き場は `--state-dir`、既定は親の checkout の `.resoloop/state`）。テスト 2 件 |
| 2 | Minor | 15.7 と引き継ぎの M05 の外接箱の寸法が、`live_checks.json` の世界の X・Z と逆 | 採用 | 記録の誤り。世界の X × 高さ × Z の順を明記し、柱 1.907 × 3.400 × 1.861 m・屋根 9.512 × 6.387 × 9.314 m に直した |

- 1 は、URL・`sourceHash`・描画のそれぞれの守りを外すと、そのテストだけが失敗することを確かめた。直した検査で実際のワールドを観察し直し、すべて合格した（07:00:10Z、`review/p2_meshy/live_checks.json`）。ワールドへの書き込みは無い
- 注意: ワールドを保存して開き直すと、資産の URL が `resdb:///` に移るが、state の URL は次の apply まで `local://` のまま残る（diff では書き直されない。apply していない world の state `p2_world.json` は 21 件とも `local://`）。apply は live の URL を state に記録する（この子が apply した D の state は、`resdb` 57 件と新しい支柱のメッシュの `local` 1 件になり、保存の後の D の diff は「source hash and imported URL match state」になった）。その間はこの検査が URL の違いで失敗する（誤りを見落とす方向ではない）。D を開き直した後に実行するときは、先に D を apply（変更 0 でよい）してから実行する

### 15.10 保存（確認事項 4）

- GPT のレビューへの対応の後に、エージェントの依頼で利用者が Resonite で 1 回保存した（2026-11-01、07:10Z より前）。保存の後は apply していない
- 保存の後に読み取りだけで確かめた（07:10:29〜07:11:03Z）: 全 17 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M08）の diff が変更 0。資産の判定は、world・E・M02 が「asset URL was migrated to resdb by a world save」、それ以外（D・M05 の 2 つ・M06 を含む）が「source hash and imported URL match state」で、M05・M06 と D の支柱の URL はまだ `local://`（ワールドを開き直していない）

### 15.11 Resonite で未確認の項目

- 再読込の後に M05・M06 の画像が保たれるか（P4）
- 回転床・座席・列車を動かしたときの見え方（P3）、VR、二人以上

## 16. W09R-E（#50）: E 西の M07 魔法の時計塔

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply したのはこのセッションだけ。着手前の確認事項は W08 #41 の回答（#50 の本文）
- 版: Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Blender 5.0.1（W09R〜W09R-D と同じ）
- スナップショットと diff・apply の報告は親の checkout の `tmp/w09r-e/`（Git の対象外）
- 閉じた子の所有ファイルのうち、W06 の `E_forest`、W08 の `modeling/p2_static/` は変えていない。W09-M07 の `review/M07/checks.json`・`M07_dial_textured.png` は、ビルドが W06 の今の針の軸と照合し直した結果をそのままコミットした（16.3。形は変えていない）
- これで採用する 8 素材（9 行）の差し替えが終わった（8 章の表）

### 16.1 保存の後の最初の diff

- 着手時のスナップショット（`tmp/w09r-e/01_snapshot_before_20261101T073258Z`）は W08 の root の下が Slot 739・Component 1,677 で、W09R-D の完了時と同じ（利用者が手で変えた所は無い）
- 最初の diff（07:33:32〜07:34:19Z、何も変える前。M07 の行を足す前の `REPLACEMENTS` で 6 キーを export した宣言 `exports/p2_static/<key>-20261101T073124Z`）: 全 17 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M08）が変更 0（no-op 29・184・655・333・318・378・780・16・15・15・17・16・18・15・15・15・19）。資産の作り直し・重複は無い
- 資産の判定: world・E・M02 は「asset URL was migrated to resdb by a world save」、それ以外は「source hash and imported URL match state」（W09R-D の保存の後、開き直していないので D・M05・M06 も `local://` のまま）

### 16.2 決めたこと

| 項目 | 決めたこと | 理由 |
|---|---|---|
| 当たり判定（**利用者の決定**、2026-11-01） | M07 のメッシュ（30,633 三角形）に `MeshCollider`（W08 と同じ `Static`・`CharacterCollider`・`DualSided`）を付ける。仮の本体の `EFR_ClockTower_001_Body_FixedCollision` は Slot と `StaticMesh` を残し、`MeshCollider` を `Enabled = false` にする（`REPLACEMENTS` の `collision: "finished"`。W09R-B の M03 と同じ形） | W06 の仮の本体（2,575 三角形）を、M07 と同じ原点・向きで Blender で比べた（下に照らし合わせのスクリプトの結果）。正面の階段: M07 は台座の上面（高さ 1.6 m）から正面へ下り y 3.3 m で地面に着くが、仮の本体は y 2.9 m まで高さ 1.56 m の平らな台が続き、その先で下りる（M07 の階段の上を歩くと最大で約 0.8 m 浮く。y 2.5 で M07 0.80 m・仮 1.56 m）。高さ 1.8〜3.0 m では仮の城の壁と角の塔が M07 の壁より 0.4〜1.3 m 外に、高さ 0.6〜1.2 m では台座の岩が 0.4〜1.3 m 外に出る（見えない壁）。台座のまわりは主動線の終点で人が近づく |
| 仮の文字盤 `EFR_ClockTower_001_Dial` | 描画だけ止める（`MeshRenderer.Enabled = false`。Slot・位置は残す）。`_Dial` は `_Body` の兄弟なので、`hide` の範囲（`visual_root` と `moving_parts` の `motion_root` の下）を、`visual_root` の兄弟で**地区の持ち主がアセット一覧の `replacement_slot.hide_on_replacement` に書いた物**にだけ広げた（`replacements.owner_hide_on_replacement`） | M07 の文字盤と重なる（`handoff/W06.md` 6 章）。範囲を行の設定だけで広げると、行の書き間違いで針・鐘のような兄弟が黙って消える。W06 が自分のデータで隠してよいと書いた物に限れば、持ち主の判断の範囲に留まる。今このデータを持つのは E の時計塔の `_Dial` だけ |
| 針・鐘・腕木 | 変えない（ID・原点・階層・可動部品の原点はそのまま） | W07 が針の軸を M07 の文字盤の実測の中心 (0.0015, 8.032) に合わせ済み（`docs/p1-handoff.md` 4 章の 4）。Resonite の実測で軸のずれ 0.0 m、針は文字盤より前でめり込まない（16.5） |
| 鐘の腕木の板 | 直さない（W06 の所有。記録だけ） | 北から見ると、腕木の板（W06 の `BellBracket`）の下の端は M07 の正面の破風に乗っているが、上の部分と鐘楼の壁の間に隙間が見える（`m07_bell_side`）。正面と広場の側からは付いて見え（`m07_bell`・`m07_front`）、高さ 11 m の細部なので、範囲外として `handoff/W09R-E.md` 6.2 に要望を書いた |
| 置き方 | `rotation_z_deg` 0（`placement_hint` -90 − 仮モデルの root -90）、`position_local` 0 | 仮の本体は M07 と同じ外接箱・原点・正面で作ってある（`handoff/W09-M07.md` 9 章） |

照らし合わせのスクリプト（セッションの一時的な物。コミットしていない）: M07 の `.blend` に E の `.blend` から仮の本体を読み込み、どちらもアセットの root のローカル（Blender の軸）で、0.1 m の格子に上からのレイ、x = 0 の正面の階段の断面、6 つの高さで外から中心への水平のレイ（5° ごと）を当てた。歩ける高さ（どちらかの上面が 2.4 m 未満）の 3,403 点のうち、上面の差が 5 cm を超える点は 3,295、30 cm を超える点は 2,803。

### 16.3 実装（`modeling/p2_meshy/`）

- `replacements.py`: `M07` の行（`hide` に `_Body` と `_Dial`、`collision: "finished"`、`dial_hands`、撮影のカメラ）。`owner_hide_on_replacement` と、`hide_placeholders` の範囲の広げ方（16.2）
- `verify_live.py`:
  - `hide` の対象は、`visual_root` の兄弟のうち地区のアセット一覧の `hide_on_replacement` に書いてある物も探す（無ければ失敗）
  - `dial_hands`（`check_dial_hands`）: 地区の時針・分針の回転軸（`_HourHandPivot`・`_MinuteHandPivot`）の原点が、素材の文字盤の中心（`review/M07/checks.json` の `dial.centre_local_m` をデータの原点と向きで置いた点）を通る軸の上 1 cm 以内で、文字盤より前にある。回転軸の Slot と針の Slot の前方（ローカルの +Z。W06 の針の回転軸）が文字盤の軸と平行で、針の Slot の原点が回転軸の Slot の原点にある（16.8 の GPT のレビューの指摘 2）。E の宣言の針のメッシュ（最新の `exports/p2_static/E_forest-*`）を Slot の変換で置き、軸に沿った前後の範囲と回る半径を求め、M07 の三角形を前後の範囲で切り取って文字盤の面へ移した形が、回る半径の円と重ならない（針は 360° 回るので、回す位置によらずめり込まない。三角形の頂点などの点で選ぶと大きな三角形が円を横切るのを見落とすので、切り取った多角形と円の距離で判定する。16.8 の指摘 1）。測った針と文字盤のメッシュがワールドに表示されている物か（W09R-D の `check_measured_mesh_is_shown`）
  - `collision: "finished"` の素材は当たり判定の節で検査を終えるので、針の検査はその前に置いた
- テスト（どれも S。`handoff/W09R-E.md` 9 章）: `tests/test_p2_meshy_replacements.py` に 1 件、`tests/test_p2_meshy_verify.py` に 2 件（16.8 の指摘 1・2 の反例を同じ 2 件に足した）。それぞれ守りを外すと、そのテストだけが失敗することを確かめた（変異ごとに `PYTHONPYCACHEPREFIX` を分けた）
- `review/M07/checks.json` の `dial.w06`（W09-M07 の所有）: M07 のビルドが W06 のアセット一覧の今の針の軸と照合し直し、軸のずれが 0.063 m → 0.0 m になった（W07 の直しの後の値）。`M07_dial_textured.png` の水色の点（W06 の針の軸）も中心に移った。形・画像の解像度・三角形は変えていない。アセット一覧の `export_result`（ビルドで `unexported` に戻る）と追跡中の `.blend`・他のキーの確認画像は戻した

### 16.4 export と validate

| 出力先 | 内容 | validate（オフライン・`--strict`） |
|---|---|---|
| `exports/p2_meshy/M07-20261101T073451Z` | M07（`--parent` は `EFR_ClockTower_001_Body`、`--preserve-hierarchy --pack-pbr`）。素材のメッシュの Slot に `MeshCollider`。撮影のカメラを足して `--recompose` した（ワールドには書かない。diff 0 を確かめた） | issues 0 |
| `exports/p2_static/E_forest-20261101T073434Z` | 仮の本体と仮の文字盤の描画、仮の本体の `FixedCollision` の `MeshCollider` を止めた E | issues 0 |
| `exports/p2_static/<key>-20261101T073124Z`（6 キー） | 16.1 の確認に使った world・A〜E（M07 の行の前） | issues 0 |

- M07: 三角形 30,633、画像 2（色 2048・詰めた PBR 1024、RGBA8 とミップの見積もり 合計 約 28 MB）、材質 1。警告なし
- 後続の作業のために、apply したバンドルを Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/p2_bundles/M07-20261101T073451Z`（`SHA256SUMS`）に控えた。新しい worktree で `verify_live.py` を実行するときは、ほかの素材と同じく同じ名前の出力先へ写す

### 16.5 diff と apply

| 時刻（UTC） | 宣言 | diff | apply |
|---|---|---|---|
| 07:35 前 | M07（最初） | 作成 16（資産 3、Slot 6、Component 7。すべて `EFR_ClockTower_001_Body/M07` の下。Component は `StaticMesh`・`MeshRenderer`・`MeshCollider`・`AI_GeneratedContent`・画像 2・材質） | — |
| 07:35 前 | E | 更新 3（`_Body` と `_Dial` の `MeshRenderer`、`_Body_FixedCollision` の `MeshCollider`。どれも `Enabled` を false に）。作成・削除・名前の変更 0 | — |
| 07:35:30〜07:35:52 | M07 → E | — | M07: Slot 6・Component 7・資産 3 を作成。E: Component の更新 3（資産は変更なし 115） |
| 07:36 | 2 つの 2 回目 | M07・E とも変更 0（no-op 16・780） | 書き込み 0 |

- `--prune` は使っていない。削除・名前の変更・Component の作り直しは 0。diff の対象は M07 の `visual_root` の下と資産、E の仮の本体・仮の文字盤の描画と仮の本体の当たり判定だけ（ほかの地区・`content/main.json`・前の素材の宣言は 0。16.1 の宣言のまま apply していない）
- apply の前のスナップショット: `tmp/w09r-e/01_snapshot_before_20261101T073258Z`（W08 の root 全体。最初の diff の後、apply まで書き込みは無い）

### 16.6 実測（`review/p2_meshy/live_checks.json`）

| 検査 | M07 |
|---|---|
| `visual_root` の世界の原点（W07 の `frame_origin_world` との差） | (-38.5, 0, 0)、0.0 m |
| 外接箱（世界の X × 高さ × Z、期待値との差） | 7.578 × 14.000 × 8.239 m、0.0 m（-90° で置くので、アセットの幅 8.239・奥行き 7.578 が入れ替わる）。`assets/manifest/M07.json` の寸法と一致 |
| 正面と鏡像 | (1, 0, 0)（東、広場の側。`placement_hint` -90）。祖先の拡縮はすべて正 |
| 描画 | 仮の本体と仮の文字盤の `MeshRenderer.Enabled` が false、素材は有効で色の画像を持つ材質を参照 |
| 針 | 文字盤の中心 (-38.1461, 8.032, -0.0015)、軸 (1, 0, 0)。時針の回転軸は軸のずれ 0.0 m・文字盤の面の 6.51 cm 前、針の前後の範囲で回る半径 0.62 m の円に重なる M07 の三角形 0、後ろで円に重なる三角形 254 のうち最も前の面（軸受け）との隙間 1.25 cm。分針は軸のずれ 0.0 m・10.51 cm 前、半径 0.93 m の範囲で 0、後ろの 1,058、隙間 4.65 cm。どちらも針の Slot は回転軸の Slot の原点にあり、前方は文字盤の軸と平行。測った針と文字盤のメッシュはワールドに表示されている物（16.8 の直しの後、07:54:20Z に観察し直した値） |
| 当たり判定 | 仮の本体の `FixedCollision` の `MeshCollider` が false、M07 のメッシュの `MeshCollider` が有効・`Static`・`CharacterCollider`・同じ Slot の `StaticMesh`・Offset 0。素材のバンドルの中のほかの Slot に当たり判定は無い |
| 取付位置 | E の時計塔に取付位置（attachment_point）は無い |

- 数: E の Slot 196・Component 482（W08 の実測に M07 の宣言の 6・7 を足した値と一致）。W08 の root の下は Slot 745・Component 1,684（着手時の 739・1,677 から +6・+7）
- 針・鐘・腕木と仮の本体・仮の文字盤・当たり判定の Slot（`EFR_ClockTower_001` と子 10 個）の ID・親・位置・回転・拡縮・有効は、着手時のスナップショットと同じ（`_HourHandPivot` (0.0015, 8.032, 0.419)、`_MinuteHandPivot` (0.0015, 8.032, 0.459)、`_BellPivot` (0.0015, 10.95, 1.45)。Resonite の軸、アセットの root のローカル）
- M01〜M06・M08 の検査と A〜D の数も合格のまま。アセットの ID・部品名・階層は変えていない

### 16.7 撮影と実機の確認

撮影（`review/p2_meshy/`、1600×900）: `m07_front`（東の主動線の先から全景）、`m07_front_close`（主動線から階段と入口）、`m07_dial`（文字盤と針の正面）、`m07_dial_oblique`（斜めから針と文字盤の隙間）、`m07_bell`・`m07_bell_side`（鐘の腕木と M07 の壁）、`m07_stairs_side`（横から階段と台座）、`m07_oblique_se`、`m07_back`（西）、`area_E_forest`（W08 と同じ E の全景）

- 撮るたびにファイルの大きさを見た（212〜396 KB。真っ黒な約 23 KB は無い）。北東からの斜めのカメラは手前の木の樹冠に遮られたので、南東（`m07_oblique_se`）に変えて撮り直した
- 黒い面・反転・透けは見つからない。仮の本体と仮の文字盤は表示されない。針は文字盤の中心にあり、斜めから見ても文字盤の前に浮いて、M07 の軸受けは針の根元の円に隠れる（`m07_dial`・`m07_dial_oblique`）。文字盤が緑がかって見えるのは近くの照明の色（照明の調整は範囲外）
- 鐘の腕木: 16.2 のとおり、北から見ると板の上の部分と鐘楼の壁の間に隙間がある（`m07_bell_side`）
- 利用者の実機（確認事項 6。2026-11-01、07:55Z ごろ、デスクトップ）: 時計塔のまわりと台座を歩き、当たり判定と、文字盤と針の見え方は「すべて問題ありません」
- 負荷（確認事項 8。利用者の測定、W08 と同じ端末）: 時計塔の近くで 60 fps（W08 の基準と同じ）
- 増えた物: 三角形 30,633（仮の本体と仮の文字盤の描画は止めた）、画像 2（約 28 MB の見積もり）、光源 0、当たり判定 1（M07 のメッシュの `MeshCollider` 30,633 三角形。仮の本体の当たり判定は止めた）

### 16.8 GPT のレビュー（確認事項 7）

- 起動: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（codex-cli 0.166.0、モデル gpt-6-astra）。対象は PR #55 の `668012f`。Resonite には接続させず、checkout も変更させていない。観点は、宣言の正しさ、`hide` の範囲の広げ方、実測の検査の追加、記録の正確さ、テストの採用基準の 5 つ
- 結果: Major 3 件・Minor 2 件。宣言の正しさと `hide` の範囲の広げ方は指摘なし、足したテスト 3 件はどれも S（書きすぎなし）。全文は PR #55 のコメント
- 採否は「直さないと致命的な問題（誤った結果を正しいと記録する、物が黙って消えるなど）になるか」で決めた

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| 1 | Major | 三角形を頂点・辺の中点・重心の 7 点で選ぶので、大きな三角形が針の回る範囲を横切っても見落とす（レビュアーが反例で再現） | 採用 | 針の位置の証拠に使う検査が、めり込みを合格と報告する経路のため。三角形を針の前後の範囲で切り取り、文字盤の面へ移した多角形と回る半径の円の距離で判定する。反例をテストに足した |
| 2 | Major | 回転軸の Slot の原点だけを比べるので、針の Slot がずれた・回転軸の向きが傾いた状態を合格にする | 採用 | 1 と同じく誤った状態を合格と報告するため。針の Slot の原点が回転軸の Slot の原点にあり、両方の前方が文字盤の軸と平行かを確かめる。テストに 2 例を足した |
| 3 | Major | 針の材質の参照が切れていても「表示されている」とする | 採用しない | 針の材質は W08 が統合したままで、この子の diff の対象外（E の宣言の針の Component は変えていない）。`check_measured_mesh_is_shown` の主張は「測ったメッシュがワールドで表示中の物」までで、W09R-D の支柱と同じ。針が見えることは撮影（`m07_dial`・`m07_dial_oblique`）と利用者の実機で確かめた |
| 4 | Minor | 8 章の表の M07 の「確認」が利用者の実機を含むのに、16.7 では記入待ち | 採用 | 利用者の実機の確認（16.7）を受けて、表と 16.7 を同じ内容にした |
| 5 | Minor | 「許可された名前でも兄弟でなければ拒否する」条件をテストしていない | 採用しない | 宣言の中に同じ名前の Slot が 2 つあると `_find_children_named` がエラーで止まるので、許可された名前が兄弟以外にあるのは、持ち主のデータの名前が兄弟に無い場合だけ。そのときは持ち主自身が隠すと書いた Slot で、針・鐘が黙って消える経路ではない |

- 1・2 は、直した判定（多角形と円の距離、針の Slot のずれ、軸の平行）・めり込みの判定・軸からのずれの判定のそれぞれの守りを外すと、対応するテストだけが失敗することを確かめた。直した検査で実際のワールドを観察し直し、すべて合格した（07:54:20Z、`review/p2_meshy/live_checks.json`）。ワールドへの書き込みは無い

### 16.9 保存（確認事項 4）

- GPT のレビューへの対応と利用者の実機の確認の後に、エージェントの依頼で利用者が Resonite で 1 回保存した（2026-11-01、08:08Z より前）。保存の後は apply していない
- 保存の後に読み取りだけで確かめた（08:08:55〜08:09:52Z）: 全 18 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M07・M08）の diff が変更 0（M07 は no-op 16、E は 780）。資産の判定は、world・M02 が「asset URL was migrated to resdb by a world save」、それ以外（E・M07 を含む）が「source hash and imported URL match state」。E の state は、この子の apply で live の URL（`resdb` 115 件）を記録した。M07 の資産の URL はまだ `local://`（ワールドを開き直していない）

### 16.10 Resonite で未確認の項目

- 再読込の後に M07 の画像と当たり判定が保たれるか（P4）
- 針・鐘を動かしたときの見え方（P3 の G20）、VR、二人以上
