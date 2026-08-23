---
title: skills リポジトリ運用ガイド
description: 自作 skill と配布 skill の管理方法を、概念、手順、リファレンスに分けた OKF バンドル。
tags: [agent-skills, operations, repository]
timestamp: 2026-08-23T18:03:28+09:00
---

# skills リポジトリ運用ガイド

このバンドルは、リポジトリへ skill を追加し、Codex と Claude Code へ安全に配置する人を対象にしている。
初めて触る場合は、まず[管理モデル](concepts/repository-model.md)を読み、続いて作業に合う playbook を選ぶ。
日常作業では、手順かコマンド一覧だけを参照すればよい。

# 最初に読む

* [管理モデル](concepts/repository-model.md) - 原本、依存宣言、導入済み実体、生成文書の関係。
* [自作 skill](concepts/local-skills.md) - リポジトリ内で保守する skill の管理単位。
* [配布 skill](concepts/external-skills.md) - gist と skills CLI 由来の skill を再現可能に管理する方法。

# 作業から探す

* [自作 skill を追加する](playbooks/add-local-skill.md) - `skills/<name>/` を作り、各エージェントへリンクする。
* [配布 skill を追加する](playbooks/add-external-skill.md) - 配布元を台帳へ登録し、導入して記録を確定する。
* [状態を検査して復旧する](playbooks/verify-and-recover.md) - dry-run、status、テストを使って差異を調べる。

# 参照資料

* [コマンド一覧](references/commands.md) - `install.sh` が公開する操作と書き込み範囲。
* [ファイル配置](references/layout.md) - リポジトリ内外のパスと役割。

# 問い合わせ先

このバンドルで判断できない場合は、リポジトリの Issue または通常のコードレビュー経路で確認する。
とくに、競合した実ディレクトリを `--force` で置換してよいかは、差分の所有者が判断する。

