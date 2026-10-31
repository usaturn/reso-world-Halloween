# P1 の引き継ぎ（W07、Issue #9）

Halloween Magical Carnival の P1（Blender での静的造形）の引き継ぎ文書。親 #1 の Spec §5.2「引き継ぎ文書」と §13「各タスクの引き継ぎに必須の項目」に当たる。

- **P1 の完了は「Blender 造形の完了」であり、「Resonite ワールドの完成」ではない**（Spec §5.2）。Resonite への apply、Meshy 素材の差し替え、ProtoFlux・ギミックは P2 以降で、この文書の時点では何も行っていない
- 確認した版: `main` の `4570658`（W09-M04 のマージ）に W07 の変更を足したもの（作業は `e592a94` から始め、PR の前に載せ直した。M04 の追加は P1 のキーに影響しない）。resoloop 0.2.0、Blender 5.0.1（`docs/environment.md`）
- 担当: Claude Code（Opus 5.5）、2026-10-31
- 出力の確認の結果は `docs/p1-export-report.md`、W07 自身の引き継ぎは `handoff/W07.md`

## 1. 完了した範囲

| キー | 子 Issue | PR（マージ commit） | 内容 | アセット | オブジェクト | 三角形 | 引き継ぎ |
|---|---|---|---|---|---|---|---|
| `probe` | W00 #2 | #10（`0e7c5c1`） | P0 の小規模検証（規約・形式・検査コマンド） | 3 | 7 | — | `handoff/W00.md`、`docs/p0-report.md` |
| `world` | W01 #3 | #11（`7641292`） | 地形・5 つの島・環状道路・4 本の主動線の橋・4 本の連絡橋・崖の柵・遠景の岩 | 13 | 21 | 12,088 | `handoff/W01.md` |
| `common` | W01 #3 | #11 | 共通部品 7 種（街灯・柵・手すり・ガーランド・ベンチ・ランタン・小カボチャ） | 7 | 7 | 2,200 | `handoff/W01.md` |
| （キー名の統一） | W01A #12 | #23（`9479b21`） | 地区キーと接頭辞を Issue に揃え、`meshy`・`M01`〜`M08` を足した | — | — | — | `handoff/W01A.md` |
| `A_plaza` | W02 #4 | #30（`d035a10`） | 中央広場（噴水・M02 の仮モデル・踊るカボチャ・浮かぶキャンディ・順番に光るランタン・操作台 3 基・ショーの台）と南の入口（M01 の仮モデル・案内板） | 29 | 141 | 18,448 | `handoff/W02.md` |
| `B_mansion` | W03 #5 | #33（`6529185`） | 北の前庭・門・M03 の仮モデル・観音開きの扉・玄関ホール・墓石・枯れ木・おばけ・窓のおばけ・鐘 | 16 | 66 | 7,540 | `handoff/W03.md` |
| `C_candy` | W04 #6 | #36（`446ca12`） | 東の通り・キャンディのアーチ・屋台 4 軒・M04 の仮モデル・大釜と色の操作台・製造機・ほうき・魔女の巡回路と M08 の仮モデル | 29 | 53 | 12,116 | `handoff/W04.md` |
| `D_amusement` | W05 #7 | #31（`6c37199`） | 南の遊園地（回転木馬と M05 の仮モデル・列車の周回路と M06 の仮モデル・カップ・チケット売り場・屋台） | 7 | 76 | 15,628 | `handoff/W05.md` |
| `E_forest` | W06 #8 | #28（`5807f37`） | 西の森（木・顔のある木・キノコ・コウモリ・木道・池と小橋・展望台・休憩所・M07 の仮モデルと文字盤・針・鐘） | 23 | 146 | 57,978 | `handoff/W06.md` |
| `overview` | W07 #9 | この PR | 全体確認用シーン・統合の検査・確認画像・地区ごとの export・この文書 | （統合 124） | 503 | 123,798 | `handoff/W07.md` |

- 数は W07 の再生成（6 章の手順）の実測。`world` と `D_amusement` の三角形は W07 の直し（4 章の 1・5）の後の値（直す前 11,824・15,348）。ほかのキーは直しの前後で同じ数。`overview` は 6 キー（`common` を除く）の合計
- Meshy 素材の準備（W09 #13 と W09-M01〜M08 #14〜#21）は P1 と並行したボードの子で、W07 の対象外。2026-10-31T14:45Z 時点で、W09 と W09-M01〜M08 はすべて `completed`（最後の M04 は PR #39、`main` の `4570658`）。状態は 5 章

## 2. 全体確認用シーン（キー `overview`）

