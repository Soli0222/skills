---
type: Playbook
title: 配布 skill を追加する
description: 外部 skill の取得元を manifest へ登録し、導入と人向け台帳の生成までを行う。
tags: [external, dependency, installation]
timestamp: 2026-08-23T18:03:28+09:00
---

# 取得元を登録する

追加コマンドは gist と GitHub リポジトリに対応する。
gist は URL または ID、GitHub リポジトリは URL または `owner/repo` で指定する。

```bash
./scripts/install.sh external add <source>
```

gist のファイル名が `SKILL.md` だけで skill 名を判定できない場合は `--name <name>` を付ける。
GitHub リポジトリから複数の skill が見つかる場合は、必要なものだけを `--skill <name>` で指定できる。

# manifest を確定する

`add` は `external/manifest.toml` に項目を即時追加する。
追加された `TODO` を埋め、概要、分類、ライセンス、更新方針が取得元と一致することを確認する。

gist のライセンスは本文だけで判断しない。
作者が gist のコメントでライセンスを宣言している場合があるため、コメントも確認する。

# 導入して記録を完成させる

まず dry-run で対象と操作を確認し、その後に適用する。

```bash
./scripts/install.sh external install <name>
./scripts/install.sh external install <name> --apply
./scripts/install.sh docs
./scripts/install.sh docs --check
./scripts/install.sh external status <name>
```

gist では、初回の `install --apply` が取得内容の SHA-256 を manifest に記録する。
最後に `git diff` を読み、manifest と `EXTERNAL.md` の変更が同じ依存を表していることを確認する。

# Citations

[1] [README の追加手順](../../README.md)

[2] [配布 skill 管理スクリプト](../../scripts/external.py)
