# skills

自作 Agent Skill の原本を置くリポジトリ。

配布されている skill は実体を持たず、[`external/manifest.toml`](external/manifest.toml) に依存として記録する。
`package.json` と同じ考え方で、書いてあるものが「使うもの」、`install` で現実を宣言に合わせ、
`status` で現実が宣言とずれていないかを見る。「導入予定」のような中間状態は持たない。
[EXTERNAL.md](EXTERNAL.md) はそこから生成する読み物で、手では編集しない。

管理モデルと作業手順は、OKF 形式の[運用ガイド](docs/)から辿れる。

## 自作 skill

| skill | 概要 |
| --- | --- |
| [delegate-implementation](skills/delegate-implementation/) | 開発タスクを分割し、ネイティブのサブエージェントや外部CLIへ委譲・統合する。worktreeの要否を判断し、依頼に応じてPR・CI・mergeまで扱う |
| [dependency-pr-release-summary](skills/dependency-pr-release-summary/) | Renovate などの依存更新 PR を、リポジトリ上の差分だけでなく上流アプリケーションのリリース影響まで含めて要約する |
| [okf](skills/okf/) | Open Knowledge Format v0.2（YAML frontmatter を持つ Markdown のナレッジバンドル）の作成・検証・利用 |

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

`gist` は revision と SKILL.md の sha256 を pin するので、いつでも同じ内容を取り直せる。
`status --offline` はネットワークに出ず、手元のファイルをこの sha256 とだけ照合する。

`skills-cli` は導入と更新を CLI に任せる。ただし `~/.agents/.skill-lock.json` の
`source` / `sourceUrl` / `skillPath` を台帳と照合するので、同名の別 skill が
入っていれば `CONFLICT` として終了コード 1 になる。

どちらの kind でも、`~/.agents/skills/<name>` の実体と `~/.claude/skills/<name>` の
symlink を同じ規則で確かめる。symlink が消えたり別の場所を向いていれば `--apply` で張り直す。

上書きの前には `~/.skills-backup/<timestamp>/external/` へ退避する。

### どこに何があるか

| | 対応するもの | git |
| --- | --- | --- |
| `external/manifest.toml` | `package.json`（依存の宣言と pin） | 追跡する |
| `~/.agents/skills/<name>` | `node_modules`（導入された実体） | repo の外 |
| `~/.agents/.skill-lock.json` | `npx skills` が書く機械記録 | repo の外 |

manifest には端末固有の値を入れない。`install` も `status` も manifest を書き換えない。
書き換えるのは、pin を進める `update --apply` と、項目を足す `add` だけで、
どちらも人が意図して打つコマンドである。

その結果 `EXTERNAL.md` は manifest だけから決まり、どの環境で生成しても同じものになる。

## skill を追加する

### 自作

1. `skills/<name>/SKILL.md` を作る。frontmatter の `name` はディレクトリ名と一致させる
2. `./scripts/install.sh link --apply`

### 配布

1. `./scripts/install.sh external add <gist または GitHub の URL>`
   id と skill 名の重複は弾く
2. `external/manifest.toml` の `TODO` を埋める。ライセンスは gist のコメントも確認する
3. `./scripts/install.sh external install --apply`（gist なら sha256 もここで記録される）
4. `./scripts/install.sh docs`

使うのをやめるときは manifest から項目を消す。実体は消えないので、
`~/.agents/skills/<name>` は自分で消すか `npx skills remove` を使う。

## テスト

```bash
./tests/run.sh
```

ネットワークには出ない。gist の取得先は `GIST_RAW_BASE` と `GITHUB_API_BASE` で
ローカルのフィクスチャに差し替えている。

名前で絞り込める（`./tests/run.sh okf` など）。
okf validator のテストは PyYAML があるときだけ走り、無ければ skip する。
