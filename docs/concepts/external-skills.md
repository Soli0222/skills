---
type: Repository Concept
title: 配布 skill
description: 外部の gist または GitHub リポジトリから導入し、manifest で再現可能に管理する skill。
resource: ../../external/manifest.toml
tags: [dependency, manifest, reproducibility]
timestamp: 2026-08-23T18:03:28+09:00
---

# 依存宣言

配布 skill の原本は上流にあり、このリポジトリには実体を置かない。
`external/manifest.toml` が、使用する skill、取得元、導入先エージェント、更新方法、ライセンスを宣言する。

導入状況を表す中間状態は manifest に記録しない。
manifest は望ましい状態だけを持ち、`install` が手元の状態を宣言へ合わせ、`status` が差異を報告する。

# gist と skills CLI

gist 由来の skill は revision と `SKILL.md` の SHA-256 を固定する。
`status --offline` はネットワークへ接続せず、導入済みファイルを記録済みハッシュと照合する。

GitHub リポジトリ由来の skill は `npx skills` に導入と更新を任せる。
管理スクリプトは `~/.agents/.skill-lock.json` の取得元を manifest と照合し、同名の別 skill が置かれていないか検査する。

# 人向け台帳

`EXTERNAL.md` は manifest だけから生成される読み物であり、手では編集しない。
依存情報を変更した後は `./scripts/install.sh docs` で再生成し、`./scripts/install.sh docs --check` で食い違いがないことを確認する。

# 関連手順

新しい依存は[配布 skill を追加する](/playbooks/add-external-skill.md)に従って登録する。
既存依存の不一致は[状態を検査して復旧する](/playbooks/verify-and-recover.md)で切り分ける。

# Citations

[1] [配布 skill の manifest](../../external/manifest.toml)

[2] [生成された配布 skill 台帳](../../EXTERNAL.md)

[3] [配布 skill 管理スクリプト](../../scripts/external.py)