- 再生成: `resoloop blender run modeling/overview/build.py --json`（確認画像を作らないときは `--arg=--no-render`）。先に各キーの `.blend` が要る（6 章の順）
- 中身: `world`・`A_plaza`・`B_mansion`・`C_candy`・`D_amusement`・`E_forest` の `.blend` からキーのコレクションを append でコピーし、`overview` の下に置く（ライブラリの参照は残さない）。`common` は地区の中に配置済みなので、単体の並べた形は置かない。地区ごとに持っている共通部品の材質・メッシュの写しは、内容が同じことを確かめて 1 つにまとめる（今回、材質 35・メッシュ 24。内容の違う写しは無かった）
- 出力: `blender/overview/overview.blend`（コミットしない）、`review/overview/*.png`（確認画像）、`review/overview/checks.json`（検査の記録）、`assets/manifest.json`（統合したアセット一覧）
- 統合したアセット一覧: `world`・`common`・5 地区のアセット一覧を順に写し、`export_result` を `exports/p1/<key>-<UTC>/` の最新の export に向ける（`modeling/overview/manifest_merge.py`）。`common` は単体で export しないので `unexported` のまま。M01〜M08 の仕上げた素材は含めない（それぞれ `assets/manifest/<M>.json`）
- `checks.json` に書く検査（Blender のシーンで実測）
  - 動線: W01 の 9 本の経路を 1 m ごと・3 本の線（中央と両端から 0.3 m 内側）で、床の有無・段差（30° を超える高さの変化）・腰から上の障害物・頭上 2 m・1 m の高さの有効幅を調べる
  - スポーン: 3 か所の半径の内側を 0.5 m の格子で同じく調べる
  - Meshy の仮モデル: 8 素材 9 行（M05 は柱と屋根）について、仮モデルの外接箱を `assets/meshy/received.json` の確定値と比べ、正面の向きと位置を `placement_hint` と比べる
  - 可動部品: 5 地区のアセット一覧の `motion_roots` 78 個について、別のオブジェクトか、メッシュを動かすか、原点がアセット一覧の `pivot_local` と一致するか、範囲（角度・移動量・ストローク・経路）の記録があるか
  - ランドマーク: W01 の 5 つのランドマークを、実際に作られたアセットの位置・高さと比べる
  - 地区間の面の重なり: ワールド全体の 0.5 m 格子で、上から見て最も上の 2 つの面が別のキーのもので、高さの差が 1 mm 以内の所を探す（オブジェクトごとの BVH で測るので、下に隠れた面も見つかる）。同じ高さで重なる面は、Resonite では z-fighting（ちらつき）、Cycles では真っ黒になる。同じオブジェクトの中の重なりはこの検査では見えないので、確認画像の黒い部分で見つける（3 章）
- 確認画像（`review/overview/`、Cycles CPU 24 サンプル）: 01・02 全景（南・北西の上から）、03 スポーンから広場、04 平面図と動線の検査の印（緑 = 床あり。段差・障害物などは別の色）、05〜09 地区ごと（桃色の点 = 可動部品の原点）、10〜13 主要な可動部品（A の噴水・カボチャ、B の扉・窓・鐘、C の大釜・製造機、D の回転木馬・列車・カップ）、14・15 北東・北西の連絡橋の着地点、20_placeholder_* Meshy の仮モデル 9 行

## 3. 受け入れ基準と確認結果

#9 の受け入れ基準（Spec §12「P1：Blender造形の完了条件」）ごとの結果。数は 2026-10-31 の W07 の実測（`review/overview/checks.json` と 6 章のコマンド）。

| 受け入れ基準 | 結果 | 証拠 |
|---|---|---|
| 5 エリアと中央・入口・主要な接続路が存在し、空間の構成が読み取れる | 満たす。全体確認用シーンに 6 キー 503 オブジェクト（`world` 21・`A_plaza` 141・`B_mansion` 66・`C_candy` 53・`D_amusement` 76・`E_forest` 146）。W01 の 9 本の経路（環状道路・4 本の主動線・4 本の連絡橋）を 1 m ごとに 3 本の線で測り、床の切れ目・段差・腰から上の障害物・頭上 2 m の干渉は 0（北東・北西の連絡橋の 0.59 m の段差は 4 章の 1 で直した）。有効幅の最小は主動線 3.30 m（ガーランドの門の柱）、環状道路 4.15 m、連絡橋 2.25 m（手すりの間）で、下限（3.0 m・2.0 m）以上。スポーン 3 か所の床は欠けなし（南の入口のベンチが空き半径に入る点は 8 章の 13） | `checks.json` の `routes`・`spawns`、`review/overview/01`〜`04`・`14`・`15` |
| 採用予定の Meshy 対象（M01〜M08）に、安定した ID・寸法・向き・仮モデルが用意されている | 満たす。8 素材 9 行すべてに仮モデルがあり、外接箱は確定値との差 0〜0.115 m（M06 の後端の連結部。差し替えの基準は確定値どおり）。向きは `placement_hint` と一致（M01・M02 は外接箱が対称で測定では判別できず、W02 の記録で南。回転する M05 と経路上の M06・M08 は基準姿勢で +Y）。差し替え先の ID の対応は 5 章 | `checks.json` の `placeholders`、`review/overview/20_placeholder_*.png` |
| 扉・回転床・座席・針・枝などが独立し、可動原点と範囲が記録されている | 満たす（注記あり）。5 地区の可動部品 78 個はすべて別のオブジェクトで、メッシュを動かし、原点はアセット一覧の `pivot_local` と 1 cm 以内で一致。範囲（角度・移動量・ストローク・経路）は 67 個で記録を確認。残る 11 個のうち 9 個は A の噴水の水（G03）と順番に光るランタン 8 基（G04）で、記録は発光・水の表現（点灯の順番・光の位置）で動きの範囲を持たない。2 個は A の入口の門の扉で、A のデータに角度が無いので、仕上げた M01 の値を 8 章の 4 に書いた。M07 の針の軸は仕上げた M07 に合わせた（4 章の 4） | `checks.json` の `motion`・`motion_parts`、7 章の表、`review/overview/05`〜`13`（桃色の点が原点） |
| `.blend` を再オープンして画像・材質・外部依存の欠損がない（全キーの .blend と全体確認用シーン） | 満たす。7 キーと `overview` の `.blend` を開き直し、見つからない画像 0・ライブラリ 0・`.001` の名前 0（どのキーも画像を使っていない）。`tools/check_blend.py` は全体で終了コード 0。全体確認用シーンは append の後にライブラリの記録を消し、外部の参照を残さない | `modeling/overview/blend_stats.py` の出力、`tools/check_blend.py`（`handoff/W07.md` 5.1） |
| 保存したスクリプトで対象範囲を再生成でき、他の完成範囲や受領素材を消さない（全キーを再生成して確かめる） | 満たす。7 キーを新規と既存の `.blend` を開いての 2 回ずつ作り直し、2 回の間でオブジェクト・メッシュ・材質・画像・三角形の数とオブジェクト名の一覧（SHA-256）が一致（直しを入れたキーは直した後に改めて 2 回）。`overview` も 2 回で同じ（`checks.json`・`assets/manifest.json` はバイト単位で同じ）。形を変えていないキーの配置データとアセット一覧の JSON は、作り直してもバイト単位で同じ。Meshy の置き場（Git の外）は全ファイルの名前・サイズ・更新時刻が作業の前後で同じで、`SHA256SUMS` も一致 | `handoff/W07.md` 5 章 |
| 全景・5 エリア・主要部品を Blender で確認し、確認画像と未解決事項を残した | 満たす。確認画像 24 枚を開いて目で確かめた。その中で見つけた不具合（環状道路・B の通路・C の歩道の黒い帯 = 同じ高さの面の重なり、C の近景のカメラの向き）は直して描き直した。未解決事項は 8 章 | `review/overview/*.png`、8 章 |
| 出力経路の確認結果（地区ごとの export のエラー・警告・非対応要素）と、Resonite で未確認の項目を区別して記録した | 満たす。6 キーの export・オフラインの validate はすべて終了コード 0、validate の issues 0、警告は性能の目安だけ。Resonite には接続していない | `docs/p1-export-report.md`、9 章 |
| P1 の引き継ぎ（`docs/p1-handoff.md`）を作成し、P2 以降へ無断で進まずに停止した | 満たす。この文書。Resonite への apply、Meshy 素材の差し替え、ProtoFlux・ギミック、P2 以降の起票はしていない | この文書、#9 の完了コメント |
| PR の差分に 3D モデル（`.blend`・`.glb`・`.gltf`・`.fbx`・`.obj` など）が無い | PR で確かめる（`git diff --name-only origin/main...HEAD` を `grep` で検査） | PR の本文 |

