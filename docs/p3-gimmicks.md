# P3 自動ギミック（W10、Issue #56）

自動ギミックを Resonite で動かす方式と、最初の 2 種類 **G13 メリーゴーラウンドの床の回転**・**G01 小カボチャのダンス**の記録。残りの先行 8 種類（Spec §8 の G03・G05・G06・G09・G11・G15・G18・G20）の子は、この文書の 2・4 章の手順と `handoff/W10.md` を使う。

- W10-A（#58）の **G03 噴水の水と光の周期変化**は 16 章（方式の追記: 共有の材質を写した専用の材質と、発光の色の drive）
- W10-B（#59）の **G05 おばけの浮遊**・**G06 屋敷の扉の開閉**は 17 章（方式の追記: B 用の 1 つのモジュール、回転だけを駆動する蝶番の中継と `managedFields`、開閉の往復の式）
- W10-C（#60）の **G09 大釜の攪拌と泡・煙**・**G11 魔女の巡回**は 18 章（方式の追記: C 用の 1 つのモジュール、素材の宣言の親（仮モデルの root）を動かす、8 点を通る三角補間の経路、液面の専用の材質、PhotonDust の粒子）
- W10-D（#61）の **G15 おばけ列車の周回**は 19 章（方式の追記: D 用の 1 つのモジュール、進んだ距離から弧の位置を決めるスタジアム型の経路、先頭車と客車の弧の差、進んだ距離 ÷ 半径で回す車輪。W05 の旗 1 つの位置の修正）
- W10-E（#62）の **G18 キノコの発光**・**G20 時計の針と鐘**は 20 章（方式の追記: E 用の 1 つのモジュール、共有の材質を個体ごとに写した発光、見る人の端末のローカル時刻で進む針、節目からの時刻の関数で一度だけ揺れる鐘。これで先行 10 種類が揃った。先行 10 種類のまとめは 20.10）

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。apply・配備したのはこのセッションだけ。GPT のレビューは PR で 1 回（14 章）
- 着手前の確認事項: W08 #41 の回答（issuecomment-6545243021）をそのまま使う（#56 の本文。起票したセッションの判断）
- Spec §5 の P3 は「GPT が主担当、Claude が確認」だが、この子は 2026-11-01 の利用者の決定で Claude Code が実装し GPT がレビューした（§5 の「個別タスクで交代できる」）

## 1. 適用先と版

- ワールド「Halloween Magical Carnival」（ResoniteLink のポートは利用者が伝えた値。恒久の値として書かない）。W08 の root `Root/HalloweenMagicalCarnival` の下だけを変えた
- Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Flux-SDK 1.9.0、Blender 5.0.1
- ProtoFlux のビルドに使った Resonite の DLL: 共有の managed data の 2026.9.18.82（`resoloop doctor` の managed data の項目は、`RESONITE_MANAGED_DATA_PATH` をコマンドだけに付けて pass。3,320 ノード）。実行中の Resonite（2026.10.29.1239）より古いが、ビルド・配備・実行は問題なかった（6 章）
- 着手時の W08 の root: Slot 745・Component 1,684（W09R-E の完了時と同じ。利用者が手で変えた所は無い）。スナップショットと diff・apply・配備の報告は親の checkout の `tmp/w10/`（Git の対象外）
- W10-A（#58、2026-11-01）も同じ版（Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Flux-SDK 1.9.0・managed data 2026.9.18.82、Blender 5.0.1）。記録は親の checkout の `tmp/w10a/`
- W10-B（#59、2026-11-01）も同じ版。記録は親の checkout の `tmp/w10b/`
- W10-C（#60、2026-11-01）も同じ版。記録は親の checkout の `tmp/w10c/`
- W10-D（#61、2026-11-02）も同じ版（Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Flux-SDK 1.9.0・managed data 2026.9.18.82、Blender 5.0.1）。記録は親の checkout の `tmp/w10d/`
- W10-E（#62、2026-11-03）も同じ版（Resonite 2026.10.29.1239、ResoniteLink 0.13.1.0、resoloop 0.2.0、Flux-SDK 1.9.0・managed data 2026.9.18.82、Blender 5.0.1）。記録は親の checkout の `tmp/w10e/`。この日は resoloop の observe が 1 回 3〜8 秒と遅かった（W10-D は 1.5〜5 秒。ほとんどが resoloop の CPU の時間で、Resonite の中で 1 つの Component を読む間隔も 約 0.15 秒と W10-D の 0.115 秒より長い）
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

## 17. W10-B（#59）G05 おばけの浮遊・G06 屋敷の扉の開閉

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。claim `agent-claims/issue-59`（11:41:58Z）。apply・配備したのはこのセッションだけ。GPT のレビューは PR で 1 回（17.11）
- 着手前の確認事項: W08 #41 の回答（issuecomment-6545243021）をそのまま使う（#59 の本文。利用者の変更なし）
- 対象: B の `BMN_FloatingGhost_001`・`_002` の `_FloatPivot`（G05）と、`BMN_MansionDoubleDoor_001_HingeLeft`・`_HingeRight`（G06）。部品・範囲は W03 の `layout/areas/B_mansion.json` の `Hero_or_Gimmick.gimmicks`。おばけの体と手提げのランタン、扉の葉と枠、玄関ホール、M03 の素材の宣言は変えていない
- 記録は親の checkout の `tmp/w10b/`（Git の対象外）

### 17.1 方式の追記

| 項目 | 決めたこと | 理由 |
|---|---|---|
| 駆動の作り方 | G05・G06 とも ProtoFlux（`flux/P3MansionMotion.pg`。B 用の 1 つのモジュール、worldState は B の state、配備先は `P3_Gimmicks/G05_G06_Mansion`）。B の宣言の各 Slot に中継の `ValueMultiDriver` を置き、その `Value` を drive する（W10 の G01 と同じ） | G05 は上下と揺れを 1 つの位相から決め、2 体の位相をずらし、I04（W11）が値を変えられる必要がある（G01 と同じ型）。G06 は「閉じたまま → 開く → 開いたまま → 閉じる」の往復で、`Spinner` のような連続回転の Component では作れない。Flux の drive は Slot のメンバーを結べないので中継が要る（2.1） |
| `managedFields` | おばけの `_FloatPivot` は `["scale"]`（位置と回転を駆動）、扉の蝶番は `["position", "scale"]`（回転だけを駆動。位置は W09R-B が M03 の開口の蝶番の線へ動かした値で、静的な apply が管理し続ける） | B を再 apply しても扉が閉じた形に戻らない（`handoff/W09R-B.md`）。17.8 で、扉が動いている最中の B の 2 回目の diff が変更 0 |
| 中継 | おばけは位置（`ValueMultiDriver<float3>`）と回転（`<floatQ>`）の 2 つ、扉は回転の 1 つ。キーは `p3_g05_<member>_<Slot のキー>`・`p3_g06_rotation_<Slot のキー>`（`district.relay_key` にギミックの接頭辞の引数を足した。G01 の `p3_g01_` のキーは変わらない）。`Value` の初期値は宣言の基準姿勢 | モジュールが無い・止まっているときは基準姿勢（閉じた扉）に止まる。キーが `p3_` で始まるので、W09R の数の検査が P3 の追加として数える（`rest_pose.p3_additions`） |
| G05 の式 | θ_i = 2π f t + s φ_i、上下 = I (0.125 + 0.225 sin θ_i) m（範囲 −0.10〜+0.35 m）、揺れ = I × 20° × sin(θ_i / 2)（Blender の Z まわり。Resonite の Y まわりは符号が逆）。φ は 001 が 0°、002 が 180° | 上下と揺れを 1 つの位相から決め、揺れは上下の半分の速さで、同じ姿勢の繰り返しに見えにくい。時刻だけから計算し、前の値を足し込まないので漂わない（Spec §8）。φ は W03 のデータに無いので決めた（2 体は 9 m 離れていて、上下が逆向きに見える） |
| G05 の上下の範囲 | W03 の −0.35〜+0.35 m の中の −0.10〜+0.35 m（`gimmicks.G05_BOB_RANGE_M`。`g05()` が W03 の範囲の中かを確かめる） | Blender の確認（17.2）で、001 は下げ幅が −0.18 m より下だと、手提げのランタン `_LanternCharm` が 1.1 m 隣のベンチ `BMN_CMN_Bench_001` の背もたれ（上端 z 2.45）に入る。−0.10 でベンチとの隙間は 8 cm 以上。上は W03 の範囲いっぱい（Spec §8「P1 の可動範囲を守る」の中） |
| G06 の式 | θ = 2π (f t + p)、c = (1 − cos θ) / 2、x = clamp01((c − 0.25) / 0.5)、開き = I × 85° × x² (3 − 2x)。左は Blender の +Z まわり（Resonite の Y まわりの負）、右は −Z まわり。どちらも内開き | `c` は時刻から決まる 0〜1 の往復。0.25 未満で閉じたまま、0.75 を超えて開いたまま、その間を smoothstep で動くので、動き始めと止まりが滑らか。既定の 24 秒の周期で、閉じたまま 8 秒 → 4 秒で開く → 開いたまま 8 秒 → 4 秒で閉じる（最大の角速度 約 32°/s）。左右は同じ角度で、対称に開く |
| 外から変えられる値 | `HMC_P3/G05Intensity`（既定 1、0〜1）・`G05Frequency`（既定 0.25 Hz、0〜1。揺れはその半分）・`G05PhaseSpread`（既定 1、0〜1。0 で 2 体がそろう）、`HMC_P3/G06Intensity`（既定 1、0〜1。開く角度の割合）・`G06Frequency`（既定 1/24 Hz、0〜0.2）・`G06Phase`（既定 0、0〜1。周期の中の位置のずらし）。`P3_Gimmicks` の `DynamicValueVariable<float>`（キー `g05_amp`・`g05_freq`・`g05_phase`・`g06_amp`・`g06_freq`・`g06_phase`、`initialFields`）。モジュールの中で範囲に収める | I04（W11。屋敷の鐘で庭のおばけが一斉に挨拶）は `G05PhaseSpread` = 0 で 2 体をそろえ、`G05Intensity`・`G05Frequency` で大きさ・速さを変えられる。範囲に収めるので、ショーが大きな値を書いても W03 の可動範囲（とベンチを避けた下げ幅）を超えない。定期ショーが扉を開けたいときは `G06Phase`（と `G06Frequency` = 0）で開いた位置に止められる |
| 同期と途中参加 | G01 と同じ。`WorldTimeDouble` と同期する HMC_P3 の値だけから計算する drive で、同期する書き込み・インパルスは無い | Spec §10.3。途中参加のユーザーも同じ時刻なら同じ姿勢を見る。2 人以上での確認は P4 |
| 当たり判定（G06） | 付けない（利用者の決定。#59 の issuecomment-6557581300）。扉の葉は W08 の方針（`motion_roots` の下に当たり判定を付けない）で P2 から当たり判定が無く、M03 の開口は切り抜かれているので、開閉に関係なく入口を通れる | 見えない壁・閉じる扉の押し出し・行き止まりの玄関ホールへの閉じ込めが起きない。閉じた扉はすり抜けられる（おばけ屋敷らしさとして許容）。Spec §11「動く装飾には不要な当たり判定を付けない」。おばけも P2 から当たり判定は無い |

採らなかった方法:

- **G06 を標準の Component で作る**（`TimeSineDriver` で回転の角度を往復させる）: 開いたまま・閉じたままの時間を入れられず、外開きの側へも同じ角度だけ振れる（sin の負の側）。駆動の Component は B の宣言に置く必要があり、B の Slot から HMC_P3 の空間に届かないので外から値を変えられない（16.1 と同じ理由）
- **扉の葉に当たり判定を付けて一緒に動かす**・**入口を固定の当たり判定で塞ぐ**: 利用者に選択肢を示して、付けない案に決まった（閉じる扉が人を押す・ホールに閉じ込める、または開いた扉の所に見えない壁が残る）
- **扉を開くときに持ち上げる**（扉の下端と玄関ホールの床・絨毯の重なりを避ける。17.2）: 利用者の決定で採らず、W03 への要望にした。蝶番の位置も駆動することになり、開いた扉の下に隙間が見える
- **G05 の上下を W03 の −0.35〜+0.35 m いっぱいに使う**: 001 のランタンがベンチの背もたれに入る（17.2）
- **G05・G06 を別のモジュールにする**: どちらも B の state を worldState にするので、1 つにまとめると配備と deploy state が 1 つで済む。W11 が片方だけを変えるときも HMC_P3 の値で足りる

### 17.2 Blender で確かめた可動範囲（保存しない一時的なスクリプト）

B の `.blend` に M03 の `.blend` の `M03_HauntedMansion_001` を、仮モデル `BMN_MansionPlaceholder_001` と同じ変換で置き（Resonite と同じ置き方。`REPLACEMENTS` の M03 は位置・回転 0）、扉を 0〜85° を 5° ごと、おばけを上下 −0.35〜+0.35 m・揺れ ±20° で動かして、ほかのメッシュとの三角形の交差を数えた（`mathutils.bvhtree`）。スクリプトと結果は親の checkout の `tmp/w10b/blender_sweep/`（Git の対象外）、要点は #59 の issuecomment-6557581300。

| 対象 | 結果 | 扱い |
|---|---|---|
| G06 の扉の下端と玄関ホールの床・絨毯 | 扉の下端 z 1.870（M03 のポーチの床と同じ）が、ホールの床（上面 1.89）に 2 cm、赤い絨毯（上面 1.92、x 0.0575〜1.3575）に開閉の途中で最大 5 cm 入る。全開（85°）・全閉では絨毯に掛からない（85° の左の葉は x −0.171〜0.051、右は 1.364〜1.586） | 利用者の決定で形は変えず、W03 への要望（handoff 6.3） |
| G06 の扉と W03 の枠・M03 の壁 | 蝶番の側の縁（厚さ 10 cm の葉の半分）が、W03 の枠の柱（蝶番の線の外 13 cm、壁の面の前後 14 cm）に開く角度とともに最大 5 cm 入る。M03 の壁（単面、y 39.952）と交わるのも蝶番の近くだけ | 柱の中に隠れて見えない（利用者に説明済み） |
| G06 の扉どうし・ほかの物 | 左右の葉は交わらない。ホールの壁・通路・ポーチへ出る物は無い（開いた葉は扉の面より奥だけ） | — |
| G05 の 001 とベンチ | 下げ幅 −0.18 m 以下で、手提げのランタンがベンチ `BMN_CMN_Bench_001`（x −4.09〜−3.52、y 27.92〜29.68、上端 z 2.45）の背もたれに入る。−0.17 で隙間 1 cm、−0.10 で 8 cm、0 で 8 cm | 上下の範囲を −0.10〜+0.35 m にした（17.1） |
| G05 の 002・ほかの物 | 交わる物は無い。どちらも体の最も低い所は地面（z 1.5）より 0.55 m 以上上 | — |

### 17.3 Reflection・Flux-SDK で確かめた物

- `resoloop flux node describe`（managed data 2026.9.18.82、3,320 ノード）: `FromEuler_floatQ`（`Angles: float3`。度で使う。W10 の G01 の傾きと同じ）、`Clamp01_Float`、`Cos_Double`。`Sin_Double`・`Pack_Float3`・`DynamicVariableValueInput<float>`・`WorldTimeDouble` は W10 と同じ
- `resoloop flux check flux/P3MansionMotion.pg`: コンパイル成功（ヒント 6 件だけ。`DynamicVariableValueInput` の代わりに `~input<T>` が使えるという案内）
- 中継の型（`ValueMultiDriver<float3>`・`<floatQ>`）と `DynamicValueVariable<float>`・`DynamicVariableSpace` は W10 で確かめた物と同じ。B の diff（実行時の Reflection の検証を含む）は警告 0

### 17.4 保存の後の最初の diff

何も変える前（11:57〜11:58Z）に、今の `main` のまま 6 キーを export した宣言（`exports/p2_static/<key>-20261101T115441Z`。W10・W10-A の駆動は入っている）で、全 19 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M07・M08・`content/p3_gimmicks.json`）の diff を取った。どれも変更 0・警告 0（no-op 29・184・668・333・318・379・780・16・15・15・17・16・18・15・15・15・16・19・11。W10-A の完了時と同じ数）。資産の作り直し・重複は無い。W10 の `P3PlazaDance`（`P3_Gimmicks/G01_Dance`）と W10-A の `P3FountainGlow`（`P3_Gimmicks/G03_Fountain`）は配備されたまま。W08 の root の下は Slot 1,013・Component 2,041（W10-A の完了時と同じ。利用者が手で変えた所は無い）

- 新しい worktree の準備: 全キーの `.blend` の作り直し（11:42〜11:45Z、約 3 分。D・E は `--arg=--no-render`）、Blender の確認（17.2）のための M03 の `.blend`（約 1 分）、Git の外の `p2_bundles/<M>-<UTC>/` を同じ名前の `exports/p2_meshy/` へ写した（コミット済みの記録は上書きせず、`SHA256SUMS` が全 9 つ一致）
- apply の前のスナップショット: 親の checkout の `tmp/w10b/01_snapshot_before_20261101T115851Z`（W08 の root 全体。最初の diff の後、最初の apply まで書き込みは無い）

### 17.5 手順

4 章の手順に、次を足す（`T` は親の checkout の `tmp/w10b/`）。

```sh
uv run python modeling/p2_static/export_p2.py --url "$URL" --key B_mansion   # おばけと蝶番に managedFields と中継を足した p2.apply.json と p3_drivers.json
resoloop diff exports/p2_static/B_mansion-<UTC>/p2.apply.json --state "$ST/p2_B_mansion.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply exports/p2_static/B_mansion-<UTC>/p2.apply.json --state "$ST/p2_B_mansion.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/build_content.py   # B の state から Slot のキーを、B の最新の export から基準の位置を読み、flux/P3MansionMotion.pg・flux/p3_mansion_motion.flux.json も作る
resoloop diff content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/deploy_flux.py --url "$URL" --manifest flux/p3_mansion_motion.flux.json --report "$T/<新しいファイル>"
# 同じ diff・apply・配備をもう 1 回行い、変更 0・書き込み 0・配備 no-op を確かめる
uv run python modeling/p3_gimmicks/verify_b.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g05_g06_live_checks.json --windows 2 --gap 300 --duration 50
uv run python modeling/p3_gimmicks/verify_b.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g05_g06_param_checks.json --param-check
```

- `build_content.py` は B の state に `_FloatPivot`・蝶番の Slot が無いと止まり（先に B を apply する）、B の最新の export でおばけ・蝶番の基準の回転が単位でないと止まる（式は基準の回転を単位として組んでいる）
- G05・G06 の deploy state は親の checkout の `.resoloop/flux-state/p3_mansion_motion.json`
- `verify_b.py` の窓は 50 秒（扉の 24 秒の周期で、半分開く角度を 3〜4 回通る）。`--param-check` は HMC_P3 の G05・G06 の値を変えて測り、最後に元に戻ったかを確かめる（途中でおばけが止まり、扉が開いた位置で止まるので、確認中に見ている人がいれば伝える）

### 17.6 G05 の結果

GPT のレビュー（17.11）で直した検査での実行: `verify_b.py --windows 2 --gap 300 --duration 50`（12:46:59Z と 12:53:20Z の 2 つの窓。`review/p3_gimmicks/g05_g06_live_checks.json`）と `--param-check`（12:43〜12:47Z。`g05_g06_param_checks.json`）。どれも問題 0。直す前の検査での実行（2 つの窓 12:16:48Z・12:22:51Z、`--param-check` 12:12〜12:16Z）も合格だった

