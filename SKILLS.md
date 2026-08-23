# 入っている skill の使い方

いま `~/.claude/skills` と `~/.agents/skills` に入っている skill を、いつ・どう呼ぶかだけまとめたもの。
何をどう管理しているかは [README.md](README.md)、配布 skill の出所とライセンスは [EXTERNAL.md](EXTERNAL.md) を見る。

Claude Code に最初から入っている skill（`code-review`、`dataviz`、`artifact-*` など）は、この repo の管理外なのでここには書かない。

## 呼び方の基本

skill は frontmatter の `description` が今の依頼に合えば自動で起動する。
「日本語の記事を書いて」と言えば `natural-japanese` が、「Renovate の PR を見て」と言えば `dependency-pr-release-summary` が立ち上がる。

明示したいときは `/<name>` と打つ。引数を取るものは `/natural-japanese score quick draft.md` のように続けて書く。

`review-animations` だけは `disable-model-invocation: true` なので、自動では起動しない。使うときは必ず `/review-animations` と打つ。

## 一覧

| skill | 出自 | 呼びどき |
| --- | --- | --- |
| [natural-japanese](#natural-japanese) | 配布 | 仕事の日本語文書を書く・直す。AI 臭さの診断も |
| [japanese-tech-writing](#japanese-tech-writing) | 配布 | 技術書・技術記事の文章規範 |
| [cognitive-rhythm-writing](#cognitive-rhythm-writing) | 配布 | 読み物としての緩急がない文章を直す |
| [hallmark](#hallmark) | 配布 | Web ページを新規に作る、監査する、作り直す |
| [emil-design-eng](#emil-design-eng) | 配布 | UI の細部の判断に迷ったとき |
| [apple-design](#apple-design) | 配布 | ジェスチャ、spring、シート、素材感 |
| [improve-animations](#improve-animations) | 配布 | コードベース全体のモーションを棚卸しして計画にする |
| [review-animations](#review-animations) | 配布 | 目の前のアニメーション差分をレビューする |
| [animation-vocabulary](#animation-vocabulary) | 配布 | 「あの動きの名前」を引く |
| [delegate-implementation](#delegate-implementation) | 自作 | 実装を実装エージェントへ委譲して進める |
| [dependency-pr-release-summary](#dependency-pr-release-summary) | 自作 | 依存更新 PR の影響をまとめる |
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
一文一行、引用ブロック、脚注、コラムといった整形と、パラグラフライティング、ツッコミどころの除去、LLM っぽい空句の禁止までを定める。

`natural-japanese` と守備範囲が重なる。技術文書の整形と論証まで面倒を見てほしいときはこちら、読みやすさと自然さだけならあちらでよい。
両方を同時に当てると規範がぶつかることがあるので、どちらを主にするか先に決める。

### cognitive-rhythm-writing

「密度はあるのに平坦でおもしろくない」文章を直す。
緩急を装飾ではなく認知モードの切替と未回収の緊張として扱い、文の拍と段落の密度波形を設計する。

`japanese-tech-writing` を前提に併用する設計で、SKILL.md から `../japanese-tech-writing/SKILL.md` を参照している。
単体で当てても効くが、技術文書なら二つ並べて使うのが本来の形。

## UI・デザイン

### hallmark

AI が作った感じのしない Web ページを作るための skill。動詞が3つある。

```
hallmark audit <target>                 採点して直すべき点を並べる。編集はしない
hallmark redesign <target> [--mood ...]  中身は保ったまま見た目の層だけ作り直す
hallmark study <screenshot|URL>          好きなデザインの DNA を抽出する
```

動詞なしで「ランディングページ作って」と頼めば、既定の Design flow でテーマを選んで作る。
既存プロジェクトでは、消すファイルを挙げて確認を取ってから動く安全弁が入っている。

### emil-design-eng

Emil Kowalski の UI ポリッシュ観。
アニメーションの是非、コンポーネントの設計、気づかれない細部の積み上げについて判断の基準をくれる。

質問なしで呼ぶと挨拶だけ返して止まる作りなので、聞きたいことと一緒に呼ぶ。

`hallmark` と役割が重なる。ページ全体を作るなら `hallmark`、部品や1つのインタラクションの詰めなら `emil-design-eng` と切り分けると衝突しない。

### apple-design

Apple 流のインターフェースと物理的なモーションを Web に翻訳したもの。
ドラッグ、スワイプ、シート、spring、慣性と中断可能な遷移、半透明のマテリアル、タイポグラフィ（optical sizing、トラッキング、行送り）、reduced-motion が対象。

### improve-animations

コードベースのモーションを一通り見て、優先度つきの所見と、他のエージェントがそのまま実行できる実装計画を書く。
**ソースコードは書き換えない**。作るのは `plans/` 配下のファイルだけ。

```
improve-animations                       recon → 全カテゴリ監査 → 計画
improve-animations quick|deep            監査の深さを変える
improve-animations performance など       カテゴリを絞る
improve-animations plan <description>    監査を飛ばして1件だけ計画を書く
improve-animations execute <plan>        計画を worktree で実行させ、差分をレビューする
improve-animations reconcile             plans/ を現在のコードと突き合わせ直す
```

### review-animations

目の前のアニメーション差分を、Emil Kowalski 由来の基準でレビューする。
既定は指摘であって、承認は勝ち取るもの、という姿勢。

自動起動しないので `/review-animations` と明示的に打つ。
コードベース全体の棚卸しは `improve-animations` の仕事で、こちらは1つの差分を見る。

### animation-vocabulary

「ポップオーバーが開くときのぽよんとしたやつ」→ Pop in、「iOS のゴムみたいなスクロール」→ Rubber-banding のように、動きの説明から正確な用語を引く逆引き辞書。
名前を知るためのもので、設計や実装はしない。

## 開発

### delegate-implementation

自分は計画・レビュー・git/GitHub 操作に徹し、コードとテストの実装は実装エージェント（Devin CLI、Claude CLI、Codex CLI）へ渡す進め方。
複数 Issue、親子・依存 Issue、Issue 単位の PR、CI 確認、依存順の squash merge までを扱う。

実装エージェントには push、PR 操作、CI 操作、merge、rebase、branch と worktree の操作を一切させない。
実装者ごとの起動方法は `skills/delegate-implementation/references/implementer-*.md` にある。

到達点を指定しなければ「Ready PR + 最新 HEAD の CI 成功」まで。merge まで進めたいなら明示して頼む。

### dependency-pr-release-summary

open な依存更新 PR を、レビューできる形に一度で要約する。
PR の差分やチャートのリリースノートで止めず、`appVersion` が動いたかどうかを見て、アプリ本体のリリース影響まで追う。

Helm/Flux のチャート更新が主な想定だが、GitHub Actions や Ansible の変数更新も扱う。
`gh` が使えて、リポジトリの git remote から対象を引ける状態で呼ぶ。

## 知識・ツール

### okf

Open Knowledge Format v0.2（YAML frontmatter を持つ Markdown のナレッジバンドル）の作成、更新、レビュー、検証。
`type` が必須で、provenance・trust・lifecycle のフィールドと、`index.md` / `log.md` の予約ファイル名を定める。

検証は `skills/okf/scripts/validate_okf.py`。この repo の [docs/](docs/) 自体が OKF で書かれている。

### find-skills

やりたいことに合う skill が世の中にあるか探して、`npx skills` で入れるところまで面倒を見る。

この repo で管理する以上、入れたあとは [EXTERNAL.md](EXTERNAL.md) の台帳にも載せる。
`./scripts/install.sh external add <url>` から始めれば、manifest と symlink まで揃う。