## 4. 統合で反映した修正（他の子の所有ファイル）

W00〜W06 がすべて `completed` で閉じたこと（2026-10-31T13:46Z に #2〜#8 を確認）を確かめてから、各子の handoff の要望と、W07 の統合の検査で見つかった不具合のうち、P1 の範囲で直すべきものだけを直した。地区の造形のやり直しはしていない。

| # | ファイル（所有） | 変更 | 理由 | 旧 → 新 |
|---|---|---|---|---|
| 1 | `modeling/world/build.py`（W01） | 北東・北西の連絡橋の板を、「C・E 側から (±19.0, 19.0) まで z 1.5 へ上がる坂（16.6°）」と「そこから北の台地へ z 1.5 で続く平らな部分」に分けた | W07 の動線の検査で見つかった不具合。板は (±22.5, 15.5, 0.02) から (±15.5, 22.5, 1.50) へ一直線に上がっていたので、北の台地（上面 z 1.5、縁 y = 20）の縁で板の上面が z 0.78〜1.2 しかなく、橋の上に高さ 0.3〜0.7 m の壁が斜めに立っていた（検査の実測は中央の線で 0.59 m の段差）。Spec §4.1「主要な段差にはスロープ」に反する | 板の区間: 1 本 → 2 本ずつ。`WLD_OuterLoopPaths_001` の三角形 912 → 1,176。オブジェクト名・ID は変えていない |
| 2 | `modeling/world/layout_data.py` → `layout/world_layout.json`（W01） | `Route_NE_Side_Bridge`・`Route_NW_Side_Bridge` の中間の経路点の高さと `max_slope_deg` | 1 の形に合わせた。経路点の折れ線の勾配は 19.47°（(±22, 16) の接続点が坂の始まりより 0.7 m 内側にあるため。板の坂は 16.6°）。`tests/test_world_layout.py` の「経路点の勾配が宣言値 + 1° 以下」を満たす | 中間点 (±19, 19, 0.75) → (±19, 19, 1.5)、`max_slope_deg` 10.1 → 19.5 |
| 3 | 同上（W01） | ランドマーク 4 つの位置・高さ・注視点を、実際に作られたアセットの実測に合わせ、E の ID と地区名を時計塔に合わせた | W06 の要望（handoff 6 章）と W07 の検査（`checks.json` の `landmarks`）。W01 の計画値のままだと、P2 が照明・視線を合わせる先がずれる | 下の対応表 |
| 4 | `modeling/E_forest/clock_tower.py`（W06） | `DIAL_CENTRE` の x・z を仕上げた M07 の文字盤の実測の中心に合わせ、針の根元の円を半径 0.06 → 0.10 m にした | W09-M07 の要望（handoff 6 章）。W09 の `dial_centre_face` は実物の中心より 6.3 cm 高く、P3 が回す針の軸（可動部品の原点）が実物とずれていた。根元の円は M07 の軸受け（中心の 3.5 cm 上）を隠す | `DIAL_CENTRE` (0.001, 0.364, 8.095) → (0.0015, 0.364, 8.032)。時針・分針の原点（`EFR_ClockTower_001_HourHandPivot`・`_MinuteHandPivot`）と仮の文字盤 `_Dial` が 6.3 cm 下がる。鐘の原点は x だけ 0.5 mm。部品名は変えていない |
| 5 | `modeling/D_amusement/mesh_helpers.py`・`assets_rides.py`（W05） | 取付位置 10 個（`DAM_*_Att_*`）を、子を持たない Empty から、原点が取付位置の小さな八角のメッシュ（半径 0.04 m、材質 `MAT_DAM_CarnivalGold`）に替えた | W07 の export の照合で見つかった不具合。`resoloop blender export --preserve-hierarchy` は子にメッシュを持たない Empty を省くので、D の取付位置（M05 の柱・屋根、M06 の車体・前照灯・連結器、カップの中央、売り場と屋台の看板・ランタン）がバンドルに 1 つも無かった。`docs/conventions.md` §4.2 の規則で、ほかの地区は小さなメッシュで作っている（A の `create_socket_attachment_mesh` と同じ形） | 名前・親・位置は同じ。D の Empty 28 → 18、メッシュのオブジェクト 48 → 58、三角形 15,348 → 15,628、export の Slot 88 → 98（`docs/p1-export-report.md`） |
| 6 | `modeling/D_amusement/build.py`（W05） | アセット一覧の `visual_roots` から取付位置を除いた | 5 でメッシュになった取付位置が、すべてのメッシュを入れる処理で `visual_roots` にも入ったため。取付位置は `attachment_points` だけに書く | 1 行 |
| 7 | `modeling/A_plaza/build.py`（W02） | 石畳の「環状道路の縁取り」の帯（半径 10.75〜14.25 m）の上面を z 0.06 → 0.063 にした | W07 の地区間の面の重なりの検査（`checks.json` の `coplanar_tops_between_keys`）で見つかった不具合。帯の上面が W01 の環状道路（`WLD_CentralRingRoad_001`）の上面 z 0.06 とぴったり重なり（約 224 m²）、全体の描画で真っ黒になった（Resonite では z-fighting になる）。0.063 は W01 の道路より 3 mm 上で、同じ石畳の中の十字の通路（上面 0.065）とも重ならない（W07 が途中で 0.065 にしたとき、交差点で十字の通路と重なったので改めた） | 数値 1 か所 |
| 8 | `modeling/B_mansion/build.py`（W03） | 前庭の中央のスレートの上面をローカル z 0.06 → 0.065（ワールド 1.56 → 1.565）にした | 7 と同じ検査。W01 の台地の上の主動線（`WLD_NorthBridge_001`、上面 z 1.56）とぴったり重なっていた（約 57 m²） | 数値 1 か所 |
| 9 | `modeling/C_candy/build.py`（W04） | 北・南の歩道と屋台の通りをつなぐ 2 つの箱を、x -10.2〜-8.4 → -9.7〜-8.8（両側の箱の間だけ）にした | W07 の全体の描画で見つかった不具合（C だけの確認画像 `review/C_candy/03_connections_and_patrol.png` にも出ていた）。つなぐ箱が歩道と屋台の通りに同じ高さ（上面 0.035）で重なり、細い帯が黒くなった（Resonite では z-fighting） | 数値 2 か所。歩ける面の形は変わらない |
| 10 | `docs/conventions.md`（W00） | §7.5 の export を `--parent` に直し、出力先・試験用の `--parent`・`--pack-pbr`・オフラインの validate を書いた。§7.2 に新しい checkout での検査の順序と `--no-file-check` を書いた | W09・W09-M01〜M08・W06 の要望。resoloop 0.2.0 では `--root-path` は `OPTION_REQUIRED: --parent is required.` で止まる | 文書のみ |

