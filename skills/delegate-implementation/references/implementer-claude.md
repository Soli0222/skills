# 実装者アダプター: Claude CLI

`SKILL.md`の実装者契約と「実装エージェントへの禁止事項」が正本。ここには起動方法だけを書く。
フラグは変わりうるので、初回起動前に`claude --help`で実在を確認する。

## 前提

- `claude`が`PATH`にあること。
- 1 work packageにつき1セッション。cwdを担当worktreeに固定する（`--cd`相当のフラグはない）。
- サブエージェント（Agent tool）でこのスキルの実装を回さない。
  呼び出し単位のツール制限がなく禁止が指示書の文言だけに落ちること、
  cwdとworktree管理が二重化することが理由。

## 起動

セッションIDを事前採番して管理表へ記録し、差し戻しで同じIDへ返せるようにする。

```sh
session_id=$(uuidgen | tr 'A-Z' 'a-z')

cd <worktreeの絶対パス> && claude -p \
  --session-id "$session_id" \
  [--model <model>] \
  --permission-mode bypassPermissions \
  --disallowedTools "Bash(git push:*)" "Bash(git worktree:*)" "Bash(git remote:*)" \
                    "Bash(git checkout:*)" "Bash(git branch:*)" "Bash(git rebase:*)" \
                    "Bash(gh:*)" \
  --output-format json \
  "実装者指示書 <指示書の絶対パス> を読み、その指示だけに従って実装せよ。" \
  > <結果JSONの絶対パス>
```

- `bypassPermissions`を使う理由: `acceptEdits`が自動承認するBashは
  `mkdir`、`touch`、`rm`、`rmdir`、`mv`、`cp`、`sed`だけで、`git commit`は承認待ちになる。
  さらに`.git`はprotected pathであり、`bypassPermissions`以外のモードでは書き込みが
  自動承認されない。無人でローカルコミットまで到達させるには`bypassPermissions`が必要。
- denyルールは`bypassPermissions`を含む全モードで適用される。`--disallowedTools`による
  push・GitHub操作の遮断は、このモードでも有効。
- 指示書は本文へ展開せず、絶対パスを渡して読ませる。
  `CLAUDE.md`は自動で読まれるが`AGENTS.md`は読まれない。適用される`AGENTS.md`は
  指示書に絶対パスで列挙し、作業開始前に読ませる。
- `--output-format json`の`result`は補助情報。完了判定に使わない。
  報告書は指示書で指定した絶対パスへ書かせる。
- モデルは`SKILL.md`側でハードコードしない。ユーザー指定があれば`--model`で固定し、
  なければ既定に任せ、使用したモデルを管理表へ記録する。

## 差し戻し

```sh
cd <worktreeの絶対パス> && claude -p --resume "$session_id" \
  --permission-mode bypassPermissions \
  --disallowedTools <起動時と同じ> \
  "<差し戻し指示>"
```

- `-c`（直近セッションの継続）は並列実行時に別セッションを掴むため使わない。
- `--fork-session`は使わない。差し戻しは同一セッションの継続として扱う。

## 禁止の強制

強制レベルは中。`--disallowedTools`のdenyは全モードで効くため、git push・GitHub操作は
機構的に遮断できる。ただし`git -C`、スクリプト経由、エイリアスなどの抜け道は残る。
指示書の文言と二重化し、Phase 4の越境監査を必ず行う。

より確実に縛る場合は、worktree側の`.claude/settings.local.json`の`permissions.deny`、
または`--settings`で同等のdenyを渡す。ハードな保証が要るなら`PreToolUse`フックを使う。

## 既知の落とし穴

- `claude -p --permission-mode bypassPermissions`では警告ダイアログは表示されない。
  事前承諾は不要。ただし`--bg`（バックグラウンドセッション）を使う場合は、
  対話セッションで一度承諾していないと起動を拒否される。
  このアダプターは`-p`を使うため、通常は事前承諾を前提条件にしない。
- root/sudoでは`bypassPermissions`は起動を拒否される。
- `-p`の非対話実行ではworkspace trustのダイアログがスキップされる。
  信頼していないリポジトリで起動しない。
- オーケストレーターもClaudeの場合、同一モデルのためレビューが甘くなりやすい。
  実装セッションのコンテキストを引き継がず、diffと検証の実測だけで判定する。

### 制限モード

未信頼リポジトリでは`bypassPermissions`を使わない。`--permission-mode dontAsk`と
`--allowedTools`で必要なコマンドだけを事前許可する構成になるが、protected pathへの
書き込みが拒否されるためローカルコミットは通らない。その場合はコミットを
オーケストレーター側の作業として切り出す。
