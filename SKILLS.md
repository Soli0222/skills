# 入っている skill の使い方

いま `~/.claude/skills` と `~/.agents/skills` に入っている skill を、いつ・どう呼ぶかだけまとめたもの。
何をどう管理しているかは [README.md](README.md)、配布 skill の出所とライセンスは [EXTERNAL.md](EXTERNAL.md) を見る。

Claude Code に最初から入っている skill（`code-review`、`dataviz`、`artifact-*` など）は、この repo の管理外なのでここには書かない。

## 呼び方の基本

skill は frontmatter の `description` が今の依頼に合えば自動で起動する。
「日本語の記事を書いて」と言えば `natural-japanese` が、「Renovate の PR を見て」と言えば `dependency-pr-release-summary` が立ち上がる。

明示したいときは `/<name>` と打つ。引数を取るものは `/natural-japanese score quick draft.md` のように続けて書く。

`yomiyasu` は description で「名前を出して頼まれたときだけ使う」と決めているので、自動では起動しない。使うときは `/yomiyasu` と打つ。

## 一覧

| skill | 出自 | 呼びどき |
| --- | --- | --- |
| [natural-japanese](#natural-japanese) | 配布 | 仕事の日本語文書を書く・直す。AI 臭さの診断も |
| [japanese-tech-writing](#japanese-tech-writing) | 配布 | 技術書・技術記事の文章規範 |
| [yomiyasu](#yomiyasu) | 配布 | AI が書いた日本語を、意味を保ったまま推敲する |
| [cognitive-rhythm-writing](#cognitive-rhythm-writing) | 配布 | 読み物としての緩急がない文章を直す |
| [delegate-implementation](#delegate-implementation) | 自作 | 実装を実装エージェントへ委譲して進める |
| [dependency-pr-release-summary](#dependency-pr-release-summary) | 自作 | 依存更新 PR の影響をまとめる |
| [misskey-upgrade](#misskey-upgrade) | 自作 | Misskey の upstream 更新から PKE 本番反映まで進める |
| [okf](#okf) | 自作 | OKF 形式のナレッジバンドルを書く・検証する |
| [find-skills](#find-skills) | 配布 | 足りない skill を探して入れる |

## 文章

### natural-japanese

議事録、レポート、社内ガイド、メール、企画書といった仕事の文書と、note・ブログ・エッセイが対象。
「検出は機械、判断は AI」で、禁止語や翻訳調は lint が決定的に拾い、直すかどうかは文脈で決める。

```
/natural-japanese [quick|full] <対象>          書く・直す（既定）
/natural-japanese write [quick|full] <お題>    新規執筆であることを明示する
/natural-japanese score [quick|full|exp] <file>  診断だけ。書き換えない
```

`quick` が既定で数十秒。`full` はサブエージェント込みで短い文書でも7分前後かかるので、対外文書や1万字級のときに使う。
`score` は0〜100の自然度スコアを返す。`exp` は初回に約1GB のモデルを落とす。

### japanese-tech-writing

技術書の章や技術記事のための規範。
パラグラフライティング、ツッコミどころの除去、LLM っぽい空句や翻訳調の比喩（「運ぶ」「効く」「開かれた問い」）の禁止までを定める。
2026-09 の改訂で、一文一行や脚注といった整形の規則は外れた。

`natural-japanese` と守備範囲が重なる。技術文書の論証まで面倒を見てほしいときはこちら、読みやすさと自然さだけならあちらでよい。
両方を同時に当てると規範がぶつかることがあるので、どちらを主にするか先に決める。

### yomiyasu

AI が生成した日本語の不自然な比喩、曖昧な主述関係、不要な装飾を直す推敲 skill。
主張、比重、言い切りの強さ、文の働きを変えず、原文にない情報を足さないことを最優先にする。
lint と推敲前後の比較スクリプトで、直した結果が原文の意味からずれていないかを確かめる。

```
/yomiyasu <対象>     推敲する。対象がなければ直前の本文か作業フォルダ直下の .md/.txt を選ぶ
```

名前を出したときだけ起動するので、使うときは `/yomiyasu` と打つか「yomiyasu で推敲して」と書く。
ファイルを推敲したときは原文を書き換えず、別名で最終稿を保存する。

SKILL.md が、他の日本語校正 skill との併用で指示がぶつかると注意している。
`natural-japanese` や `japanese-tech-writing` と同じ文章に重ねて当てない。

### cognitive-rhythm-writing

「密度はあるのに平坦でおもしろくない」文章を直す。
緩急を装飾ではなく認知モードの切替と未回収の緊張として扱い、文の拍と段落の密度波形を設計する。

`japanese-tech-writing` を前提に併用する設計で、SKILL.md から `../japanese-tech-writing/SKILL.md` を参照している。
単体で当てても効くが、技術文書なら二つ並べて使うのが本来の形。

## 開発

### delegate-implementation

開発タスクを独立した成果物に分割し、ネイティブのサブエージェントまたは外部CLIへ委譲して、レビュー・統合する。
直接実装も選択肢に含め、実行手段とworktreeの要否を別々に判断する。

共有作業ツリーでは編集担当を分け、Git操作は親が担当する。
専用worktreeは別branchでの並行開発や既存変更との分離が必要な場合に使う。
ネイティブ委譲、外部CLI、GitHub運用の詳細は `skills/delegate-implementation/references/` にある。

到達点は依頼に従う。ローカル実装、PR作成、CI確認、mergeを区別し、必要な範囲だけ進める。

### dependency-pr-release-summary

open な依存更新 PR を、レビューできる形に一度で要約する。
PR の差分やチャートのリリースノートで止めず、`appVersion` が動いたかどうかを見て、アプリ本体のリリース影響まで追う。

Helm/Flux のチャート更新が主な想定だが、GitHub Actions や Ansible の変数更新も扱う。
`gh` が使えて、リポジトリの git remote から対象を引ける状態で呼ぶ。

### misskey-upgrade

Soli0222/misskey の upstream 取り込み、競合解消、2つの package version 更新、develop → master の PR と Release、GHCR 公開確認を進める。
設定変更は PKE の Helm chart に反映し、本番更新まで依頼された場合は Flux とアプリの稼働状態まで確認する。

Codex では `$misskey-upgrade`、Claude Code では `/misskey-upgrade` を使う。

```text
$misskey-upgrade 最新リリースを取り込んで、PR作成まで
$misskey-upgrade 最新リリースを取り込んで、本番更新まで
$misskey-upgrade 前回の更新を続きから
```

到達点が省略された初回は PR 作成まで。既存の `psr.x.y` を保持して upstream version を更新する。
再開時は保存した対象 SHA と実際の PR・Release・image・Flux の状態を照合する。

## 知識・ツール

### okf

Open Knowledge Format v0.2（YAML frontmatter を持つ Markdown のナレッジバンドル）の作成、更新、レビュー、検証。
`type` が必須で、provenance・trust・lifecycle のフィールドと、`index.md` / `log.md` の予約ファイル名を定める。

検証は `skills/okf/scripts/validate_okf.py`。この repo の [docs/](docs/) 自体が OKF で書かれている。

### find-skills

やりたいことに合う skill が世の中にあるか探して、`npx skills` で入れるところまで面倒を見る。

この repo で管理する以上、入れたあとは [EXTERNAL.md](EXTERNAL.md) の台帳にも載せる。
`./scripts/install.sh external add <url>` から始めれば、manifest と symlink まで揃う。