| 項目 | 結果 |
|---|---|
| 上下 | 001 は −0.0999〜+0.3499 m・−0.0998〜+0.3500 m、002 は −0.0947〜+0.3471 m・−0.1000〜+0.3500 m（窓ごと）。−0.10〜+0.35 m の中（許容 2 mm）。W03 の −0.35〜+0.35 m を超えない |
| 揺れ | 2 体とも −20.000〜+20.000°。±20° の中（許容 0.2°）。回転は Y 軸まわりだけ（X・Z 成分 0.001 以内） |
| 水平のずれ | 1 mm 以内（位置は基準から上下だけ） |
| 位相 | 時刻を止めた標本（`G05Frequency` = 0）で、`G05PhaseSpread` 1 のとき 001 は θ = 0（上下 0.125 m・揺れ 0°）、002 は θ = π（0.125 m・20°）、0.5 で 002 が θ = π/2（0.35 m・14.142°）、0 で 2 体とも θ = 0。中継の値と `_FloatPivot` の Slot そのものの両方が式と一致（差 0.5 mm・0.05° 以内） |
| 時刻の基準 | ゆっくりの時刻（`G05Frequency` = 0.004 Hz）で 22.15 秒あけた 2 回の観察で、002 の θ/2 が 15.969° 進んだ（時刻からの予測 15.945°、差 0.024°。許容 2°）。最初の観察で 2 体の θ/2 の差が式（s (φ1 − φ2) / 2 = −90°）と 0.168° 差。測った各観察で、揺れから求めた θ の式の上下と観察した上下の差は 0.6 mm 以内（許容 5 mm。GPT のレビューの指摘 M-1 で足した確認）。001 は 2 回目の観察の揺れが小さく（|sin(θ/2)| < 0.2）θ/2 を求められなかった。GPT のレビューの前の 2 回の実行（12:08〜12:11Z・12:12〜12:16Z）は 001 だけが測れ、差 0.016° |
| 漂い | 6.4 分あけた 2 つの窓の最初に、時刻を止めた標本（`G05Frequency`・`G06Frequency` = 0。001 は θ = 0、002 は θ = π）を `_FloatPivot` の Slot そのもので取って速さを戻し、窓の間で比べた。同じ位相の上下・揺れの差は 2 体とも 0.00001 m・0.0001° 未満（許容 1 cm・0.5°。#59 の受け入れ基準「同じ位相の位置の差が 1 cm 以内」。GPT のレビューの指摘 M-2 で足した確認）。範囲・軸・構造も 2 つの窓で同じ（時刻だけから計算し、前の値を足し込まない） |
| 外から変えられる値 | `G05Intensity` 0.5 で上下 −0.049〜+0.174 m・揺れ 9.8° 以内（範囲の半分）、0 で 2 体とも基準姿勢。範囲の外の値: `G05Intensity` 5 → 1、−1 → 0、`G05PhaseSpread` 1.5 → 1（収めないと 002 が θ = 1.5π の姿勢になる）、`G05Frequency` −1 → 0（止まる）で、どれも式の値と一致。`G05Frequency` の上限（1 Hz）は観察の間隔では測れない（`P3MansionMotion.pg` の `GF = if GF0 < 0.0 then 0.0 else if GF0 > 1.0 then 1.0 else GF0` で収めている） |
| 戻した値 | `G05Intensity` 1、`G05Frequency` 0.25、`G05PhaseSpread` 1（変える前と同じ。違えば問題にする） |
| 構造 | 両方の窓の最初と最後で、`_FloatPivot` の下の `_GhostBody`・`_LanternCharm` が宣言と同じパス・ローカルの変換（差 0）。中継 4 つは有効で、`Drives` は自分の `_FloatPivot` の `Position`・`Rotation` を指す |
| 包絡 | 動く範囲の水平の半径は 2 体とも 0.655 m で、W03 の配置の余裕 `clearance_radius_m` 1.0 m の内側。中央の通路（`Excl_B_CentralSightlineCorridor`、x −2〜2）に入る点は 0。最も低い所は z 2.05 m（001）・2.25 m（002）。ベンチとの隙間は 17.2 |

### 17.7 G06 の結果

| 項目 | 結果 |
|---|---|
| 開く角度 | 左右とも 0.0〜85.0°（内開き。2 つの窓）。0〜85° の中（許容 0.2°）。回転は Y 軸まわりだけ |
| 向き | 左（`_HingeLeft`）は Resonite の Y まわりの負、右は正に回る（Blender の +Z・−Z まわり = 上から見て、左は反時計回り、右は時計回りで、どちらも建物の奥へ開く）。時刻を止めた標本で、開きの符号を逆にしたグラフはここで外れる |
| 対称 | 時刻を止めた標本で左右が同じ角度（周期の位置 0・0.2・0.25・0.5 で 0・8.117・42.5・85.0°、式と差 0.05° 以内）。動いている間の左右の差は最大 3.9°・3.7°（1 回の observe の中で 2 つの中継を読む時刻のずれ。開閉の最大の速さ 約 32°/s。許容 10°） |
| 速さ | 半分開いた角度（42.5°）を通る時刻の間隔が 11.906・12.011・12.183 秒、11.841・12.158・12.040 秒（周期の半分 12 秒と 0.18 秒以内。許容 1.5 秒）。2 つの窓の最初の時刻を止めた標本（周期の位置 0）で、左右とも 0°（窓の間の差 0）。開く・閉じるが交互。既定の 24 秒の周期で、閉じたまま 8 秒 → 4 秒で開く → 開いたまま 8 秒 → 4 秒で閉じる |
| 時刻を止めた標本 | `G06Frequency` = 0 で、周期の位置 0（閉）・0.2（8.117°）・0.25（42.5°）・0.5（85°）、`G06Intensity` 0.5（42.5°）のとき、中継の値と蝶番の Slot そのものの回転が式と一致し、蝶番の位置は宣言のまま（差 0.1 mm 以内） |
| 外から変えられる値 | 範囲の外の値: `G06Intensity` 5 → 1（全開の位置で 85°。収めないと 425°）、−1 → 0（閉じる）、`G06Phase` 1.5 → 1（閉じる。収めないと θ = 3π で全開）、`G06Frequency` −1 → 0（止まる）で、どれも式の値と一致。`G06Frequency` の上限（0.2 Hz）は観察の間隔では測れない（`DF = if DF0 < 0.0 then 0.0 else if DF0 > 0.2 then 0.2 else DF0`） |
| 戻した値 | `G06Intensity` 1、`G06Frequency` 0.041666668（1/24）、`G06Phase` 0（変える前と同じ） |
| 構造 | 両方の窓の最初と最後で、扉の枠・葉が宣言と同じパス・ローカルの変換（差 0）、蝶番の位置と拡縮も宣言のまま（M03 の開口の蝶番の線）。中継 2 つは有効で、`Drives` は自分の蝶番の `Rotation` を指す |
| B の再 apply | 扉が動いている最中の B の 2 回目の diff は変更 0（no-op 339）、2 回目の apply は書き込み 0。その後の窓でも扉は 0〜85° の往復を続けた（`managedFields` に回転を入れていないので、静的な apply が閉じた形に戻さない） |
| 包絡 | 葉が 0〜85° で動く範囲（バンドルのメッシュ、5° ごと）は、W03 の扉の振れる範囲 `Excl_B_DoorSwingAndPorch`（x −0.9775〜2.2225、y 37.4〜41.2）の中で、閉じた形の前面（z 39.86、ノッカー）よりポーチ側に出ない。玄関ホールの床・絨毯・枠の柱との重なりは 17.2 |
| 当たり判定 | 付けない（17.1。利用者の決定）。扉の葉には P2 から当たり判定が無く、W08 の宣言のまま。扉の枠（`_Frame`）とホールの部屋の `MeshCollider` は静的なまま |

### 17.8 diff・apply・配備と、再適用・所有範囲

| 時刻（UTC） | 宣言・操作 | diff | apply・配備 |
|---|---|---|---|
| 11:57〜11:58 | 全 19 宣言（17.4。`<key>-20261101T115441Z`） | どれも変更 0・警告 0 | — |
| 11:59〜12:00 | B（`B_mansion-20261101T115934Z`。おばけと蝶番に `managedFields` と中継） | 作成 6（おばけ 2 体の `ValueMultiDriver<float3>`・`<floatQ>`、蝶番 2 つの `<floatQ>`）・更新 0・no-op 333。`managedFields` の追加は今の値と同じで変更にならない | Component の追加 6（資産は変更なし 45、取り込み 0） |
| 12:00 | P3（`content/p3_gimmicks.json`） | 作成 7（Slot `G05_G06_Mansion`、値の Component 6）・no-op 11 | Slot の作成 1・Component の追加 6 |
| 12:01 | ProtoFlux（`deploy_flux.py --manifest flux/p3_mansion_motion.flux.json`） | — | モジュール `P3MansionMotion` を `P3_Gimmicks/G05_G06_Mansion` の下に作成（`action` create、drive の結び先 6 個がすべて解決） |
| 12:02 | B・P3 の 2 回目の diff（動いている最中） | どちらも変更 0・警告 0（B は no-op 339、P3 は 18）。おばけの位置・回転と扉の回転は差分にならない | — |
| 12:02 | B・P3 の 2 回目の apply、2 回目の配備 | — | apply はどれも書き込み 0（作成・更新・削除 0、資産の取り込み 0）。配備は `no-op`（「source and transitive dependency hashes match deploy state」） |
| 12:29〜12:30 | 全 19 宣言の 2 回目の diff（動いている最中。B は `115934Z`） | どれも変更 0・警告 0（no-op は 17.4 と同じで、B は 339、P3 は 18） | — |

- `--prune` は使っていない。削除・名前の変更・Component の作り直しは 0
- 所有範囲: diff の対象は B のおばけ 2 体の `_FloatPivot` と扉の蝶番 2 つの中継、P3 の宣言の G05・G06 の値と `G05_G06_Mansion` だけ。world・A・C・D・E・`content/main.json`・Meshy の素材の宣言（M03 を含む）は、最初の diff から最後まで変更 0 で、apply していない。A・D をこの子のコードで export し直した `p2.apply.json`・`p3_drivers.json` は `main` の export（`115441Z`）とバイト単位で同じ（中継のキーの関数にギミックの接頭辞を足しても、G01 のキーは変わらない）。W10・W10-A の `flux/P3PlazaDance.pg`・`p3_plaza_dance.flux.json`・`P3FountainGlow.pg`・`p3_fountain_glow.flux.json` は `build_content.py` で作り直してもバイト単位で同じ（`git diff` が空）
- 数: W08 の root の下は Slot 1,013・Component 2,041 → Slot 1,149・Component 2,227（P3 の宣言 1・6、B の中継 0・6、モジュール `P3MansionMotion` 135・174。親の checkout の `tmp/w10b/02_snapshot_after_*`）。2 回目の apply で増えない
- apply・配備の記録は親の checkout の `tmp/w10b/`（`diff_first/`・`diff_second/`・`diff_b*`・`apply_b*`・`diff_p3_*`・`apply_p3_*`・`flux_b_*`）

### 17.9 既存の検査

- 動いている状態（12:24〜12:27Z）で実行した。どれも直していない（`rest_pose.py` は `gimmicks.driven_slots()` に B を足しただけで、B の駆動される項目も基準姿勢に戻す）
- W10 の G01・G13（`modeling/p3_gimmicks/verify_live.py`、1 つの窓 30 秒）: 合格。G13 は 17.996°/s・上から見て反時計回り、G01 は 6 体とも範囲の中、包絡の問題 0（親の checkout の `tmp/w10b/p3_prev_live_1.json`。W10 の `live_checks.json`・`param_checks.json` は書き換えていない）
- W10-A の G03（`modeling/p3_gimmicks/verify_g03.py`、1 つの窓 30 秒）: 合格（`tmp/w10b/g03_prev_live_1.json`。`g03_live_checks.json`・`g03_param_checks.json` は書き換えていない）
- W09R（`modeling/p2_meshy/verify_live.py`）: 全項目合格（M01〜M08 の 9 行、5 地区の数）。B の数の照合は、P3 が足した Component 6（中継。`rest_pose.p3_additions` がキーの `p3_` で数える）を加えて実物 Slot 94・Component 213 と一致。基準姿勢への置き換えは 11 個（A の Body 6、D の TurnRoot、B のおばけ 2 体・蝶番 2 つ）。結果は親の checkout の `tmp/w10b/p2_meshy_live_1.json`（`review/p2_meshy/live_checks.json` は W10 の記録のまま書き換えていない）
- W08（`modeling/p2_static/verify_live.py`）: W09R 以降の既知の 11 件のまま（項目は 11 章と同じ）。B の件は実物と宣言の Component がどちらも 6 増えた（207 / 169 → 213 / 175）だけで、P3・G05・G06 による失敗は 0（`tmp/w10b/p2_static_checks_1.json`）。置き換えを外して同じ観察から測ると、カボチャ 5 体・座席 4 基とおばけ 2 体の 11 件が増える（`tmp/w10b/p2_static_checks_without_rest.json`。この観察の時刻ではカボチャ 006 はたまたま 1 cm 以内だった。扉の蝶番はこの検査が位置だけを比べるので、回転では増えない）。`review/p2_static/live_checks.json` は書き換えていない

### 17.10 撮影と実機の確認

- 撮影（`review/p3_gimmicks/`、1600×900、カメラは `content/p3_gimmicks.json` の `cameras`。12:28〜12:29Z）: `g05_ghosts`・`g05_ghosts_later`（中庭の石畳の南から 2 体のおばけ。約 7 秒あけて高さと向きが違う）、`g05_ghost_bench`（001 と隣のベンチ）、`g06_doors_closed`・`g06_doors_half`・`g06_doors_open`（ポーチの段の前から。`G06Frequency` = 0 にして周期の位置 0・0.25・0.5 で止め、撮った後に戻した）、`g06_doors_inside_open`（玄関ホールの奥から、全開の扉の内側）。どれも 11〜25 万バイトで、真っ黒な約 23 KB の画像は無い。利用者のアバター・名札は写っていない。`<名前>.scene.json` は作業ツリーの絶対パスを含むのでコミットせず、親の checkout の `tmp/w10b/capture_scenes/` に移した。一時カメラ `ResoLoop_Test_Capture_*` は残っていない（`resoloop find`）
- 撮影で見えたこと: 扉は左右対称に建物の奥へ開き、全開ではホールの両側の壁際に収まる。半開の撮影では、扉の下端が絨毯の縁に掛かる所が見える（17.2）。おばけは墓地の上で、001 はベンチの背もたれの後ろに浮く
- 利用者の確認（確認事項 6、デスクトップ。作業の途中で利用者が席を外したので、戻った後の 13:0xZ ごろ）: G05 のおばけの漂い方、G06 の扉の開閉（向き・速さ・角度）と当たり判定（無いので閉じていても通れる）、通路・玄関ホールへのはみ出し、resoloop が接続していない間も動き続けることを見てもらい、「問題なし」
- 負荷（確認事項 8）: W08 の基準と同じ端末（デスクトップ一人）で 60 fps（W10・W10-A と同じ）。足した物は B の Component 6（中継）、P3 の宣言の Slot 1・Component 6、ProtoFlux のモジュールの Slot 135・Component 174（ノード）。粒子は無い。drive は各ユーザーが毎フレーム評価する（ネットワークの送信は無い）
- 常駐しない: resoloop はコマンドごとに接続して終わる。2 つの窓の間の 5 分（接続していない）も動き続け、2 つ目の窓で同じ範囲・速さ（17.6・17.7。再接続後の観察）

### 17.11 GPT のレビュー（確認事項 7）と保存（確認事項 4）

- GPT のレビュー: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（モデル gpt-6-astra）。対象は PR #64 の `e775c30`。Resonite には接続させず、checkout も変更させていない。観点は、宣言と駆動の正しさ、実測の検査、既存の検査への影響、記録の正確さ、テストの採用基準の 5 つ。全文は PR #64 のコメント
- 結果: Major 2 件・Minor 2 件（宣言・駆動・生成物・既存の検査への影響は指摘なし）

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| M-1 | Major | ゆっくりの時刻の確認は、上下から cos(θ/2) の符号だけを使うので、上下だけが 2 倍の速さの式（揺れは正しい）でも θ/2 の進みと位相差が合って合格する | 採用 | G05 の速さが正しいと誤って報告するため。測った各観察で、揺れから求めた θ の式の上下と観察した上下が 5 mm 以内かを見る（`check_clock` の `lift_consistency`） |
| M-2 | Major | #59 の受け入れ基準「時間を空けた 2 回の実測で同じ位相の位置の差が 1 cm 以内」を判定していない。窓ごとの範囲と幅だけでは、上下の中心が 2 cm ずれても合格する | 採用 | 漂っていないと誤って報告するため。各窓の最初に時刻を止めた標本（`G05Frequency`・`G06Frequency` = 0）を Slot そのもので取って速さを戻し、窓の間で比べる（上下 1 cm・揺れと扉の開き 0.5° 以内。`frozen_probe`・`check_drift`） |
| m-1 | Minor | handoff の当たり判定・はみ出しを、実機の確認が残っているのに「満たす」としている | 採用 | 「構造・包絡は確認済み、実機の確認待ち」に直し、利用者の確認の後に更新する |
| m-2 | Minor | `rest_pose` のテストに足した B の全可動 Slot の復元の確認は、A・D の同じ置き換えの確認と重なる（D） | 採用 | B の fixture と、蝶番の位置のずれを残す確認（S）は残し、復元の網羅の assert を外した |

- テスト（S）: 指摘 M-1・M-2 の守りに、正しい状態で通る例と外れる例を 1 つずつ足した（`tests/test_p3_gimmicks_b_verify.py` は全 9 件）。守りを外す変異でそのテストだけが失敗することを確かめた
- 直した検査で実機を測り直した（17.6・17.7）

#### 17.11.1 保存

- GPT のレビューへの対応と実機の測り直し、利用者の実機の確認の後に、エージェントの依頼で利用者がワールドを 1 回保存した（2026-11-01 13:07Z より前。保存の操作の種類は記録していない）
- 保存の後（13:07〜13:08Z）に全 19 宣言（W08 の 7 つ・Meshy の 11 個・P3）の diff を取り、どれも変更 0・警告 0（no-op は 17.8 と同じ。親の checkout の `tmp/w10b/diff_aftersave/`）。おばけと扉は動き続けていた（中継の値が 4 秒ごとに別の値、扉は開いた位置の前後）。保存・再読込の後に中継・モジュール・HMC_P3 の値が残って動くかは P4（開き直していない）

### 17.12 Resonite で未確認の項目

- 2 人以上での同期、途中参加（P4）。この子の確認は、共有の時刻と同期する値だけから計算する drive の仕組みの説明と、単独の確認まで
- 保存・再読込の後に、中継・ProtoFlux のモジュール・HMC_P3 の値が残って動くか（P4。開き直していない）
- VR での見え方、開閉する扉とアバターのすれ違い（当たり判定は無いので押されない）、メモリの負荷

## 18. W10-C（#60）G09 大釜の攪拌と泡・煙・G11 魔女の巡回

- 担当: Claude Code（Opus 5.5）、2026-11-01（UTC）。claim `agent-claims/issue-60`（13:16:57Z）。apply・配備したのはこのセッションだけ。GPT のレビューは PR で 1 回（18.11）
- 着手前の確認事項: W08 #41 の回答（issuecomment-6545243021）をそのまま使う（#60 の本文。利用者の指示は「推奨案で行けるところまで」）
- 対象: C の大釜 `CCD_MagicCauldron_001` の攪拌棒の Pivot `_StirRodPivot`、液面 `_Liquid`、泡・煙の取付位置 `_BubbleAttach`・`_SmokeAttach`（G09）。魔女の仮モデル `CCD_M08_FlyingWitchProxy_001`（M08 の素材の宣言の親）と巡回路の `CCD_WitchPatrolLoop_001_CarrierPivot`（G11）。部品・範囲は W04 の `layout/areas/C_candy.json` の `Hero_or_Gimmick`（G09・G11）と `assets/manifest/C_candy.json`。大釜の本体・巡回路の帯・M08 の素材の宣言と点光源 2 つは変えていない
- 記録は親の checkout の `tmp/w10c/`（Git の対象外）

### 18.1 方式の追記

