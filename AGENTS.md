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
- ワールド: reso-world-Halloween（Halloween Magical Carnival）。所有キーと所有ルートスロットは、ワールドの設計が決まったらここに書く
- state ファイル: `flux/resoloop.flux.json` の `worldState` を既定とする。ワールドごとに分ける場合はここに書く
- リポジトリ: `usaturn/reso-world-Halloween`（公開、remote は `origin`、統合の基準は `main`）。公開なので、秘密情報と利用者の個人情報をコミットしない
- 仕様と進め方: 親 Issue #1（https://github.com/usaturn/reso-world-Halloween/issues/1）。子 Issue を担当するときは、#1 の「子 Issue の進め方」に従う
- コンセプトアート: `concept_art/`。雰囲気の参考で、寸法図ではない。#1 の仕様と配置データを優先する
