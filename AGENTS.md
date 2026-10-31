# ResoLoop project guide

Use `resoloop` as the only mutation interface for Resonite content in this project. Use the project skills under `.agents/skills/` for the requested workflow. If no connection URL is configured, follow resonite-build's automatic discovery workflow: discover first, connect if there is one candidate, or ask the user to choose if there are multiple. Run `resoloop doctor --json` with the selected URL before world work.

## Required workflow

- Inspect unfamiliar Component types, members, methods, and Flux nodes through Reflection or Flux-SDK metadata. Never guess runtime names.
- Before mutation, review `diff --brief` targets and reasons. Diff already includes offline and runtime Reflection validation; standalone validate is for offline authoring or diagnosis. Apply repeats preflight. Re-run the same apply and confirm it converges without writes.
- Keep declarative content in `content/`, ProtoGraph source in `flux/`, and session state under `.resoloop/`.
- Prefer stable selectors such as `$slot:key`, `$component:key`, and `$member:key.Member`; pass `--state` after reconnecting.

## Resonite safety

- Never delete or mutate `Root`, an unverified ID, or existing user content outside the requested ownership boundary.
- Put experiments below an unmistakable `ResoLoop_Test_*` Slot and clean only its exact verified ID.
- Review delete candidates before `--prune --yes`. Slot delete and Component remove always require explicit `--yes`.
- Treat ResoniteLink IDs as session-scoped and re-observe after a session restart.

## このプロジェクト固有

- テスト: このディレクトリで `uv run pytest` を実行する
- 検査コマンド（W00 で定義）:
  - 配置データ・アセット一覧の検査: `uv run python tools/check_data.py`（キー指定は `--key <key>`）
  - `.blend` の検査: `uv run python tools/check_blend.py`（キー指定は `--key <key>`）
- 再生成コマンド（W00 で定義）: `resoloop blender run modeling/<key>/build.py --json`
- ワールド: reso-world-Halloween（Halloween Magical Carnival）
  - 所有キー: `probe`（W00）、`world`・`common`（W01）、`A_plaza`（W02）、`B_mansion`（W03）、`C_candy`（W04）、`D_amusement`（W05）、`E_forest`（W06）、`overview`（W07）、`meshy`（W09）、`M01`〜`M08`（W09-M01〜W09-M08）。接頭辞は `docs/conventions.md` §3（W01A で `BMN`・`CCD`・`DAM`・`MSH`・`M01`〜`M08` に揃えた）
  - 詳細な座標・命名・ディレクトリ規約は `docs/conventions.md`、環境情報は `docs/environment.md` を参照
- state ファイル: `flux/resoloop.flux.json` の `worldState`（`.resoloop/state/reso_world_halloween.json`）を既定とする。P0 小規模検証では `.resoloop/state/p0_probe_test.json` を使い、テスト用の `ResoLoop_Test_P0_Probe` スロット配下のみを操作する
- リポジトリ: `usaturn/reso-world-Halloween`（公開、remote は `origin`、統合の基準は `main`）。公開なので、秘密情報と利用者の個人情報をコミットしない
- 3D モデルはコミットしない（2026-10-31 の利用者の指示）。`.blend`、GLB・glTF・FBX・OBJ などのモデルのファイル、export のバンドルが対象。`.blend` は再生成のスクリプトで作り直し、Meshy の原本と仕上げた物は Git の外の `/workspaces/reso-world/worlds/reso-world-Halloween-meshy/` に置く。既にコミット済みの `blender/probe/probe.blend`・`blender/world/world.blend`・`blender/common/common.blend` は残すが、作り直した版はコミットしない（コミットの前に `git restore` で戻す）
- 仕様と進め方: 親 Issue #1（https://github.com/usaturn/reso-world-Halloween/issues/1）。子 Issue を担当するときは、#1 の「子 Issue の進め方」に従う
- コンセプトアート: `concept_art/`。雰囲気の参考で、寸法図ではない。#1 の仕様と配置データを優先する