| 項目 | 決めたこと | 理由 |
|---|---|---|
| 駆動の作り方 | G09・G11 とも ProtoFlux（`flux/P3CandyStreet.pg`。C 用の 1 つのモジュール、worldState は C の state、配備先は `P3_Gimmicks/G09_G11_Candy`）。C の宣言の中継（`ValueMultiDriver`）の `Value`、液面の専用の材質の色、粒子の量と色を drive する | 攪拌の速さ（`HMC_P3/G09StirFrequency`）は I02 のショー（W11）が変えられる値で、C の Slot の `Spinner` からは HMC_P3 の空間に届かない（16.1 と同じ理由）。揺れ（W04 の `wobble_tilt_deg` ±12°）は回転と同じ位相から決めるので、`Spinner` だけでは作れない。G11 は経路の位置と向きの計算が要る。どちらも C の state を worldState にするので 1 つにまとめた |
| G11 で動かす Slot | 魔女の仮モデルの root（`CCD_M08_FlyingWitchProxy_001`。位置と回転）と、巡回路の `CarrierPivot`（W04 の G11 の `motion_root`。位置と回転）を同じ姿勢で動かす。M08 と点光源 2 つは仮モデルの子なので一緒に動く | M08 の素材の宣言の親のパス（`C_candy/CCD_M08_FlyingWitchProxy_001`）を変えない（#60 の範囲）。仮モデルは CarrierPivot の子ではない（C の宣言で兄弟の asset root）ので、CarrierPivot だけを動かしても魔女は動かない。CarrierPivot を動かさないと、その子の取付位置の目印（星の光の材質の小さな八面体）が巡回の点 0 の空に残る |
| `managedFields` | 攪拌棒の Pivot は `["position", "scale"]`（回転だけを駆動。G06 の蝶番と同じ）、魔女の仮モデルと CarrierPivot は `["scale"]`（位置と回転を駆動） | C を再 apply しても駆動された姿勢を基準姿勢に戻さない（18.7 で動いている最中の 2 回目の diff が変更 0） |
| 中継 | 攪拌棒は回転の 1 つ（`p3_g09_rotation_<Slot のキー>`）、魔女と CarrierPivot は位置と回転の 2 つずつ（`p3_g11_<member>_<Slot のキー>`）。`Value` の初期値は宣言の基準姿勢（巡回の点 0、攪拌の角度 0） | モジュールが無い・止まっているときは基準姿勢に止まる。キーが `p3_` で始まるので、W09R の数の検査が P3 の追加として数える |
| G09 の式 | φ = 2π (f t + p)、揺れ w = 12° × sin 2φ、回転 = Y(−φ) × Z(w)（四元数の積を成分で組む: (sy sz, sy cz, cy sz, cy cz)、sy = sin(−φ/2)・cy = cos(φ/2)・sz = sin(w/2)・cz = cos(w/2)） | W04 の攪拌は Blender の +Z まわり（上から見て反時計回り = Resonite の Y まわりの負）。揺れは攪拌棒のローカル Z（Blender のローカル Y。棒が傾いている面に垂直な軸）まわりで、1 周に 2 回大きく傾くので、櫂が楕円を描くように見える。角度は時刻 t が大きくなっても float の精度を失わないよう、double の sin・cos の半角から四元数を作る（`FromEuler_floatQ` に度で渡すと、時刻が大きいと角度の精度が落ちる）。φ = 0 で基準姿勢 |
| G09 の液面の色 | 液面の 1 つ目の材質（P2 のエメラルド）を写した専用の `PBS_Metallic`（キー `p3_g09_lm`）を C の宣言で液面の Slot に足し、液面の MeshRenderer の 1 つ目の材質だけを付け替える（`district.add_g09_effects`）。`AlbedoColor` = 色、`EmissiveColor` = 色 × K（K = 1.9646。P2 の発光 / 色の 3 成分の平均）。色は `HMC_P3/G09LiquidColor`（`DynamicValueVariable<colorX>`、既定は P2 の液面の色 sRGB (0.4614, 0.9822, 0.7484, 1)） | エメラルドの材質は液面のほかに 3 つの MeshRenderer（泡の取付位置の目印、I02 の台座、北東の薬の屋台）が使う。共有の材質を変えると、それらも I02 の色に変わる（16.1 と同じ）。2 つ目のマゼンタ（液面の盛り上がり 2 つ）は変えない。I02 は色のプリセット（`#2EFF88` など）をそのまま書けばよく、明るさはモジュールが決める。`Mul_ColorX_Float` は sRGB の値の成分をそのまま掛け、profile を保つ（18.5） |
| G09 の泡・煙 | PhotonDust の粒子。取付位置の Slot に Component だけを足す（Slot は足さない）: `ParticleSystem`・`ParticleStyle`・`MeshParticleRenderer`（小さな `IcoSphereMesh` を白の `UnlitMaterial`（Alpha）で描く）・`CircleEmitter`（取付位置の水平の円から上へ）・寿命・速さ・大きさ・大きさの変化・色の変化（`ColorOverLifetimeStartEnd`）・位置の計算（`PositionSimulatorModule`）、煙は乱流（`SimplexTurbulentForce`）も。泡は毎秒 6 個・寿命 0.6〜1.2 秒・最大 16 個、煙は毎秒 3 個・寿命 2.5〜3.5 秒・最大 24 個。量は `Rate`、色は液面の色 × 1.6（泡、透明度 0.9 → 0.6）・× 1.1（煙、0.45 → 0）を ProtoFlux が drive する | Spec §11「大量の粒子を控える」。2 つ合わせて最大 40 個。粒子の色は材質の色にかかり、透明度も効く（2026-11-01 に `ResoLoop_Test_W10C_Particles` で試して確かめた。18.2）。I02 が液面の色を変えると泡と煙も同じ色になる |
| G11 の経路 | 8 点（W04 の `patrol_loop_waypoints_m`）を等間隔の角度 2πk/8 で通る三角補間（x・y・z を cos nθ・sin nθ（n = 0〜4）の和にする。`gimmicks.trig_coefficients`）。高さは W04 の 9.8〜10.5 m に収める。θ = 2π (f t + p) | 閉じた滑らかな曲線で 8 点をすべて通り、向きの変化が単調（左右に揺れない）。θ = 2πk/8 で巡回の点 k なので、時刻を止めた標本で配置データの値とそのまま照合できる。補間した高さは点 1・7 の近くで最大 10.538 m になるので 10.5 m に収める（収めた区間は高さが平らになるだけで、点はすべて範囲の中） |
| G11 の向き | ψ = atan2(dx/dθ, dy/dθ)（Blender の x・y の微分）、回転 = Y(ψ)（(0, sin ψ/2, 0, cos ψ/2)） | 魔女の正面（W09R-C の M08 の正面、仮モデルのローカル +Y = Resonite の +Z）が進む向きを向く。θ = 0 で ψ = 0（北）なので、基準姿勢（巡回の点 0、回転 0）と一致する。高さの変化（最大 0.3 m / 7 m）は小さいので、上下の傾きは付けない |
| 既定の速さ | 攪拌は 6 秒で 1 周（1/6 Hz）、巡回は 45 秒で 1 周（1/45 Hz。経路 61.1 m、平均 1.36 m/s、点の間の速さは平均の 0.86〜1.21 倍） | W04 のデータに速さが無いので、この子で決めた（鍋をゆっくりかき混ぜる・魔女が見上げて追える速さ） |
| 外から変えられる値 | `HMC_P3/G09StirFrequency`（既定 1/6、0〜1 回/秒）・`G09StirPhase`（0、0〜1。回転の位置）・`G09Bubbles`（1、0〜2。泡の量の倍率）・`G09Smoke`（1、0〜2）・`G09LiquidColor`（colorX）、`HMC_P3/G11Frequency`（1/45、0〜0.1 周/秒）・`G11Phase`（0、0〜1。k/8 で巡回の点 k）。`P3_Gimmicks` の `DynamicValueVariable`（キー `g09_freq`・`g09_phase`・`g09_bub`・`g09_smk`・`g09_color`・`g11_freq`・`g11_phase`、`initialFields`）。モジュールの中で範囲に収める | I02（W11）は `G09LiquidColor` を書けば液面・泡・煙の色が変わる。定期ショーは `G11Phase`（と `G11Frequency` = 0）で魔女を決まった点に止められ、`G09Bubbles`・`G09Smoke` で盛り上げられる。範囲に収めるので、大きな値でも粒子は最大の数（16・24）を超えない |
| 同期と途中参加 | G01 と同じ。`WorldTimeDouble` と同期する HMC_P3 の値だけから計算する drive で、同期する書き込み・インパルスは無い。粒子の放出は各ユーザーの画面で行われ、粒子の位置は同期しない（放出の量と色は共有の値から決まる） | Spec §10.3。途中参加のユーザーも同じ時刻なら同じ攪拌棒の角度・魔女の位置を見る。泡・煙の 1 粒ずつの位置は人ごとに違うが、演出として問題にならない。2 人以上での確認は P4 |
| 当たり判定 | 付けない。魔女（M08）は P2 から当たり判定が無い（W09R-C）。攪拌棒・粒子にも付けない（粒子の `PositionSimulatorModule` の `Collisions` は既定のまま） | Spec §11「動く装飾には不要な当たり判定を付けない」。大釜の本体の `MeshCollider` は静的なまま |

採らなかった方法:

- **攪拌棒を `Spinner` で回す**（`handoff/W10.md` 6.2 の案）: 攪拌の速さを HMC_P3 から変えられない（C の Slot から HMC_P3 の空間に届かない）。`_speed` を ProtoFlux で drive すれば変えられるが、`Spinner` は角度を速さ × 時刻で決めるので速さを変えた瞬間に角度が跳び、揺れは別に要る
- **M08 を CarrierPivot の子へ移す**: M08 の素材の宣言の親のパスが変わる（#60 の「M08 の素材の宣言の親のパスを変えない」）
- **魔女の仮モデルだけを動かす**: CarrierPivot の子の取付位置の目印が巡回の点 0 の空に残る
- **8 点を直線で結ぶ（巡回路の帯と同じ八角形）**: 点ごとに向きが 45° 跳ぶ。角を丸めるには区間ごとの式を `if` でつなぐ必要があり、ノードが増える
- **点を増やした三角補間（帯の上を 16〜48 点で通る）**: 帯からのずれは 0.12〜0.31 m に減るが、向きが左右に揺れる（向きの変化の符号が 1,228〜1,602 回 / 4,000 回逆になる）
- **平滑化した級数（Lanczos・Fejér の重みで 6〜16 次）**: 揺れは消えるが、巡回の点から 0.4〜2.1 m 外れる（帯の目印の点を通らない）
- **ビルボードの粒子（`BillboardParticleRenderer`）**: Reflection で探した手続きのテクスチャ（`GradientStripTexture`・`NoiseTexture`・`GridTexture` など）に丸い形が無く、四角い板になる。小さな球のメッシュの粒子にした
- **大釜の造形を直して液面を見せる**: 18.2 の 4 のとおり液面は大釜の縁の蓋に隠れているが、地区の造形のやり直しは #60 の範囲外。W04 への要望にした（handoff 6.3）

### 18.2 Blender・Reflection・試しの Slot で確かめたこと

1. **Reflection（`resoloop type search`・`type describe`）**: PhotonDust の `ParticleSystem`（`MaxParticleCount`・`Style`）、`ParticleStyle`（`Renderer`・`Modules`）、`MeshParticleRenderer`（`Mesh`・`Material`）、`CircleEmitter`（`Rate`・`Radius`・`CircleAlignment` XY/XZ/YZ・`DirectionMode` Fixed など）、`LifetimeRangeInitializer`・`SpeedRangeInitializer`・`UniformSizeRangeInitializer`（`MinValue`・`MaxValue`）、`UniformSizeOverLifetimeStartEnd`、`ColorOverLifetimeStartEnd`（`StartColor`・`EndColor` は colorX）、`SimplexTurbulentForce`、`PositionSimulatorModule`、`IcoSphereMesh`、`UnlitMaterial`（`BlendMode` Alpha・`ZWrite` Off）。旧来の粒子（`ParticleSpray`）と `Legacy*Adapter` は使わない
2. **Flux-SDK（`resoloop flux node describe`、managed data 2026.9.18.82、3,320 ノード）**: `Atan2_Double`（Y, X）、`Pack_FloatQ`（X, Y, Z, W）、`Mul_ColorX_Float`、`ColorXSetAlpha`、`DynamicVariableValueInput<colorX>`。四元数どうしの積のノードは無い（`Mul_FloatQ_Float3` はベクトルの回転だけ）ので、攪拌棒の回転は成分の式で組んだ。`resoloop flux check flux/P3CandyStreet.pg` はヒント 7 件だけでコンパイル成功
3. **試しの Slot**（`Root/HalloweenMagicalCarnival/ResoLoop_Test_W10C_Particles`。大釜の位置に泡と煙を試し、撮影してから ID を確かめて `slot delete` で消した。`resoloop find` で残っていない）: 粒子は `PositionSimulatorModule` が無いと生まれた位置から動かない。`ColorOverLifetimeStartEnd` の色（試しは白 → 透明な赤）は `UnlitMaterial` の色にかかり、透明度も効く。`ParticleSystemMetadata` の `ParticleCount` は observe で値が読めない（kind empty）ので使わない
4. **大釜の液面は大釜の蓋の下に隠れている**（W04 の造形）: `modeling/C_candy/build.py` の `_add_frustum_z` は円錐台の上と下に面を張るので、大釜の縁（z 1.14〜1.28）の上面 z 1.28 が蓋になり、液面（z 1.12〜1.26。盛り上がりを含む）は外から見えない（撮影 `g09_cauldron` でも蓋の上に攪拌棒が刺さって見える）。液面の色の変化は材質の値で確かめ（18.5）、見た目の色は泡・煙で見える。W04 への要望（handoff 6.3）
5. **Blender の確かめ**（保存しない一時的なスクリプト。親の checkout の `tmp/w10c/blender_sweep/sweep_c.py` と `sweep_c.json`）: overview の `.blend` に M04・M08 の `.blend` を仮モデルと同じ変換で置き、M08 を経路に沿って 720 の位置・向きに動かして、高さ 6 m を超えるほかのメッシュとの最短距離と三角形の交差を数えた。3 m 以内に来るのは巡回路自身の星の光の帯（`_GuideRing`。8 点を結ぶ帯と点の目印。720 の位置のうち 302 で交わる）と CarrierPivot の子の取付位置の目印（動かすので一緒に動く）だけ。M04（上端 7.628 m）・キャンディのアーチ（上端 9.5 m）・浮島（上端 10.5 m）は 3 m より遠い。魔女の最も低い所は 9.19 m。攪拌棒は φ を 10° ごと・揺れ ±12° で回して、縁の上面の高さで軸から 6 cm 以内（縁の内側 0.72 m）、櫂の上端は最大 z 0.996（液面 1.12 の下）、最も低い所は 0.578（大釜の腹の底 0.20 の上）
6. **巡回路の帯と経路のずれ**: 帯は 8 点を直線で結ぶが、経路は滑らかな曲線なので、点と点の間で帯から外へ最大 0.95 m ふくらむ（点 0 と点 1 の間の中ほどなど）。点の目印はすべて通る（18.6）

### 18.3 保存の後の最初の diff

何も変える前（13:23〜13:25Z）に、今の `main` のまま 6 キーを export した宣言（`exports/p2_static/<key>-20261101T132345Z`。W10・W10-A・W10-B の駆動は入っている）で、全 19 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M07・M08・`content/p3_gimmicks.json`）の diff を取った。どれも変更 0・警告 0（no-op 29・184・668・339・318・379・780・16・15・15・17・16・18・15・15・15・16・19・18。W10-B の完了時と同じ数）。資産の作り直し・重複は無い。W10 の `P3PlazaDance`（`P3_Gimmicks/G01_Dance`）、W10-A の `P3FountainGlow`（`G03_Fountain`）、W10-B の `P3MansionMotion`（`G05_G06_Mansion`）は配備されたまま。W08 の root の下は Slot 1,149・Component 2,227（W10-B の完了時と同じ。利用者が手で変えた所は無い）

- 新しい worktree の準備: 全キーの `.blend` の作り直し（13:17〜13:20Z、約 3 分。D・E は `--arg=--no-render`）、Blender の確かめ（18.2）のための M04・M08 の `.blend`（約 3 分）と overview の `.blend`（`--arg=--no-render`）、Git の外の `p2_bundles/<M>-<UTC>/` を同じ名前の `exports/p2_meshy/` へ写した（コミット済みの記録は上書きせず、`SHA256SUMS` が全 9 つ一致）。overview のビルドが書き換えた `assets/manifest.json`・`review/overview/checks.json`（W07 の所有）と確認画像は戻した
- apply の前のスナップショット: 親の checkout の `tmp/w10c/01_snapshot_before_20261101T132551Z`（W08 の root 全体。最初の diff の後、最初の apply まで書き込みは無い。試しの Slot（18.2 の 3）はスナップショットの後に作り、消した）

### 18.4 手順

4 章の手順に、次を足す（`T` は親の checkout の `tmp/w10c/`）。

```sh
uv run python modeling/p2_static/export_p2.py --url "$URL" --key C_candy   # 攪拌棒・魔女・CarrierPivot の managedFields と中継、液面の専用の材質、泡・煙の粒子を足した p2.apply.json と p3_drivers.json
resoloop diff exports/p2_static/C_candy-<UTC>/p2.apply.json --state "$ST/p2_C_candy.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply exports/p2_static/C_candy-<UTC>/p2.apply.json --state "$ST/p2_C_candy.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/build_content.py   # C の state から Slot のキーを、C の最新の export から基準の位置と液面の色を読み、flux/P3CandyStreet.pg・flux/p3_candy_street.flux.json も作る
resoloop diff content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/deploy_flux.py --url "$URL" --manifest flux/p3_candy_street.flux.json --report "$T/<新しいファイル>"
# 同じ diff・apply・配備をもう 1 回行い、変更 0・書き込み 0・配備 no-op を確かめる
uv run python modeling/p3_gimmicks/verify_c.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g09_g11_live_checks.json --windows 2 --gap 300
uv run python modeling/p3_gimmicks/verify_c.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g09_g11_param_checks.json --param-check
```

- `build_content.py` は C の state に攪拌棒の Pivot・魔女の仮モデル・CarrierPivot の Slot が無いと止まり（先に C を apply する）、C の最新の export でそれらの基準の回転が単位でない・魔女と CarrierPivot の基準の位置が巡回の点 0 でない・液面の専用の材質が無いと止まる
- G09・G11 の deploy state は親の checkout の `.resoloop/flux-state/p3_candy_street.json`
- `verify_c.py` の窓は、攪拌棒だけを 20 秒（1 回 約 1.5 秒。60°/s の回転を連続にできる間隔）、全部の駆動の値を 40 秒（1 回 約 3 秒）観察する。窓の最初の時刻を止めた標本と `--param-check` は HMC_P3 の値を変えて測り、最後に元に戻ったかを確かめる（途中で攪拌棒と魔女が止まり、液面がマゼンタになるので、確認中に見ている人がいれば伝える）

### 18.5 G09 の結果

GPT のレビュー（18.11）で直した検査での実行: `verify_c.py --windows 2 --gap 300`（14:34:11Z と 14:41:25Z の 2 つの窓。7.2 分あけた。`review/p3_gimmicks/g09_g11_live_checks.json`）と `--param-check`（14:43〜14:47Z。`g09_g11_param_checks.json`）。どれも問題 0。直す前の検査での実行（2 つの窓 14:08:09Z・14:15:17Z、`--param-check` 14:17〜14:21Z）と試しの実行（1 つの窓 13:44Z、`--param-check` 13:47〜13:50Z）も合格だった

| 項目 | 結果 |
|---|---|
| 回る向きと速さ | 上から見て反時計回り（Resonite の Y まわりの負。攪拌の角度 φ を 13・15 回の観察で連続にした傾きが正）。59.628・60.173°/s（6 秒で 1 周 = 60°/s と 0.7% 以内。許容 5%）。隣の観察の間は最大 133.0°（連続にできる 150° 未満）。当てはめた直線からの各観察の差は最大 12.59°・4.39°（許容 15°。observe の時刻の見積もりのずれの分。1 つ目の窓は observe が遅い回があった） |
| 回転の形と揺れ | 各観察の回転が Y まわり × ローカル Z まわりの形（残差 1e-3 未満）で、揺れが 12° × sin 2φ と 0.1° 以内で一致。揺れの範囲は −11.646〜+11.992°（±12° の中） |
| 時刻を止めた標本 | `G09StirFrequency` = 0 で `G09StirPhase` 0・0.125・0.3・0.6・0.9 のとき、中継の値と攪拌棒の Pivot の Slot そのものの回転が式の四元数と 1e-7 以内で一致。窓ごとの標本（φ = 0.125 周）も同じ |
| 大釜の縁・液面から外れない（包絡） | 攪拌棒を 5° ごと・揺れ込みで回したとき、縁の上面（z 1.28）より下の部分は軸から最大 0.392 m（液面の半径 0.70 m の内側）、最も低い所は z 0.578（大釜の腹の底 0.20 の上）、`clear_radius_m` 1.4 m の外に出る点 0。Blender の確かめ（18.2 の 5）でも縁の高さで軸から 6 cm 以内、櫂は液面の下 |
| 泡・煙 | 泡は毎秒 6 個・寿命 0.6〜1.2 秒・最大 16 個（大きさ 0.05〜0.10 m が 0.6 → 1.4 倍）、煙は毎秒 3 個・寿命 2.5〜3.5 秒・最大 24 個（0.16〜0.24 m が 0.6 → 2.2 倍、乱流 0.3）。`Rate` は両方の窓の全観察で 6・3（`G09Bubbles`・`G09Smoke` = 1）。撮影 `g09_cauldron`・`_later` で泡と煙が出ている |
| 色の値を変えると液面と煙の色が変わる | `G09LiquidColor` を I02 の Magenta（#F53DC7）にすると、液面の専用の材質の `AlbedoColor` が (0.9608, 0.2392, 0.7804, 1)、`EmissiveColor` が × 1.9646、泡・煙の `StartColor`・`EndColor` が × 1.6・× 1.1（透明度 0.9・0.6、0.45・0）に変わり、式と 1e-3 以内で一致。撮影 `g09_cauldron_magenta` で泡・煙がマゼンタ。Magenta にしている間も、元の材質の色と、元の材質を使う 8 つの MeshRenderer の参照は変わらない。元の色（sRGB (0.4614, 0.9822, 0.7484, 1)）に戻した。液面そのものは大釜の蓋に隠れて見えない（18.2 の 4） |
| 液面の材質（共有の材質） | 液面の MeshRenderer の材質は [`p3_g09_lm`, マゼンタ]。G09 を足す前の宣言で液面の元の材質（エメラルド・マゼンタ）を使うほかの 7 つ（北東の薬の屋台、泡の取付位置の目印、I02 の台座と水晶玉、攪拌棒、キャンディの製造機、南東のガムボールの屋台）は元の材質のまま、元の材質の `AlbedoColor`・`EmissiveColor` も宣言の値のまま（1e-4 以内。両方の窓と Magenta の間）。P2 の発光との差は 0.4% 以内（`Mul_ColorX_Float` は sRGB の値の成分をそのまま掛け、profile は sRGB のまま） |
| 範囲の外の値 | `G09StirPhase` 1.5 → 1（φ = 2π で基準姿勢。収めないと 180° 回った姿勢）、`G09StirFrequency` −1 → 0（止まる）、`G09Bubbles` 5 → 2（`Rate` 12）・−1 → 0、`G09Smoke` −1 → 0・5 → 2（`Rate` 6）。どれも式の値と一致 |
| ゆっくりの時刻 | `G09StirFrequency` = 0.004 Hz で 23.90 秒あけた 2 回の観察で φ が 34.492° 進んだ（時刻からの予測 34.415°。許容 1°） |
| 戻した値 | `G09StirFrequency` 0.16666667、`G09StirPhase` 0、`G09Bubbles` 1、`G09Smoke` 1、`G09LiquidColor` 元の色（変える前と同じ。違えば問題にする） |
| 構造 | 両方の窓の最初と最後で、大釜の子孫（本体・液面・取付位置・攪拌棒）が宣言と同じパス・ローカルの変換（攪拌棒の Pivot は位置と拡縮）。中継は有効で、`Drives` は攪拌棒の Pivot の `Rotation` を指す |

