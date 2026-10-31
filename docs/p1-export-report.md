# P1 の地区ごとの export の確認（W07、Issue #9）

P1 の Blender の成果を、地区ごとに `resoloop blender export` で出力し、`resoloop validate` でオフラインに検査した結果。親 #1 の Spec §5.2 の「出力確認（利用可能な範囲でエリア単位に export し、エラー・警告・非対応要素を記録）」と §12 の「出力経路の確認結果と、Resonite 未確認の項目を区別して記録した」に当たる。

**Resonite には接続していない。apply・diff・`validate --strict`（ライブの Reflection との照合）は行っていない。** ここで確かめたのは、Blender の `.blend` から ResoLoop のバンドルが作れること、バンドルの宣言がオフラインの検査を通ること、export が報告する警告・非対応要素の有無だけである。

## 1. 方法

- 実行: `uv run python modeling/overview/export_p1.py`（プロジェクトのディレクトリ。先に各キーをビルドする。`docs/p1-handoff.md` 6 章）
- キーごとに次を実行する（resoloop 0.2.0。オプションは導入済みの `resoloop blender export --help` と `docs/conventions.md` §7.5 で確かめた）

  ```sh
  resoloop blender export blender/<key>/<key>.blend --output exports/p1/<key>-<UTC> \
      --parent Root/ResoLoop_Test_W07_<key> --collection <key> --preserve-hierarchy --json
  resoloop validate exports/p1/<key>-<UTC>/model.apply.json --json   # --strict なし = オフライン
  ```

- 対象: `world` と 5 地区（`A_plaza`・`B_mansion`・`C_candy`・`D_amusement`・`E_forest`）。`common` は単体では出力しない（共通部品は各地区の中に配置済みで、各地区のバンドルに含まれる。`common.blend` は部品を並べただけで、ワールドの配置ではない）。`overview` も出力しない（同じ形が地区ごとのバンドルに分かれている。Spec §10.1「エリア／アセット単位で出力と状態ファイルを分ける」）
- `--parent`: resoloop 0.2.0 では必須。apply しないので、試験用のパス `Root/ResoLoop_Test_W07_<key>` を渡した。**ライブのワールドで確かめた Slot ではない**。P2 は、確かめた Slot を `--parent` にして新しい出力先へ export し直す（W00 の頃の `--root-path` や過去の Slot ID は使わない）
- `--pack-pbr`: 付けない。P1 の 7 キーは画像を使っていない（どの `.blend` も画像 0。材質は Principled BSDF の値だけ）
- 出力先: 毎回新しい `exports/p1/<key>-<UTC>/`。古い出力は消さず、使い回さない。コミットするのは resoloop の `report.json` と、validate の結果の `validate.json` だけ。バンドル本体（`model.apply.json`・`*.mesh.json`）は `.gitignore` で除く（`docs/conventions.md` §8）

## 2. 結果（2026-10-31、resoloop 0.2.0、Blender 5.0.1）

6 つとも export・validate とも終了コード 0、validate の `issues` は 0 件。export の非対応要素の報告（`report.json` の `warnings`）は性能の目安だけで、変換できなかった要素の報告は無い。

| キー | 出力先 | export の終了コード | validate の終了コード・valid | Slot / Component / 参照 | validate の issues | メッシュ | 三角形 | 頂点 | 材質 | 描画の区切り | 画像 | staticOnly | 警告 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `world` | `exports/p1/world-20261031T141428Z/` | 0 | 0・True | 40 / 59 / 109 | 0 | 21 | 12,088 | 25,731 | 17 | 67 | 0 | True | 2 |
| `A_plaza` | `exports/p1/A_plaza-20261031T143556Z/` | 0 | 0・True | 164 / 241 / 460 | 0 | 110 | 18,448 | 40,149 | 21 | 240 | 0 | True | 2 |
| `B_mansion` | `exports/p1/B_mansion-20261031T142609Z/` | 0 | 0・True | 87 / 109 / 202 | 0 | 45 | 7,540 | 17,783 | 19 | 112 | 0 | True | 2 |
| `C_candy` | `exports/p1/C_candy-20261031T143556Z/` | 0 | 0・True | 79 / 108 / 235 | 0 | 42 | 12,116 | 29,226 | 24 | 151 | 0 | True | 2 |
| `D_amusement` | `exports/p1/D_amusement-20261031T142609Z/` | 0 | 0・True | 98 / 136 / 310 | 0 | 58 | 15,628 | 37,719 | 20 | 194 | 0 | True | 2 |
| `E_forest` | `exports/p1/E_forest-20261031T141428Z/` | 0 | 0・True | 189 / 271 / 515 | 0 | 115 | 57,978 | 146,714 | 41 | 285 | 0 | True | 3 |

