---
type: Architecture
title: skills リポジトリの管理モデル
description: 自作 skill と配布 skill を、異なる原本と配置規則で管理する。
resource: ../
tags: [architecture, source-of-truth, agent-skills]
generated: { by: codex/gpt-5.6-sol, at: 2026-08-23T18:03:28+09:00 }
verified: { by: human:Soli0222, at: 2026-08-23T19:16:43+09:00 }
sources:
  - id: readme
    resource: ../../README.md
    title: リポジトリ README
    last_modified: 2026-08-23T19:16:43+09:00
  - id: install-sh
    resource: ../../scripts/install.sh
    title: 配置スクリプト
    last_modified: 2026-08-23T17:29:24+09:00
  - id: external-py
    resource: ../../scripts/external.py
    title: 配布 skill 管理スクリプト
    last_modified: 2026-08-23T17:57:22+09:00
---

# 二つの管理方式

このリポジトリは、自分で保守する skill と、外部から導入する skill を同じ場所へ複製しない。
[自作 skill](/concepts/local-skills.md)は `skills/<name>/` を原本とし、エージェントの読み取り先から原本へ symlink を張る。
[配布 skill](/concepts/external-skills.md)は `external/manifest.toml` に取得元と固定情報を記録し、導入済みの実体をリポジトリの外へ置く。

この分離により、自作コードの変更履歴と、外部依存の更新履歴を別々に追跡できる。
配布物をリポジトリへコピーして保守すると、上流の更新とローカル変更の境界が曖昧になるためである。

# 四つの保存場所

| 保存場所 | 役割 | 手で編集するか |
| --- | --- | --- |
| `skills/<name>/` | 自作 skill の原本 | 編集する |
| `external/manifest.toml` | 配布 skill の依存宣言と pin | 編集する |
| `~/.agents/skills/<name>/` | エージェントが読む実体または symlink | 管理コマンドを使う |
| `EXTERNAL.md` | manifest から生成する人向け台帳 | 編集しない |

`~/.claude/skills/<name>` は `~/.agents/skills/<name>` を指す symlink であり、Claude Code 用に別の実体を持たない。
skills CLI 由来の機械記録は `~/.agents/.skill-lock.json` に置かれるが、これは依存宣言の代わりではない。

# 変更の入口

管理対象を変えるときは、原本か依存宣言を先に変更する。
その後、[コマンド一覧](/references/commands.md)の dry-run で予定された操作を確認し、`--apply` で現実を宣言に合わせる。