### 18.6 G11 の結果

| 項目 | 結果 |
|---|---|
| 経路 | 両方の窓の全観察（11 回ずつ）で、魔女の仮モデルと CarrierPivot（巡回路の root の原点を足した位置）が経路の上（ずれ 5e-6 m 未満。許容 1 cm）。θ は 1 つ目の窓で 25.6〜355.7°、2 つ目で 10.8〜342.2°（ほぼ 1 周を観察） |
| 巡回の点 | 時刻を止めた標本（`G11Frequency` = 0）で `G11Phase` = k/8（k = 0〜7）のとき、魔女と CarrierPivot が配置データの巡回の点 k と 1e-6 m 以内（中継の値と Slot そのものの両方）。点の間（0.0625）も式と一致 |
| 向き | 動いている間、正面の向きと経路の接線の差は最大 1.19°・1.34°（位置と回転は別の中継で、1 回の observe の中で読む時刻がずれる。許容 3°）、Y 軸まわりだけ。隣の観察の間に進んだ向き（弦）と正面の向きの差は最大 4.29°・5.07°（許容 8°）。時刻を止めた標本では 0.0° |
| 高さ | 9.8017〜10.5 m・9.8287〜10.5 m（W04 の 9.8〜10.5 m の中。許容 1 mm）。M08 の最も低い所は 9.21 m（バンドルのメッシュ）、W04 の上空の通り道 `EX_C_SkyPatrolCorridor` の下端 9.0 m より上で、平面でも外に出る点 0 |
| 屋根・塔に当たらない | M04 の外接箱（上端 7.628 m）から最短 2.465 m（バンドルのメッシュ）。Blender の確かめ（18.2 の 5）で、3 m 以内に来るのは巡回路自身の帯と CarrierPivot の目印だけ |
| 1 周の時間と速さ | 45 秒（`G11Frequency` 1/45）。θ の速さは魔女 8.040・7.990°/s、CarrierPivot 8.040・7.992°/s（8.0°/s と 0.5% 以内）。直線からの各観察の差は最大 2.14°・0.76°（CarrierPivot 2.21°・0.72°。許容 4°）。同じ観察の中の魔女と CarrierPivot の θ の差は −2.13〜−1.72°（CarrierPivot を後に読む分。許容 4°）。経路 61.1 m、平均 1.36 m/s |
| 漂わない | 2 つの窓の最初の時刻を止めた標本（`G11Phase` 0.25 = 巡回の点 2）の位置の差 0.0 m（許容 1 cm）。各窓の θ − 360 f t（t は壁の時計）の円の平均は魔女 1.878°・1.716°（差 0.162°）、CarrierPivot 3.674°・3.516°（差 0.158°。許容 6°）で、θ が時刻から決まり、5 分の間に漂っていない |
| 範囲の外の値 | `G11Phase` 1.5 → 1（巡回の点 0。収めないと点 4）、`G11Frequency` −1 → 0（止まる）。式の値と一致 |
| ゆっくりの時刻 | `G11Frequency` = 0.004 Hz で θ が 34.491° 進んだ（予測 34.415°） |
| 戻した値 | `G11Frequency` 0.022222223、`G11Phase` 0 |
| M08 と光源 | 両方の窓の最初と最後で、仮モデルの下の `M08`（素材の宣言の root）と `M08_FlyingWitch_001`・`M08_FrontGlow`・`M08_UnderGlow` が宣言と同じパス・ローカルの変換（差 1e-4 未満）。M08 の素材の宣言の diff は最後まで変更 0（18.7） |
| 構造 | 巡回路の子孫（帯・CarrierPivot・取付位置）と仮モデルが宣言と同じパス（CarrierPivot・仮モデルは拡縮）。中継 4 つは有効で、`Drives` は自分の Slot の `Position`・`Rotation` を指す |

### 18.7 diff・apply・配備と、再適用・所有範囲

| 時刻（UTC） | 宣言・操作 | diff | apply・配備 |
|---|---|---|---|
| 13:23〜13:25 | 全 19 宣言（18.3。`<key>-20261101T132345Z`） | どれも変更 0・警告 0 | — |
| 13:39 | C（`C_candy-20261101T133857Z`。攪拌棒・魔女・CarrierPivot に `managedFields` と中継、液面の専用の材質、泡・煙の粒子） | 作成 31（中継 5、液面の材質 1、泡 12・煙 13）・更新 1（液面の MeshRenderer の `Materials` の 1 つ目）・no-op 317・警告 0。`managedFields` の追加は今の値と同じで変更にならない | Component の追加 31・更新 1（資産は変更なし 42、取り込み 0） |
| 13:41 | P3（`content/p3_gimmicks.json`） | 作成 8（Slot `G09_G11_Candy`、値の Component 7）・no-op 18 | Slot の作成 1・Component の追加 7 |
| 13:41 | ProtoFlux（`deploy_flux.py --manifest flux/p3_candy_street.flux.json`） | — | モジュール `P3CandyStreet` を `P3_Gimmicks/G09_G11_Candy` の下に作成（drive の結び先 13 個がすべて解決） |
| 13:54 | C・P3 の 2 回目の diff（動いている最中） | どちらも変更 0・警告 0（C は no-op 349、P3 は 26）。攪拌棒の回転、魔女・CarrierPivot の位置と回転、液面と粒子の色・量は差分にならない | — |
| 13:54 | C・P3 の 2 回目の apply、2 回目の配備 | — | apply はどれも書き込み 0（作成・更新・削除 0、資産の取り込み 0）。配備は `no-op`（「source and transitive dependency hashes match deploy state」） |
| 14:13 | 全 19 宣言の 2 回目の diff（動いている最中。C は `133857Z`） | どれも変更 0・警告 0（no-op は 18.3 と同じで、C は 349、P3 は 26）。M08 の素材の宣言も変更 0（魔女は親の仮モデルの動きについて動く） | — |

- `--prune` は使っていない。削除・名前の変更・Component の作り直しは 0
- 所有範囲: diff の対象は C の攪拌棒の Pivot・魔女の仮モデル・CarrierPivot の中継、液面の専用の材質と液面の MeshRenderer の 1 つ目の材質、泡・煙の取付位置の粒子、P3 の宣言の G09・G11 の値と `G09_G11_Candy` だけ。world・A・B・D・E・`content/main.json`・Meshy の素材の宣言（M04・M08 を含む）は、最初の diff から最後まで変更 0 で、apply していない。world・A・B・D・E をこの子のコードで export し直した `p2.apply.json`・`p3_drivers.json` は `main` の export（`132345Z`）とバイト単位で同じ（比べた後に消した）。W10・W10-A・W10-B の `flux/P3PlazaDance.pg`・`p3_plaza_dance.flux.json`・`P3FountainGlow.pg`・`p3_fountain_glow.flux.json`・`P3MansionMotion.pg`・`p3_mansion_motion.flux.json` は `build_content.py` で作り直してもバイト単位で同じ（`git diff` が空）
- 数: W08 の root の下は Slot 1,149・Component 2,227 → Slot 1,372・Component 2,556（P3 の宣言 1・7、C の中継・材質・粒子 0・31、モジュール `P3CandyStreet` 222・291。親の checkout の `tmp/w10c/02_snapshot_after_*`）。2 回目の apply で増えない
- apply・配備の記録は親の checkout の `tmp/w10c/`（`diff_first/`・`diff_second/`・`diff_c*`・`apply_c*`・`diff_p3_*`・`apply_p3_*`・`flux_c_*`）

### 18.8 撮影（`review/p3_gimmicks/`、1600×900、カメラは `content/p3_gimmicks.json` の `cameras`。14:05〜14:07Z）

- `g09_cauldron`・`g09_cauldron_later`（南の上から大釜。約 3 秒あけて攪拌棒の向きと泡・煙が違う）、`g09_cauldron_magenta`（`G09LiquidColor` を I02 の Magenta にして撮り、戻した。泡・煙がマゼンタになる）
- `g11_patrol_watch`（地上の鑑賞位置 `VP_C_SkyPatrolWatch` から見上げる。キャンディのアーチの奥、M04 の屋根の上の魔女と星の光の帯）、`g11_patrol_overview`・`g11_patrol_overview_later`（南西の上から巡回の全体。約 10 秒あけて魔女の位置が違う）、`g11_witch_close`（`G11Phase` 0.25・`G11Frequency` 0 で巡回の点 2 に止めて近くから撮り、戻した。魔女は点 2 の目印のそばで帯の上を進む向きを向く）
- どれも 16〜29 万バイトで、真っ黒な約 23 KB の画像は無い。利用者のアバター・名札は写っていない。`<名前>.scene.json` は作業ツリーの絶対パスを含むのでコミットせず、親の checkout の `tmp/w10c/capture_scenes/` に移した。一時カメラ `ResoLoop_Test_Capture_*` は残っていない（`resoloop find`）

### 18.9 既存の検査

- 動いている状態（13:55〜14:00Z）で実行した。どれも直していない（`rest_pose.py` は `gimmicks.driven_slots()` に C を足しただけで、C の駆動される項目も基準姿勢に戻す）
- W10 の G01・G13（`modeling/p3_gimmicks/verify_live.py`、1 つの窓 30 秒）: 合格。G13 は 17.904°/s・上から見て反時計回り（親の checkout の `tmp/w10c/p3_prev_live_1.json`。W10 の `live_checks.json`・`param_checks.json` は書き換えていない）
- W10-A の G03（`verify_g03.py`、1 つの窓 30 秒）: 合格（`tmp/w10c/g03_prev_live_1.json`）
- W10-B の G05・G06（`verify_b.py`、1 つの窓 50 秒）: 合格。おばけの上下 −0.10〜+0.35 m・揺れ ±20° 以内、扉 0〜85.0°（`tmp/w10c/b_prev_live_1.json`。`g05_g06_*.json` は書き換えていない）
- W09R（`modeling/p2_meshy/verify_live.py`）: 全項目合格（M01〜M08 の 9 行、5 地区の数）。C の数の照合は、P3 が足した Component 31（キーの `p3_` で数える）を加えて実物 Slot 95・Component 242 と一致。基準姿勢への置き換えは 14 個（A の Body 6、D の TurnRoot、B のおばけ 2 体・蝶番 2 つ、C の攪拌棒の Pivot・魔女の仮モデル・CarrierPivot）。M08 は魔女の仮モデルを基準姿勢（巡回の点 0）に戻した位置で、W09R-C の外接箱・原点・正面と一致（`tmp/w10c/p2_meshy_live_1.json`。`review/p2_meshy/live_checks.json` は書き換えていない）
- W08（`modeling/p2_static/verify_live.py`）: W09R 以降の既知の 11 件のまま（項目は 11 章と同じ）。C の件は実物と宣言の Component がどちらも 31 増えた（211 / 166 → 242 / 197）だけで、G09・G11 による失敗は 0（`tmp/w10c/p2_static_checks_1.json`）。`review/p2_static/live_checks.json` は書き換えていない

### 18.10 実機の確認と負荷

- 利用者の確認（確認事項 6、デスクトップ、14:0xZ ごろ）: G09 の攪拌と泡・煙（量・見え方）、G11 の魔女の巡回（向き・速さ・高さ、星の光の帯からのふくらみ）、通路・鑑賞位置へのはみ出し、resoloop が接続していない間も動き続けることを見てもらい、「問題なし」
- 大釜の液面が蓋に隠れている点（18.2 の 4）は、利用者の決定で W04 への要望として記録だけにした（handoff 6.3）
- 負荷（確認事項 8）: W08 の基準と同じ端末（デスクトップ一人）で 60 fps 前後（W10・W10-A・W10-B と同じ）。足した物は C の Component 31（中継 5、液面の材質 1、粒子 25）、P3 の宣言の Slot 1・Component 7、ProtoFlux のモジュールの Slot 222・Component 291（ノード）。粒子は泡が最大 16 個・煙が最大 24 個（既定の量で同時に 約 7 個・約 9 個。毎秒の数 × 寿命の平均）。drive は各ユーザーが毎フレーム評価する（ネットワークの送信は無い）
- 常駐しない: resoloop はコマンドごとに接続して終わり、常駐するプロセスは無い。利用者の画面で、resoloop が接続していない間も動き続けた（確認事項 6）。GPT のレビューの後の測り直し（18.5・18.6）では、2 つの窓の間（1 つ目の窓の最後の観察 14:36:2xZ から 2 つ目の窓の 14:41:25Z まで 約 5 分）に resoloop のコマンドを実行せず、2 つ目の窓で θ − ω t が 1 つ目と合った（再接続後の観察）。GPT のレビューの前の実行（14:08Z・14:15Z の窓）では、窓の間の 14:13Z に全 19 宣言の diff を実行していたので、その実行は「接続していない間」の証拠にしない（GPT のレビューの指摘 m-1）

### 18.11 GPT のレビュー（確認事項 7）と保存（確認事項 4）

- GPT のレビュー: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（モデル gpt-6-astra）。対象は PR #65 の `268d0dc`。Resonite には接続させず、checkout も変更させていない。観点は、宣言と駆動の正しさ、実測の検査、既存の検査への影響、記録の正確さ、テストの採用基準の 5 つ。全文は PR #65 のコメント
- 結果: Major 3 件・Minor 1 件・Info 1 件（宣言・駆動・生成物・既存の検査への影響・テストの採用基準は指摘なし）

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| M-1 | Major | 速さ・進んだ向き・時刻の基準を魔女の θ だけで見るので、CarrierPivot だけが止まっていても（`θ = 2π G11Phase`）合格する | 採用 | CarrierPivot が止まった・遅れた状態を合格と報告するため。CarrierPivot の θ にも速さ・直線からの差・時刻の基準（窓の間）を見て、同じ観察の中の魔女との θ の差を 4° 以内とした（実測 1.6〜2.4°。後に読むので遅れる。`check_speeds` の `carrier`、`check_carrier_phase`、`check_drift` の `carrier_offsets`） |
| M-2 | Major | 材質の検査は参照先だけを比べ、共有の材質の色を読まない。守る MeshRenderer を変更後の宣言から取るので、誤って付け替えた物が対象から抜ける。色を変えている間は見ていない | 採用 | 共有の材質が変わった状態を合格と報告するため。G09 を足す前の宣言（同じ export の `model.apply.json`）から、液面の元の材質（エメラルド・マゼンタ）を使う MeshRenderer の並びと元の材質の色を取り、参照と色（sRGB、1e-4 以内）を照合する（`material_expectations`・`compare_materials`）。Magenta にしている間にも照合する |
| M-3 | Major | 回帰の傾きと窓ごとの θ − ωt の平均だけなので、平均の速さが合えば途中で時刻から ±20° 外れても合格する | 採用 | 時刻どおりに進まない式を合格と報告するため。角度を連続にして当てはめた直線からの各観察の差を、攪拌棒 15°・巡回 4° 以内とした（実測 ±5.1°・±1.2°。observe の時刻の見積もりのずれの分。`max_residual`） |
| m-1 | Minor | 記録の「2 つの窓の間の 5 分は接続していない」は、窓の間の 14:13Z に全 19 宣言の diff を実行した記録と食い違う | 採用 | 記録の誤り。測り直しでは窓の間に resoloop のコマンドを実行せず、その実行を根拠にした（18.10） |
| Info-1 | Info | handoff の撮影の枚数が 8 枚（実際は 7 枚） | 採用 | 7 枚に直した |

- テスト（S）: 指摘 M-1〜M-3 の守りに、正しい状態で通る例と外れる例を足した（`tests/test_p3_gimmicks_c_verify.py` は全 9 件。速さの検査のテストに CarrierPivot だけが止まった例と時刻から ±20° 外れる例、魔女と CarrierPivot の位相の差のテスト、材質の検査のテスト（宣言が屋台まで付け替えた例と、共有の色が変わった例）、漂いの検査のテストに CarrierPivot の時刻の基準）。守りを外す 21 の変異で、それぞれ狙ったテストだけが失敗することを確かめた
- 直した検査で実機を測り直した（18.5・18.6）

#### 18.11.1 保存

- GPT のレビューへの対応と実機の測り直し、利用者の実機の確認の後に、エージェントの依頼で利用者がワールドを 1 回保存した（2026-11-01 15:09Z より前。保存の操作の種類は記録していない）
- 保存の後（15:09〜15:10Z）に全 19 宣言（W08 の 7 つ・Meshy の 11 個・P3）の diff を取り、どれも変更 0・警告 0（no-op は 18.7 と同じ。親の checkout の `tmp/w10c/diff_aftersave/`）。魔女と攪拌棒は動き続け（3 秒あけた観察で中継の値が別の値）、泡の `Rate` は 6、HMC_P3 の G09・G11 の値は既定のままだった。保存・再読込の後に中継・モジュール・HMC_P3 の値・粒子が残って動くかは P4（開き直していない）

### 18.12 Resonite で未確認の項目

- 2 人以上での同期、途中参加（P4）。この子の確認は、共有の時刻と同期する値だけから計算する drive の仕組みの説明と、単独の確認まで。粒子の 1 粒ずつの位置は人ごとに違う（同期しない）
- 保存・再読込の後に、中継・ProtoFlux のモジュール・HMC_P3 の値・粒子が残って動くか（P4）
- 液面の色の見た目（大釜の蓋に隠れて見えない。18.2 の 4。W04 の要望の後に見る）。色の変化そのものは材質の値と泡・煙で確かめた
- 粒子の数の実測（`ParticleSystemMetadata.ParticleCount` は observe で読めない。最大の数は `MaxParticleCount` で決まり、撮影で出ていることを見た）
- VR での見え方、頭上を通る魔女の見え方の人による違い、メモリの負荷

## 19. W10-D（#61）G15 おばけ列車の周回

- 担当: Claude Code（Opus 5.5）、2026-11-02（UTC）。claim `agent-claims/issue-61`（04:43:48Z）。apply・配備したのはこのセッションだけ。GPT のレビューは PR で 1 回（19.11）
- 着手前の確認事項: W08 #41 の回答（issuecomment-6545243021）をそのまま使う（#61 の本文。利用者の着手の指示は 2026-11-02。ResoniteLink のポートは利用者が伝えた値）
- 対象: D の列車 `DAM_GhostTrain_001` の先頭車の root `DAM_GhostTrain_001_EngineRoot`（M06 の素材の宣言の親 `_M06_EngineShell` と前照灯の取付位置 `_Att_Headlamp` の親）、客車の root `DAM_GhostTrain_001_CarRoot_001`、4 つの車輪（`_EngineWheelFront`・`_EngineWheelRear`・`_CarWheelFront_001`・`_CarWheelRear_001`）。経路・速さ・弧の差は W05 の `layout/areas/D_amusement.json` の `gimmick_specs.G15_ghost_train_loop`、部品は `assets/manifest/D_amusement.json`。線路・M06 の素材の宣言・仮の車体は変えていない
- 記録は親の checkout の `tmp/w10d/`（Git の対象外）

### 19.1 方式の追記

