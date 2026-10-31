# 開発環境・ツール・コンセプトアート確認記録 (`docs/environment.md`)

本ドキュメントは P0（Issue #2 / W00）で実施した開発環境・CLI ツール・スキル同期・Blender 実行経路・Git ワークツリー構成、および `concept_art/` 画像 7 枚の読み込み確認結果を記録する。

---

## 1. CLI ツールとバージョン確認結果

実行環境（Linux Dev Container `x86_64-unknown-linux-gnu`）で計測した各ツールの実測バージョンは以下のとおり。

| ツール | 確認コマンド | 実測結果 |
| --- | --- | --- |
| `agy` | `agy --version` | `1.4.12` |
| `blender` | `blender --version` | `Blender 5.0.1` (build date `2025-12-16`, commit `a3db93c5b259`, Release) |
| `resoloop` | `resoloop --version` | `0.2.0` |
| `flux-sdk` | `flux-sdk --version` | `Flux SDK Version: 1.9.0+e674229f9b959ac8e6615ff35a2cd1d7971503e8` |
| `uv` | `uv --version` | `uv 0.13.6 (x86_64-unknown-linux-gnu)` |
| Python (`.venv`) | `uv run python --version` | `Python 3.14.4` (`pytest 9.2.0`) |

---

## 2. `resoloop` スキル同期・Blender 検出・オプション確認

### 2.1 `resoloop skills sync --check`
- 実行コマンド: `resoloop skills sync --check --json`
- 結果: `"ok": true`, `"synchronized": true`, `"missing": []`, `"outdated": []`（同梱スキルおよび UIX レシピ計 19 ファイルすべて最新状態と一致）。

### 2.2 `resoloop blender find --json`
- 実行コマンド: `resoloop blender find --json`
- 結果:
  ```json
  {
    "ok": true,
    "data": {
      "executable": "/workspaces/reso-world/worlds/reso-world-Halloween/.resoloop/blender-system-python",
      "source": "configuration",
      "version": "Blender 5.0.1"
    }
  }
  ```

### 2.3 `resoloop blender` サブコマンドと主要オプション
`resoloop blender --help` により以下のオフラインサブコマンド・オプションを確認した：

1. `resoloop blender find [--blender-executable PATH] [--json]`
2. `resoloop blender run SCRIPT.py [--blend FILE.blend] [--arg=VALUE ...] [--json]`
   - 指定した Python スクリプトを Headless Blender (`--background`) 上で実行する。
   - 既存 `.blend` を開いて実行する場合は `--blend FILE.blend` を指定する。
3. `resoloop blender export FILE.blend --output NEW_DIRECTORY --parent VERIFIED_SLOT [--name NAME] [--collection NAME] [--json] [--preserve-hierarchy] [--pack-pbr] [--legacy-root-providers]`
   - `--preserve-hierarchy`: ローカルメッシュ形状・親子階層・回転ピボットを保持して `model.apply.json` と `report.json`、メッシュ JSON、テクスチャ PNG を出力する。
   - `--collection NAME`: 指定したコレクション内のオブジェクトのみを対象に出力する。
   - `--pack-pbr`: Non-Color の Metallic / Roughness マップを統合パックする。
   - 出力先の `--output NEW_DIRECTORY` は未存在のディレクトリを指定する必要がある（再出力時は事前に出力先ディレクトリを削除してから実行する）。

---

## 3. Git Checkout / Worktree 管理方針

1. **メイン checkout（基準ブランチ `main`）**
   - パス: `/workspaces/reso-world/worlds/reso-world-Halloween`
   - リモート `origin`: `https://github.com/usaturn/reso-world-Halloween.git`
   - メイン checkout は常に `main`（`origin/main` と一致、未追跡ファイルなし）に保ち、直接作業しない。
