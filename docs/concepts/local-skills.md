---
type: Repository Concept
title: 自作 skill
description: "`skills/<name>/` を原本として、エージェントの読み取り先へ symlink で公開する skill。"
resource: ../../skills/
tags: [local, symlink, source-of-truth]
timestamp: 2026-08-23T18:03:28+09:00
---

# 管理単位

自作 skill は、`skills/<name>/SKILL.md` を持つディレクトリ単位で管理する。
ディレクトリ名と `SKILL.md` の frontmatter にある `name` は一致していなければならない。

原本はリポジトリ内に一つだけ置く。
`~/.agents/skills/<name>` は原本を直接指し、`~/.claude/skills/<name>` は agents 側を相対 symlink で指す。
したがって、原本を編集した後にリンクを張り直す必要はない。

# 競合の扱い

配置先に実ディレクトリがある場合、管理スクリプトは内容、ファイル種別、実行ビットを原本と比較する。
完全に一致すればバックアップして symlink へ置換できるが、差異があれば `CONFLICT` として停止する。

`--force` は差異を消す許可になるため、表示された差分の所有者と必要性を確認してから使う。
置換される実体は `~/.skills-backup/<timestamp>/` へ退避される。

# 関連手順

新規追加は[自作 skill を追加する](/playbooks/add-local-skill.md)に従う。
リンク切れや配置差異は[状態を検査して復旧する](/playbooks/verify-and-recover.md)で調べる。

# Citations

[1] [配置スクリプト](../../scripts/install.sh)

[2] [回帰テスト](../../tests/run.sh)