| 項目 | 決めたこと | 理由 |
|---|---|---|
| 駆動の作り方 | ProtoFlux（`flux/P3GhostTrain.pg`。D 用の 1 つのモジュール、worldState は D の state（G13 の `Spinner` と同じ地区）、配備先は `P3_Gimmicks/G15_GhostTrain`）。D の宣言の先頭車・客車の root と車輪の中継（`ValueMultiDriver`）の `Value` を drive する | 速さ（`HMC_P3/G15Speed`）を Resonite の中から変えられる必要があり、D の Slot の Component からは HMC_P3 の空間に届かない（16.1 と同じ理由）。経路の位置と向きの計算が要る。Flux の drive は Slot のメンバーを結べないので中継を置く（2.1） |
| 動かす Slot | 先頭車の root と客車の root（W05 の `motion_roots`。位置と回転）、4 つの車輪（回転だけ）。M06（素材の宣言の親は先頭車の root の下の仮の車体）と前照灯の取付位置は先頭車の root の子なので一緒に動く | M06 の素材の宣言の親のパス（`D_amusement/DAM_GhostTrain_001/DAM_GhostTrain_001_EngineRoot/DAM_GhostTrain_001_M06_EngineShell`）を変えない（#61 の範囲）。W10-C の handoff 6.2 の案 |
| `managedFields` | 先頭車・客車の root は `["scale"]`（位置と回転を駆動）、車輪は `["position", "scale"]`（回転だけを駆動。G06 の蝶番と同じ） | D を再 apply しても駆動された姿勢を基準姿勢に戻さない（19.6 で動いている最中の 2 回目の diff が変更 0） |
| 中継 | root は位置と回転の 2 つずつ、車輪は回転の 1 つずつ（キー `p3_g15_<member>_<Slot のキー>`）。`Value` の初期値は宣言の基準姿勢（W05 の西の直線の上、回転 0） | モジュールが無い・止まっているときは基準姿勢に止まる。キーが `p3_` で始まるので、W09R の数の検査が P3 の追加として数える |
| 経路の式 | 進んだ距離 D = V t + p L（t は `WorldTimeDouble`、L は周の長さ 36.2743 m）。先頭車・客車の弧の位置 u_k = L × repeat01((s_k + D) / L)（s_k は基準姿勢の弧の位置。先頭車 3.0 m、客車 0.25 m で、差は W05 の 2.75 m）。位置と向きは `gimmicks.stadium_pose`: 西の直線 → 北の半円 → 東の直線 → 南の半円の各区間の進み具合を `Clamp01` で切って足す（d1 = S·clamp01(u/S)、β1 = π·clamp01((u − S)/πR)、d2 = S·clamp01((u − S − πR)/S)、β2 = π·clamp01((u − 2S − πR)/πR)、x = −R − R cos β1 + R cos β2、y = −S/2 + d1 + R sin β1 − d2 − R sin β2、向き = Y(β1 + β2)） | 弧の長さが時刻に比例するので一定の速さで進み、先頭車と客車の弧の差がいつも 2.75 m。区間ごとの分岐（`if`）が要らず、Python の照合の式と同じ形。時刻だけから決まり、前の値を足し込まないので漂わない（Spec §8）。D は double で計算し、u は `Repeat01_Double` で周に戻す（時刻が大きくなっても精度を失わない） |
| 車輪の回転 | X(D / r)（Resonite の +X まわりの正）。r は軸の高さ（W05 の `pivot_local` の z。root の原点はレールの上面なので半径）: 先頭車 0.21 m、客車 0.20 m | 利用者の決定で回す（19.9）。+X まわりの正は上端が前（+Z）へ進む向き = 前へ転がる（G13 で実測した四元数の向きと同じ式。19.2 の 4）。周の中の位置 u ではなく進んだ距離 D から決めるので、周の継ぎ目で角度が跳ばない |
| 外から変えられる値 | `HMC_P3/G15Speed`（既定 2.2 m/s = W05 の推奨、0〜3。0 で止まる）、`HMC_P3/G15Phase`（既定 0、0〜1。周の中の位置のずらし）。`P3_Gimmicks` の `DynamicValueVariable<float>`（キー `g15_speed`・`g15_phase`、`initialFields`）。モジュールの中で範囲に収める | 定期ショーには組み込まない（Spec §9.2）が、Resonite の中から速さを変え・止められる。`G15Phase` は時刻を止めた標本（`G15Speed` = 0）で決まった位置に止める（検査と、後の演出用）。既定の速さが W05 の推奨と食い違えば `gimmicks.g15()` が止める |
| 同期と途中参加 | G01 と同じ。`WorldTimeDouble` と同期する HMC_P3 の値だけから計算する drive で、同期する書き込み・インパルスは無い | Spec §10.3。途中参加のユーザーも同じ時刻なら同じ位置・向き・車輪の角度を見る。2 人以上での確認は P4 |
| 当たり判定 | 付けない（利用者の決定。19.9）。列車は P2 から当たり判定が無い（W08 は可動部品の下に付けない。M06 の素材も `collision: False`）。線路のレール・枕木・ガイドの静的な `MeshCollider` はそのまま | 人は列車をすり抜け、押される・挟まれる・はじかれることが無い。Spec §11「動く装飾には不要な当たり判定を付けない」。W10-B の扉と同じ扱い |
| 検査用の時計 | 列車と線路の asset root に `ValueField<double>` を 1 つずつ（キー `p3_g15ck1`・`p3_g15ck2`）置き、モジュールが `WorldTimeDouble` を drive する。`verify_d.py` は 1 回の observe で「時計 1 → 先頭車の位置 → 客車の位置 → 時計 2」を読み、位置を読んだワールドの時刻を挟む | observe の結果に時刻は無く、壁の時計の見積もり（コマンドの前後の中点）は 1 回の実行時間（1.5〜5 秒）の半分だけずれ得るので、動いている間の車間や時刻からのずれを細かく判定できなかった（GPT のレビューの指摘 M-1・M-2。19.11）。observe は書いた順に Component を読む（1 つ 約 0.115 秒）ので、時計 1・2 の間に読んだ位置は、その 2 つの時刻の式の位置の間にある。動かない・見えない Component で、ワールドの見た目は変わらない |
| W05 の経路点の照合 | 経路点 20 個の位置と向きは弧の上にある（曲線は 22.5° ごと）が、`distance_m` は曲線を弦の長さで足した値（弧の長さとの差は最大 0.17 m。`total_loop_length_m` 36.2743 は弧の長さ）。照合は位置から弧の位置を求めて（`gimmicks.stadium_arc`）、式の位置・向きと比べる | `distance_m` で式を照合すると、正しい式が経路点 3 で 1 cm ずれて見える（着手時に気付いた）。W05 への要望（handoff 6.3） |

採らなかった方法:

- **G11 と同じ三角補間の経路**: θ と弧の長さが比例しない（W10-C の handoff 6.2）ので、速さが場所で変わり、先頭車と客車の弧の差が一定にならない
- **区間ごとに `if` で分岐する式**: `Clamp01` で切った進み具合の和なら分岐が要らず、ノードが少ない。各区間の境目で位置・向きが連続（境目の値が両側で同じ）
- **車輪を周の中の位置 u から回す**: 1 周ごとに L / r（先頭車 約 172.7 rad。2π の倍数でない）の角度の跳びが出る
- **車輪を回さない**: 一様な色の 16 角柱で回っても見分けにくいが、利用者の決定で回す（中継 4 つ・検査を足した）
- **列車に動く当たり判定を付ける・線路を見えない壁で囲む**: 利用者に選択肢を示して、付けない案に決まった（動く当たり判定が人を押す・はじく、見えない壁で線路の内側に入れなくなる）
- **W05 の旗 003 を記録だけにする・描画を止める**: 利用者の決定で、配置データの位置を南へ 0.85 m ずらした（19.10）

### 19.2 Blender・Flux-SDK・観察で確かめたこと

1. **Flux-SDK（`resoloop flux node describe`、managed data 2026.9.18.82、3,320 ノード）**: `Repeat01_Double`（`Value: double`。小数部分）、`Clamp01_Double`（`N: double`）、`Floor_Double`（候補として見た）、`Sin_Double`・`Cos_Double`、`Pack_FloatQ`（X, Y, Z, W）、`Pack_Float3`。`resoloop flux check flux/P3GhostTrain.pg` はヒント 2 件（`DynamicVariableValueInput` の代わりに `~input<T>` が使える）だけでコンパイル成功
2. **Blender の確かめ**（保存しない一時的なスクリプト。親の checkout の `tmp/w10d/blender_sweep/sweep_d.py`・`sweep_d.json`・`sweep_d_after.json`）: D の `.blend` に world の物と M06 の `.blend` を足し、M06 を先頭車の root に置いて（仮の車体は描画を止めているので除く）、列車を経路に沿って 0.05 m ごと（725 の位置）に動かし、ほかのメッシュとの三角形の交差と 0.6 m 以内の最短距離を数えた（`mathutils.bvhtree`）
   - 最初の確かめで、W05 の共通部品の旗 `DAM_GarlandFlag_003`（(11.5, −38.4)、柱 2 本の高さ 3.2 m、吊り飾りの下端 約 2.3 m）の柱が南の曲線の外側のレールのすぐ外（曲線の中心から 5.04 m・5.37 m）に立ち、列車が通る範囲（中心から最大 約 5.3 m）の中にあった。M06 は 55 の位置、客車は 50 の位置で柱と交差（弧の位置 23.4〜28.6 m）。吊り飾りは列車（高さ 1.905 m）の上
   - 旗を南へ 0.85 m ずらした後（19.10）: 交差は線路との接触だけ（車輪とレール、先頭車の原点の取付位置の目印 `_Att_M06_Engine` と線路のガイド `LoopGuide`。目印とガイドの重なりは P2 の基準姿勢から同じ）。旗との最短距離は M06 0.497 m・客車 0.519 m。排障器（M06）とレールは最小 3.3 cm（W09-M06 で 3 cm 上げた分）、広場の床とは M06 0.128 m・車輪 0.09 m。柵・街灯・チケットブース・パンプキンカップは 0.6 m より遠い
3. **パンプキンカップの台との余裕**: 旗の柱（x 9.8・13.2、y −39.25）とパンプキンカップの台（中心 (11.5, −42.5)、外接箱 ±3.25 m）の水平の距離は 約 0.42 m（柱の根元の半径 0.15 m を引くと 約 0.27 m）。G16 は未実装（追加の 10 種類）で、カップは台の内側で回る
4. **車輪の回る向き**: ResoniteLink の Slot の観察（`resoloop inspect`）は親のローカルの変換だけで、世界座標は読めないので、回した点の位置を実機で読むことはできない。四元数の向きの解釈（Hamilton の積、`verify_live.qrot`）は W10 の G13（Y まわり）で実機の回る向きと照合済みで、この子でも利用者の実機の確認で列車が進む向きを向いていた（Y まわり。19.9）。X まわりも同じ式なので、+X まわりの正は上端が前（+Z）へ進む向き。検査は、ゆっくりの時刻で車輪の角度が +X まわりの正の向きに、同じ観察の列の先頭車（客車）の速さ ÷ 半径で増えることを見る（19.5）。車輪そのものが前へ転がって見えるかは、一様な色の 16 角柱で見分けにくく、目では確かめていない（19.12）

### 19.3 保存の後の最初の diff

何も変える前（04:48:55〜04:49:36Z）に、今の `main` のまま 6 キーを export した宣言（`exports/p2_static/<key>-20261102T044742Z`。W10・W10-A・W10-B・W10-C の駆動は入っている）で、全 19 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M07・M08・`content/p3_gimmicks.json`）の diff を取った。どれも変更 0・警告 0（no-op 29・184・668・339・349・780・379・16・15・15・17・16・18・15・15・15・16・19・26。W10-C の完了時と同じ数）。資産の作り直し・重複は無い。W10 の `P3PlazaDance`（`P3_Gimmicks/G01_Dance`）、W10-A の `P3FountainGlow`（`G03_Fountain`）、W10-B の `P3MansionMotion`（`G05_G06_Mansion`）、W10-C の `P3CandyStreet`（`G09_G11_Candy`）は配備されたまま。W08 の root の下は Slot 1,372・Component 2,556（W10-C の完了時と同じ。利用者が手で変えた所は無い）

- 新しい worktree の準備: 全キーの `.blend` の作り直し（04:44〜04:47Z、約 3 分。D・E は `--arg=--no-render`）、Blender の確かめ（19.2）のための M06 の `.blend`（約 1 分。M06 のビルドが書き換えた `assets/manifest/M06.json`・`review/M06/checks.json` は戻した）、Git の外の `p2_bundles/<M>-<UTC>/` を同じ名前の `exports/p2_meshy/` へ写した（コミット済みの記録は上書きせず、`SHA256SUMS` が全 9 つ一致）
- apply の前のスナップショット: 親の checkout の `tmp/w10d/01_snapshot_before_20261102T044948Z`（W08 の root 全体。最初の diff の後、最初の apply まで書き込みは無い）

### 19.4 手順

4 章の手順に、次を足す（`T` は親の checkout の `tmp/w10d/`）。

```sh
uv run python modeling/p2_static/export_p2.py --url "$URL" --key D_amusement   # 列車の root と車輪の managedFields と中継を足した p2.apply.json と p3_drivers.json
resoloop diff exports/p2_static/D_amusement-<UTC>/p2.apply.json --state "$ST/p2_D_amusement.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply exports/p2_static/D_amusement-<UTC>/p2.apply.json --state "$ST/p2_D_amusement.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/build_content.py   # D の state から Slot のキーを、D の最新の export から基準の位置を読み、flux/P3GhostTrain.pg・flux/p3_ghost_train.flux.json も作る
resoloop diff content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/deploy_flux.py --url "$URL" --manifest flux/p3_ghost_train.flux.json --report "$T/<新しいファイル>"
# 同じ diff・apply・配備をもう 1 回行い、変更 0・書き込み 0・配備 no-op を確かめる
uv run python modeling/p3_gimmicks/verify_d.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g15_live_checks.json --windows 2 --gap 300
uv run python modeling/p3_gimmicks/verify_d.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g15_param_checks.json --param-check
```

- `build_content.py` は D の state に列車の root・車輪の Slot が無いと止まり、D の最新の export で列車の root・車輪の基準の回転が単位でない、root が基準の弧の位置の経路の上に無い、車輪の軸の高さが半径でないと止まる。`gimmicks.g15()` は経路の式が W05 の経路点 20 個（位置と向き）と周の長さに合わない、`G15Speed` の既定が W05 の推奨と違うと止まる
- G15 の deploy state は親の checkout の `.resoloop/flux-state/p3_ghost_train.json`
- `verify_d.py` の窓は、時計で挟んだ先頭車・客車の位置を 30 秒（1 回 約 1.5 秒）、全部の駆動の値を 40 秒（1 回 約 2.5〜5 秒）観察する。窓の最初の時刻を止めた標本と `--param-check` は HMC_P3 の値を変えて測り、最後に元に戻ったかを確かめる（途中で列車が止まり、速さが変わるので、確認中に見ている人がいれば伝える）。位置と時刻の照合は、同じ observe で読んだ時計（ワールドの時刻）で行い、壁の時計には頼らない（時計の幅が 0.8 秒を超えた観察は判定しない）

### 19.5 G15 の結果

GPT のレビュー（19.11）で直した検査（検査用の時計で挟んだ照合）での実行: `verify_d.py --windows 2 --gap 300`（07:12:27Z と 07:19:27Z の 2 つの窓。`review/p3_gimmicks/g15_live_checks.json`）と `--param-check`（07:09〜07:12Z。`g15_param_checks.json`）。どれも問題 0。直す前の検査での実行（2 つの窓 06:30:43Z・06:37:25Z、`--param-check` 06:14〜06:17Z）も合格だった

| 項目 | 結果 |
|---|---|
| 経路 | 両方の窓の全観察（全部の駆動の値 13・14 回、時計で挟んだ位置 13・12 回）で、先頭車・客車の位置が経路の上（ずれ 1e-5 m 未満。許容 1 cm）、高さがレールの上面（差 1e-6 m 未満）。先頭車の弧の位置はほぼ 1 周を観察（0.55〜36.18 m・2.43〜34.25 m） |
| 経路点 | 時刻を止めた標本（`G15Speed` = 0）で、`G15Phase` を先頭車が W05 の経路点 0・3・6・10・13・16・19 に、客車が経路点 6・16 に来る値にしたとき、位置が経路点のデータと 0.05 mm 以内（経路点のデータの 4 桁の丸めの分）、向きが `yaw_z_deg` と 0.0001° 以内（中継の値と Slot そのものの両方）。先頭車と客車の弧の差は式どおり（位置の差 1e-6 m 以内）。各窓の最初の標本（`G15Phase` 0.5）も同じ |
| 向き | 動いている間、正面の向きと経路の接線の差は最大 4.26°（位置と回転は別の中継で、1 回の observe の中で回転を後に読む。曲線の向きの変わる速さは 28°/s。許容 6°）、Y 軸まわりだけ。隣の観察の間に進んだ向き（弦）と正面の向きの差は最大 15.97°（許容 30°。後ろ向き・横向きを見つける）。時刻を止めた標本では 0.0° |
| 時計回り | 時計で挟んだ観察の先頭車の位置の、線路の中心まわりの角度の変化の合計が −628°・−639°（負 = 上から見て時計回り。観察した位置だけから決める） |
| 時刻の式との照合（時計で挟んだ観察） | 1 回の observe で「時計 1 → 先頭車の位置 → 客車の位置 → 時計 2」を読み、全観察（25 回）で、先頭車・客車の弧の位置が、時計 1 と時計 2 のワールドの時刻の式の位置の間にあった。時計の幅は 0.318〜0.495 秒（判定しない 0.8 秒を超えた観察は 0）。先頭車は時計 1 の式の位置から 0.24〜0.64 m、客車は 0.50〜0.87 m 先（= 読んだ時刻。時計の幅の式の位置の差は 0.70〜1.09 m）。客車の車間の誤りや、時刻から外れる式は、この幅の外に出て見つかる（19.11 の M-1・M-2） |
| 速さ | ワールドの時刻（時計の中点）に対して、先頭車 2.19772・2.20064 m/s、客車 2.19978・2.19972 m/s（2.2 m/s と 0.2% 以内。許容 5%）。1 周 16.49 秒 |
| 先頭車と客車の弧の差 | 時刻を止めた標本で 2.75 m（差 1e-6 m 以内）。動いている間は、時計で挟んだ照合で先頭車・客車それぞれが時刻の式の位置にある（上の行）ので、弧の差も式どおり |
| 漂わない | 2 つの窓の最初の時刻を止めた標本（`G15Phase` 0.5）の位置の差は先頭車・客車とも 0.0 m（許容 1 cm）、車輪の回転も同じ。両方の窓で、時計で読んだワールドの時刻の式と位置が合う（7 分あけても、u がワールドの時刻から決まっている） |
| 車輪 | 動いている間、4 つとも +X まわりだけの回転（X 以外の成分 1e-3 未満）で、観察ごとに角度が変わる。時刻を止めた標本で、`G15Phase` の進んだ距離 ÷ 半径の回転と 1e-4 以内（中継と Slot そのもの）。ゆっくりの時刻（`G15Speed` = 0.05 m/s、40 秒・14 回。時刻は時計で読んだワールドの時刻）で、先頭車・客車の速さ 0.04995・0.04994 m/s（許容 2%）、車輪の回る速さは +X まわりの正の向きに 0.24997・0.24993（客車、測った速さ ÷ 0.20 m = 0.24971）・0.23808・0.23828 rad/s（先頭車、÷ 0.21 m = 0.23787）。差は 0.2% 以内（許容 1%） |
| 外から変えられる値 | 時計で挟んだ照合で、`G15Speed` 1.1 で 1.09645・1.09677 m/s（先頭車・客車）、10 → 3 に収まり 2.99801・2.99691 m/s、−1 → 0 で止まる（4 回の観察で基準の位置のまま、動き 0）。どれも全観察が時刻の式の幅の中。`G15Phase` 1.5 → 1（基準の位置。収めないと周の反対側）、−1 → 0（基準の位置、車輪の回転 0）。どれも式の値と一致 |
| 戻した値 | `G15Speed` 2.2、`G15Phase` 0（変える前と同じ。違えば問題にする） |
| M06 と前照灯の取付位置 | 両方の窓の最初と最後で、先頭車の root の下の `_M06_EngineShell`・M06 の素材の宣言の root `M06` とその子 `M06_GhostTrainEngine_001`・`_Att_Headlamp`（ローカル (0, 1.39, 1.26)）・`_Att_CouplerRear`・`_Att_M06_Engine`・車輪の位置が、宣言と同じパス・ローカルの変換（差 1e-4 未満）。M06 の素材の宣言の diff は最後まで変更 0（19.6）。W09R の検査（M06 の外接箱・原点・前照灯とレンズの前面）も合格（19.7） |
| 構造 | 列車と線路の子孫が宣言と同じパス（先頭車・客車の root は拡縮、車輪は位置と拡縮も）。中継 8 つは有効で、`Drives` は自分の Slot の `Position`・`Rotation` を指す |
| はみ出し（包絡） | M06 と客車・車輪・取付位置のバンドルのメッシュを経路に沿って 0.2 m ごとに動かすと、曲線の中心からの距離は 3.82〜5.27 m。W01 の主動線 `Route_South_Entrance_Approach`（幅 4 m）・南東と南西の連絡橋の通路に入る点 0、D の除外範囲（スポーン、中央の視線、両側の連絡橋の入口）に入る点 0、ほかの物の外接箱（線路と広場の床を除く）に入る点 0。最も近い外接箱は旗 003 の 0.33 m、街灯 006 の 0.35 m、パンプキンカップ 0.48 m、チケットブース 0.69 m、柵 001・002 の 0.78・0.81 m。三角形での確かめは 19.2 の 2 |
| 当たり判定 | 付けない（19.1。利用者の決定）。列車の Slot の下に `MeshCollider` は無く、P2 の宣言のまま。線路の `MeshCollider` は静的なまま |
| 利用者の確認 | 問題なし（19.9） |

