# P3 自動ギミック（W10、Issue #56）

自動ギミックを Resonite で動かす方式と、最初の 2 種類 **G13 メリーゴーラウンドの床の回転**・**G01 小カボチャのダンス**の記録。残りの先行 8 種類（Spec §8 の G03・G05・G06・G09・G11・G15・G18・G20）の子は、この文書の 2・4 章の手順と `handoff/W10.md` を使う。

- W10-A（#58）の **G03 噴水の水と光の周期変化**は 16 章（方式の追記: 共有の材質を写した専用の材質と、発光の色の drive）

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply・配備したのはこのセッションだけ。GPT のレビューは PR で 1 回（14 章）
- 着手前の確認事項: W08 #41 の回答（issuecomment-6545243021）をそのまま使う（#56 の本文。起票したセッションの判断）
- Spec §5 の P3 は「GPT が主担当、Claude が確認」だが、この子は 2026-11-01 の利用者の決定で Claude Code が実装し GPT がレビューした（§5 の「個別タスクで交代できる」）

## 1. 適用先と版

- ワールド「Halloween Magical Carnival」（ResoniteLink のポートは利用者が伝えた値。恒久の値として書かない）。W08 の root `Root/HalloweenMagicalCarnival` の下だけを変えた
- Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Flux-SDK 1.9.0、Blender 5.0.1
- ProtoFlux のビルドに使った Resonite の DLL: 共有の managed data の 2026.9.18.82（`resoloop doctor` の managed data の項目は、`RESONITE_MANAGED_DATA_PATH` をコマンドだけに付けて pass。3,320 ノード）。実行中の Resonite（2026.10.29.1239）より古いが、ビルド・配備・実行は問題なかった（6 章）
- 着手時の W08 の root: Slot 745・Component 1,684（W09R-E の完了時と同じ。利用者が手で変えた所は無い）。スナップショットと diff・apply・配備の報告は親の checkout の `tmp/w10/`（Git の対象外）
- W10-A（#58、2026-11-01）も同じ版（Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Flux-SDK 1.9.0・managed data 2026.9.18.82、Blender 5.0.1）。記録は親の checkout の `tmp/w10a/`
- 駆動は、対象のワールドが Resonite の前面にあるときだけ進む（背面では `Spinner` も ProtoFlux の drive も止まって見える。最初の観察で回転が単位回転のまま変わらず、利用者に前面へ出してもらうと動いた）。観察・撮影の前に前面へ出してもらう

## 2. 方式

### 2.1 決めたこと

| 項目 | 決めたこと | 理由 |
|---|---|---|
| 静的な apply と動きの分け方 | P3 が駆動する Slot（G13 の `DAM_Carousel_001_TurnRoot`、G01 の 6 体の `APL_DancingPumpkin_00N_Body`）の宣言に `managedFields` を付ける（TurnRoot は `["position", "scale"]`、Body は `["scale"]`）。基準姿勢（宣言の位置・回転）は作るときの値として宣言に残す（`docs/p2-static-integration.md` 11 章の 2 つ目の案） | 1 つ目の案（動かす Slot を可動部品の root の子に分ける）は階層を変える（#56 の「してはいけない編集」）。M05 の素材の宣言は TurnRoot の子の `visual_root` を親にしていて、分けると親のパスが変わる。G01 の Body は見た目のメッシュそのもので、子に分けるとメッシュを動かせない |
| 駆動の作り方 | G13 は標準の `FrooxEngine.Spinner`（TurnRoot の `Rotation` を駆動）。G01 は ProtoFlux（`flux/P3PlazaDance.pg`）。Reflection で探した周期の Component（`TimeSineDriver`・`Wobbler*`・`Wiggler`）は、位相を持たない・出力が float だけ・乱数の揺れで、上下と傾きを個体ごとの位相で動かせない | Spec §8「単純な回転には標準 Component を優先し、複数状態の制御に ProtoFlux」。G13 は回転だけなので `Spinner` で足りる。G01 は上下と傾きを 1 つの位相から決め、位相を個体ごとにずらす必要があり、Component だけでは中間の値と駆動の鎖が長くなる（`resonite-build` スキルの選び方） |
| 宣言の置き場 | 駆動する側の Component は、駆動される Slot と同じ地区の宣言に置く（`modeling/p3_gimmicks/district.py` が `export_p2.py` の最後に足す。G13 の `Spinner`、G01 の中継 `ValueMultiDriver<float3>`・`<floatQ>` を各 Body に 2 つ）。外から変えられる値と ProtoFlux の配備先は、W08 の root の直下の別の宣言 `P3_Gimmicks`（`content/p3_gimmicks.json`、ownership `hmc_p3`、state `p3_gimmicks.json`） | resoloop の宣言の参照（`$slot-member:` など）は同じ state の中しか結べない。駆動先の Slot は地区の state にあるので、駆動の Component は地区の宣言に入れる。ProtoFlux のノードは Slot・Component が多い（192・249）ので、地区の下に置くと W08・W09R の数の検査が崩れる。`P3_Gimmicks` の下に置けば地区の数は宣言どおりのまま |
| G01 の中継 | Flux のマニフェストの `drive` は Component のメンバー（`$member:`）しか結べない（Slot のメンバーを `$member:` で指すと `STABLE_COMPONENT_NOT_FOUND`、`$slot-member:` は `FLUX_BINDING_TARGET_INVALID`）。各 Body に `ValueMultiDriver` を 2 つ置き、`Drives` に Body の `Position`・`Rotation`、`Value` を ProtoFlux の出力が drive する。`Value` の初期値は基準姿勢（`initialFields`） | モジュールが無い・止まっているときも基準姿勢に止まる。`Value` は駆動されるので `fields` に書かない（`resonite-build` スキル。駆動される値を宣言すると apply が駆動と競う） |
| 外から変えられる値 | `P3_Gimmicks` の `DynamicVariableSpace`（`HMC_P3`）と `DynamicValueVariable<float>` 3 つ: `HMC_P3/G01Intensity`（既定 1。上下・傾きの大きさ。0 で基準姿勢）、`HMC_P3/G01Frequency`（既定 0.8 Hz。上下の速さ。傾きはその半分）、`HMC_P3/G01PhaseSpread`（既定 1。W02 の位相にかける倍率。0 で 6 体がそろう）。モジュールの中で範囲に収める（I・s は 0〜1、f は 0〜2）。値は `initialFields`（apply し直しても Resonite の中で変えた値を戻さない）。G13 の速さは `Spinner` の `_speed`（`initialFields`。既定 (0, -18, 0) 度/秒） | 定期ショー（W11。§9.2「カボチャのダンスが盛り上がる」）が Resonite の中から値を変えられる。DynamicVariable は名前で読むので、ショーのモジュールを `P3_Gimmicks` の下に置けば同じ値に書ける。範囲に収めるので、ショーが大きな値を書いても W02 の可動範囲（包絡）を超えない |
| 同期と途中参加 | G01 は `WorldTimeDouble`（ワールドで共有の時刻）と HMC_P3 の値だけから位置・回転を計算し、各ユーザーが自分の画面で drive を評価する（同期する書き込みは無い）。G13 の `Spinner` も時刻から角度を決める（7 章の実測: 8 秒止めて再開した角度が、止める前の時刻の延長上に 1.6° の差で乗った。積算する方式なら 144° 遅れる） | Spec §10.3「共通の時刻基準から復元」。途中参加しても同じ時刻なら同じ姿勢になり、毎フレームの値をネットワークで送らない（`resonite-flux` スキルの Drive の分類）。2 人以上での確認は P4 |
| 座標と向き | Blender の Z まわり +θ = Resonite の Y まわり −θ。G13 の W05 の値（Blender の +Z まわり 18°/s、上から見て反時計回り）は `Spinner._speed` = (0, −18, 0)。G01 の傾き（W02 の `tilt_roll`）は Body のローカル Z まわり（顔はローカル −Z。取付位置 `_GlowAttach` が z −0.22） | 実測で、回した +X 軸が東 → 北へ回る（上から見て反時計回り）ことを確かめた（5 章）。P2 で未確認だった回る向き（`docs/p2-static-integration.md` 14 章）はこれで確認済み |