- 頂点の数は Blender より多い（例 `world` 7,720 → 25,731）。resoloop が面の向き（法線）と UV の切れ目で頂点を分けるため。三角形の数は Blender の実測（`modeling/overview/blend_stats.py`）と一致する
- `A_plaza`・`B_mansion`・`C_candy`・`D_amusement` は、W07 の統合の直し（`docs/p1-handoff.md` 4 章の 5〜9）の後に出し直した。直す前の出力は最終の形を表さないので消し、コミットしていない。D の直す前の出力は Slot 88・メッシュ 48・三角形 15,348 で、取付位置 10 個が無かった（下の 3）。A・B・C は直す前と後で数が同じ（面の高さと箱の範囲だけの直し）

### 警告（`report.json` の `warnings`）

| 警告 | 対象 | 意味と扱い |
|---|---|---|
| `More than 8 materials: review draw calls and atlas/shared material opportunities.` | 6 つすべて（材質 17〜41） | 描画の呼び出しの数の目安。P1 は形と色の確認が目的で、材質をまとめていない。P2 で負荷を測ってから、共通の材質・アトラスにまとめるかを決める（Spec §11「未計測で数値を保証しない」） |
| `More than 16 submeshes/draw sections: consider combining static meshes that share materials.` | 6 つすべて（描画の区切り 67〜285） | 同じ。「1 オブジェクト = 1 メッシュ」（後から人がインスペクターで触りやすくする規約）なので区切りが多い。動かない部品の結合は P2 で負荷を見て決める |
| `More than 50,000 triangles: review the viewing distance, instances and silhouette budget.` | `E_forest`（57,978） | 木・キノコの形はシリーズごとに 1 つのメッシュを共有しているが、export ではオブジェクトごとのメッシュになる。P2 で負荷を測る |

## 3. 出力に入らない要素・変わる要素（オフラインで確かめた範囲）

- **オブジェクトの欠け**: 各キーの `.blend` のオブジェクト名と、バンドルの Slot 名を照合した（W07 の一時的な確認。結果だけを記録）。最終の 6 つの出力で、`.blend` のオブジェクトはすべて Slot として入っている（`world` 21・`A_plaza` 141・`B_mansion` 66・`C_candy` 53・`D_amusement` 76・`E_forest` 146）。Slot がオブジェクトより多いのは、キーの root Slot と、材質・メッシュを持つ `Blender_Providers` の下の Slot の分
- **取付位置（直した）**: 直す前の `D_amusement` では、子にメッシュを持たない Empty で作られた取付位置 10 個（`DAM_*_Att_*`）がバンドルに無かった。resoloop は子孫にメッシュの無い Empty を出力しない（`docs/p0-report.md` 3.5、`docs/conventions.md` §4.2）。W07 が小さなメッシュに替えて出し直し、10 個とも Slot として入ったことを確かめた
- **発光**: Blender の発光は `PBS_Metallic` の `EmissiveColor` になる（発光のある材質: `world` 2・`A_plaza` 6・`B_mansion` 4・`C_candy` 5・`D_amusement` 3・`E_forest` 7）。発光の強さの見え方は Resonite で未確認
- **透過**: 出力の材質はすべて不透明（`AlbedoColor` のアルファ 1）。Blender 側で透過・屈折を使う材質の有無は `docs/p1-handoff.md` 3 章
- **画像**: P1 のキーは画像を使っていないので、`tex_*.png`・`pbr_*.png` は出力されない
- **動き**: P1 は形だけで、アニメーションは出力されない（Spec §1.2）。可動部品は原点（Slot の位置）と階層で渡す。回転の向きの変換（Blender の Z 軸まわり +θ → Resonite の Y 軸まわり -θ、`docs/p0-report.md` 3.2）が地区の部品でも正しいかは Resonite で未確認
- **当たり判定**: 出力にコライダーは含まれない。歩行用のコライダーは P2（W08）で作る

## 4. Resonite で未確認の項目

- apply、`diff`、`validate --strict`（ライブの Reflection との照合）、再 apply の収束。どれも行っていない
- 試験用の `--parent` の下の階層を、P2 が確かめた Slot に置き換えたときの位置・回転
- 見た目（色・発光・片面の表示・縮尺）、負荷（警告の項目）、歩行
- 一覧は `docs/p1-handoff.md` 9 章

## 5. 作り直す

```sh
# 先に各キーをビルドする（docs/p1-handoff.md 6 章）
uv run python modeling/overview/export_p1.py                                   # world と 5 地区
uv run python modeling/overview/export_p1.py --key D_amusement                 # 1 キーだけ
resoloop blender run modeling/overview/build.py --json --arg=--no-render       # assets/manifest.json の export_result を最新の出力に向ける
```

- 出力先は実行のたびに新しい `exports/p1/<key>-<UTC>/` になる。`assets/manifest.json` は、キーごとに最も新しい（`report.json` のある）出力を指す
- `handoff/W09-M02.md` によると、export のたびにメッシュの JSON の接線がわずかに変わり、`*.mesh.json` の SHA-256 は毎回違う（形は同じ）。W07 は同じ形のキーを 2 回 export して比べてはいない
