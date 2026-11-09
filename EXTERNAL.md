# 配布 skill の台帳

自分で書いていない skill の記録。実体はこのリポジトリに置かず、導入元と確認した revision だけを残す。

> **このファイルは `external/manifest.toml` から生成している。手で編集しない。**
> 変更は manifest 側で行い、`./scripts/install.sh docs` で再生成する。

ここに書いてあるのは台帳の内容だけで、いま実際に何が入っているかは含まない。
手元の導入状況は `./scripts/install.sh external status` で見る。
`npx skills` が書く機械側の記録は `~/.agents/.skill-lock.json` にある。

gist はライセンスがファイルではなくコメントで示されることがある。リポジトリのファイル一覧だけを見て「明示なし」と判断しない。

```bash
curl -s https://api.github.com/gists/<id>/comments | jq -r '.[].body'
```

最終棚卸し: 2026-11-09

---

## 文章

### japanese-tech-writing

日本語技術文書の文章規範。パラグラフライティング、論証の厳密さ、LLM っぽい空句と翻訳調の比喩の禁止など。

- 使用先: 両方（`~/.agents/skills/japanese-tech-writing` に実体、`~/.claude/skills` から symlink）
- 出所: k16shikano / gist [`fd287c3133457c4fd8f5601d34aa817d`](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d)
- ライセンス: Unlicense（パブリックドメイン献呈）。gist のファイルではなく[コメント](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d?permalink_comment_id=6210840#gistcomment-6210840)で明示され、[k16shikano/67625f2a7d96e3bbdfae8d571a936063](https://gist.github.com/k16shikano/67625f2a7d96e3bbdfae8d571a936063) を参照している
- revision: `8f2d57610a73efc97d743c9b0b0ecb1002e09fa4` (2026-09-09)
- SKILL.md の sha256: `ad350e0e6f5630fd94d8ab98a6aee194053b0096fdc944c23e271d6dfa09ee68`
- 更新方針: 手動追従
- ローカル変更: なし

```bash
curl -sfL https://gist.githubusercontent.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d/raw/8f2d57610a73efc97d743c9b0b0ecb1002e09fa4/SKILL.md \
  -o ~/.agents/skills/japanese-tech-writing/SKILL.md
```

2026-08-23 に `5ed08e4`（2026-06-16）から `c7189cd` へ追従した。差分は「辞書型断定で始めない」と「イ形容詞＋です を書かない」の2ルール追加。

2026-11-09 に `8f2d576`（2026-09-09）へ追従した。「整形」の節（一文一行、脚注、ダッシュ・中黒の禁止など）と「辞書型断定で始めない」が削除され、「翻訳調の比喩と擬人化の禁止」の節、対比定義・概念導入の語順・複数媒体の書き分けの規則が追加された。frontmatter に `license` が入った。

同じ gist のコメント 6201959 に、この規範を呼び出す派生 skill の実例（`argument-gap-edit`）がある。

### cognitive-rhythm-writing

説明的な文章の緩急を、認知モードの切替と未回収の緊張の管理として設計する規範。`japanese-tech-writing` と併用する。

- 使用先: 両方（`~/.agents/skills/cognitive-rhythm-writing` に実体、`~/.claude/skills` から symlink）
- 出所: k16shikano / gist [`eb2929f13ed19c97188393d297be8432`](https://gist.github.com/k16shikano/eb2929f13ed19c97188393d297be8432)
- ライセンス: Unlicense（パブリックドメイン献呈）。[k16shikano/67625f2a7d96e3bbdfae8d571a936063](https://gist.github.com/k16shikano/67625f2a7d96e3bbdfae8d571a936063) が「k16shikano の public gist にはすべて Unlicense を適用します」と包括宣言しており、この gist は public
- revision: `a3b1e26beced71d582e13314fb6f5b179b023c76`
- SKILL.md の sha256: `65486e64f33ce2ab03c5db198b1f92e2838e71abfb1a80085d1b405340c11437`
- 更新方針: 手動追従
- ローカル変更: なし

```bash
curl -sfL https://gist.githubusercontent.com/k16shikano/eb2929f13ed19c97188393d297be8432/raw/a3b1e26beced71d582e13314fb6f5b179b023c76/SKILL.md \
  -o ~/.agents/skills/cognitive-rhythm-writing/SKILL.md
```

SKILL.md 内で `../japanese-tech-writing/SKILL.md` を参照するので、両者を同じディレクトリ階層に置く必要がある。

### natural-japanese

読みやすい日本語の業務文書を書くための skill。形態素解析で「AI っぽい」パターンを検出する。

- 使用先: 両方（`~/.agents/skills/natural-japanese` に実体、`~/.claude/skills` から symlink）
- 出所: [coji/natural-japanese](https://github.com/coji/natural-japanese)
- ライセンス: MIT
- 更新方針: `npx skills update`
- ローカル変更: なし

```bash
npx skills add coji/natural-japanese -g -a claude-code -a codex \
  --skill natural-japanese
```

`japanese-tech-writing` と規範が競合しないか確認してから常用する。

### yomiyasu

AI が生成した日本語の不自然な比喩、曖昧な主述関係、不要な装飾を、意味を保ったまま推敲する skill。lint と前後比較の検査スクリプトを持つ。

- 使用先: 両方（`~/.agents/skills/yomiyasu` に実体、`~/.claude/skills` から symlink）
- 出所: [nanaism/yomiyasu](https://github.com/nanaism/yomiyasu)
- ライセンス: MIT
- 更新方針: `npx skills update`
- ローカル変更: なし

```bash
npx skills add nanaism/yomiyasu -g -a claude-code -a codex \
  --skill yomiyasu
```

名前を出して頼んだとき（`/yomiyasu`、「yomiyasu で推敲して」）だけ起動する description になっている。SKILL.md 自身が、他の日本語校正 skill と併用すると指示が食い違うことがあると注意しているので、`natural-japanese` や `japanese-tech-writing` と同時に当てない。

Claude Code プラグインとしても配布されているが、ここでは他と揃えて `npx skills` で入れる。

---

## ツール

### find-skills

skill 自体を検索・導入するための skill。

- 使用先: 両方（`~/.agents/skills/find-skills` に実体、`~/.claude/skills` から symlink）
- 出所: [vercel-labs/skills](https://github.com/vercel-labs/skills)
- ライセンス: MIT
- 更新方針: `npx skills update`
- ローカル変更: なし

```bash
npx skills add vercel-labs/skills -g -a claude-code -a codex \
  --skill find-skills
```