### 2.2 採らなかった方法

- **可動部品の root の子に動かす Slot を分ける**（`docs/p2-static-integration.md` 11 章の 1 つ目の案）: 2.1 のとおり階層を変える
- **ProtoFlux を A の地区の下に配備する**: 地区の数（W08 の `verify_live.py`、W09R の `check_counts`）がモジュールの Slot・Component の分だけずれる
- **G13 も ProtoFlux にする**: 標準の `Spinner` で速さ・向き・時刻の基準を満たす（Spec §8）。速さは `Spinner._speed` を変えれば変わる
- **G01 の値を `ValueField` にして Flux の `source` で結ぶ**: Flux のマニフェストの `worldState` は 1 つで、駆動先（A の state）と値（P3 の state）を同時に結べない。DynamicVariable は名前で読むので state をまたがない
- **`TimeSineDriver` などの Component で G01 を作る**: 2.1 のとおり位相・出力の型が合わない

## 3. 保存の後の最初の diff

何も変える前（08:38〜08:40Z）に、P3 の変更を入れずに 6 キーを export した宣言（`exports/p2_static/<key>-20261101T083805Z`。`district.add_drivers_in_file` を外して実行）で、全 18 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M07・M08）の diff を取った。どれも変更 0（no-op 29・184・655・333・318・378・780・16・15・15・17・16・18・15・15・15・16・19）。資産の作り直し・重複は無い。

