---
type: Playbook
title: 自作 skill を追加する
description: 新しい自作 skill を原本へ追加し、Codex と Claude Code から読めるようにする。
tags: [local, authoring, installation]
generated: { by: codex/gpt-5.6-sol, at: 2026-08-23T18:03:28+09:00 }
verified: { by: human:Soli0222, at: 2026-08-23T19:16:43+09:00 }
sources:
  - id: readme
    resource: ../../README.md
    title: README の追加手順
    last_modified: 2026-08-23T19:16:43+09:00
  - id: install-sh
    resource: ../../scripts/install.sh
    title: 配置スクリプト
    last_modified: 2026-08-23T17:29:24+09:00
---

# 前提

この手順は、作成者が内容を保守する skill に使う。
外部の gist や GitHub リポジトリをそのまま導入する場合は、[配布 skill を追加する](/playbooks/add-external-skill.md)へ進む。

# 手順

1. `skills/<name>/SKILL.md` を作り、frontmatter の `name` をディレクトリ名と一致させる。
2. 必要な `scripts/`、`references/`、`assets/`、`agents/` を同じディレクトリへ置く。
3. `README.md` の「自作 skill」一覧へ概要を追加する。
4. `./scripts/install.sh link` を実行し、作成または置換されるリンクを確認する。
5. 予定された変更が正しければ、`./scripts/install.sh link --apply` を実行する。
6. `./tests/run.sh` を実行し、既存の管理操作を壊していないことを確認する。

# 完了条件

`~/.agents/skills/<name>` がリポジトリ内の原本を指し、`~/.claude/skills/<name>` が agents 側を指していれば配置は完了している。
二度目の `./scripts/install.sh link` で変更予定が出なければ、処理の冪等性も確認できる。

# 競合が出た場合

`CONFLICT` が出たときは `--force` をすぐに付けず、配置先と原本の差分を確認する。
配置先だけに必要な変更があれば、先に原本へ取り込むか、別の skill として退避する。