1〜9 で作り直した生成物（`layout/world_layout.json`・`assets/manifest/world.json`・`layout/areas/E_forest.json`・`assets/manifest/E_forest.json`・`assets/manifest/D_amusement.json` と、形が見て分かるほど変わった確認画像）もコミットした。A・B・C・D の確認画像は、変わったのが数 mm の高さ・重なりの解消・4 cm の金具だけなので、元の画像のままにした（A・B・C の元の画像は、それぞれの地区だけのシーンで描いたもので、重なりの相手が写っていないか、黒い帯が小さい）。

ランドマークの対応表（3）:

| ID | 位置（旧 → 新） | 高さ m（旧 → 新） | 注視点（旧 → 新） | 実際のアセット |
|---|---|---|---|---|
| `LM_A_PumpkinTower_001` | (0, 0, 0) のまま | 12.0 → 7.6 | (0, 0, 7.5) → (0, 0, 4.6) | `APL_GiantJackProxy_001`（噴水の器 z 1.6 の上、上端 z 7.6） |
| `LM_B_HauntedMansion_001` | (0, 36, 1.5) → (0, 41.5, 1.5) | 20.0 → 10.607 | (0, 36, 12) → (0, 41.5, 6.8) | `BMN_MansionPlaceholder_001`（M03 の確定寸法） |
| `LM_C_CandyArch_001` | (33, 0, 0) のまま | 9.5 のまま | 変更なし | `CCD_CandyArch_001`（計画値と一致） |
| `LM_D_CarouselGate_001` | (0, -33, 0) → (-10.5, -32, 0) | 12.0 → 9.901 | (0, -33, 6.5) → (-10.5, -32, 5.0) | `DAM_Carousel_001`（南の主動線を空けるため西に置かれた） |
| `LM_E_WitchWorkshop_001` → **`LM_E_ClockTower_001`** | (-35, 0, 0) → (-38.5, 0, 0) | 11.5 → 14.0 | (-35, 0, 6) → (-38.5, 0, 8.0) | `EFR_ClockTower_001`（M07 の仮モデル）。魔女の工房は C の M04 になった |