- `exports/p2_meshy/` の宣言は、Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/p2_bundles/<M>-<UTC>/` を同じ名前の出力先へ写して使った（`SHA256SUMS` が一致）。`M02-20261031T164004Z` は記録だけのディレクトリで宣言ではない

## 4. 手順

プロジェクト（worktree）のディレクトリ。`ST` は親の checkout の `.resoloop/state`、`T` は親の checkout の `tmp/w10/`、`URL` は確かめた接続先。

```sh
for key in world common A_plaza B_mansion C_candy D_amusement E_forest; do resoloop blender run modeling/$key/build.py --json || exit 2; done
uv run python modeling/p2_static/export_p2.py --url "$URL" --key A_plaza --key D_amusement   # managedFields と駆動を足した p2.apply.json と p3_drivers.json
resoloop import Root/HalloweenMagicalCarnival --output "$T/<新しいディレクトリ>" --url "$URL" --json   # apply の前のスナップショット
resoloop diff exports/p2_static/<key>-<UTC>/p2.apply.json --state "$ST/p2_<key>.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply exports/p2_static/<key>-<UTC>/p2.apply.json --state "$ST/p2_<key>.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/build_content.py                     # content/p3_gimmicks.json・flux/P3PlazaDance.pg・flux/p3_plaza_dance.flux.json
resoloop diff content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/deploy_flux.py --url "$URL" --report "$T/<新しいファイル>"   # ProtoFlux（G01）の配備
# 同じ diff・apply をもう 1 回行い、変更 0・書き込み 0 を確かめる
uv run python modeling/p3_gimmicks/verify_live.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/live_checks.json --windows 2 --gap 300
uv run python modeling/p3_gimmicks/verify_live.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/param_checks.json --param-check
uv run python modeling/p2_meshy/verify_live.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p2_meshy/live_checks.json
resoloop capture content/p3_gimmicks.json --camera <名前> --output review/p3_gimmicks/<名前>.jpg --width 1600 --height 900 --url "$URL" --json
```

- `build_content.py` は A の state から Body の Slot のキーを読むので、A の地区の宣言を apply した後に実行する。キーは名前から作られていて、export し直しても変わらない
- `deploy_flux.py` は、マニフェストの `worldState`・`deployState`（親の checkout から見た相対パス）を親の checkout の絶対パスに直した一時のマニフェストを作って配備する（worktree の中に state を作らない）。Flux-SDK の DLL は `RESONITE_MANAGED_DATA_PATH` をこのコマンドだけに付けて渡す（`flux deploy-manifest` に `--library-path` は無い）
- ProtoFlux の式を変えるときは `build_content.py` を直して作り直し、`deploy_flux.py` で配備し直す（同じ名前のモジュールを置き換える。deploy state は `.resoloop/flux-state/p3_plaza_dance.json`）
- 宣言のキー（ownership・Slot・Component）は 10 文字未満か、エントロピーの低い名前にする。Gitleaks の `generic-api-key` は `"key": "<10 文字以上の識別子>"` に当たり、push の前の検査で止まる（10 章の注）
- 後続の子が駆動を足すときは、`gimmicks.driven_slots()` に Slot を、`district.add_drivers` にその駆動の Component を足し、地区を export し直す。キーは `p3_` で始める（W09R の数の検査が `rest_pose.p3_additions` で数える）

## 5. G13 メリーゴーラウンドの床の回転の結果

| 項目 | 結果（`review/p3_gimmicks/live_checks.json`、2 つの窓。9 章） |
|---|---|
| 速さ | 18.096°/s（10:00Z の窓、14 回の観察・28.8 秒）、18.025°/s（10:06Z の窓、18 回・28.5 秒）。W05 の 18°/s と 0.6% 以内（基準 5%） |
| 向き | 上から見て反時計回り（回した +X 軸が東 → 北へ回る）。W05 の Blender の +Z まわりと一致。`Spinner._speed` = (0, −18, 0) |
| 軸 | 回転は Y 軸まわりだけ（X・Z 成分の最大 0.0） |
| 一緒に回る部品 | TurnRoot の子孫（床・支柱・座席 4 基・M05 の柱と屋根の `visual_root`・取付位置）は、両方の窓の最初と最後で宣言と同じパス・同じローカルの変換（差の最大 0.0）。TurnRoot の位置も宣言のまま（0, 0.36, 0）。M05 の素材そのものの位置・向き・支柱との関係は W09R の検査が基準姿勢で確かめ、合格（11 章） |
| `Spinner` | 有効、`_target` が TurnRoot の `Rotation`、`_offset` 単位回転、`_speed` (0, −18, 0) |
| 包絡 | 回る部分の水平の半径は最大 4.860 m（屋根）、床の上面から 2.2 m までの部分は 4.680 m で、台座 `DAM_Carousel_001_Base` の半径 5.689 m の内側（通路へ出ない）。座席の上下（G14）は動かしていない |
| 利用者の確認 | 問題なし（13 章） |

## 6. G01 小カボチャのダンスの結果

| 項目 | 結果 |
|---|---|
| 上下 | 6 体とも −0.0199〜+0.1797 m（2 つの窓）。W02 の −0.02〜+0.18 m の中（許容 2 mm）。各個体の上下の幅は窓ごとに 0.146〜0.199 m（動いている） |
| 傾き | ローカル Z まわりだけで −11.999〜+11.999°。W02 の ±12° の中（許容 0.2°） |
| 水平のずれ | 0.0 m（位置は基準から上下だけ） |
| 式と位相 | 時刻を止めた標本で 6 体とも中継と Body が式の値と一致、ゆっくりの時刻で θ/2 が時刻どおり進み、位相差も W02 どおり（7 章）。`G01PhaseSpread` = 0 で 6 体がそろう |
| 漂い | 6.4 分あけた 2 つの窓で、範囲・軸・構造が同じ（式は共有の時刻と値だけから計算し、前の値を足し込まないので漂わない） |
| 台座と取付位置 | `_Pedestal` は動かず、`_GlowAttach` は Body の子のまま（宣言と同じパス・ローカルの変換）。中継は 12 個とも有効で、`Drives` は自分の Body の `Position`・`Rotation` を指す |
| 包絡 | 傾いたときの Body と取付位置の水平の半径は最大 0.428 m で、W02 の `envelope_radius_m` 0.55 m の内側（W02 が通路との余裕を確かめた範囲） |
| 既定の値 | 強さ 1、上下の速さ 0.8 Hz（傾きは 0.4 Hz）、位相の倍率 1。W02 のデータに速さが無いので、この子で決めた（弾む・揺れるのが分かり、せわしなくない速さ） |
| 利用者の確認 | 問題なし（13 章） |

## 7. 外から変えられる値と、時刻の基準（`review/p3_gimmicks/param_checks.json`）

`verify_live.py --param-check` が値を変えて測り、元に戻した（09:57〜09:59Z。GPT のレビュー（14 章）で守りを足した後の実行。最初の実行は 09:01〜09:02Z で同じ結果）。

| 確認 | 結果 |
|---|---|
| 時刻を止めた標本（`G01Frequency` = 0、`G01PhaseSpread` = 1）: θ_i = φ_i | 6 体とも、中継の値と Body の Slot そのものの位置・回転が式の値と一致（上下・傾き: 001 0.08 m・0°、002 0.1666 m・6.0°、003 0.1666 m・10.392°、004 0.08 m・12.0°、005 −0.0066 m・10.392°、006 −0.0066 m・6.0°）。式・位相・中継の結び先と、中継が Body を実際に駆動していることの確認 |
| `G01PhaseSpread` = 0（時刻は止めたまま） | 6 体とも 0.08 m・0°（そろう） |
| ゆっくりの時刻（`G01Frequency` = 0.004 Hz）で 22.97 秒あけた 2 回の観察 | 測れた 4 体の θ/2 の進みは 16.51〜16.58°（時刻からの予測 16.54°、差 0.05° 以内）、5 体の組 10 組の位相差は W02 の値と 0.86° 以内（許容 2°）。時刻の項が止まっている・速さが違うグラフはここで外れる。最初に 0.01 Hz で測ったときは、1 回の observe の中で最初と最後の個体を読む時刻のずれ（約 1 秒）で、001 と 006 の位相差が 2.16° ずれたので、0.004 Hz に下げた |
| `G01Intensity` = 0.5 | 上下 −0.009〜+0.090 m、傾き 6.0° 以内（W02 の範囲の半分） |
| `G01Intensity` = 0 | 6 体とも基準姿勢（上下 0、傾き 0） |
| 戻した値 | `G01Intensity` 1、`G01Frequency` 0.8、`G01PhaseSpread` 1（変える前と同じ。違えば問題にする） |
| G13 の `_speed` を (0, −9, 0) に | 実測 9.03°/s。戻した後の `_speed` は (0, −18, 0)（違えば問題にする） |
| `Spinner` を 8 秒止めて再開 | 再開の 1 秒後の角度は、止める前の速さと時刻からの予測と 2.21° の差（積算する方式なら 144.7° 遅れる。10° を超えたら問題にする）。`Spinner` はワールドの時刻から角度を決めている。戻した後の `Enabled` は true。止める前に回っていなければ「前面に無いかもしれない」と報告する（9 章の注のとおり、途中で背面に回った実行で、止める前から角度が 0° のままだった） |

## 8. 同期と途中参加

- G01: `WorldTimeDouble` と HMC_P3 の値から計算する drive だけで、同期する書き込み・インパルスは無い（`flux/P3PlazaDance.pg` の先頭）。同じワールドの時刻なら、途中参加のユーザーも同じ姿勢を見る。HMC_P3 の値は同期する通常のフィールド（ショーが書いた値は全員に届く）
- G13: `Spinner` が時刻から角度を決めることを 7 章で確かめた
- 2 人以上での確認、途中参加、保存・再読込の後の動作は P4（未確認）

## 9. 動いている間の実測（`review/p3_gimmicks/live_checks.json`）

`verify_live.py --windows 2 --gap 300 --duration 30`（10:00:12Z と 10:06:38Z の 2 つの窓。GPT のレビューの後の実行）。両方の窓とも問題 0、包絡の問題 0。

- 窓ごとに: HMC_P3 の値と `Spinner` の設定を観察 → 中継の `Drives` の結び先と構造（`hierarchy`）→ G13 を約 2 秒ごとに 30 秒（14・18 回。隣の観察の間は最大 2.9 秒 = 53°）→ G01 を 30 秒（観察の後に 1 秒待つが、observe そのものに約 3 秒かかるので、実際の間隔は約 4 秒。8 回ずつ）→ 構造をもう一度。各個体の上下・傾きの幅が範囲の 15% 未満なら「動いていない」とする（14 章の指摘 4）
- 最初の実行（09:03Z・09:09Z の窓）は、G13 と G01 を交互に観察していたので G13 の観察の間が約 8 秒（約 144°）あき、1 つ目の窓で角度を連続にできずに速さが 9.71°/s と出た（2 つ目の窓は 18.08°/s）。G13 を続けて観察する形に直し、間が 150° 分を超えたら問題にする守りを足した（`check_g13`）。上の結果は直した後の実行
- G01 の上下と傾きは別の Component（中継）で、1 回の `observe` の中でも読む時刻がずれる。動いている間は範囲・軸だけを見て、式と位相は 7 章の時刻を止めた標本で確かめる
- その前の実行（09:23Z・09:30Z の窓、GPT のレビューの前の検査）も合格（18.05・18.04°/s）
- 生の観察（ResoniteLink の ID を含む）は親の checkout の `tmp/w10/p3_raw_windows_4.json`（Git の対象外）。コミットした要約に ID は含めない

## 10. diff・apply・配備と、再適用・所有範囲

| 時刻（UTC） | 宣言・操作 | diff | apply |
|---|---|---|---|
| 08:42 | D（`D_amusement-20261101T084052Z`） | 作成 1（TurnRoot の `Spinner`）。`managedFields` の追加は今の値と同じで変更にならない | Component 1 を作成（資産は変更なし 58） |
| 08:42 | A（`A_plaza-20261101T084052Z`。Body に `managedFields` だけ） | 変更 0 | 書き込み 0 |
| 08:42 | P3（`content/p3_gimmicks.json`、state `p3_gimmicks.json` を新しく作る） | 作成 7（Slot 2、Component 5。`AI_GeneratedContent` は resoloop が足した物） | 作成 |
| 08:45 | A（`A_plaza-20261101T084502Z`。中継を足した） | 作成 12（6 体の Body に `ValueMultiDriver<float3>`・`<floatQ>`） | Component 12 を作成（資産は変更なし 110） |
| 08:45 | ProtoFlux（`deploy_flux.py`） | — | モジュール `P3PlazaDance` を `P3_Gimmicks/G01_Dance` の下に作成（drive の結び先 12 個がすべて解決。Slot 192・Component 249） |
| 09:11 | 全 19 宣言の 2 回目の diff（動いている最中） | どれも変更 0（W08 の 7 つ・Meshy の 11 個・P3。A は no-op 667、D は 379、P3 は 7）。回転・位置は差分にならない | — |
| 09:12 | A・D・P3 の 2 回目の apply | — | どれも書き込み 0（Slot・Component の作成・更新・削除 0、資産の取り込み 0） |

| 09:35〜09:36 | P3 の宣言のキーの変更（下の注） | 新しい state で `--adopt` の diff が no-op 7（作成・更新・削除 0） | 引き取りの apply が書き込み 0。`identityFields` を足して引き取り直し、2 回目の diff 変更 0・警告 0、apply 書き込み 0 |

- P3 の宣言のキーの変更: push の前の Gitleaks の検査で、`generic-api-key` が宣言の ownership のキー（旧 `halloween_p3_gimmicks`）と値の Component のキー（旧 `p3_var_G01Intensity` など）の行に当たった（名前から作った識別子で、秘密情報ではない）。まだ push していないこの子のコミットなので、キーを 10 文字未満（ownership `hmc_p3`、値の Component `g01_amp`・`g01_freq`・`g01_phase`）に変えてコミットを直した。resoloop は ownership の違う state を拒否する（`APPLY_STATE_OWNERSHIP_MISMATCH`）ので、旧 state を親の checkout の `tmp/w10/state_backup_ownership_halloween_p3_gimmicks/` に移し、同じ名前の新しい state（`p3_gimmicks.json`）へ `--adopt` で既存の Slot・Component を引き取った（ワールドの物の作り直し・ID の変更なし。ProtoFlux のモジュールもそのまま）。同じ Slot に同じ型が 3 つある値の Component には、diff の警告どおり `identityFields: ["VariableName"]` を足し、もう一度引き取って state に識別の値を入れた
- 最初の配備の前に 2 回失敗した（ワールドは変わっていない）: Body の Slot のメンバーを `$member:` で結ぶと `STABLE_COMPONENT_NOT_FOUND`（Component のキーしか解決しない）、`$slot-member:` は `FLUX_BINDING_TARGET_INVALID`（マニフェストの検証で止まる）。そこで中継を足した（2.1）
- `--prune` は使っていない。削除・名前の変更・Component の作り直しは 0
- 所有範囲: diff の対象は D の TurnRoot の `Spinner`、A の 6 体の Body の中継、P3 の宣言の Slot だけ。B・C・E・world・`content/main.json`・Meshy の素材の宣言は、最初の diff から最後まで変更 0 で、apply していない
- 数: W08 の root の下は Slot 745・Component 1,684 → Slot 939・Component 1,951（P3 の宣言 2・5、モジュール 192・249、中継 0・12、`Spinner` 0・1）
- apply の前のスナップショット: 親の checkout の `tmp/w10/01_snapshot_before_20261101T083720Z`（W08 の root 全体。最初の diff の後、最初の apply まで書き込みは無い）

## 11. 既存の検査（`modeling/p2_static/verify_live.py`・`modeling/p2_meshy/verify_live.py`）

- 両方の検査は、観察の中の P3 が駆動する Slot の駆動される項目（TurnRoot の回転、6 体の Body の位置と回転）だけを、最新の地区の宣言の基準姿勢に戻してから測る（`modeling/p3_gimmicks/rest_pose.py`。TurnRoot の位置は静的な apply が管理し続けるので観察のまま。14 章の指摘 5）。子孫（座席・M05・取付位置）は基準姿勢の親の下で今までどおり検査される。駆動された値そのものは P3 の検査が見る
- W09R の検査（`modeling/p2_meshy/verify_live.py`）の地区の数の照合に、P3 が地区の宣言に足した数（キーが `p3_` の物。A は中継 12、D は `Spinner` 1）を加えた（`rest_pose.p3_additions`）
- 動いている状態での結果: W09R の検査は全項目合格（M01〜M08 の 9 行、5 地区の数。W08 の root の下は Slot 939・Component 1,951）。W08 の検査（`p2_static`）は W09R 以降の既知の 11 件（Meshy の素材の宣言の分の地区の数、M01 の門扉の置き直しと W03 の扉の古い蝶番の値（`docs/p2-meshy-replacement.md` 14.3）、M03・M07 の当たり判定の数）で失敗するのは変わらず、P3 の駆動による失敗は 0。置き換えを外して同じ観察から測ると、カボチャ 6 体と座席 4 基の 10 件が増える（`tmp/w10/p2_static_checks_without_rest.json`）。W08 の検査の結果ファイル（`review/p2_static/live_checks.json`）は W09R の検査が W08 の基準の数として読むので、書き換えていない

## 12. 直した閉じた子のファイル

| ファイル（持ち主） | 直した内容 | 理由 |
|---|---|---|
| `modeling/p2_static/export_p2.py`（W08） | Meshy の差し替えの後に `district.add_drivers_in_file` を呼び、`p3_drivers.json` を書く（6 行） | 地区の宣言に P3 の駆動と `managedFields` を入れる（2.1） |
| `modeling/p2_static/verify_live.py`（W08） | 観察を検査する前に `rest_pose.apply_rest_pose` を呼ぶ。プロジェクトの root を `sys.path` に入れる | 動いている可動部品を「ずれた」と誤って判定しない（11 章） |
| `modeling/p2_meshy/verify_live.py`（W09R 系） | 同じく `rest_pose.apply_rest_pose` を呼ぶ。`check_counts` に P3 が足した数を加える（引数 `p3_added`。既定は 0） | 同上。地区の数の期待値に P3 の Component を入れる |
| `review/p2_meshy/live_checks.json`（W09R 系） | 動いている状態で検査し直した結果（`p3_rest_pose` と `p3_added` の欄が増えた） | 11 章 |
| `exports/p2_static/A_plaza-*`・`D_amusement-*`（W08 の記録） | 083805Z（6 キー、P3 なし。3 章）、084052Z（A・D に `managedFields` と `Spinner`）、084502Z（A に中継）の `report.json`・`validate.json`・`colliders.json`・`replacements.json`・`p3_drivers.json` | export のやり直しの記録 |

A・D の地区のキー（W02・W05）の所有ファイルと、Meshy の素材（M01〜M08）の所有ファイルは変えていない。アセットの ID・部品名・可動部品の原点と階層も変えていない。

## 13. 撮影と実機の確認

- 利用者の確認（確認事項 6、デスクトップ、09:19Z ごろ）: G13（床・支柱・座席・M05 の屋根と柱が一緒に、上から見て反時計回りに約 20 秒で 1 周）と G01（台座の上で上下に弾みながら左右に傾き、個体ごとにタイミングがずれる）は「どちらも問題ない」。通路へのはみ出し・不自然な点は無い
- 負荷（確認事項 8）: W08 の基準と同じ端末（3440×1440、Ryzen 7 5700G、デスクトップ一人）で 60 fps 前後（W08 は 60、差し替えの後は 60 前後）。足した物は Component 13（`Spinner` 1、中継 12）と、P3 の宣言の Slot 2・Component 5、ProtoFlux のモジュールの Slot 192・Component 249（ノード）。G01 の drive は各ユーザーが毎フレーム評価する（ネットワークの送信は無い）
- 撮影（`review/p3_gimmicks/`、1600×900、カメラは `content/p3_gimmicks.json` の `cameras`。09:21〜09:23Z）: `g13_carousel`（東から。床・座席・M05 の屋根と柱）、`g13_carousel_top`・`g13_carousel_top_later`（上から約 10 秒の間をあけた 2 枚。屋根の顔の向きと座席の位置が回っている）、`g01_ring`（南から噴水のまわり。個体ごとに傾きが違う）、`g01_close`・`g01_close_later`（南の 2 体）
  - 撮るたびにファイルの大きさを見た（234〜503 KB。真っ黒な約 23 KB は無い）。最初の G13 のカメラ（南東）は南の入場ゲート M01 に、低いカメラは手前の屋台に遮られたので、W09R-D の M05 の撮影の位置を基に東と上へ替えた。広場の全景は利用者のアバターの名札が写ったので、画角を絞って撮り直した（公開リポジトリのため）
  - `resoloop capture` の `<名前>.scene.json` は作業ツリーの絶対パスを含むのでコミットせず、親の checkout の `tmp/w10/capture_scenes/` に移した。一時カメラ `ResoLoop_Test_Capture_*` は残っていない（`resoloop find`）

### 13.1 保存（確認事項 4）

- GPT のレビューへの対応と実機の測り直しの後に、エージェントの依頼で利用者がワールドを 1 回保存した（2026-11-01 10:11Z より前。保存の操作の種類は記録していない）
- 保存の後（10:11〜10:13Z）に全 19 宣言（W08 の 7 つ・Meshy の 11 個・P3）の diff を取り、どれも変更 0・警告 0。メリーゴーラウンドは回り続けていた（TurnRoot の回転が単位回転でない）。保存・再読込の後に `Spinner`・ProtoFlux のモジュール・HMC_P3 の値・中継が残って動くかは P4（開き直していない）

## 14. GPT のレビュー（確認事項 7）

- 起動: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（モデル gpt-6-astra）。対象は PR #57 の `c7367c6`。Resonite には接続させず、checkout も変更させていない。観点は、宣言と駆動の正しさ、W08・W09R のファイルの修正、実測の検査、記録の正確さ、テストの採用基準の 5 つ
- 結果: Major 4 件・Minor 2 件・Info 1 件（どれも実測の検査と記録。宣言・生成コード・`check_counts` の加え方は指摘なし）。全文は PR #57 のコメント

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| 1 | Major | 包絡の判定（W02 の範囲・台座の内側・M05 のバンドルの欠け）が最終の判定に入っていない | 採用 | 誤って合格と報告するため。`envelope_problems` を最終の `ok` に入れた |
| 2 | Major | 時刻の基準の検査に外れても、値の戻し忘れがあっても合格になる | 採用 | 同上。`follows_world_time` が偽、速さ・`Enabled` が元の値と違えば問題にした |
| 3 | Major | 中継の値と結び先だけを見るので、中継が無効・Body が動いていなくても合格する | 採用 | 時刻を止めた標本で Body の Slot そのものの位置・回転も式と照合し、中継の `Enabled` を確かめる |
| 4 | Major | 時刻の項が止まった（各個体が一定の姿勢の）グラフでも、動いている間の検査と値の確認を通る | 採用 | 動いている間の各個体の上下・傾きの幅が範囲の 15% 未満なら問題にする（`check_g01_variation`）。ゆっくりの時刻で θ/2 の進みと位相差を確かめる（`check_g01_clock`） |
| 5 | Minor | 基準姿勢への置き換えが、TurnRoot の位置（P3 は駆動していない）の本当のずれも消す | 採用 | 置き換えは駆動される項目（`managedFields` に残っていない位置・回転）だけにした。TurnRoot は回転だけ |
| 6 | Minor | 構造の照合を名前で探すので、取付位置を Body の外へ付け替えても合格する | 採用 | 宣言と同じパス（親子関係）でたどって照合する |
| 7 | Info | 記録の「G01 を約 1 秒ごと」は、実際の間隔（約 4 秒）と違う | 採用 | 記録の誤りなので直した（9 章） |

- テスト（S）: 指摘 1・3・4・5・6 の守りに、正しい状態で通る例と外れる例を 1 つずつ足した（`tests/test_p3_gimmicks_verify.py` に 5 件、`tests/test_p3_gimmicks_rest_pose.py` の 2 件目を拡張）。指摘 2 は `--param-check` の実機の流れの中の判定で、外れたときの文言を確かめるだけになるので足していない（実機で外れる実行を 1 回見た。9 章の注）。どれも守りを外す変異でそのテストだけが失敗することを確かめた
- 直した検査で実機を測り直し、すべて合格した（7・9・11 章）

## 15. Resonite で未確認の項目

- 2 人以上での同期、途中参加、イベントの実行主体の退出（P4）
- 保存・再読込の後に、`Spinner`・ProtoFlux のモジュール・HMC_P3 の値・中継が残って動くか（P4）
- VR での見え方、動くカボチャ・回転床とアバターのすれ違い（P4）
- 負荷のメモリ

## 16. W10-A（#58）G03 噴水の水と光の周期変化

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。claim `agent-claims/issue-58`（10:37:05Z）。apply・配備したのはこのセッションだけ。GPT のレビューは PR で 1 回（16.11）
- 着手前の確認事項: W08 #41 の回答（issuecomment-6545243021）をそのまま使う（#58 の本文。利用者の変更なし）
- 対象: A の `APL_Fountain_001_Water`（W02 の水の幕のメッシュ。`assets/manifest/A_plaza.json` の `motion` が `tiered_fountain_water_and_glow`）。動きの範囲は無く、水の発光の色と明るさだけを変える。水のメッシュ・取付位置 `APL_Fountain_001_WaterAttach`・M02 の素材の宣言と点光源は変えていない

### 16.1 方式の追記

| 項目 | 決めたこと | 理由 |
|---|---|---|
| 何を変えるか | 水の材質の `EmissiveColor`（明るさの脈と、水色 → 紫の色の移り変わり）。`AlbedoColor`・金属・滑らかさ・メッシュ・位置は変えない | Spec §8 の「水／光の流れが周期的に変化」。水の材質に画像は無い（`MAT_APL_MagicWater` は色だけ）ので、画像のずらし（`TextureOffset`）では見た目が変わらない |
| 共有の材質の扱い | A の宣言で、水の Slot に共有の材質を写した専用の `PBS_Metallic`（キー `p3_g03_wm`）を足し、水の MeshRenderer の `Materials` だけをそれに付け替える（`modeling/p3_gimmicks/district.py` の `add_g03_material`。`export_p2.py` が呼ぶ `add_drivers_in_file` から）。専用の材質の `fields` は元の材質と同じ値、`EmissiveColor` は元の値を `initialFields` に置く（ProtoFlux が drive する） | `MAT_APL_MagicWater` は水のほかに 7 個の MeshRenderer（水の取付位置の目印、I03 の台座の `EffectAttach`、ショーの装置の `Pylons` と `GhostOrbitAttach` 4 つ）が使う。共有の材質を駆動すると、それらが全部光り方を変える（`docs/p2-static-integration.md` 11 章）。材質を写せば、水以外の物は元の材質のまま |
| 駆動の作り方 | ProtoFlux（`flux/P3FountainGlow.pg`）。`WorldTimeDouble` と HMC_P3 の値 3 つから発光の色を計算し、専用の材質の `EmissiveColor` を drive で結ぶ（`flux/p3_fountain_glow.flux.json`、worldState は A の state）。配備先は `P3_Gimmicks/G03_Fountain`（P3 の宣言の Slot） | Flux の drive は Component のメンバーを直接結べる（材質は Component なので、G01 のような中継は要らない）。HMC_P3 の DynamicVariableSpace は `P3_Gimmicks` にあり、A の地区の Slot から上へたどっても届かないので、値を読む物は `P3_Gimmicks` の下に置く必要がある |
| 式 | θ = 2π f t、脈 = 1 + 0.5 A sin θ、混ぜ = A (1 − cos(θ/2)) / 2、発光 = I × 脈 × ((1 − 混ぜ) E0 + 混ぜ E1)。E0 は P2 の水の発光の線形の値 (0.504, 0.99, 1.764)（A の宣言の元の値 sRGB (0.738, 0.996, 1.281) を線形にした値。Blender の発光 (0.28, 0.55, 0.98) × 1.8 と同じ）、E1 は紫 (1.2, 0.4, 2.0)（`gimmicks.G03_SHIFT_EMISSIVE_LINEAR`）。出力は `Pack_ColorX(…, ColorProfile.Linear)` | 時刻だけから決まり、前の値を足し込まないので漂わない（Spec §8）。A = 0・I = 1 で P2 の見た目と同じ（モジュールの外の基準）。色の移り変わりは脈の半分の速さで、明るさと色が同じ周期でそろわない |
| 色の空間 | 計算は線形の値で行い、Linear の profile の `colorX` で出す | ProtoGraph では enum の値を `ColorProfile.Linear` と書ける。`ColorProfile.sRGB` は小文字で始まるので構文で書けなかった（`flux check` が「Unable to parse」）。元の材質の値は sRGB（`resoloop observe` の `profile`）なので、P2 の値は sRGB → 線形に直して式に入れた（`gimmicks.srgb_to_linear`） |
| 外から変えられる値 | `HMC_P3/G03Intensity`（既定 1、0〜2。発光の強さの倍率。2 は定期ショーの盛り上がり用）、`HMC_P3/G03Frequency`（既定 0.2 Hz、0〜1。明るさの脈の速さ。色はその半分）、`HMC_P3/G03Swing`（既定 1、0〜1。変化の深さ。0 で P2 の色のまま一定）。`P3_Gimmicks` の `DynamicValueVariable<float>`（キー `g03_amp`・`g03_freq`・`g03_swing`、`initialFields`）。モジュールの中で範囲に収める | G01 と同じ置き場（ショーのモジュールが名前で書ける）。範囲に収めるので、ショーが大きな値を書いても、発光の倍率は最大 3 倍（強さ 2 × 脈 1.5）に収まる |
| 既定の速さ | 脈は 5 秒、色の一巡は 10 秒 | W02 のデータに速さが無いので、この子で決めた（水が呼吸するように見え、せわしなくない。利用者の確認で問題なし） |
| 同期と途中参加 | G01 と同じ。共有の時刻と、同期する値だけから計算する drive で、同期する書き込み・インパルスは無い | Spec §10.3。途中参加のユーザーも同じ時刻なら同じ色を見る。2 人以上での確認は P4 |

採らなかった方法:

- **共有の材質 `MAT_APL_MagicWater` をそのまま駆動する**: 水以外の 7 個の MeshRenderer も一緒に光り方が変わる（#58 の受け入れ基準の「共有の材質」に反する）
- **標準の Component（`TimeSineDriver` で `ValueGradientDriver<colorX>` の `Progress` を動かす）**: Reflection で確かめた（`TimeSineDriver` は `Target`・`Speed`・`Min`・`Max`、`ValueGradientDriver<colorX>` は `Progress`・`Target`・`Interpolate`・`Points`）。駆動の Component は材質と同じ A の宣言に置く必要があるが、A の Slot から HMC_P3 の空間に届かないので外から値を変えられない（DynamicVariable の駆動を足しても同じ）。範囲に収める処理も無い
- **発光用の別の Slot（重ねたメッシュや点光源）を足す**: メッシュを重ねると同じ高さの面が重なり（W07 の z-fighting）、点光源は M02 とまわりの物の照らされ方を変える（「M02 の見た目が変わっていない」に反する）
- **水の材質を Blender（W02 の `modeling/A_plaza/build.py`）で分ける**: W02 の所有ファイルの造形のやり直しになる（#58 の範囲外）。export の後の宣言で分ければ、W02 のデータも `.blend` も変えずに済む

### 16.2 Reflection・Flux-SDK で確かめた物

- `resoloop type describe`: `FrooxEngine.PBS_Metallic`（`AlbedoColor`・`EmissiveColor` は `colorX`、`TextureOffset` など）、`FrooxEngine.TimeSineDriver`、`FrooxEngine.ValueGradientDriver<colorX>`。`resoloop type search`（Gradient・Sine・Pulse・Panner）で周期の Component の候補を見た
- `resoloop flux node describe`（managed data 2026.9.18.82、3,320 ノード）: `Pack_ColorX`（R・G・B・A と `ColorProfile`）、`Cos_Double`、`Cast_float4_To_colorX`・`Mul_ColorX_Float`・`ColorXSetProfile`（候補として見た）。`resoloop flux check` で、`ColorProfile.Linear` は書け、`ColorProfile.sRGB` は構文で書けないことを確かめた
- 観察: 元の材質の `EmissiveColor` は sRGB の (0.7379854, 0.9955913, 1.281473, 1)。配備の後、専用の材質の値は Linear の profile で時間とともに変わる

### 16.3 保存の後の最初の diff

何も変える前（10:44〜10:45Z）に、今の `main` のまま 6 キーを export した宣言（`exports/p2_static/<key>-20261101T104312Z`。W10 の駆動は入っている）で、全 19 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M07・M08・`content/p3_gimmicks.json`）の diff を取った。どれも変更 0・警告 0（no-op 29・184・667・333・318・379・780・16・15・15・17・16・18・15・15・15・16・19・7）。資産の作り直し・重複は無い。W10 の ProtoFlux のモジュール `P3PlazaDance` は `P3_Gimmicks/G01_Dance` の下に配備されたまま。W08 の root の下は Slot 939・Component 1,951（W10 の完了時と同じ。利用者が手で変えた所は無い）

- 新しい worktree の準備: 全キーの `.blend` の作り直し（10:37〜10:42Z、約 5 分）と、Git の外の `p2_bundles/<M>-<UTC>/` を同じ名前の `exports/p2_meshy/` へ写した（コミット済みの記録は上書きせず、`SHA256SUMS` が全 9 つ一致）
- apply の前のスナップショット: 親の checkout の `tmp/w10a/01_snapshot_before_20261101T104558Z`（W08 の root 全体。最初の diff の後、最初の apply まで書き込みは無い）

### 16.4 手順

4 章の手順に、次を足す（`T` は親の checkout の `tmp/w10a/`）。

```sh
uv run python modeling/p2_static/export_p2.py --url "$URL" --key A_plaza      # 水の専用の材質を足した p2.apply.json と p3_drivers.json
resoloop diff exports/p2_static/A_plaza-<UTC>/p2.apply.json --state "$ST/p2_A_plaza.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply exports/p2_static/A_plaza-<UTC>/p2.apply.json --state "$ST/p2_A_plaza.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/build_content.py   # A の最新の export から E0 を読み、flux/P3FountainGlow.pg・flux/p3_fountain_glow.flux.json も作る
resoloop diff content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/deploy_flux.py --url "$URL" --manifest flux/p3_fountain_glow.flux.json --report "$T/<新しいファイル>"
# 同じ diff・apply・配備をもう 1 回行い、変更 0・書き込み 0・配備 no-op を確かめる
uv run python modeling/p3_gimmicks/verify_g03.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g03_live_checks.json --windows 2 --gap 300
uv run python modeling/p3_gimmicks/verify_g03.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g03_param_checks.json --param-check
```

- `build_content.py` は A の最新の export に専用の材質（`p3_g03_wm`）が無いと止まる（先に A を export する）
- `deploy_flux.py --manifest` は `flux/` の下のマニフェストだけを受け付ける。G03 の deploy state は親の checkout の `.resoloop/flux-state/p3_fountain_glow.json`
- `resoloop apply --json` は進み具合の行を標準出力に出し、最後の行が JSON になる（読むときは最後の行だけを読む）

### 16.5 G03 の結果

GPT のレビュー（16.11）で直した検査での実行: `verify_g03.py --windows 2 --gap 300 --duration 30`（11:23:56Z と 11:30:02Z の 2 つの窓。`review/p3_gimmicks/g03_live_checks.json`）と `--param-check`（11:20〜11:22Z。`g03_param_checks.json`）。どれも問題 0。直す前の検査での実行（`--param-check` 10:59〜11:00Z、2 つの窓 11:01:41Z・11:07:19Z）も合格だった（窓の θ の速さ 1.2569・1.2559 rad/s）

| 項目 | 結果 |
|---|---|
| 式 | 発光の色は 1 つのメンバーなので、1 回の観察の 3 成分は同じ時刻の値。各観察から θ を 0〜4π で求めると、式との残差は 2 つの窓の 40 回とも 1e-6 未満（許容 0.01） |
| 速さ | θ を観察の時刻で連続にして当てはめた傾きは 1.2612・1.2548 rad/s（2π × 0.2 = 1.2566 と 0.4% 以内。許容 5%）。各観察の θ と当てはめた直線の差は最大 0.19 rad（許容 0.4。観察の時刻のずれの分。平均の速さだけが合う曲がった式はここで外れる）。脈は 5 秒、色の一巡は 10 秒 |
| 変化の幅 | 脈は両方の窓で 0.500〜1.499 倍（式の 0.5〜1.5）。発光の輝度（線形の Y）は 0.36〜1.34。色は水色（E0）から紫（E1）まで（撮影 16.10） |
| 漂い | 6.1 分あけた 2 つの窓で、式・速さ・幅が同じ（時刻だけから計算し、前の値を足し込まない） |
| 時刻を止めた標本（`G03Frequency` = 0） | θ = 0 で発光は I × E0。`G03Intensity` 1・0.5・0 で (0.504, 0.99, 1.764)・(0.252, 0.495, 0.882)・0。5 は 2 に収まり (1.008, 1.98, 3.528)、−1 は 0 に収まる（差 1e-4 以内）。`G03Frequency` = −1 も 0 に収まり、P2 の発光で止まる |
| `G03Swing` = 0・−1 | 速さを戻した状態で、どちらも 3 回とも P2 の発光 (0.504, 0.99, 1.764) のまま一定（−1 は 0 に収まる） |
| `G03Swing` = 5 | 1 に収まる。動いている間の 9 回の観察が A = 1 の式に合う（残差 1e-6 未満、θ の速さ 1.2560 rad/s、直線との差 0.057 rad、脈 0.50〜1.46 倍）。収めていなければ脈が 1 ± 2.5 倍になり残差で外れる |
| `G03Frequency` の上限 | 実測していない。1 Hz では θ が観察の間隔（約 1.4 秒）に 8.8 rad 進み、連続にできない（4π の周期の中で 1.8π まで）。生成した `flux/P3FountainGlow.pg` の `F = if F0 < 0.0 then 0.0 else if F0 > 1.0 then 1.0 else F0` で収めている |
| ゆっくりの時刻（`G03Frequency` = 0.004 Hz） | 21.35 秒あけた 2 回の観察で θ が 0.5366 rad 進んだ（時刻からの予測 0.5365、差 0.0001 rad。許容 0.05）。時刻の項が止まっている・速さが違うグラフはここで外れる |
| 戻した値 | `G03Intensity` 1、`G03Frequency` 0.2、`G03Swing` 1（変える前と同じ。違えば問題にする） |
| モジュール | 両方の窓で `P3_Gimmicks/G03_Fountain/P3FountainGlow` と `G01_Dance/P3PlazaDance` がある |
| 利用者の確認 | 問題なし（16.10） |

- 生の観察は親の checkout の `tmp/w10a/g03_raw_windows_3.json`・`g03_param_raw_2.json`（直す前の検査の実行は `_1`。Git の対象外）。コミットした要約に ResoniteLink の ID は含めない（構造の照合は参照先を宣言のキーで書く）
- 最初の確認（10:54Z、1 つの窓 20 秒）も合格（14 回、残差 1.6e-7、1.2503 rad/s）
- 構造の観察は 1 回の `resoloop observe` に 64 個まで（`OBSERVE_LIMIT`。超えると `OBSERVE_LIMIT` のエラー）なので、MeshRenderer 110 個と材質 21 個を分けて読む

### 16.6 共有の材質（水以外の物と M02 の見た目）

- 構造の照合（`verify_g03.py` の各窓の `structure`）: 基準は G03 を足す前の宣言（同じ export の `model.apply.json`）。A の MeshRenderer 110 個すべての `Materials` を、基準の並びと順番まで比べた（水だけは専用の材質 1 つ）。G03 を足した後の宣言そのものも基準と比べ、違うのは水の MeshRenderer だけ。水の MeshRenderer は専用の材質 `p3_g03_wm` だけを指す。同じ `MAT_APL_MagicWater` を使っていた 7 個（`APL_Fountain_001_WaterAttach`、`APL_JackInteractionPedestal_001_EffectAttach`、`APL_PeriodicShowRig_001_Pylons`（4 つ目の材質）と `_GhostOrbitAttach_E`・`_N`・`_S`・`_W`）は元の材質を指したまま。元の材質の `AlbedoColor`・`EmissiveColor`・`Metallic`・`Smoothness` は宣言の値のまま（色は profile を考慮して線形の値で比べ、差 1e-5 以内）。専用の材質の `AlbedoColor`・`Metallic`・`Smoothness` は元の材質と同じ
- M02 の素材の宣言（`exports/p2_meshy/M02-20261031T164338Z/p2m.apply.json`）の diff は、最初・2 回目・保存の後のどれも変更 0（no-op 17）。M02 の点光源も変えていない
- 撮影（16.10）: G03Swing = 0（P2 と同じ発光）の `g03_fountain_swing0` と、動いている間の `g03_fountain`・`g03_fountain_later` で、水の輪だけが水色・明るい紫・淡い紫と変わり、M02・踊るカボチャ・灯り・手前の I03 の台座は同じ見た目
- 利用者の確認（確認事項 6）: ほかの物の見た目は変わっていない（16.10）

### 16.7 はみ出し

- G03 は発光の色だけを変え、メッシュ・Slot の位置・回転・拡縮を動かさない（専用の材質と MeshRenderer の付け替えだけ。駆動する Slot は無く、`managedFields` も足していない）。水の輪の外径は W02 の 3.64 m（台の外径 8.4 m の内側）のまま
- 光で通路が隠れる・まぶしいといった点も含めて、利用者の実機の確認で問題なし（16.10）

### 16.8 diff・apply・配備と、再適用・所有範囲

| 時刻（UTC） | 宣言・操作 | diff | apply・配備 |
|---|---|---|---|
| 10:44〜10:45 | 全 19 宣言（16.3。`<key>-20261101T104312Z`） | どれも変更 0・警告 0 | — |
| 10:52 | A（`A_plaza-20261101T105131Z`。専用の材質を足した） | 作成 1（水の Slot の `p3_g03_wm`）・更新 1（水の MeshRenderer の `Materials`。「one or more fields differ or depend on a new target」）・no-op 666 | Component の追加 1・更新 1（資産は変更なし 110、取り込み 0） |
| 10:53 | P3（`content/p3_gimmicks.json`） | 作成 4（Slot `G03_Fountain`、値の Component 3）・no-op 7 | Slot の作成 1・Component の追加 3 |
| 10:53 | ProtoFlux（`deploy_flux.py --manifest flux/p3_fountain_glow.flux.json`） | — | モジュール `P3FountainGlow` を `P3_Gimmicks/G03_Fountain` の下に作成（`action` create、drive の結び先 `p3_g03_wm.EmissiveColor` が解決） |
| 10:55 | 全 19 宣言の 2 回目の diff（動いている最中。A は `105131Z`） | どれも変更 0・警告 0（A は no-op 668、P3 は 11）。発光の値は差分にならない | — |
| 10:56 | A・P3 の 2 回目の apply、2 回目の配備 | — | apply はどれも書き込み 0（作成・更新・削除 0、資産の取り込み 0）。配備は `no-op`（「source and transitive dependency hashes match deploy state」、モジュールの Slot は同じ） |

- `--prune` は使っていない。削除・名前の変更・Component の作り直しは 0。MeshRenderer は作り直されず、`Materials` の要素の更新だけ
- 所有範囲: diff の対象は A の水の Slot の専用の材質と水の MeshRenderer、P3 の宣言の G03 の Slot と値だけ。world・B・C・D・E・`content/main.json`・Meshy の素材の宣言（M02 を含む）は、最初の diff から最後まで変更 0 で、apply していない。W10 の `flux/P3PlazaDance.pg`・`flux/p3_plaza_dance.flux.json` は `build_content.py` で作り直してもバイト単位で同じ（`git diff` が空）
- 数: W08 の root の下は Slot 939・Component 1,951 → Slot 1,013・Component 2,041（P3 の宣言 1・3、A の専用の材質 0・1、モジュール `P3FountainGlow` 73・86。`tmp/w10a/02_snapshot_after_*` と `03_g03_module_*`）
- apply・配備の記録は親の checkout の `tmp/w10a/`（`diff_first/`・`diff_second/`・`diff_g03_*`・`apply_g03_*`・`flux_g03_deploy_*`）

### 16.9 既存の検査

- 動いている状態（10:56〜10:58Z）で実行した。どれも直していない
- W10 の G01・G13（`modeling/p3_gimmicks/verify_live.py`、1 つの窓 30 秒）: 合格。G13 は 18.01°/s・上から見て反時計回り、G01 は 6 体とも範囲の中（記録は親の checkout の `tmp/w10a/p3_prev_live_1.json`。W10 の `live_checks.json`・`param_checks.json` は書き換えていない）
- W09R（`modeling/p2_meshy/verify_live.py`）: 全項目合格（M01〜M08 の 9 行、5 地区の数）。A の数の照合は、P3 が足した Component 13（W10 の中継 12 と、この子の専用の材質 1。`rest_pose.p3_additions` がキーの `p3_` で数える）を加えて実物 Slot 192・Component 417 と一致。結果は親の checkout の `tmp/w10a/p2_meshy_live_1.json`（`review/p2_meshy/live_checks.json` は W10 の記録のまま書き換えていない）
- W08（`modeling/p2_static/verify_live.py`）: W09R 以降の既知の 11 件のまま（項目は W10 の記録 11 章と同じ）。A の件は実物と宣言の Component がどちらも 1 増えた（416 / 344 → 417 / 345）だけで、P3・G03 による失敗は 0（`tmp/w10a/p2_static_checks_1.json`）。`review/p2_static/live_checks.json` は書き換えていない

### 16.10 撮影と実機の確認

- 撮影（`review/p3_gimmicks/`、1600×900、カメラは `content/p3_gimmicks.json` の `cameras`。11:00〜11:01Z）: `g03_fountain_swing0`（南東から。G03Swing = 0 で P2 と同じ発光。撮った後に 1 に戻した）、`g03_fountain`・`g03_fountain_later`（同じ位置から約 6 秒あけた 2 枚。水の輪が明るい紫と淡い紫）、`g03_water`・`g03_water_later`（南西から水の輪の近く）。どれも 39〜40 万バイトで、真っ黒な約 23 KB の画像は無い。`<名前>.scene.json` は作業ツリーの絶対パスを含むのでコミットせず、親の checkout の `tmp/w10a/capture_scenes/` に移した
- 利用者の確認（確認事項 6、デスクトップ、11:03Z ごろ。2 つの窓の間）: 噴水の水の変化、ほかの物（M02、I03 の台座、ショーの柱の目印、踊るカボチャ、回転床）の見た目が変わっていないこと、通路へのはみ出し・不自然な点が無いこと、resoloop がつながっていない間も変化が続くことの 4 点とも「どれも問題ない」
- 負荷（確認事項 8）: W08 の基準と同じ端末（デスクトップ一人）で 60 fps 前後（W10 と同じ）。足した物は A の Component 1（専用の材質）、P3 の宣言の Slot 1・Component 3、ProtoFlux のモジュールの Slot 73・Component 86（ノード）。粒子は無い。drive は各ユーザーが毎フレーム評価する（ネットワークの送信は無い）

### 16.11 保存（確認事項 4）と GPT のレビュー（確認事項 7）

- 保存は下の 16.11.1（GPT のレビューへの対応と実機の測り直しの後）
- GPT のレビュー: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（モデル gpt-6-astra）。対象は PR #63 の `97f5b73`。Resonite には接続させず、checkout も変更させていない。観点は、宣言と駆動の正しさ、W10 の行・検査・生成物、実測の検査、記録の正確さ、テストの採用基準の 5 つ。全文は PR #63 のコメント
- 結果: Major 1 件・Minor 3 件（どれも実測の検査の見逃し。配備・宣言・生成物・W10 への影響・記録の集計値・追加したテストは指摘なし）

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| 1 | Major | 照合の対象（同じ材質を使う MeshRenderer）を G03 を足した後の宣言から探すので、宣言でも水以外を付け替えると対象から消える。参照を含むかしか見ないので、`Pylons` の材質の並びが減っても合格する | 採用 | 水以外の見た目が変わった状態を合格と報告するため。基準を G03 を足す前の宣言（`model.apply.json`）にし、A の MeshRenderer 110 個すべての `Materials` を順番まで比べる。G03 を足した後の宣言も基準と比べる |
| 2 | Minor | 各観察の θ を直線に当てはめた傾きしか見ないので、平均の速さだけが合う曲がった時刻の式（θ = ωt + 0.8 sin ωt）も合格する | 採用 | 式・速さが正しいと誤って報告するため。各観察の θ と直線の差を 0.4 rad 以内とした（実測のばらつきは最大 0.13 rad） |
| 3 | Minor | 材質の色の比較が profile を捨てるので、同じ数値で sRGB → Linear に変わっても合格する | 採用 | 共有の材質の発光が変わった状態を合格と報告するため。色は profile を考慮して線形の値で比べる（宣言の配列は sRGB） |
| 4 | Minor | 範囲外の値を試すのが `G03Intensity` だけで、`G03Frequency`・`G03Swing` の範囲の収め方を実測していない | 一部採用 | `G03Frequency` −1（0 に収まる）、`G03Swing` −1（0 に収まる）・5（1 に収まる）を `--param-check` に足した。`G03Frequency` の上限は観察の間隔では測れないので、理由を 16.5 に書いた |

- テスト（S）: 指摘 1〜3 の守りに 3 件（`tests/test_p3_gimmicks_g03_verify.py`。曲がった時刻の式、共有の材質の値と profile の変化、宣言と観察の両方の付け替えと並びの減り）を足し、構造の照合の 1 件を新しい基準の形に直した（全 8 件）。指摘 4 は `--param-check` の実機の流れの中の判定で、守りそのもの（`check_frozen`・`check_samples` に収めた値を渡す）は既存のテストが見るので足していない（D）。どれも守りを外す変異でそのテストだけが失敗することを確かめた
- 直した検査で実機を測り直し、すべて合格した（16.5・16.6）

#### 16.11.1 保存

- GPT のレビューへの対応と実機の測り直し（16.5）の後に、エージェントの依頼で利用者がワールドを 1 回保存した（2026-11-01 11:36Z より前。保存の操作の種類は記録していない）
- 保存の後（11:37〜11:38Z）に全 19 宣言（W08 の 7 つ・Meshy の 11 個・P3）の diff を取り、どれも変更 0・警告 0（`tmp/w10a/diff_aftersave/`）。水の発光は変わり続けていた（専用の材質の `EmissiveColor` が 3 秒あけて別の値）。保存・再読込の後に専用の材質・モジュール・HMC_P3 の値が残って動くかは P4（開き直していない）

### 16.12 Resonite で未確認の項目

- 2 人以上での同期、途中参加（P4）。この子の確認は、共有の時刻と同期する値だけから計算する drive の仕組みの説明と、単独の確認まで
- 保存・再読込の後に、専用の材質・ProtoFlux のモジュール・HMC_P3 の値が残って動くか（P4。開き直していない）
- VR での見え方（発光の明るさ・まぶしさ）、メモリの負荷
