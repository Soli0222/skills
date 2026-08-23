# skills

自作 Agent Skill の原本を置くリポジトリ。

配布されている skill は実体を持たず、[EXTERNAL.md](EXTERNAL.md) に台帳として記録する。

## 自作 skill

| skill | 概要 |
| --- | --- |
| [delegate-implementation](skills/delegate-implementation/) | 実装エージェント（Devin / Claude / Codex CLI）へ開発タスクを委譲する手順。Issue 単位の PR 作成、CI 確認、依存順の squash merge までを扱う |
| [dependency-pr-release-summary](skills/dependency-pr-release-summary/) | Renovate などの依存更新 PR を、リポジトリ上の差分だけでなく上流アプリケーションのリリース影響まで含めて要約する |
| [okf](skills/okf/) | Open Knowledge Format（YAML frontmatter を持つ Markdown のナレッジバンドル）の作成・検証・利用 |

## 配置

原本はこのリポジトリだけに置き、各エージェントの読み取り先へは symlink を張る。

```
<repo>/skills/<name>          原本（git 管理下）
~/.agents/skills/<name>   ->  原本                        Codex などが読む
~/.claude/skills/<name>   ->  ../../.agents/skills/<name>  Claude Code が読む
```

`~/.agents/skills` を経由させるのは、`npx skills add -g` で入れた配布 skill と同じ流儀に揃えるため。
これにより `~/.claude/skills` 配下は「symlink = どこかで管理されている」「実ディレクトリ = 野良」で判別できる。

なお `~/.agents/skills` 配下は、このリポジトリ由来のものが symlink、配布 skill が実ディレクトリになる。
判別規則が成り立つのは `~/.claude/skills` 配下だけである点に注意する。

## インストール

```bash
./scripts/install.sh           # dry-run。何が変わるかだけ表示する
./scripts/install.sh --apply   # 実際に symlink を張る
```

冪等なので、原本を編集したあとに張り直す必要はない。リンクが壊れたり張り替えられたときだけ再実行する。

`skills/*/SKILL.md` があり、かつディレクトリ名と frontmatter の `name` が一致するものだけを対象にする。
リンク先に既存の実ディレクトリがある場合、内容・ファイル種別・実行ビットが原本と完全一致するときだけ、
`~/.skills-backup/<timestamp>/` へ退避したうえで symlink に置き換える。
一致しなければ `CONFLICT` として差分を表示し、何もせずに終了する（終了コード 1）。
差分を確認したうえで原本で上書きしてよければ `--force` を付ける。この場合も退避は行う。

管理対象にない skill には一切触れない。

環境変数 `AGENTS_SKILLS_DIR` / `CLAUDE_SKILLS_DIR` / `SKILLS_BACKUP_DIR` で配置先を差し替えられる。

## skill を追加する

1. `skills/<name>/SKILL.md` を作る。frontmatter の `name` はディレクトリ名と一致させる
2. `./scripts/install.sh --apply`