- 生の観察は親の checkout の `tmp/w10d/g15_raw_windows_4.json`・`g15_param_raw_2.json`（Git の対象外。ResoniteLink の ID を含む）。GPT のレビューの前の検査での実行は `g15_raw_windows_1.json`〜`_3.json`・`g15_param_raw_1.json`、試しは `d_try1_raw.json`・`d_param_try1_raw.json`
- W05 の経路点の位置は 4 桁に丸めてあるので、経路点との照合は 0.05 mm の差が残る

### 19.6 diff・apply・配備と、再適用・所有範囲

| 時刻（UTC） | 宣言・操作 | diff | apply・配備 |
|---|---|---|---|
| 04:48〜04:49 | 全 19 宣言（19.3。`<key>-20261102T044742Z`） | どれも変更 0・警告 0 | — |
| 05:33〜05:34 | D（`D_amusement-20261102T053231Z`。列車の root と車輪に `managedFields` と中継、旗 003 の位置） | 作成 8（先頭車・客車の root の `ValueMultiDriver<float3>`・`<floatQ>`、車輪 4 つの `<floatQ>`）・更新 1（旗 003 の Slot。「one or more managed transforms differ」）・no-op 378・警告 0。`managedFields` の追加は今の値と同じで変更にならない | Component の追加 8・Slot の更新 1（資産は変更なし 58、取り込み 0） |
| 05:34 | P3（`content/p3_gimmicks.json`） | 作成 3（Slot `G15_GhostTrain`、値の Component 2）・no-op 26 | Slot の作成 1・Component の追加 2 |
| 05:34 | ProtoFlux（`deploy_flux.py --manifest flux/p3_ghost_train.flux.json`） | — | モジュール `P3GhostTrain` を `P3_Gimmicks/G15_GhostTrain` の下に作成（`action` create、drive の結び先 8 個がすべて解決） |
| 05:34〜05:35 | D・P3 の 2 回目の diff（動いている最中） | どちらも変更 0・警告 0（D は no-op 387、P3 は 29）。列車の位置・回転と車輪の回転は差分にならない | — |
| 05:35 | D・P3 の 2 回目の apply、2 回目の配備 | — | apply はどれも書き込み 0（作成・更新・削除 0、資産の取り込み 0）。配備は `no-op`（「source and transitive dependency hashes match deploy state」） |
| 06:23〜06:24 | M05 の屋根・M07 の素材の宣言（W09R の検査の前の state の URL の更新。19.7） | どちらも変更 0・警告 0（no-op 15・16。資産は「asset URL was migrated to resdb by a world save」） | どちらも書き込み 0（資産の取り込み 0）。state が実物の `resdb:///` の URL を記録した |
| 06:28〜06:29 | 全 19 宣言の 2 回目の diff（動いている最中。D は `053231Z`） | どれも変更 0・警告 0（no-op は 19.3 と同じで、D は 387、P3 は 29）。M06 の素材の宣言も変更 0（M06 は親の先頭車の root の動きについて動く） | — |
| 07:02〜07:03 | D（`D_amusement-20261102T070224Z`。検査用の時計。GPT のレビューへの対応。19.11） | 作成 2（列車と線路の asset root の `ValueField<double>` `p3_g15ck1`・`p3_g15ck2`）・no-op 387・警告 0。最初は 2 つとも列車の asset root に置き、同じ Slot に同じ型が 2 つあるという警告（`APPLY_COMPONENT_IDENTITY_RISK`）が出たので、apply の前に線路の asset root へ分けた | Component の追加 2（資産の取り込み 0） |
| 07:03 | ProtoFlux（時計の出力 2 つを足したモジュール） | — | モジュール `P3GhostTrain` を置き換え（`action` update、drive の結び先 10 個がすべて解決） |
| 07:07〜07:08 | D・P3 の 2 回目の diff・apply、2 回目の配備（時計を足した後） | D は変更 0（no-op 389）、P3 は変更 0（no-op 29） | apply は書き込み 0。配備は `no-op` |

- `--prune` は使っていない。削除・名前の変更・Component の作り直しは 0
- 所有範囲: diff の対象は D の列車の root と車輪の中継、旗 003 の Slot の位置（利用者の決定。19.10）、P3 の宣言の G15 の値と `G15_GhostTrain` だけ。world・A・B・C・E・`content/main.json`・Meshy の素材の宣言（M06 を含む）は、最初の diff から最後まで変更 0。このうち apply したのは、W09R の検査の前に state の URL を更新するための M05 の屋根と M07 の素材の宣言だけで（変更 0 の diff を確かめてから。ワールドへの書き込み・資産の取り込みは 0。19.7）、ほかは apply していない（GPT のレビューの指摘 I-1 で、apply の有無と書き込みの有無を分けて書き直した）。world・A・B・C・E をこの子のコードで export し直した `p2.apply.json`・`p3_drivers.json` は `main` の export（`044742Z`）とバイト単位で同じ（2026-11-02 に、同じ `model.apply.json` から当たり判定・差し替え・P3 の駆動を足し直して比べた。Resonite には接続していない）。W10〜W10-C の `flux/P3PlazaDance.pg`・`p3_plaza_dance.flux.json`・`P3FountainGlow.pg`・`p3_fountain_glow.flux.json`・`P3MansionMotion.pg`・`p3_mansion_motion.flux.json`・`P3CandyStreet.pg`・`p3_candy_street.flux.json` は `build_content.py` で作り直してもバイト単位で同じ（`git diff` が空）。`content/p3_gimmicks.json` は G15 の値 2 つを Component の並びの末尾に足し、前の子の値の並びは変えていない
- 数: W08 の root の下は Slot 1,372・Component 2,556 → Slot 1,574・Component 2,806（P3 の宣言 1・2、D の中継 0・8、モジュール `P3GhostTrain` 201・240。親の checkout の `tmp/w10d/02_snapshot_after_*` と `03_g15_module_*`）→ 時計を足した後は Slot 1,576・Component 2,818（D の時計 0・2、モジュールの時計の出力のノード 2・10。モジュールは Slot 203・Component 250。親の checkout の `tmp/w10d/03b_g15_module_*`、W09R の検査の `root_live`）。2 回目の apply で増えない
- apply・配備の記録は親の checkout の `tmp/w10d/`（`diff_first/`・`diff_d*`・`apply_d*`・`diff_p3_*`・`apply_p3_*`・`flux_d_*`）

### 19.7 既存の検査

- 動いている状態（06:17〜06:26Z）で実行した。どれも直していない（`rest_pose.py` は `gimmicks.driven_slots()` に D の列車を足しただけで、列車の root と車輪の駆動される項目も基準姿勢に戻す）
- W10 の G01・G13（`modeling/p3_gimmicks/verify_live.py`、1 つの窓 30 秒）: 1 回目（06:17Z）は G13 を観察した 25 秒の間だけ TurnRoot の角度が −31.879° のまま変わらず「G13 speed 0.00 deg/s」で外れた（同じ実行の後の G01 は動いていた。`Spinner` は有効で `_speed` (0, −18, 0) のまま）。直後の観察では回っていて、2 回目（06:25Z）は合格（18.005°/s、上から見て反時計回り）。検査用の時計を足した後の 3 回目（07:22Z）も合格（18.118°/s）。1 回目の原因は確かめられなかった（ワールドが一時的に背面に回った可能性。1 章の注）。親の checkout の `tmp/w10d/p3_prev_live_1.json`・`_2.json`。W10 の `live_checks.json`・`param_checks.json` は書き換えていない
- W10-A の G03（`verify_g03.py`、1 つの窓 30 秒）: 合格（`tmp/w10d/g03_prev_live_1.json`）
- W10-B の G05・G06（`verify_b.py`、1 つの窓 50 秒）: 合格。おばけの上下 −0.098〜+0.348 m・揺れ ±20° 以内、扉 0〜85.0°（`tmp/w10d/b_prev_live_1.json`）
- W10-C の G09・G11（`verify_c.py`、1 つの窓）: 合格。攪拌 60.25°/s、巡回 7.99°/s（`tmp/w10d/c_prev_live_1.json`）
- W09R（`modeling/p2_meshy/verify_live.py`）: 1 回目は M05 の屋根と M07 の「測ったメッシュの `StaticMesh.URL` が apply の state の記録と同じ」の 2 件で外れた。前回の保存の後にワールドが開き直され、資産の URL が `resdb:///` に移ったが、state は `local://` のままだったため（全 19 宣言の diff の資産の判定は「asset URL was migrated to resdb by a world save; state will record the live URL」）。`handoff/W09R-D.md` の手順（先に apply（変更 0 でよい）してから実行する）どおり、M05 の屋根と M07 の素材の宣言の diff が変更 0（no-op 15・16）であることを確かめてから apply し（書き込み 0、資産の取り込み 0。state が実物の `resdb:///` の URL を記録した。apply の前の state は親の checkout の `tmp/w10d/state_backup_before_url_refresh/`）、2 回目は全項目合格（M01〜M08 の 9 行、5 地区の数）。D の数の照合は、P3 が足した Component 9（G13 の `Spinner` 1、G15 の中継 8。キーの `p3_` で数える）を加えて一致。基準姿勢への置き換えは 20 個（W10-C までの 14 個と、列車の root 2 つ・車輪 4 つ）。`tmp/w10d/p2_meshy_live_1.json`・`_2.json`。GPT のレビューの後、検査用の時計を足してからの 3 回目も全項目合格で、D の P3 の追加は Component 11（`Spinner` 1、中継 8、時計 2）。`_3.json`。`review/p2_meshy/live_checks.json` は書き換えていない）
- W08（`modeling/p2_static/verify_live.py`）: W09R 以降の既知の 11 件のまま（項目は 11 章と同じ）。D の件は実物と宣言の Component がどちらも 8 増えた（241 / 195 → 249 / 203。時計を足した後は 251 / 205）だけで、G15 による失敗は 0（`tmp/w10d/p2_static_checks_1.json`・`_2.json`）。`review/p2_static/live_checks.json` は書き換えていない

### 19.8 撮影（`review/p3_gimmicks/`、1600×900、カメラは `content/p3_gimmicks.json` の `cameras`。06:27〜06:28Z）

- `g15_train_loop`・`g15_train_loop_later`（南の上から線路の全体。間をあけた 2 枚で、列車が南の曲線（旗の柱の間）と西の直線にいる）、`g15_train_curve`（南東の柵の外から。西の直線を北へ進む先頭車（M06）と客車、奥にチケットブース）
- どれも 34〜37 万バイトで、真っ黒な約 23 KB の画像は無い。利用者のアバター・名札は写っていない。`<名前>.scene.json` は作業ツリーの絶対パスを含むのでコミットせず、親の checkout の `tmp/w10d/capture_scenes/` に移した
- 確認画像（Blender）: 旗を動かした D の `review/D_amusement/01`〜`04`（19.10）

### 19.9 実機の確認と負荷

- 当たり判定の扱い（Spec §11、確認事項 6）: 利用者に、付けない（推奨）・列車に動く当たり判定・線路を囲む見えない壁の 3 つを示し、付けない案に決まった（2026-11-02）
- 車輪の回転（#61 の範囲で任意）: 利用者に、回さない（推奨。一様な色の 16 角柱で見分けにくい）・回すを示し、回す案に決まった
- W05 の旗 003: 利用者に、南へ 0.85 m ずらす（推奨）・記録だけ・描画を止めるを示し、ずらす案に決まった（19.10）
- 利用者の確認（確認事項 6、デスクトップ、05:47〜05:56Z ごろ。直す前の検査の 2 つの窓の間）: 先頭車（M06）と客車が上から見て時計回りに約 16.5 秒で 1 周し曲線でも線路に沿って向きを変える、車輪が回る（見分けにくい程度でよいとして）、当たり判定が無く列車をすり抜ける、南の曲線の外の旗・柵・チケットブース・パンプキンカップにめり込まない、resoloop を接続していない約 7 分の間も動き続ける、の 5 点とも「問題なし」
- 負荷（確認事項 8）: W08 の基準と同じ端末（デスクトップ一人）で 60 fps 前後（W10〜W10-C と同じ。利用者の確認、06:4xZ。検査用の時計を足す前）。足した物は D の Component 10（中継 8、検査用の時計 2）、P3 の宣言の Slot 1・Component 2、ProtoFlux のモジュールの Slot 203・Component 250（ノード）。粒子は無い。drive は各ユーザーが毎フレーム評価する（ネットワークの送信は無い）
- 常駐しない: resoloop はコマンドごとに接続して終わり、常駐するプロセスは無い。利用者の画面で、resoloop が接続していない間も動き続けた。最後の 2 つの窓の間（1 つ目の窓の最後の観察 07:14:19Z から 2 つ目の窓の 07:19:27Z まで 約 5 分）は resoloop のコマンドを実行せず、2 つ目の窓でも位置が時計で読んだワールドの時刻の式と合った（19.5。再接続後の観察）

### 19.10 直した閉じた子のファイル

| ファイル（持ち主） | 直した内容（旧 → 新） | 理由 |
|---|---|---|
| `modeling/D_amusement/layout_data.py`（W05） | 共通部品の旗 `DAM_GarlandFlag_003` の位置 (11.5, −38.4, 0) → (11.5, −39.25, 0)（コメントを 2 行足した） | 柱 2 本が線路の南の曲線の外側のレールのすぐ外に立ち、列車が通るたびに先頭車（M06）・客車が柱をすり抜けていた（19.2 の 2）。利用者の決定（19.9）。#61 の「してよい編集」に無い W05 の配置データの修正なので、利用者に選択肢（南へずらす・記録だけ・描画を止める）を示して決めた |
| `layout/areas/D_amusement.json`（W05。D のビルドが生成） | `Common_Placement` の旗 003 の `position` の y −38.4 → −39.25 | 上の修正で D を作り直した結果 |
| `review/D_amusement/01`〜`04_*.png`（W05） | D を作り直して描き直した確認画像 | 配置を変えたキーの確認画像（`docs/p1-handoff.md` 6 章）。旗が線路とパンプキンカップの台の間に移った |
| `exports/p2_static/<key>-20261102T044742Z`（6 キー、最初の diff 用）・`D_amusement-20261102T053231Z`・`D_amusement-20261102T070224Z`（検査用の時計を足した export）（W08 の記録） | `report.json`・`validate.json`・`colliders.json`・`replacements.json`・`p3_drivers.json` | export のやり直しの記録（バンドル本体はコミットしない） |

- 作り直した D の検査: `uv run python tools/check_data.py --key D_amusement`・`tools/check_blend.py --key D_amusement`、`tests/test_D_amusement_layout.py`（スポーン・主動線・接続口・視線への非干渉）は合格
- D の宣言の diff は、旗 003 の Slot の位置の更新 1 つ（「one or more managed transforms differ」。メッシュの資産は変わらず、取り込み 0）。旗の当たり判定（`MeshCollider`）は同じ Slot にあるので一緒に動く
- W05 のほかの所有ファイル、アセット・部品の ID、可動部品の原点と階層は変えていない。`modeling/p2_static/`・`modeling/p2_meshy/` の検査は直していない（19.7）

### 19.11 検査の直し・GPT のレビュー（確認事項 7）と保存（確認事項 4）

- PR の前の直し: 実測の検査（`verify_d.py`）は、最初の試しと 2 回の 2 つの窓の実行で、決めておいた許容が実測に合わない所を直した。動いている間の先頭車と客車の弧の差と、各観察と直線の差の許容を、observe の実行時間（壁の時計の見積もりの幅）から決める形にし、ゆっくりの時刻を 40 秒に延ばして車輪の回る速さを同じ観察の進みとの比で見るようにした。包絡の「最も低い点が床の外接箱の上面より上」の判定は外した（広場の床の外接箱の上面 0.13 m は別の場所の縁石で、列車の下の床ではない。M06 の排障器の下端 0.10 m は線路の間の地面より上。床・枕木との交差は Blender の三角形の確かめで見た）。このうち前の 2 つは、誤って失敗しないよう許容を広げたもので、GPT のレビューで「誤りを見落とす」と指摘された（下の M-1・M-2）。最初の記録（`e4a497e`）にあった「誤りを見落とす向きの緩め方ではない」は誤りだった
- GPT のレビュー: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（モデル gpt-6-astra）。対象は PR #66 の `e4a497e`。Resonite には接続させず、checkout も変更させていない。観点は、宣言と駆動の正しさ、実測の検査、既存の検査への影響、記録の正確さ、テストの採用基準の 5 つ。全文は PR #66 のコメント
- 結果: Major 2 件・Info 1 件（宣言と駆動・既存の検査への影響・テストの採用基準は指摘なし）

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| M-1 | Major | 動いている間の車間の許容を observe の実行時間から決めるので、1 回 2.4 秒なら 5.3 m まで縮んでも合格する。客車の式に `+0.5 × V` が入る（動いている間だけ車間が 1.1 m 縮む）誤りを見落とす。止めた標本・ゆっくりの時刻では誤りが消える | 採用 | 車間が違う状態を合格と報告するため。検査用の時計（19.1）で、1 回の observe で「時計 1 → 先頭車の位置 → 客車の位置 → 時計 2」を読み、先頭車・客車の弧の位置が、時計 1 と時計 2 のワールドの時刻の式の位置の間（と 1 cm・2 フレームの分）にあるかを見る（`check_clocked`）。客車は時計 2 の 約 0.115 秒前に読まれるので、時刻から 約 0.25 m より大きく外れる客車（車間が縮む・広がる）を見つける。時計の幅が 0.8 秒を超えた観察は判定せず、判定できた観察が 4 回未満なら問題にする |
| M-2 | Major | 直線からの差の許容が広く、平均の速さが合う周期的な速さの揺れ（D = V (t + 0.4 cos(2πt/20))。速さ 1.92〜2.48 m/s）を合格にする | 採用 | 時刻どおりに進まない式を合格と報告するため。M-1 と同じ時計で挟んだ照合で、ワールドの時刻の式から 約 0.25 m より大きく外れる位置を見つける（この例は最大 0.88 m）。壁の時計で見積もった直線からの差・弧の差・窓の間の u − V t の判定は外し、速さもワールドの時刻（時計の中点）に対して当てはめる。値の確認の速さ（1.1・10・−1）とゆっくりの時刻も時計で測る |
| I-1 | Info | 記録の「Meshy の素材の宣言は apply していない」が、M05 の屋根・M07 を変更 0 で apply した記録と食い違う | 採用 | 記録の誤り。apply したのはこの 2 つだけで、ワールドへの書き込みは 0 と分けて書いた（19.6） |

- テスト（S）: 指摘 M-1・M-2 の守りに、正しい状態で通る例と、客車の車間が動いている間だけ縮む・広がる例、周期的な速さの揺れ、2 倍の速さ、時計の幅が広すぎる観察を足した（`tests/test_p3_gimmicks_d_verify.py` の `test_clocked_check_*`。壁の時計の直線からの差と弧の差のテストは、判定を外したので消した）。守りを外す変異（上側・下側・判定できた観察の数）で、それぞれそのテストだけが失敗することを確かめた
- 直した検査で実機を測り直した（19.5。2 つの窓 07:12:27Z・07:19:27Z、`--param-check` 07:09〜07:12Z、既存の検査 07:21〜07:23Z。どれも合格）

#### 19.11.1 保存

- GPT のレビューへの対応と実機の測り直しの後に、エージェントの依頼で利用者がワールドを 1 回保存した（2026-11-02 07:46Z より前。保存の操作の種類は記録していない）
- 保存の後（07:46〜07:47Z）に全 19 宣言（W08 の 7 つ・Meshy の 11 個・P3）の diff を取り、どれも変更 0・警告 0（no-op は 19.6 と同じで、D は 389、P3 は 29。親の checkout の `tmp/w10d/diff_aftersave/`）。列車は動き続けていた（時計で挟んだ 2 回の観察で、ワールドの時刻 5.07 秒の間に先頭車が 11.14 m 進んだ = 2.2 m/s）。HMC_P3 の G15 の値は既定のまま（`G15Speed` 2.2、`G15Phase` 0）。保存・再読込の後に中継・モジュール・時計・HMC_P3 の値が残って動くかは P4（開き直していない）

### 19.12 Resonite で未確認の項目

