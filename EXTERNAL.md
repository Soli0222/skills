# 配布 skill の台帳

自分で書いていない skill の記録。実体はこのリポジトリに置かず、導入元と確認した revision だけを残す。
ここは人間向けの台帳で、`npx skills` が書く機械側の記録は `~/.agents/.skill-lock.json` にある。役割を混ぜない。

最終棚卸し: 2026-08-23

## 記録する項目

- **状態** — 使用中 / 導入予定 / 停止中
- **使用先** — Claude / Codex / 両方
- **導入** — 再現できる完全なコマンド
- **revision** — 確認した時点の commit / tag / gist revision SHA
- **更新方針** — 手動追従 / 固定 / `npx skills update`
- **ローカル変更** — なし / あり（あるなら内容）

---

## 文章

### japanese-tech-writing

日本語技術文書の文章規範。整形、パラグラフライティング、論証の厳密さ、LLM っぽい空句の禁止など。

- 状態: 使用中
- 使用先: 両方（`~/.agents/skills/japanese-tech-writing` に実体、`~/.claude/skills` から symlink）
- 出所: k16shikano / gist [`fd287c3133457c4fd8f5601d34aa817d`](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d)
- ライセンス: 明示なし（gist に LICENSE がない）
- revision: `c7189cdc9c2520be50418209834145bdf3a46e97` (2026-07-24)
- 更新方針: 手動追従
- ローカル変更: なし
- 導入:
  ```bash
  curl -sfL https://gist.githubusercontent.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d/raw/c7189cdc9c2520be50418209834145bdf3a46e97/SKILL.md \
    -o ~/.agents/skills/japanese-tech-writing/SKILL.md
  ```
- メモ: 2026-08-23 に `5ed08e4`（2026-06-16）から `c7189cd` へ追従した。差分は「辞書型断定で始めない」と「イ形容詞＋です を書かない」の2ルール追加。

### cognitive-rhythm-writing

説明的な文章の緩急を、認知モードの切替と未回収の緊張の管理として設計する規範。`japanese-tech-writing` と併用する。

- 状態: 使用中
- 使用先: 両方（`~/.agents/skills/cognitive-rhythm-writing` に実体、`~/.claude/skills` から symlink）
- 出所: k16shikano / gist [`eb2929f13ed19c97188393d297be8432`](https://gist.github.com/k16shikano/eb2929f13ed19c97188393d297be8432)
- ライセンス: 明示なし（gist に LICENSE がない）
- revision: `a3b1e26beced71d582e13314fb6f5b179b023c76`
- 更新方針: 手動追従
- ローカル変更: なし
- 導入:
  ```bash
  curl -sfL https://gist.githubusercontent.com/k16shikano/eb2929f13ed19c97188393d297be8432/raw/a3b1e26beced71d582e13314fb6f5b179b023c76/SKILL.md \
    -o ~/.agents/skills/cognitive-rhythm-writing/SKILL.md
  ```
- メモ: SKILL.md 内で `../japanese-tech-writing/SKILL.md` を参照するので、両者を同じディレクトリ階層に置く必要がある。

### natural-japanese

読みやすい日本語の業務文書を書くための skill。形態素解析で「AI っぽい」パターンを検出する。

- 状態: 導入予定
- 使用先: 未定
- 出所: [coji/natural-japanese](https://github.com/coji/natural-japanese)
- ライセンス: MIT
- revision: 未確認
- 更新方針: `npx skills update`
- ローカル変更: なし
- 導入:
  ```bash
  npx skills add coji/natural-japanese -g -a claude-code -a codex --skill natural-japanese
  ```
- メモ: `japanese-tech-writing` と規範が競合しないか確認してから常用する。

---

## UI・デザイン

### emilkowalski/skills

Emil Kowalski の UI ポリッシュ・アニメーション設計。リポジトリには12個あるが、使っているのは5個。

- 状態: 使用中
- 使用先: 両方（`~/.agents/skills/<name>` に実体、`~/.claude/skills` から symlink）
- 出所: [emilkowalski/skills](https://github.com/emilkowalski/skills)
- ライセンス: MIT
- 使用中の skill と `~/.agents/.skill-lock.json` 記録の folder hash:
  | skill | skillFolderHash |
  | --- | --- |
  | `emil-design-eng` | `0e6f8d7223a0abe73f81e890b3ec76257029a834` |
  | `apple-design` | `e9f5b472dfb28d8cf29f64001b6c01ef94b8168b` |
  | `animation-vocabulary` | `e6dc24ca1ff1e70c9677df9a1d2d1c80415cbb3c` |
  | `improve-animations` | `ec57cb65ea60a23af278d305d1425ce4f998f510` |
  | `review-animations` | `0012fc43a25cce5df019102ab28bb6a68ad9db3d` |
- 更新方針: `npx skills update`
- ローカル変更: なし
- 導入 (2026-07-12):
  ```bash
  npx skills add emilkowalski/skills -g -a claude-code -a codex \
    --skill emil-design-eng --skill apple-design --skill animation-vocabulary \
    --skill improve-animations --skill review-animations
  ```
- 未導入: `animate`, `animate-expo`, `find-animation-opportunities`, `write-swift`, `pick-ui-library`, `prototype`, `ask-sonner`

### hallmark

AI っぽくない Web UI を生成する design skill。`hallmark audit` / `redesign` / `study` の各動詞を持つ。

- 状態: 導入予定
- 使用先: 未定
- 出所: [Nutlope/hallmark](https://github.com/Nutlope/hallmark)
- ライセンス: MIT
- revision: 未確認
- 更新方針: `npx skills update`
- ローカル変更: なし
- 導入:
  ```bash
  npx skills add nutlope/hallmark -g -a claude-code -a codex --skill hallmark
  ```
- メモ: `emil-design-eng` および Anthropic 公式の `frontend-design` と役割が重なる。3つ入れたままにするか整理するか、使ってから決める。

### frontend-design

Anthropic 公式。テンプレート然としない視覚デザインの指針。

- 状態: 使用中
- 使用先: Claude のみ（`~/.claude/skills/frontend-design` に実体。`npx skills` 経由ではない）
- 出所: Anthropic 公式プラグイン（`claude-plugins-official` marketplace の `frontend-design`）
- ライセンス: 同梱の `LICENSE.txt` を参照
- revision: 未確認（marketplace 側は version `unknown`）
- 更新方針: 固定
- ローカル変更: なし
- メモ: `~/.claude/skills` 配下では数少ない実ディレクトリ。プラグインとしても `/Users/soli/work/misskey` に project scope で入っている。

---

## ツール

### find-skills

skill 自体を検索・導入するための skill。

- 状態: 使用中
- 使用先: 両方（`~/.agents/skills/find-skills` に実体、`~/.claude/skills` から symlink）
- 出所: [vercel-labs/skills](https://github.com/vercel-labs/skills)
- ライセンス: MIT
- revision: `skillFolderHash` `76a98a285cb0434f3d39e1a873823556330e398b`
- 更新方針: `npx skills update`
- ローカル変更: なし
- 導入 (2026-07-12):
  ```bash
  npx skills add vercel-labs/skills -g -a claude-code -a codex --skill find-skills
  ```
