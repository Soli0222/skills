---
type: Path Reference
title: 管理対象のファイル配置
description: リポジトリ内の原本と、ホームディレクトリ内の導入済み実体の対応表。
tags: [filesystem, layout, reference]
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
---

# リポジトリ内

| パス | 内容 | 管理方法 |
| --- | --- | --- |
| `skills/<name>/` | 自作 skill の原本 | Git で追跡 |
| `external/manifest.toml` | 配布 skill の依存宣言 | Git で追跡 |
| `EXTERNAL.md` | manifest から作る人向け台帳 | 生成して Git で追跡 |
| `scripts/install.sh` | 自作 skill の配置と共通入口 | Git で追跡 |
| `scripts/external.py` | 配布 skill の管理処理 | Git で追跡 |
| `tests/run.sh` | 管理処理のオフライン回帰テスト | Git で追跡 |
| `docs/` | この OKF バンドル | Git で追跡 |

# ホームディレクトリ内

| パス | 内容 | 原本との関係 |
| --- | --- | --- |
| `~/.agents/skills/<name>` | Codex などが読む skill | 自作は symlink、配布は導入済み実体 |
| `~/.claude/skills/<name>` | Claude Code が読む skill | agents 側への相対 symlink |
| `~/.agents/.skill-lock.json` | skills CLI の導入記録 | manifest と取得元を照合する材料 |
| `~/.skills-backup/<timestamp>/` | 置換前の退避先 | 復旧が必要なときだけ参照 |

# 所有関係

リポジトリ外の配置先を直接編集すると、次回の検査で宣言との差異になる。
自作 skill は `skills/<name>/` を編集し、配布 skill は上流の更新を取り込むか manifest の依存を変更する。
