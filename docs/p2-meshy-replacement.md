# P2 Meshy 素材の差し替え（W09R、Issue #44）

仮モデルを Meshy の仕上げた素材に差し替える方式と、最初の素材 M02 巨大ジャック・オー・ランタンの差し替えの記録。残りの 7 素材の子は、この文書の 2・4 章の手順と `handoff/W09R.md` を使う。

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

| 検査 | 結果 |
|---|---|
| 外接箱 | 世界で x -3.1011〜3.1014、高さ 1.6001〜7.6001、z -2.9351〜2.935（6.2025 × 6.0 × 5.8701 m）。アセット一覧の寸法を `_Body` の位置と 180° で置いた値との差 0.0 m |
| 正面 | 素材の前方は Resonite の (0, 0, -1)（南。スポーンの向き +Z の逆で、入口から顔が見える） |
| 描画 | 仮モデルの本体と目印 3 つの `MeshRenderer.Enabled` が false、M02 は true。材質 `PBS_Metallic` 1 つに色の画像がある |
| 取付位置 | `_EyeLightAttach` (0, 3.917, -2.676)、`_MouthReactionAttach` (0, 2.972, -2.806)、`_InteriorLightAttach` (0, 2.581, 2.409)。アセットの root から `pivot_local` の位置との差 0.0 m（差し替えの前と同じ） |
| 当たり判定 | `APL_GiantJackProxy_001_Body_FixedCollision` に `MeshCollider` があり、`_Body` と同じメッシュの資産を参照する。M02 の下に当たり判定は無い |
| 数 | A の Slot 173・Component 386（W08 の 166・379 に、M02 の宣言の Slot 7・Component 6 と自動の `AI_GeneratedContent` 1 を足した値と一致）。W08 の root の下は Slot 681・Component 1,619（W08 から +7・+7） |

ID・部品名・可動部品は変えていない。`APL_GiantJackProxy_001` の名前（Proxy）は ID なので残した。

### 5.4 撮影（`review/p2_meshy/`、1600×900、カメラは `replacements.py` の `cameras`）

`m02_front`・`m02_front_close`（正面）、`m02_oblique_se`（南東の斜め上）、`m02_back`（北）、`m02_eyes_low`・`m02_eyes_low_side`（器の縁の近くの下から。6 章）、`area_A_plaza`（W08 と同じ A の全景）、`overview_south`（W08 と同じ全景）。

- 黒い面・反転・透け・ちらつきは見つからない。顔は南を向き、本体の底は器の上に乗る
- 帽子は Blender では紫、帯は青緑だが、Resonite では茶色寄り・暗い緑に見える。材質の値は正常（金属 約 0、滑らかさ 約 0.4）で、広場の真上 (0, 9.5, 0) の橙色の主要ライト `PlazaPumpkinLight`（W08、色 (1.0, 0.62, 0.28)）を受けた色と合う。照明は W08 の宣言でこの子の範囲外なので、利用者の決定で記録して後続（P3・P4 の照明の調整）に回した
- M02 の手前 (0, 4.8, -3.8) に見える水色の小さな部品は、W02 の定期ショーの取付位置の目印 `APL_PeriodicShowRig_001_GhostOrbitAttach_S`。差し替えの前からあり、範囲外なので変えていない（`handoff/W09R.md` 6 章の要望）

### 5.5 実機の確認（利用者、デスクトップ）

- 2026-10-31: 噴水の器と台座のまわりを歩き、当たり判定は基本的に問題なし。要望として「かぼちゃの中の光源を調整して、近くの下から見ても目が光って見えるようにしてほしい」（6 章で対応）
- 光源を足した後の見え方を利用者が見て「このままでよい」

## 6. 目の光（利用者の要望）

- `M02` の宣言に、空洞の中の点光源 `M02_InteriorGlow`（`FrooxEngine.Light`、Point、色 (1.0, 0.55, 0.15)、強さ 3.0、範囲 5.0 m、影なし）を足した。位置は M02 のローカル（Blender）(0, 0.8, 1.6)、世界で (0, 3.2, -0.8)
- M02 の内側の壁は空洞の中心を向いているので、中から照らすと目・鼻・口の奥が光る（`m02_eyes_low` と光源の前の比較で確かめた）。顔の穴から漏れた光として、帽子のつばの裏と器の縁が少し橙色になる
- 材質の発光は使っていない（本体の材質を光らせると全体が光る。`handoff/W09-M02.md` 8 章）
- P3 の I03（目の発光の反応）は、この Light の `Intensity` を動かせる（`$component:m02_interior_glow_light`、state は `p2m_M02.json`）。I03 の範囲（反応の演出）は P3

## 7. 負荷