2. **Issue ごとの作業用 worktree**
   - 各 Issue `W00`〜`W08` の作業時は、兄弟パス `/workspaces/reso-world/worlds/reso-world-Halloween-<KEY>`（ブランチ `work/<KEY>`）に `git worktree add` で分離環境を作成する。
   - Worktree 作成直後に `uv sync` を実行し、`.resoloop.json` の Blender ラッパー設定を必要に応じて同期する。
   - PR マージ後はメイン checkout を `git merge --ff-only origin/main` で更新し、作業用 worktree と `work/<KEY>` ブランチを削除する。

---

## 4. `concept_art/` 画像 7 枚の確認結果と Blender / Resonite からの参照性

### 4.1 画像一覧と Blender (`bpy.data.images.load`) での実測結果

`modeling/probe/build.py` 内の `verify_concept_art_readability_in_blender()` により、全 7 枚の PNG が Headless Blender 5.0.1 から正常に読み込めることを確認した。

| ファイルパス | 対象範囲・内容 | 解像度 (`width × height`) | チャンネル数 | Blender 読込確認 |
| --- | --- | --- | --- | --- |
| `concept_art/01_world_overview.png` | ワールド全体俯瞰（中央広場・大樹・背後の洋館・周囲の街並みと森の全体ムード） | `1672 × 941` | 4 (RGBA) | OK (`true`) |
| `concept_art/02_world_layout_guide.png` | ワールド全体レイアウトガイド（A〜E の 5 エリア配置と回遊動線の構成図） | `1448 × 1086` | 4 (RGBA) | OK (`true`) |
| `concept_art/03_magical_pumpkin_plaza.png` | エリア A：魔法のパンプキン広場（巨大ジャック・オー・ランタン大樹、噴水、石畳広場、外周の建物） | `1448 × 1086` | 4 (RGBA) | OK (`true`) |
| `concept_art/04_haunted_mansion.png` | エリア D：ホーンテッド・マンション（丘の上のゴシック洋館、鉄柵と門扉、枯れ木、満月シルエット） | `1448 × 1086` | 4 (RGBA) | OK (`true`) |
| `concept_art/05_witchs_candy_street.png` | エリア B：魔女のキャンディ横丁（とんがり屋根の店舗群、光るショーウィンドウ、吊り看板、ガーランド） | `1448 × 1086` | 4 (RGBA) | OK (`true`) |
| `concept_art/06_pumpkin_amusement.png` | エリア C：カボチャの遊園・祝祭パーク（カボチャのメリーゴーランド／回転遊具、テント屋台、祝祭ライト） | `1448 × 1086` | 4 (RGBA) | OK (`true`) |
| `concept_art/07_enchanted_forest.png` | エリア E：幻想の森・墓地小径（ねじれた樹木、墓石群、石橋、紫〜青緑の霧と発光キノコ・ランタン） | `1448 × 1086` | 4 (RGBA) | OK (`true`) |

### 4.2 Blender および Windows 側 Resonite からの画像受け渡し仕様

1. **Blender からの参照**:
   - コンテナ内のローカルファイルシステム上に存在するため、`bpy.data.images.load()` で全 PNG ファイルを直接読み込み可能。
   - アセット用テクスチャは `save_blend(..., pack_images=True)` により `.blend` ファイル内にもパックするため、`resoloop blender export` 実行時に `exports/<key>/bundle/tex_*.png` として確実に抽出される。
2. **Windows 側 Resonite からの参照**:
   - 本環境は Linux Dev Container 内で動作しており、コンテナ内パス（`/workspaces/...`）は Windows ホスト上の Resonite プロセスから直接ファイルパスとして開けない場合がある。
   - そのため、Windows 上で動作する Resonite へ `resoloop apply` でテクスチャ付きバンドルを反映する際は、`--texture-transfer data` オプション（または環境変数 `RESOLOOP_TEXTURE_TRANSFER=data`）を指定する。これにより `resoloop` がコンテナ側で PNG をデコードしてピクセルデータを ResoniteLink 経由で送信するため、ホスト・コンテナ間のファイルパス差異に依存せず確実にテクスチャを転送できる。
