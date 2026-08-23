---
type: Command Reference
title: 管理コマンド一覧
description: 自作 skill、配布 skill、生成文書を扱うコマンドの早見表。
resource: ../../scripts/install.sh
tags: [cli, reference, operations]
generated: { by: codex/gpt-5.6-sol, at: 2026-08-23T18:03:28+09:00 }
verified: { by: human:Soli0222, at: 2026-08-23T19:16:43+09:00 }
sources:
  - id: install-sh
    resource: ../../scripts/install.sh
    title: 配置スクリプト
    last_modified: 2026-08-23T17:29:24+09:00
  - id: external-py
    resource: ../../scripts/external.py
    title: 配布 skill 管理スクリプト
    last_modified: 2026-08-23T17:57:22+09:00
---

# 既定では書き込まない操作

`link`、`external install`、`external update` は、`--apply` を付けない限り変更予定を表示する。
ただし、`external add` は manifest に、`docs` は `EXTERNAL.md` に即時書き込む。

| コマンド | 対象 | 動作 |
| --- | --- | --- |
| `./scripts/install.sh` | 自作と配布 | link と external install の dry-run |
| `./scripts/install.sh --apply` | 自作と配布 | 宣言された配置を適用 |
| `./scripts/install.sh link [--apply]` | 自作 | symlink を検査または作成 |
| `./scripts/install.sh external status [name...]` | 配布 | 導入、pin、取得元、symlink を検査 |
| `./scripts/install.sh external status --offline [name...]` | gist | SHA-256 と配置だけを検査 |
| `./scripts/install.sh external install [name...] [--apply]` | 配布 | manifest の宣言どおりに導入 |
| `./scripts/install.sh external update [name...] [--apply]` | 配布 | 上流との差分を表示または更新 |
| `./scripts/install.sh external add <source>` | 配布 | manifest に新しい依存を追加 |
| `./scripts/install.sh docs [--check]` | 生成文書 | `EXTERNAL.md` を生成または照合 |
| `./tests/run.sh [filter]` | 管理機能 | ネットワークを使わず回帰テストを実行 |

# `external add` の補助オプション

| オプション | 用途 |
| --- | --- |
| `--name <name>` | gist やリポジトリ名から決められない管理 ID を指定する |
| `--category <category>` | `EXTERNAL.md` で使う分類を指定する |
| `--skill <name>` | GitHub リポジトリから導入する skill を絞る。複数回指定できる |

# 書き込みと退避

置換が必要な操作は、既存の実体を `~/.skills-backup/<timestamp>/` へ退避する。
manifest を変更するのは `external add` と、pin を進める `external update --apply`、未記録のハッシュを確定する gist の `external install --apply` である。