- 利用者の測定（W08 と同じ端末、3440×1440・Ryzen 7 5700G・RTX 4070 Ti SUPER、デスクトップ）: 広場の中央から M02 を見て「たまに 54 FPS ぐらい」。W08 の基準は 60 fps
- 差し替えで増えた物: 三角形 30,792（仮モデル 932 は描画を止めた）、画像 2（約 28 MB の見積もり）、点光源 1（影なし）
- 低下の原因（素材・画像・光源のどれか、測定の揺れか）は切り分けていない（未確認。P4 で通常時・ショー時と比べる）

## 8. 全素材の状態（Spec §12「P2」の 3 つ目、2026-10-31）

受領は W09 #13（`assets/meshy/received.json`、PR #26）。どの素材も未着ではない。採用しない物は、利用者が作り直す前の版（各ディレクトリの `size_over/`）と、M07 の `NG/`（針が塔に溶接されていた）だけで、確定版で置き換えた。

| 素材 | 受領 | 仕上げ（子・PR） | Resonite への投入 | 確認 | 採用 |
|---|---|---|---|---|---|
| M01 入場ゲート | 済（約 3.0 万三角形） | 済（W09-M01 #14・PR #29。門扉を切り離し両面化） | 未（仮モデル `APL_EntranceGateProxy_001`） | Blender・export・validate まで | 採用 |
| M02 巨大ジャック・オー・ランタン | 済（約 3.1 万） | 済（W09-M02 #15・PR #27） | **済（この子）** | **Resonite で実測・撮影・利用者の実機**（5 章） | 採用 |
| M03 幽霊屋敷の外観 | 済（約 3.0 万） | 済（W09-M03 #16・PR #35。入口の開口） | 未（`BMN_MansionPlaceholder_001`） | Blender・export・validate まで | 採用 |
| M04 魔女のお菓子工房の外観 | 済（約 3.1 万） | 済（W09-M04 #17・PR #39。窓の発光） | 未（`CCD_M04_CandyWorkshopProxy_001`） | Blender・export・validate まで | 採用 |
| M05 メリーゴーラウンドの屋根 | 済（約 4.2 万） | 済（W09-M05 #18・PR #34） | 未（`DAM_Carousel_001_M05_Canopy`） | Blender・export・validate まで | 採用 |
| M05 メリーゴーラウンドの中央の柱 | 済（約 3.2 万） | 済（同上） | 未（`DAM_Carousel_001_M05_CenterCasing`） | Blender・export・validate まで | 採用 |
| M06 おばけ列車の先頭車外装 | 済（約 1.5 万） | 済（W09-M06 #19・PR #38） | 未（`DAM_GhostTrain_001_M06_EngineShell`） | Blender・export・validate まで | 採用 |
| M07 魔法の時計塔 | 済（約 3.1 万。針の無い作り直しの版） | 済（W09-M07 #20・PR #32。文字盤の計測） | 未（`EFR_ClockTower_001_Body`・`_Dial`） | Blender・export・validate まで | 採用（`NG/` の版は不採用） |
| M08 ほうきに乗った魔女 | 済（約 3.1 万） | 済（W09-M08 #21・PR #37） | 未（`CCD_M08_FlyingWitchProxy_001`） | Blender・export・validate まで | 採用 |

仕上げた物は Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/finished/<M>/`。各素材の差し替えの注意は `handoff/W09R.md` 6 章。

## 9. 直した閉じた子のファイル

| ファイル（所有） | 変更 | 理由 |
|---|---|---|
| `modeling/p2_static/export_p2.py`（W08） | `colliders.compose` の後に `replacements.hide_in_file` を呼び、止めた仮モデルを `replacements.json` に書く（6 行） | 地区を export し直しても、差し替えた仮モデルが再び表示されないようにする（2.1） |

- `A_plaza`（W02）と `M02`（W09-M02）の所有ファイルは変えていない。`.blend` を作り直して変わった追跡中の `.blend`・確認画像・`assets/manifest/M02.json`（`export_result` が `unexported` に戻る）はコミットしていない（形は変えていない）
- `docs/conventions.md` §2・§7.6 と `AGENTS.md` に、キー `p2_meshy` と差し替えの手順・state を足した

## 10. Resonite で未確認の項目

- 保存・再読込の後の状態（資産の URL が `resdb:///` に変わった後の再 apply、M02 の画像と光源が保存されるか）。P4
- VR での見え方、二人以上
- 負荷の低下（60 → ときどき 54 fps）の原因（7 章）
- 帽子の色の照明による変化の調整（5.4。後続）
- `docs/p1-handoff.md` 8 章の 1〜4・6〜8（残りの 7 素材の子）