- 2 人以上での同期、途中参加（P4）。この子の確認は、共有の時刻と同期する値だけから計算する drive の仕組みの説明と、単独の確認まで
- 保存・再読込の後に、中継・ProtoFlux のモジュール・HMC_P3 の値が残って動くか（P4）。この子の着手の時点でワールドは前回の保存の後に開き直されていて、W10〜W10-C の駆動はどれも動いていた（19.3・19.7）
- 車輪が前へ転がって見えるか（一様な色の 16 角柱で見分けにくく、目では確かめていない。回る向きは四元数の式と、ゆっくりの時刻の進みとの比で確かめた。19.2 の 4）
- VR での見え方、列車とアバターのすれ違い（当たり判定は無いのですり抜ける）、メモリの負荷

## 20. W10-E（#62）G18 キノコの発光・G20 時計の針と鐘

E 西・魔法の森の **G18 キノコが異なる周期で柔らかく発光する**と **G20 時計の針が進み、節目に鐘の演出が出る**の記録。これで先行 10 種類（Spec §8）が揃った。

- 担当: Claude Code（Opus 5.5）、2026-11-03（UTC）。apply・配備したのはこのセッションだけ。実装は Claude、GPT がレビュー（W10 と同じ扱い。20.11）
- 着手前の確認事項: W08 #41 の回答（issuecomment-6545243021）をそのまま使う（#62 の本文。起票したセッションの判断）
- 利用者の決定（2026-11-03、着手の直後）: G20 の時刻の基準は**見る人の端末のローカル時刻**（選択肢は「実際の日本時間（UTC+9 固定）」「`WorldTimeDouble`」「各自のローカル時刻」の 3 つ。推奨は日本時間だった）。人によって針の位置と鐘の時刻が違う（同期しない）ことを含めて選んだ

### 20.1 方式の追記

| 項目 | 決めたこと | 理由 |
|---|---|---|
| 駆動の作り方 | ProtoFlux（`flux/P3ForestClock.pg`。E 用の 1 つのモジュール、worldState は E の state、配備先は `P3_Gimmicks/G18_G20_Forest`、deploy state は `p3_forest_clock.json`）。キノコ 14 個の個体ごとの材質の `EmissiveColor`、時計塔の時針・分針・鐘の Pivot の中継（`ValueMultiDriver<floatQ>`）の `Value`、検査用の時計 2 つを drive する | 外から変えられる値（`HMC_P3/G18*`・`G20*`）を Resonite の中から読むので、`P3_Gimmicks` の下に置く（16.1 と同じ理由）。G18 と G20 は同じ地区（E）なので 1 つのモジュールにまとめた（W10-B・C と同じ） |
| G18 の共有の材質 | E の宣言で、キノコの発光の部品（W06 の取付位置 `<個体>_Glow`。それぞれ専用の MeshRenderer に共有の材質 `MAT_EFR_MushGlow` 1 つだけ）に、共有の材質を写した個体ごとの `PBS_Metallic`（キー `p3_g18_01`〜`14`。番号は W06 のアセット一覧の `glow_individuals` の並び）を足し、`_Glow` の MeshRenderer の `Materials` だけを付け替える（`district.add_g18_materials`）。`EmissiveColor` は元の値を `initialFields` に置く | 共有の材質は 15 個の MeshRenderer が使い、14 個がキノコの `_Glow`、1 個が池 `EFR_Pond_001`（5 つの材質のうち 4 つ目。睡蓮の光る部分）。個体ごとに周期を変えるには、少なくとも個体の数だけ発光の値が要る。池は付け替えず、元の材質の値も変えないので、見た目は P2 のまま（20.5） |
| G18 の式 | θ_i = 2π (S t + φ_i) / T_i、倍率_i = I (lo_i + (hi_i − lo_i)(0.5 + 0.5 sin θ_i))、発光_i = 倍率_i × E0（Linear の colorX。E0 は P2 の発光 (1.536, 2.752, 3.2) 線形）。t は `WorldTimeDouble`、T_i・φ_i・lo_i・hi_i は W06 の `period_s`（3.2〜6.52 秒）・`phase_s`・`intensity_min`（0.35）・`intensity_max`（1.0） | 「柔らかく」= 正弦で滑らかに。倍率 1 が P2 の明るさ（W06 の `intensity_max`）。色合いは変えず明るさだけを変える（3 つの成分に同じ倍率）。周期が全部違うので、隣の個体と揃わない（20.5 の観察で近くの組の倍率の差は最大 0.24〜0.65） |
| G20 の時刻 | 見る人の端末のローカル時刻 L = `ToLocalTime(UtcNow)` の 0 時からの秒 s = 時 × 3600 + 分 × 60 + 秒 + ミリ秒 / 1000（`DateTimeHour` などの int を double に） | 利用者の決定。ProtoFlux の drive は見る人ごとにその端末で評価されるので、各自の端末のタイムゾーンの時刻になる。Flux-SDK に `LocalNow` は無く、`ToLocalTime`（`DateTime` → `DateTime`）と `UtcNow` の組で作る |
| G20 の針 | 時針 = Z(2π × repeat01(s / 43200))、分針 = Z(2π × repeat01(s / 3600))（Pivot のローカル +Z まわりの正、四元数 (0, 0, sin(φ/2), cos(φ/2))）。中継は回転の 1 つずつ、`managedFields` は `["position", "scale"]`（G06 の蝶番と同じ） | W06 の「Pivot のローカル −Y_B まわりの正 = 前から見て時計回り、基準は 12 時」を Resonite に写すと、軸の入れ替えで右手系と左手系が入れ替わるので −Y_B の +θ = −Z_R の −θ = +Z_R の +θ。実機で、3 時の針の先が W06 の「前から見た右 = −X_B（−X_R）」を向くことを確かめた（20.5。針の先の向きの照合） |
| G20 の鐘 | 節目（s が `G20BellInterval` の倍数。既定 3600 で毎正時）からの秒 τ = N × repeat01(s / N)、x = clamp01(τ / 12)、角度 = A (1 − x)² sin(2π × 6 x)（A = 25° × `G20BellSwing`）、Pivot のローカル +X まわり。中継は回転の 1 つ | 一度だけの演出を、インパルスやタイマーを使わない「節目からの時刻の関数」にした。12 秒で 6 往復して真下に戻り（x = 1 で (1 − x)² = 0）、次の節目まで止まる。\|角度\| ≤ A なので W06 の ±25° を超えない（最初の山で 約 23°）。途中参加の人は、揺れている途中なら同じ揺れの続きを見て、揺れの後なら止まった鐘を見る（鳴り直さない）。演出は見る人ごとに計算されるだけで、何も生成しない（参加者ごとに重ならない） |
| 外から変えられる値 | `HMC_P3/G18Intensity`（既定 1、0〜2。0 で消える、2 は定期ショーの盛り上がり）・`G18Speed`（既定 1、0〜3。0 で時刻を止める）・`G20BellSwing`（既定 1、0〜1）・`G20BellInterval`（既定 3600 秒、20〜3600）。`P3_Gimmicks` の `DynamicValueVariable<float>`（キー `g18_amp`・`g18_speed`・`g20_swing`・`g20_int`、`initialFields`）。モジュールの中で範囲に収める | W11 のショーが Resonite の中から変えられる。`G20BellInterval` は確かめのために節目を短くする値（最小 20 秒 > 揺れの 12 秒）。確かめた後に 3600 に戻した（20.5） |
| 検査用の時計 | 時計塔の asset root と鐘の腕木に `ValueField<double2>` を 1 つずつ（キー `p3_g20ck1`・`p3_g20ck2`）置き、モジュールが (`WorldTimeDouble`, s) を drive する | W10-D と同じ（observe に時刻が無い）。G18 はワールドの時刻、G20 はローカル時刻で照合するので、2 つの時刻を 1 つの値で読む。同じ Slot に同じ型を 2 つ置かない（`APPLY_COMPONENT_IDENTITY_RISK`） |
| 当たり判定 | 付けない。針・鐘・キノコは P2 から当たり判定が無い（鐘の腕木の `MeshCollider` は静的なまま） | Spec §11。針・鐘は高さ 7〜11 m で、人の届く高さより上（20.5 の包絡） |

採らなかった方法:

- **G18 で共有の材質そのものを drive する**: 14 個と池が同じ明るさで一斉に変わり、「異なる周期」にならない
- **周期の近い個体をまとめて材質を減らす**: W06 の周期は 14 個とも違う（3.2〜6.52 秒）。まとめると W06 のデータの周期を変えることになる。分けて増えるのは材質の Component 14 個（負荷は 20.9）
- **キノコごとに発光用の Slot（点光源や別のメッシュ）を足す**: Spec §11「すべてに実ライトを付けない」。見た目のメッシュを足すと形が変わる
- **G20 を日本時間（UTC+9 固定）や `WorldTimeDouble` にする**: 利用者に 3 つを示して、各自のローカル時刻に決まった（日本時間は全員が同じ時刻・本当の時刻を見る、`WorldTimeDouble` はほかのギミックと同じ共有の時刻だが本当の時刻は指さない）
- **鐘をインパルス（`FireOnTrue`・`DelayTimeSpan` など）で一度だけ鳴らす**: 実行する人の数だけ鳴り、途中参加の人の分の扱いが要る。時刻の関数なら同期も状態も要らない
- **鐘を正時の数だけ鳴らす（1 時に 1 回、2 時に 2 回）**: 演出の長さが時刻で変わり、2 人以上で同じ演出を見るとき（日本時間の場合）以外に利点が少ない。W11 の定期ショーの演出の候補として handoff に書いた

### 20.2 Reflection・Flux-SDK・Blender で確かめたこと

1. **Flux-SDK（`resoloop flux node search`・`describe`、managed data 2026.9.18.82、3,320 ノード）**: `UtcNow`（`DateTime`）、`ToLocalTime`（`DateTime` → `DateTime`）、`DateTimeHour`・`DateTimeMinute`・`DateTimeSecond`・`DateTimeMillisecond`（`DateTime` → `int`）、`LocalTimeOffset`（`TimeSpan`。候補として見た）、`Pack_Double2`、`Repeat01_Double`・`Clamp01_Double`。`LocalNow` は無い。`resoloop flux check` で `ToLocalTime(UtcNow)`・`DateTimeHour(L)->as<double>`・`Sod / N`（double の割り算）が書けることを試しのファイル（scratchpad、コミットしない）で確かめ、`flux/P3ForestClock.pg` はヒント 4 件（`DynamicVariableValueInput` の代わりに `~input<T>` が使える）だけでコンパイル成功
2. **Reflection（`resoloop type describe`・`specialize`）**: `[FrooxEngine]FrooxEngine.ValueField<double2>`（`Value: double2`）、`FrooxEngine.PBS_Metallic` の `EmissiveColor`（`colorX`）
3. **E の宣言**: キノコの発光の部品 `<個体>_Glow` 14 個は、それぞれ MeshRenderer 1 つに共有の材質 `MAT_EFR_MushGlow`（`AlbedoColor` (0.854, 0.964, 1.0)、`EmissiveColor` sRGB (1.2066, 1.5536, 1.6579) = 線形 (1.536, 2.752, 3.2)）1 つだけ。同じ材質を使うほかの物は池 `EFR_Pond_001` だけ（5 つの材質の 4 つ目）。時計塔の Pivot 3 つは asset root（Resonite の Y まわり +90°）の子で、基準の回転は単位、メッシュは子の `_HourHand`・`_MinuteHand`・`_Bell`
4. **Blender の確かめ**（保存しない一時的なスクリプト。親の checkout の `tmp/w10e/blender_sweep/sweep_e.py`・`sweep_e.json`）: E の `.blend` に M07 の `.blend` を W09R-E と同じく `_Body` の下に置き、鐘を ±25°（0.5° ごと）、時針・分針を 1 周（3° ごと）回して、M07・鐘の腕木・もう一方の針との三角形の交差と最短距離を数えた（`mathutils.bvhtree`）
   - 鐘と M07: 交差 0、最短 0.292 m（−25° のとき）
   - 鐘と腕木: どの角度でも交差がある。腕木の吊り棒（半径 2.2 cm）の先が、基準姿勢で鐘の上の金具（幅 12 cm・高さ 10 cm の箱）に 1 cm 入っている（W06 の形。吊り点）ため。±22° より大きく振ると、金具の上面の縁が吊り棒の側面を横切り、交差する三角形が 5 → 11 になる。どれも吊り点から 3 cm 以内の金具の中で、外からは見えない。腕木の屋根（下面は吊り点の 0.17 m 上）には届かない
   - 針と M07: 交差 0、最短は時針 1.94 cm・分針 5.45 cm（W09R-E の 1.25 cm は軸受けまでの隙間の別の測り方）。針どうし: 交差 0、最短 1.0 cm。腕木とは 1.7 m 以上

### 20.3 保存の後の最初の diff

何も変える前（03:58:46〜04:00:03Z）に、今の `main` のまま 6 キーを export した宣言（`exports/p2_static/<key>-20261103T035710Z`。W10〜W10-D の駆動は入っている）で、全 19 宣言（`content/main.json`・6 キー・M01 の 3 つ・M02・M03・M04・M05 の 2 つ・M06・M07・M08・`content/p3_gimmicks.json`）の diff を取った。どれも変更 0・警告 0（no-op 29・184・668・339・349・389・780・16・15・15・17・16・18・15・15・15・16・19・29。W10-D の完了時と同じ数）。資産の作り直し・重複は無い。W10〜W10-D の 5 つのモジュール（`P3PlazaDance`・`P3FountainGlow`・`P3MansionMotion`・`P3CandyStreet`・`P3GhostTrain`）は配備されたまま（`P3_Gimmicks` の下の Slot・Component は 193・249、74・86、136・174、223・291、204・250）。W08 の root の下は Slot 1,576・Component 2,818（W10-D の完了時と同じ。利用者が手で変えた所は無い）

- 新しい worktree の準備: 全キーの `.blend` の作り直し（03:49〜03:55Z、約 6.5 分。確認画像を描く）、Blender の確かめ（20.2 の 4）のための M07 の `.blend`（約 1 分。M07 のビルドが書き換えた `assets/manifest/M07.json` と、全キーの確認画像は戻した）、Git の外の `p2_bundles/<M>-<UTC>/` を同じ名前の `exports/p2_meshy/` へ写した（`SHA256SUMS` が全 9 つ一致）
- apply の前のスナップショット: 親の checkout の `tmp/w10e/01_snapshot_before_20261103T040010Z`（W08 の root 全体。最初の diff の後、最初の apply まで書き込みは無い）

### 20.4 手順

4 章の手順に、次を足す（`T` は親の checkout の `tmp/w10e/`）。

```sh
uv run python modeling/p2_static/export_p2.py --url "$URL" --key E_forest   # キノコの個体ごとの材質、時計塔の中継と managedFields、検査用の時計を足した p2.apply.json と p3_drivers.json
resoloop diff exports/p2_static/E_forest-<UTC>/p2.apply.json --state "$ST/p2_E_forest.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply exports/p2_static/E_forest-<UTC>/p2.apply.json --state "$ST/p2_E_forest.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/build_content.py   # E の state から Pivot のキーを、E の最新の export から発光の基準を読み、flux/P3ForestClock.pg・flux/p3_forest_clock.flux.json も作る
resoloop diff content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --brief --report "$T/<新しいファイル>" --url "$URL" --json
resoloop apply content/p3_gimmicks.json --state "$ST/p3_gimmicks.json" --url "$URL" --json
uv run python modeling/p3_gimmicks/deploy_flux.py --url "$URL" --manifest flux/p3_forest_clock.flux.json --report "$T/<新しいファイル>"
# 同じ diff・apply・配備をもう 1 回行い、変更 0・書き込み 0・配備 no-op を確かめる
uv run python modeling/p3_gimmicks/verify_e.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g18_g20_live_checks.json --windows 2 --gap 300
uv run python modeling/p3_gimmicks/verify_e.py --url "$URL" --raw-out "$T/<新しいファイル>" --output review/p3_gimmicks/g18_g20_param_checks.json --param-check
```

- `build_content.py` は E の state に時計塔の Pivot が無いと止まり、E の最新の export で Pivot の基準の回転が単位でない、キノコの個体ごとの材質が 14 個揃わない・発光の初期値が個体ごとに違うと止まる。`gimmicks.g18()`・`g20()` は W06 のアセット一覧の発光の部品・軸・範囲・周期の説明がこの形でなければ止まる
- G18・G20 の deploy state は親の checkout の `.resoloop/flux-state/p3_forest_clock.json`
- `verify_e.py` の窓は、時計で挟んだ G18 を 30 秒（2 個ずつ、14 個を一巡するまで）、14 個を続けて 20 秒、時計で挟んだ G20 を 30 秒観察する。窓の最初の時刻を止めた標本と `--param-check` は HMC_P3 の値を変えて測り、最後に元に戻ったかを確かめる（途中でキノコが止まり、鐘が 20 秒ごとに揺れるので、確認中に見ている人がいれば伝える）

### 20.5 G18・G20 の結果

最終の実行（GPT のレビュー（20.11）で直した検査）: `verify_e.py --windows 2 --gap 300`（06:01:10Z と 06:09:35Z の 2 つの窓。間の 5 分は resoloop を実行していない。`review/p3_gimmicks/g18_g20_live_checks.json`）と `--param-check`（05:49〜05:53Z。`g18_g20_param_checks.json`）。どれも問題 0。そのほか、正時をまたいだ既定の鐘の観察 2 回（04:59:15〜05:00:35Z と 05:59:20〜06:00:34Z。親の checkout の `tmp/w10e/bell_hour_raw.json`・`bell_hour2_raw.json`）、直す前の検査での 2 つの窓（05:18:13Z・05:26:26Z）と `--param-check`（05:13Z。どちらも合格）、試しの 1 つの窓 2 回（04:18Z・04:25Z）・`--param-check`（04:30Z）・2 つの窓（04:35Z・04:44Z）を実行した。04:35Z の 2 つの窓の 2 つ目で「近くの組が揃って変わる」の判定が外れ、判定をデータからの記録に替えた（この節の「揃わない」の行）