- E の地区名（`areas[].name`）: 「西・魔女の森と魔法工房 (Witch's Forest & Potion Workshop)」→「西・魔法の森と時計塔 (Enchanted Forest & Clock Tower)」（Spec §4.1 の「E：西・魔法の森」と M07）
- `line_of_sight` は変えていない。W02〜W06 の配置の検査がこの値を使っているため

直さずに記録したもの（理由つき）は 8 章。

## 5. Meshy の仮モデル（M01〜M08）と差し替え先

仮モデルの外寸は、W07 が全体確認用シーンで仮モデルのメッシュを測り、W09 の確定値（`assets/meshy/received.json` の `derived.bounds_local_m`）と比べた値（`review/overview/checks.json` の `placeholders`）。差し替えは P2 で行う（W07 は仮モデルの ID・寸法・向き・差し替え位置を確かめるまで）。

| 行 | 仮モデル（地区） | 置いた位置（ワールド、m） | 仮モデルの外寸 / 確定値（m） | 外接箱の最大の差 | 正面 | 仕上げ（子・PR） | 仕上げた素材の ID | 仮モデルの `future_target` |
|---|---|---|---|---|---|---|---|---|
| M01 | `APL_EntranceGateProxy_001`（A） | (0, -40, 0) | 11.0 × 2.622 × 7.739 / 同じ | 0.000 | 南。仮モデルは回転 0 でローカル -Y を正面に造形（`handoff/W02.md`）。外接箱が前後対称なので、W07 の測定では向きを判別できない | W09-M01 #14・#29 | `M01_EntranceGate_001`（+Y 正面。Z 180° で置く） | `M01_EntranceGate` |
| M02 | `APL_GiantJackProxy_001`（A） | (0, 0, 1.6)（噴水の器の上） | 6.202 × 5.87 × 6.0 / 同じ | 0.000 | 南。M01 と同じ | W09-M02 #15・#27 | `M02_GiantPumpkin_001`（同上） | `M02_GiantJack` |
| M03 | `BMN_MansionPlaceholder_001`（B） | (0, 41.5, 1.5)、Z 180° | 15.0 × 10.221 × 10.607 / 15.0 × 10.22 × 10.607 | 0.0005 | 南（`placement_hint` と一致） | W09-M03 #16・#35 | `M03_HauntedMansion_001` | `M03_HauntedMansion_001` |
| M04 | `CCD_M04_CandyWorkshopProxy_001`（C） | (38, 0, 0)、Z 90° | 8.0 × 5.366 × 7.628 / 同じ | 0.000 | 西（一致） | W09-M04 #17・#39 | `M04_WitchCandyWorkshop_001` | `M04_WitchCandyWorkshop_001` |
| M05 柱 | `DAM_Carousel_001_M05_CenterCasing`（D） | (-10.5, -32, 0.55)（回転床の上） | 1.86 × 1.86 × 3.4 / 1.861 × 1.906 × 3.4 | 0.034 | 回転する部品。回転 0 で +Y（`placement_hint` の -90° は基準姿勢の取り方の違いで、W05 が回転 0 を基準にした） | W09-M05 #18・#34 | `M05_PumpkinCarousel_001` の `M05_CenterCasing_001` | `M05_CenterCasing` |
| M05 屋根 | `DAM_Carousel_001_M05_Canopy`（D） | (-10.5, -32, 3.514)（柱の原点の 2.964 m 上） | 9.32 × 9.5 × 6.387 / 9.314 × 9.512 × 6.387 | 0.014 | 同上 | 同上 | `M05_PumpkinCarousel_001` の `M05_Canopy_001` | （柱と同じアセット） |
| M06 | `DAM_GhostTrain_001_M06_EngineShell`（D） | (7.5, -30.5, 0.14)（`EngineRoot` の下） | 1.211 × 3.115 × 1.845 / 1.211 × 3.0 × 1.905 | 0.115 | 北（進む向き。経路の上なので `placement_hint` なし） | W09-M06 #19・#38 | `M06_GhostTrainEngine_001` | `M06_GhostTrainEngine` |
| M07 | `EFR_ClockTower_001_Body`（E） | (-38.5, 0, 0)、Z -90° | 8.239 × 7.578 × 14.0 / 同じ | 0.000 | 東（一致） | W09-M07 #20・#32 | `M07_ClockTower_001` | なし（M07 側の `replacement.replaces_placeholder` が仮モデルを指す） |
| M08 | `CCD_M08_FlyingWitchProxy_001`（C） | (43.2, 0, 10.2)（巡回路の 0 番の点） | 1.542 × 2.178 × 2.5 / 1.542 × 2.127 × 2.5 | 0.041 | 北（進む向き。経路の上） | W09-M08 #21・#37 | `M08_FlyingWitch_001` | `M08_FlyingWitch_001` |

- M06 の差は、仮モデルの後端（後ろの連結部）が確定値より 0.115 m 後ろに出ていることと、底が 0.06 m 浮いていること。差し替えの基準（`DAM_GhostTrain_001_EngineRoot` と取付点）は確定値どおり
- M05 の柱・屋根の位置は `placement_hint` (-10, -32) から 0.5 m 西。`placement_hint` の注記どおり W05 が最終の位置を決めた
- 仮モデルを差し替えるときに残す部品（扉・針・鐘・回転床・座席・車輪・客車など）は、各地区の handoff と 8 章の 1〜4

## 6. 全キーの `.blend` を作り直す手順

`.blend` はコミットしないので、新しい checkout ではまず次を実行する（プロジェクトのディレクトリ。W07 の実測で全体 約 7 分、確認画像を描くキーを含む）。

```sh
uv sync
for key in world common A_plaza B_mansion C_candy D_amusement E_forest; do
  resoloop blender run modeling/$key/build.py --json || exit 2
done
uv run python modeling/overview/export_p1.py                  # 地区ごとの export と validate（任意。docs/p1-export-report.md）
resoloop blender run modeling/overview/build.py --json      # 全体確認用シーン・checks.json・確認画像・assets/manifest.json
```

- 順序: `world` と各地区は、コミット済みの `blender/common/common.blend` から共通部品を読む。共通部品を変えたら `common` を先に作り直し、その後に `world` と各地区を作り直す。`overview` は最後
- 確認画像を作らずに速く作り直す: `D_amusement`・`E_forest`・`overview` は `--arg=--no-render` が使える（`world`・`common`・`A_plaza`・`B_mansion`・`C_candy` は毎回描く。キーあたり 5〜85 秒）
- 2 回目の実行（既存の `.blend` を開いて作り直す）: `resoloop blender run modeling/<key>/build.py --blend blender/<key>/<key>.blend --json`。各ビルドは最初にシーンを空にするので、数は増えない
- 件数と外部依存の確認: `resoloop blender run modeling/overview/blend_stats.py --blend blender/<key>/<key>.blend --json` が `BLEND_STATS:` の行に、オブジェクト・メッシュ・材質・画像の数、三角形、オブジェクト名の一覧の SHA-256、見つからない画像、ライブラリ、`.001` の名前を出す（ファイルは保存しない）
- 検査: `uv run python tools/check_data.py --key <key>`、`uv run python tools/check_blend.py --key <key>`（または引数なしで全体）、`uv run pytest`。M01〜M08 をビルドしていない checkout では、引数なしの `check_data.py` は M キーの `.blend` が無くて終了コード 1 になる（8 章の 10）
- コミットの前に、作り直して変わった追跡中の `.blend` を戻す: `git restore --staged --worktree -- blender/probe/probe.blend blender/world/world.blend blender/common/common.blend`。確認画像は、形を変えたキーのものだけをコミットし、ほかは戻す（Cycles のノイズと PNG のメタデータで、形を変えなくても毎回バイトが変わる）
- ビルドが書き換えるのは自分のキーの場所だけ（W07 の確認: 配置データとアセット一覧の JSON は、形を変えていないキーではバイト単位で同じに戻る）

## 7. 地区ごとの部品・原点・取付位置の参照先

P2・P3 が部品を探すときの入口。値そのものは各ファイルにあり、この表には写さない（写すと食い違う）。可動部品の原点は、全体確認用シーンで 78 個すべてがアセット一覧の `pivot_local` と 1 cm 以内で一致した（3 章）。

| キー | 配置・通路 | アセット一覧（部品・原点・取付位置） | 可動部品の軸・範囲・基準姿勢の記録 | 取付位置（`attachment_points`） | 確認画像 | 引き継ぎ |
|---|---|---|---|---|---|---|
| `world` | `layout/world_layout.json`（地区の枠・接続点・経路・入口・スポーン・ランドマーク・視線・照明の方針）、`layout/areas/world.json` | `assets/manifest/world.json` | — | — | `review/world/` 3 枚 | `handoff/W01.md` |
| `common` | （各地区の `Common_Placement`） | `assets/manifest/common.json` | — | — | `review/common/` 2 枚 | `handoff/W01.md` |
| `A_plaza` | `layout/areas/A_plaza.json` | `assets/manifest/A_plaza.json`（M01・M02 は `replacement.replacement_slot`） | アセット一覧の各アセットの `motion`（G01 の上下と傾き、G02 の上下と周回、I01・I03 の押す量、I05 の角度）。G03 の水と G04 のランタンは発光・水の表現で、動きの範囲は無い。入口の門の扉の角度は 8 章の 4 | 44 個（小さな八角錐のメッシュ） | `review/A_plaza/` 4 枚 | `handoff/W02.md` 6 章 |
| `B_mansion` | `layout/areas/B_mansion.json` | `assets/manifest/B_mansion.json` | 配置データの `Hero_or_Gimmick`（`rotation_axis`・`rotation_range_deg`・`translation_range_m`・`rest_pose_euler_deg`） | 8 個 | `review/B_mansion/` 3 枚 | `handoff/W03.md` 6 章 |
| `C_candy` | `layout/areas/C_candy.json` | `assets/manifest/C_candy.json` | 配置データの `Hero_or_Gimmick`（`motion_axis`・`motion_range`、G11 の 8 点の巡回路） | 6 個 | `review/C_candy/` 3 枚 | `handoff/W04.md` 4・6 章 |
| `D_amusement` | `layout/areas/D_amusement.json` | `assets/manifest/D_amusement.json` | 配置データの `gimmick_specs`（G13〜G16 の `axis_local`・範囲・速さ、G15 の周回の経路点） | 10 個 | `review/D_amusement/` 4 枚 | `handoff/W05.md` 7 章 |
| `E_forest` | `layout/areas/E_forest.json`（実測の外接箱つきの配置・通路・鑑賞位置） | `assets/manifest/E_forest.json`（M07 は `replacement_slot`） | アセット一覧の `motion`（`part_name`・`axis`・`range`・`rest_pose`・`envelope_world`）、`glow_individuals`、`flight_range` | 4 個 | `review/E_forest/` 9 枚 | `handoff/W06.md` 7 章 |
| `overview` | — | `assets/manifest.json`（上の 7 つを 1 つにしたもの） | `review/overview/checks.json` の `motion_parts`（78 個の原点のワールド座標と、範囲の記録の場所） | — | `review/overview/` | この文書 |

- 末端の Empty は export で省かれるので、取付位置は各子が小さなメッシュとして作った（`docs/conventions.md` §4.2）
- Spec §6.3 の `AssetRoot / MotionRoot / VisualRoot` の Slot 構成は、P1 の Blender の階層（`asset_root`・`motion_root`・`visual_root`）が元になる。実際の Slot 名は P2 で決める

## 8. P2 への注意（各 handoff の要望と W07 の検査のまとめ）

| # | 対象 | 内容 | 出典 | W07 の扱いと理由 |
|---|---|---|---|---|
| 1 | M03 の扉・玄関ホール（W03 の `BMN_MansionDoubleDoor_001`・`BMN_EntranceHall_001`） | 仕上げた M03 の開口は、ワールドで x -0.1015〜1.5165（中心 0.7075）、床 z 1.870、高さ 2.592 m。W03 の扉・ホール・仮モデルの開口は W09 の当初値（中心 0.335、床 1.779、高さ 2.683 m）。M03 に差し替えるとき、扉とホールを x +0.3725 m・z +0.091 m 動かし、扉の高さを 2.592 m にする。蝶番の線はワールド x -0.1015 と 1.5165、y 39.952、z 1.870〜4.462。ポーチの階段の上端も z 1.870 に合わせる。M03 の壁は厚みの無い片面なので、切り口の縁を扉の枠で覆い、開口の奥を玄関ホールで塞ぐ（塞がないと Resonite で建物の向こうが透けて見える） | #5 の W09-M03 のコメント、`handoff/W09-M03.md` 2・8 章 | 記録のみ。P1 では仮モデルの開口と扉・ホールが同じ値で揃っている。W03 の値は `modeling/B_mansion/` の 2 ファイルの 30 か所以上に書かれていて、P1 で動かすと仮モデルの造形のやり直しになる。差し替えは P2 |
| 2 | M05 の支柱（W05 の `DAM_Carousel_001_Poles`） | 仕上げた屋根の下面は、支柱の位置で M05 の座標の z 3.64〜4.02 m。支柱の上端は z 3.06 m で、0.58〜0.96 m 空く。差し替えるときに支柱を屋根の下面まで伸ばすか、位置を見直す。座席と乗る人の頭は柱の原点から 3.045 m 未満に収める | `handoff/W09-M05.md` 6 章 | 記録のみ。仮モデルの屋根の下面は低いので、P1 で伸ばすと仮モデルを突き抜ける |
| 3 | M06 の前照灯の取付点（W05 の `DAM_GhostTrain_001_Att_Headlamp`） | 仕上げた M06 のレンズの前面の前（`EngineRoot` のローカルで例 (0, 1.26, 1.39)。今は (0, 1.233, 1.498)）へ移す。見える連結器を作るなら、`handoff/W09-M06.md` 6.4 の梁の面から連結点まで | `handoff/W09-M06.md` 7 章 | 記録のみ（光の取付位置で、P3 の前照灯の実装と一緒に直せる） |
| 4 | 入口の門の扉の可動範囲（W02 の `APL_EntranceGateProxy_001_DoorLeft`・`_DoorRight`） | A のデータには蝶番の位置だけで、開く角度が無い（仮モデルの扉はローカルの Z ±88° の開いた形で置かれている。W07 の実測）。仕上げた M01（`assets/manifest/M01.json` の `leaves`）は、Z 軸まわりの回転 0 で閉じ、左 +90°・右 -90° で内側（広場の側）へ開く（M01 のローカル。M01 は Z 180° で置く）。P3 はこの値を使う | W07 の検査（`checks.json` の `motion_parts`）、`handoff/W09-M01.md` 2・8 章 | 記録のみ（P3 は M01 の扉を動かす。仮モデルの扉は差し替えで消える） |
| 5 | 西の主動線の床と時計塔の台座（W01 の `WLD_WestBridge_001`、W06 の `EFR_ClockTower_001`） | 床は x -42.25 まで伸び、時計塔の台座の下を通る（時計塔の本体は x -42.289〜-34.711。W07 の実測で、床の上面 z 0.05 は x -34.5 まで見え、x -35 からは台座の階段が上に来る）。見た目は台座に隠れる。歩行用のコライダーを床と台座の両方から作ると重なるので、台座の当たり判定を優先するか、床のコライダーを階段の手前（x ≈ -34.7）で止める | `handoff/W06.md` 6 章 | 記録のみ。重なりは台座の中に隠れていて、歩ける面に段差も穴も無い（W07 の動線の検査）。コライダーの作り方は P2（W08）で決める |
| 6 | 仕上げた Meshy 素材の ID | 地区のアセット一覧の `replacement.future_target` と、仕上げた素材の ID が一部違う。対応は 5 章の表を使う（地区のデータは直していない） | W07 の確認 | 記録のみ |
| 7 | 差し替え元のファイル | `handoff/W04.md` 6 章の `blender/meshy/M04/M04_normalized.blend`・`blender/meshy/M08/M08_normalized.blend` は存在しない。仕上げた物は `blender/<M>/<M>.blend`（`modeling/<M>/build.py` で作る）か、Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/finished/<M>/` | `handoff/W09-M08.md` 6 章 | 記録のみ（この表を正しい参照先とする） |
| 8 | 仕上げた Meshy 素材の向き | `handoff/W02.md` 6 章の「W07 で実 GLB を Z 180° 回して置く」は、W09 の受け入れ（置いた後の正面を全素材 +Y に統一）より前の記述で、差し替えも W07 ではなく P2。仕上げた M01〜M08 は、`assets/manifest/<M>.json` と `handoff/W09-<M>.md` 8 章の置き方（`received.json` の `placement_hint`）に従う | `docs/meshy-intake.md`、各 `handoff/W09-<M>.md` | 記録のみ |
| 9 | export の `--parent` | `exports/p1/` のバンドルは試験用の `--parent Root/ResoLoop_Test_W07_<key>` で作った。そのまま apply せず、ライブのワールドで確かめた Slot を `--parent` にして新しい出力先へ export し直す | `docs/p1-export-report.md` | 記録のみ（P2 の作業） |
| 10 | 新しい checkout での検査 | `.blend`・画像をコミットしないので、ビルドの前は `tools/check_data.py` が終了コード 1 になる。全体（`--key` なし）は M01〜M08 のアセット一覧も読むので、M キーをビルドしていない checkout では 1 のまま（W07 の worktree も同じ。7 章）。P1 のキーは `--key <key>`、データの形だけは `--no-file-check` で確かめる | W06・W09 系の handoff | `docs/conventions.md` §7.2 に手順を書いた。`tools/check_data.py` は変えていない（失敗はエラーで分かり、黙って誤る不具合ではない） |
| 11 | `tools/check_data.py --key meshy` | キー `meshy` は配置データもアセット一覧も持たないので終了コード 1 | `handoff/W09.md` | 記録のみ（P1 のキーではない） |
| 12 | 共通部品の街灯の向き | `handoff/W01.md` の「吊りランタンは +Y 側」は誤りで、実物は +X 側（`assets/manifest/common.json` の外接箱も x 側に 0.67） | `handoff/W06.md` 6 章 | 記録のみ |
| 13 | スポーンの空き半径（W01 の `spawn`・`spawn_candidates`） | 南の入口のベンチ 2 脚（`WLD_WelcomeBench_East_001`・`_West_001`、x ±3.2、y -43.5）の内側の縁は、スポーン (0, -44) から 2.86 m。宣言の空き半径 3.0 m（`spawn`）・3.5 m（`Spawn_South_Entrance_Gate`）に 0.14 m・0.64 m 入る。規約の下限 1.5 m は満たす | W07 の検査（`checks.json` の `spawns`） | 記録のみ。P2 でスポーンの実際の位置・範囲を Resonite で決めるときに、ベンチを外へ寄せるか宣言の半径を 2.8 m にする |
| 14 | 同じ高さで重なる面 | W07 は、地区間の重なり（2 章の検査）と、全体の描画で黒くなった所を直した（4 章の 7〜9）。同じオブジェクトの中の重なりで、確認画像のカメラから見えない所は残っているかもしれない。また、A・B の直しは W01 の面との差が 3〜5 mm（A の十字の通路など、元からの重ね方と同じ）なので、Resonite の遠景でちらつかないかを見る | W07 の検査 | P2 の実機で確かめる |
| 15 | 主動線の有効幅 | ガーランドの門（`WLD_EntranceGarland_*`・`APL_PortalGarland_*`）の柱の内側は ±1.65 m で、幅 4.0 m の主動線の有効幅は 3.30 m になる（下限 3.0 m は満たす）。連絡橋は手すりの間が 2.38 m（下限 2.0 m は満たす） | W07 の検査（`checks.json` の `routes`） | 記録のみ。P2 でアバターのすれ違いを実機で確かめる（Spec §4.1） |

## 9. Resonite で未確認の項目

W07 を含め、P1 のどの子も Resonite に apply していない（P0 の `probe` だけが W00 で apply 済み）。次はすべて未確認で、P2 以降で確かめる。

- 全キーの見た目（材質の色・発光・片面の表示）、縮尺・向き・座標の変換（Blender の (x, y, z) → Resonite の (x, z, y)）が地区の規模でも意図どおりか
- 地区ごとのバンドルの apply・`diff`・`validate --strict`（ライブの Reflection との照合）・再 apply の収束
- 歩行: スポーン、動線の段差・勾配・有効幅、橋の手すり、落下防止。W07 の検査は Blender のシーンへのレイの実測で、アバターの当たり判定や移動ではない
- 可動部品の回転の向き・原点が、resoloop の変換の後に意図どおりか（例: W06 の時計の「時計回り = 各 Pivot のローカル -Y 軸まわりの正の回転」）。末端の Empty は export で省かれるので、取付位置は小さなメッシュとして作られている（W00 の規約。W07 は export の Slot 数で確かめていない）
- 負荷（三角形・描画の区切り・材質の数）と、10 人程度での動作
- Meshy の仕上げた素材の差し替え（P2）と、差し替えたときの 8 章の 1〜4

## 10. 次に触ってよい範囲

- P2（W08 以降。起票と着手は利用者の指示を待つ）: この文書の 5〜9 章を入力にして、各地区のバンドルを確かめた Slot へ出し直し、静的ワールドを統合する。Meshy 素材の差し替えは 5 章・8 章
- 各キーの形や配置を直すときは、そのキーの `modeling/<key>/` を直して 6 章の手順でビルドし、そのキーの検査と `uv run pytest` を通してから、`overview` を作り直して `review/overview/checks.json` の差分を確かめる
- ID・原点・部品名を変えるときは、理由と旧名との対応表を残す（Spec §6.1）。W07 が変えた ID は 4 章の 3 のランドマークの 1 つ（`LM_E_WitchWorkshop_001` → `LM_E_ClockTower_001`）だけ

## 11. 上書きしてはいけない範囲

- 3D モデル（`.blend`、GLB などのモデルのファイル、export のバンドル）はコミットしない（2026-10-31 の利用者の指示）。既にコミット済みの `blender/probe/`・`blender/world/`・`blender/common/` の `.blend` は、作り直してもコミットしない（コミットの前に `git restore`）
- Meshy の原本と仕上げた物（Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/`。原本は `SHA256SUMS`）と、W09 の確定値（`assets/meshy/received.json`）。W07 は読んだだけで、作業の前後で置き場の全ファイルの名前・サイズ・更新時刻と `SHA256SUMS` が変わっていないことを確かめた
- M01〜M08 の所有ファイル（W09-M01〜M08）。W07 の対象外
- 利用者が手で調整した部分: 2026-10-31 時点で、P1 のキーには無い（どの子の handoff にも記録が無く、すべてスクリプトから作り直せる）
- `concept_art/` は読むだけ
