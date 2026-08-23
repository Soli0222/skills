# skills

自作 Agent Skill の原本を置くリポジトリ。

配布されている skill は実体を持たず、[`external/manifest.toml`](external/manifest.toml) に台帳として記録する。
[EXTERNAL.md](EXTERNAL.md) はそこから生成する読み物で、手では編集しない。

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

## 使い方

```bash
./scripts/install.sh                  # dry-run。自作の symlink と配布の導入状況を出す
./scripts/install.sh --apply          # 両方まとめて適用
```

サブコマンドで片方だけ扱える。

```bash
./scripts/install.sh link --apply           # 自作: symlink だけ
./scripts/install.sh external status        # 配布: 導入状況と pin・上流の一致
./scripts/install.sh external install --apply
./scripts/install.sh external update --apply
./scripts/install.sh external add <url>     # manifest に項目を足す
./scripts/install.sh docs                   # EXTERNAL.md を生成
./scripts/install.sh docs --check           # 生成物が manifest と食い違っていないか
```

`link` / `external install` / `external update` は `--apply` を付けない限り何も書き換えない。
名前を渡せばその skill だけを対象にできる。
`external add` は manifest に、`docs` は EXTERNAL.md に、それぞれ即座に書き込む。

### 自作 skill（link）

冪等なので、原本を編集したあとに張り直す必要はない。リンクが壊れたり張り替えられたときだけ再実行する。

`skills/*/SKILL.md` があり、かつディレクトリ名と frontmatter の `name` が一致するものだけを対象にする。
リンク先に既存の実ディレクトリがある場合、内容・ファイル種別・実行ビットが原本と完全一致するときだけ、
`~/.skills-backup/<timestamp>/` へ退避したうえで symlink に置き換える。
一致しなければ `CONFLICT` として差分を表示し、何もせずに終了する（終了コード 1）。
差分を確認したうえで原本で上書きしてよければ `--force` を付ける。この場合も退避は行う。

管理対象にない skill には一切触れない。

### 配布 skill（external）

`external/manifest.toml` の `kind` で扱いが変わる。

| kind | install | update |
| --- | --- | --- |
| `gist` | pin した revision を取得して `~/.agents/skills/<name>/SKILL.md` に置き、`~/.claude/skills` から symlink を張る | 上流の最新 revision との差分を表示し、`--apply` で本体と manifest の pin を同時に更新する |
| `skills-cli` | `npx skills add <repo> -g -a … --skill … -y` を呼ぶ | `npx skills update <name> -g -y` を呼び、前後の folder hash を比較する |
| `manual` | 何もしない（存在確認だけ） | 何もしない |

`gist` は revision と SKILL.md の sha256 を pin するので、いつでも同じ内容を取り直せる。
`status --offline` はネットワークに出ず、手元のファイルをこの sha256 とだけ照合する。

`skills-cli` は導入と更新を CLI に任せる。ただし `~/.agents/.skill-lock.json` の
`source` / `sourceUrl` / `skillPath` を台帳と照合するので、同名の別 skill が
入っていれば `CONFLICT` として終了コード 1 になる。

どちらの kind でも、`~/.agents/skills/<name>` の実体と `~/.claude/skills/<name>` の
symlink を同じ規則で確かめる。symlink が消えたり別の場所を向いていれば `--apply` で張り直す。

上書きの前には `~/.skills-backup/<timestamp>/external/` へ退避する。

### 台帳と機械記録

`EXTERNAL.md` は `external/manifest.toml` だけから決まる。手元に何が入っているかは
読まないので、どの環境で生成しても同じものになる。現在の状況は `external status`、
`npx skills` の機械記録は `~/.agents/.skill-lock.json` と、参照先を分けている。

## skill を追加する

### 自作

1. `skills/<name>/SKILL.md` を作る。frontmatter の `name` はディレクトリ名と一致させる
2. `./scripts/install.sh link --apply`

### 配布

1. `./scripts/install.sh external add <gist または GitHub の URL>`
   `state = "planned"` で追記される。id と skill 名の重複は弾く
2. `external/manifest.toml` の `TODO` を埋める。ライセンスは gist のコメントも確認する
3. `./scripts/install.sh external install <id> --apply`
   名前を指定して導入に成功すると `state` が `active` になる（gist なら sha256 も記録される）。
   名前を省いた `external install` は `active` のものしか見ないので、追加直後は id を渡す
4. `./scripts/install.sh docs`

## テスト

```bash
./tests/run.sh
```

ネットワークには出ない。gist の取得先は `GIST_RAW_BASE` と `GITHUB_API_BASE` で
ローカルのフィクスチャに差し替えている。