| 項目 | 結果 |
|---|---|
| G18 の式（時計で挟んだ照合） | 両方の窓で 14 個とも、2 個ずつ「時計 1 → 発光 → 発光 → 時計 2」を読んだ倍率（線形の色 ÷ P2 の発光）が、時計 1・2 の間のワールドの時刻の式の値の範囲の中（許容 0.003）。判定した観察 14・21 回、時計の幅 0.35〜0.60 秒。3 つの成分の倍率の差は 0.001 未満（色合いは P2 のまま）。ゆっくりの時刻（`G18Speed` 0.05。変化は 1/20）と速い時刻（2）でも 14 個とも式の範囲の中（時計の幅 0.23〜0.32 秒。ゆっくりの時刻の範囲は 1 回 最大 0.01 程度なので、周期・位相を細かく見る） |
| G18 の個体ごとの位相・強さ | 時刻を止めた標本（`G18Speed` = 0）で 14 個とも I (lo + (hi − lo)(0.5 + 0.5 sin(2π φ / T))) と 1e-4 以内（`G18Intensity` 1・0.5・3 → 2・−1 → 0 のそれぞれ）。0.5 で倍率 0.176〜0.487、2 で 0.703〜1.948、0 で消える。2 つの窓の標本の差は 0.0（漂わない） |
| G18 の強さの範囲 | 14 個を続けて読んだ観察（5・7 回）と時計で挟んだ観察で、倍率は 0.3503〜0.9998（W06 の 0.35〜1.0 の中） |
| 揃わない | 近くの組 10 組（発光の部品が最も近い個体どうし）の、観察した倍率の差の最大は 0.27〜0.65。W06 のデータから求めると、9 組は 20 秒続けて揃う（倍率の差 0.1 未満）ことが無い。`EFR_MushroomTall_004`（5.69 秒）と `EFR_MushroomMedium_003`（5.61 秒、2.6 m 離れている）だけは、位相の差が 399 秒で一巡し、最長 41.9 秒揃って見える（時間の 5.6%）。最初の 2 つの窓の 2 つ目（04:44Z）はちょうどその時間に当たり、観察した差の最大が 0.028 で「揃って変わる」の判定が外れた。周期が違うのでまたずれていく（W06 のデータどおり）。利用者の決定で W06 のデータのままにし（20.9）、判定は「データからの記録」（`verify_e.sync_report`、`g18_neighbour_sync`）に替えた。同じ出力に結ばれた組（モジュールの誤り）は、個体ごとの式と照合する時計で挟んだ照合が見つける |
| G20 の針 | 両方の窓で、「時計 1 → 時針 → 分針 → 鐘 → 時計 2」を読んだ中継の角度が、時計のローカル時刻の式の値の範囲の中（判定した観察 11・14 回。時計の幅 0.50〜0.72 秒）。時計の幅の中点の式との差は時針 0.0015°・分針 0.0058° 以下（分針 6°/分、時針 0.5°/分）。回転は Pivot のローカル Z（Blender の Y）まわりだけ（ほかの成分 1e-4 未満）。針の先（Pivot のローカル +Y を回した向き）が、前から見て 12 時から時計回りの向き（W06: 3 時 = −X_B）と 0.03° 以内 |
| G20 の時刻の基準 | 時計のローカル時刻は、この端末の UTC（壁の時計）に +9:00 を足した値と 1 秒前後の差（observe の実行時間の半分の中）。+9:00 は、Resonite を動かしている端末（この端末と同じ）のタイムゾーン（`TZ=Asia/Tokyo`）から入力した期待の値（`--utc-offset-hours`。GPT のレビュー M-3）と一致。`ToLocalTime` が抜けて UTC のまま動けば差は 0 で外れる。針はその時刻（撮影でも 14:00 過ぎに 2 時を指す。20.8） |
| Pivot そのもの | 両方の窓の最初と最後（4 回）に、「時計 → hierarchy → 時計」で時針・分針・鐘の Pivot の Slot の回転を読み、挟んだローカル時刻（3.5〜4.7 秒の幅）の式の範囲の中（例: 06:01Z の時針 90.990°（式 90.975〜91.005°）・分針 11.878°（11.695〜12.060°）、06:12Z の分針 75.317°（75.135〜75.495°））。鐘は真下。中継の値だけでなく、Pivot が中継に追従している（GPT のレビュー M-2） |
| 文字盤の中心 | 時針・分針の Pivot の位置（Resonite のローカル x・y = Blender の x・z）と、M07 の文字盤の中心（`review/M07/checks.json` の `dial.centre_local_m`）のずれ 0.0 m（許容 1 cm）。針の回る範囲は W06 の包絡と一致し、M07 の面とは交差しない（20.2 の 4。W09R の検査の `check_dial_hands` も合格。20.7） |
| G20 の鐘（既定） | 正時を 2 回観察した。ローカル時刻 14:00:00（日本時間）の節目の後に揺れ（最大 22.99°。式の最初の山 約 23°）、節目の前と、節目から 12 秒の後の 27 回の観察は真下（角度 0）。15:00:00 の節目の後も揺れ（最大 15.27°）、前後の 21 回は真下。ただし、どちらも揺れている間の観察（6 回・3 回）は時計の幅が 0.3 秒を超え（14:00 は 5 つの Component を読んだ 0.47〜0.61 秒、15:00 は鐘だけで 0.24〜0.43 秒のうち揺れている間の 3 回）、GPT のレビュー M-1 で直した判定では式との照合に数えない（15:00 の観察の判定は「観察した節目 0」で外れた）。式との照合は、同じ式の間隔を 20 秒にした値の確認で行った（次の行）。どちらの観察も、範囲の超過・節目の間の揺れ・X 軸以外の回転は 0。2 つの窓は節目の間で、鐘は真下のまま |
| G20 の鐘（節目の間隔を短く） | 鐘だけを時計で挟んで読み（時計の幅 0.23〜0.32 秒）、`G20BellInterval` 20 秒で、節目（ローカル時刻の秒が 20 の倍数）ごとに揺れ、時計の幅 0.3 秒以下の観察（節目ごとに 2〜5 回）がすべて式の範囲の中、節目の間（12〜20 秒）は真下（鳴り直さない）。`G20BellSwing` 3 → 1 に収まり 2 つの節目で最大 22.38°・12.01°（観察の間隔で山を外すことがある）、0.5 で最大 8.75°（12.5° 以内）、`G20BellInterval` 5 → 20 に収まり最大 6.68° |
| 戻した値 | `G18Intensity` 1、`G18Speed` 1、`G20BellSwing` 1、`G20BellInterval` 3600（変える前と同じ。違えば問題にする） |
| 構造 | 両方の窓の最初と最後で、時計塔の子孫 11 個が宣言と同じパスで同じローカルの変換（Pivot は回転を除く）。中継 3 つは有効で、`Drives` は自分の Pivot の `Rotation` を指す |
| 共有の材質 | E のすべての MeshRenderer（115 個）の `Materials` が、G18 を足す前の宣言（同じ export の `model.apply.json`）の並びと同じ（キノコの 14 個の `_Glow` だけ個体ごとの材質）。池 `EFR_Pond_001` は共有の材質のまま。共有の材質の値は G18 を足す前の宣言の値のまま（発光も P2 のまま）、個体ごとの材質の `EmissiveColor` 以外の値もそれと同じ（基準を G18 を足す前の宣言にしたのは GPT のレビュー m-1） |
| はみ出し（包絡） | 時針・分針を 1 周（5° ごと）、鐘を ±25°（1° ごと）回したバンドルのメッシュの点の外接箱は、W06 の包絡（`motion_envelopes`）と一致（はみ出し 0.0 m）。いちばん低い点は歩く高さ（2.8 m）より 4.30 m（分針）・4.61 m（時針）・7.40 m（鐘）上。E の除外範囲（主動線・視線・入口）と鑑賞位置（時計と鐘を見る前庭 `EFR_View_Forecourt` を含む）に入る点 0。キノコは動かない |
| 常駐しない | 2 つの窓の間の 5 分は resoloop を実行せず、2 つ目の窓で G18 の式・G20 の針が時刻どおり。正時の鐘も、接続していない間の時刻から決まる式どおり |
| 当たり判定 | 付けない（20.1）。針・鐘・キノコの下に `MeshCollider` は無く、P2 の宣言のまま |
| 利用者の確認 | 問題なし・60 fps 前後（20.9） |

- 生の観察は親の checkout の `tmp/w10e/e_windows_raw_2.json`・`e_param_raw_2.json`・`bell_hour_raw.json`（Git の対象外。ResoniteLink の ID を含む）。試しは `e_try1_raw.json`・`e_try2_raw.json`・`e_param_try1_raw.json`・`e_windows_raw_1.json`
- 1 回目の試し（04:18Z）は、observe が遅く（1 章の注）、時計の幅 0.62〜0.80 秒の観察が多くて、判定に使う上限（0.8 秒）の中の観察が足りず外れた。上限を 1.2 秒にした（時計の幅が広いほど式の範囲も広く判定は緩むが、細かい照合はゆっくりの時刻で行う）

### 20.6 diff・apply・配備と、再適用・所有範囲

| 時刻（UTC） | 宣言・操作 | diff | apply・配備 |
|---|---|---|---|
| 03:58〜04:00 | 全 19 宣言（20.3。`<key>-20261103T035710Z`） | どれも変更 0・警告 0 | — |
| 04:10〜04:11 | E（`E_forest-20261103T041006Z`。キノコの個体ごとの材質 14、時計塔の Pivot 3 つの中継と `managedFields`、時計 2） | 作成 19（`p3_g18_01`〜`14` の `PBS_Metallic`、Pivot の `ValueMultiDriver<floatQ>` 3、`ValueField<double2>` 2）・更新 14（キノコの `_Glow` の MeshRenderer の `Materials`。「one or more fields differ or depend on a new target」）・no-op 766・警告 0。`managedFields` の追加は今の値と同じで変更にならない | Component の追加 19・更新 14（資産は変更なし 115、取り込み 0） |
| 04:11 | P3（`content/p3_gimmicks.json`） | 作成 5（Slot `G18_G20_Forest`、値の Component 4）・no-op 29 | Slot の作成 1・Component の追加 4 |
| 04:11 | ProtoFlux（`deploy_flux.py --manifest flux/p3_forest_clock.flux.json`） | — | モジュール `P3ForestClock` を `P3_Gimmicks/G18_G20_Forest` の下に作成（`action` create、drive の結び先 19 個がすべて解決） |
| 04:12 | E・P3 の 2 回目の diff（動いている最中） | どちらも変更 0・警告 0（E は no-op 799、P3 は 34）。針・鐘の回転とキノコの発光は差分にならない | — |
| 04:12〜04:13 | E・P3 の 2 回目の apply、2 回目の配備 | — | apply はどれも書き込み 0（作成・更新・削除 0、資産の取り込み 0）。配備は `no-op`（「source and transitive dependency hashes match deploy state」） |

### 20.7 既存の検査

- 動いている状態（04:48〜04:58Z）で実行した（親の checkout の `tmp/w10e/prev_checks.sh`）。どれも直していない（`rest_pose.py` は `gimmicks.driven_slots()` に E の Pivot を足しただけで、Pivot の回転も基準姿勢に戻す）
- W10 の G01・G13（`verify_live.py`、1 つの窓 30 秒）: 合格（G13 17.966°/s、上から見て反時計回り）。W10-A の G03（`verify_g03.py`）: 合格（A の MeshRenderer 110 個の材質の並びも基準どおり）。W10-B の G05・G06（`verify_b.py`）: 合格（おばけの上下 −0.099〜+0.350 m・揺れ ±20° 以内、扉 0〜85.0°）。W10-C の G09・G11（`verify_c.py`）: 合格（攪拌 59.88°/s、巡回 8.00°/s）。W10-D の G15（`verify_d.py`、1 つの窓）: 合格（時計で挟んだ照合で先頭車 2.19994・客車 2.19986 m/s）。親の checkout の `tmp/w10e/p3_prev_live_1.json`・`g03_prev_live_1.json`・`b_prev_live_1.json`・`c_prev_live_1.json`・`d_prev_live_1.json`。W10 の `live_checks.json`・`param_checks.json` は書き換えていない
- W09R（`modeling/p2_meshy/verify_live.py`）: 全項目合格（M01〜M08 の 9 行、5 地区の数）。今回は state の URL の更新は要らなかった（W10-D の保存の後、ワールドは開き直されていない）。E の数の照合は、P3 が足した Component 19（材質 14、中継 3、時計 2。キーの `p3_` で数える）を加えて一致（Slot 196・Component 501）。基準姿勢への置き換えは 23 個（W10-D までの 20 個と、時計塔の Pivot 3 つ）。W08 の root の下は Slot 1,985・Component 3,336。`tmp/w10e/p2_meshy_live_1.json`。`review/p2_meshy/live_checks.json` は書き換えていない
- W08（`modeling/p2_static/verify_live.py`）: W09R 以降の既知の 11 件のまま（項目は 11 章と同じ）。E の件は実物と宣言の Component がどちらも 19 増えた（482 / 403 → 501 / 422）だけで、G18・G20 による失敗は 0（`tmp/w10e/p2_static_checks_1.json`）。`review/p2_static/live_checks.json` は書き換えていない

### 20.8 撮影（`review/p3_gimmicks/`、1600×900、カメラは `content/p3_gimmicks.json` の `cameras`。05:00:50〜05:01:00Z）

- `g18_mushrooms.jpg`（東の木道の上から森の北）・`g18_mushrooms_south.jpg`（南の休憩所の大きなキノコのまわり）: キノコの傘の裏と斑点が個体ごとに違う明るさで光る（1 枚の中で明るい物と暗い物が混ざる）。池の睡蓮の光り方は P2 のまま。黒い面・透けなし
- `g20_clock.jpg`（東の正面から文字盤）: 撮影した 14:00:5x（日本時間）に、分針は 12 の少し右、時針は 2 を指す（前から見て時計回り）。針は M07 の文字盤の中心の軸の上で、文字盤の前
- `g20_bell.jpg`（北から鐘）: 節目の間で、鐘は腕木の下に真下に下がっている。撮影の `scene.json` は親の checkout の `tmp/w10e/capture_scenes/`（コミットしない）

### 20.9 実機の確認と負荷

- 利用者の確認（確認事項 6、2026-11-03 05:02〜05:12Z ごろ）: 「問題なし」。デスクトップで、キノコの発光（周期のばらつき・明るさ）、時計の針（利用者の端末の時刻を時計回りに指す）、鐘（確認のため `G20BellInterval` を一時的に 20 秒にして、20 秒ごとに 12 秒揺れて止まる）を見た。確認の後に 3600 に戻した（05:13Z）
- 利用者の決定（同じ確認のとき）: 周期の近い組 `EFR_MushroomTall_004`・`EFR_MushroomMedium_003` が約 6.7 分ごとに最長約 42 秒揃って見える件（20.5）は、W06 のデータのままにする（選択肢は「W06 のデータのまま」（推奨）と「片方の周期を変えて E を作り直す」）。W06 への要望として `handoff/W10-E.md` 6.3 に書いた
- 負荷（確認事項 8）: W08 の基準と同じ端末で 60 fps 前後（利用者の確認。森の中か時計塔の前）
- 足した物: E の Component 19（材質 14、中継 3、時計 2）、P3 の宣言の Slot 1・Component 4、モジュール `P3ForestClock` の Slot 408・Component 495（親の checkout の `tmp/w10e/02_snapshot_after_*`）。W08 の root の下は Slot 1,576・Component 2,818 → 1,985・3,336。粒子なし、光源なし
- モジュールが大きいのは、キノコ 14 個の式（個体ごとに角度・倍率・色の 3 成分）を個体ごとのノードで組んだため（1 個あたり 約 20 ノード）。60 fps 前後で、減らす必要は無かった

### 20.10 先行 10 種類のまとめ

先行 10 種類（Spec §8: G01・G03・G05・G06・G09・G11・G13・G15・G18・G20）が、W10・W10-A〜E の 6 つの子で揃った。どれも Resonite の中だけで動き（resoloop を常駐させない）、時刻（`WorldTimeDouble`、G20 だけは見る人のローカル時刻）と同期する HMC_P3 の値から決まる drive で、インパルス・同期する書き込みは無い。

| 子 | ギミック | 駆動 | 地区に足した Component | モジュールの Slot・Component | 利用者の fps |
|---|---|---|---|---|---|
| W10 #56 | G13・G01 | `Spinner`、ProtoFlux `P3PlazaDance` | A 12（中継）、D 1（`Spinner`） | 192・249 | 60 前後 |
| W10-A #58 | G03 | ProtoFlux `P3FountainGlow` | A 1（材質） | 73・86 | 60 前後 |
| W10-B #59 | G05・G06 | ProtoFlux `P3MansionMotion` | B 6（中継） | 135・174 | 60 前後 |
| W10-C #60 | G09・G11 | ProtoFlux `P3CandyStreet`、PhotonDust | C 31（中継 5、材質 1、粒子 25） | 222・291 | 60 前後 |
| W10-D #61 | G15 | ProtoFlux `P3GhostTrain` | D 10（中継 8、時計 2） | 203・250 | 60 前後 |
| W10-E #62 | G18・G20 | ProtoFlux `P3ForestClock` | E 19（材質 14、中継 3、時計 2） | 408・495 | 60 前後 |
| 計 | 10 種類 | `Spinner` 1、モジュール 6 | 80 | 1,233・1,545 | — |

- P3 の宣言（`P3_Gimmicks`）: Slot 7（root と配備先 6）、Component 27（宣言の `DynamicVariableSpace` 1・値 25 と、Resonite が足す `AI_GeneratedContent` 1）。`P3_Gimmicks` の下の全体は Slot 1,240・Component 1,572
- W08 の root の下: P2 の完了時（W09R-E の後）の Slot 745・Component 1,684 → 先行 10 種類の後 1,985・3,336（P3 で +1,240・+1,652。モジュールが大半）。fps は W08 の基準の 60 前後のまま（どの子も利用者の確認）。粒子は G09 の泡・煙だけ（最大 16 + 24 個）、光源は P3 で増やしていない
- 負荷で気になる所: モジュールのノード数（G18 の 14 個の式が 400 を超える）。追加の 10 種類で同じ形（個体ごとの式）が増えるなら、同じ式の個体を 1 つのノードの組で回す（ProtoFlux の値の配列や、周期だけ違う個体を 1 つの式の入力の違いにする）か、`TimeSineDriver` のような標準の Component で足りる物はそれにする（Spec §8「標準コンポーネントを優先」）。メモリ・VR・2 人以上の負荷は P4
- 方式の定まった型（後続の子が使える）: 回転だけ（`Spinner`・中継の回転 1 つ、`managedFields` ["position", "scale"]）、位置と回転（中継 2 つ、`managedFields` ["scale"]）、閉じた経路（三角補間 G11・スタジアム型 G15）、発光（共有の材質を写した専用の材質 G03・G18、液面 G09）、粒子（G09）、一度だけの演出（G20 の鐘。節目からの時刻の関数）、検査用の時計（G15・G20）
- 追加の 10 種類・W11 の進め方の案は `handoff/W10-E.md` 6.2

### 20.11 GPT のレビュー（確認事項 7）と保存（確認事項 4）

- GPT のレビュー: `codex exec --sandbox read-only -C <worktree> -o <出力> "<依頼文>" < /dev/null`（モデル gpt-6-astra、05:32〜05:43Z）。対象は PR #67 の `b5b0445`。Resonite には接続させず、checkout も変更させていない。観点は、宣言と駆動の正しさ、実測の検査、既存の検査への影響、記録の正確さ、テストの採用基準の 5 つ。全文は PR #67 のコメント
- 結果: Major 3 件・Minor 2 件・Info 1 件（宣言と駆動・既存の検査への影響は指摘なし）。採否は「直さないと、誤った状態を合格と報告するか」で決めた

| # | 重大度 | 指摘 | 採否 | 対応 |
|---|---|---|---|---|
| M-1 | Major | 鐘の照合を時計の幅 1.2 秒の観察でも行うので、12 秒で 3 往復する誤った式（1.85 秒ごと・幅 1.19 秒の 24 回）を合格にする | 採用 | 往復の回数の違う鐘を合格と報告するため。揺れている間の鐘は、時計の幅 0.3 秒以下の観察だけで式と照合する（`BELL_SPREAD_MAX_S`。0.3 秒なら 3〜12 往復の誤りを試した 40 通りの観察のどれでもすり抜けない）。節目ごとに、そうした観察が 2 つ以上ないと「観察した節目」に数えない（`check_bell_marks`）。広い観察は揺れを判定しない（真下と範囲の超過は判定する）。正時の観察も鐘だけを読み直した（20.5） |
| M-2 | Major | 時系列で読むのは中継の `Value` だけで、Pivot そのものの回転を照合していない。中継の値だけが進み Pivot が追従しない状態を見分けられない | 採用 | 針が止まっていても合格と報告するため。窓の最初と最後に「時計 → hierarchy → 時計」で Pivot の Slot の回転を読み、挟んだローカル時刻の式の範囲の中かを見る（`pivot_probe`・`check_pivots`） |
| M-3 | Major | UTC との差を 15 分の倍数に丸めた残りだけを見るので、`ToLocalTime` が抜けて時計も針も UTC で動いても合格する | 採用 | 利用者の決定（ローカル時刻）と違う時計を合格と報告するため。Resonite を動かす端末のタイムゾーンの UTC からの時間を入力（`--utc-offset-hours`。既定はこの端末のタイムゾーン = 同じ端末の Resonite のタイムゾーン、`TZ=Asia/Tokyo` で +9）にし、時計の差と照合する |
| m-1 | Minor | 共有の材質の比較の基準を、G18 を足した後の宣言から取っている。共有の材質を変えた宣言を apply すると、池の見た目が変わっても合格する | 採用 | 池の見た目が変わった状態を合格と報告するため（W10-A のレビューの M と同じ型）。基準を G18 を足す前の宣言（`model.apply.json`）の共有の材質にし、個体ごとの材質の値もそれと照合する |
| m-2 | Minor | 同じ出力の組のテストと周期・位相の違うテストが、同じ範囲の判定を守っている（D） | 採用 | テストの採用基準の違反。同じ出力の組を代表の 1 例にまとめ、周期・位相の例を外した |
| I-1 | Info | handoff のテストの件数（9）と「針の式と照合の式の両方を逆にした」の説明が、コードと違う | 採用 | テストを直すので、同じ段落を実際のコードに合わせて書き直した |

- テスト（S）: 指摘 M-1〜M-3・m-1 の守りに、反例と正しい状態を足した（`tests/test_p3_gimmicks_e_verify.py`。10 件）。守りを外す 20 の変異で、それぞれ狙ったテストが失敗することを確かめた。例外は `judge_bell` の「時計の幅が広い観察は揺れを判定しない」で、外しても誤った合格にはならない（広い観察は節目の観察に数えず、`check_bell_marks` が M-1 の反例を問題にする）ので、守りの重なりとしてテストしていない
- 直した検査で実機を測り直した（20.5）

#### 20.11.1 保存

<!-- SAVE -->

### 20.12 Resonite で未確認の項目

- 2 人以上での同期、途中参加（P4）。この子の確認は、使った Component・ノードの仕組みの説明（20.1）と、単独の確認まで。G20 は見る人のローカル時刻なので、タイムゾーンの違う 2 人は違う時刻の針と鐘を見る（利用者の決定。同期しないことが仕様）。G18 は `WorldTimeDouble` なので、同じワールドの人は同じ明るさを見るはず（未確認）
- 保存・再読込の後に、材質・中継・モジュール・時計・HMC_P3 の値が残って動くか（P4）
- 端末の時計がずれている人の G20（ローカル時刻の元は各自の端末の UTC。ずれていれば、その人だけ針と鐘がずれる）
- VR での見え方、メモリの負荷、鐘の音（素材が無い。範囲外）
