# 実装者アダプター: Devin CLI

`SKILL.md`の実装者契約と「実装エージェントへの禁止事項」が正本。ここには起動方法だけを書く。
フラグは変わりうるので、初回起動前に`devin --help`で実在を確認する。

## 前提

- `devin`が`PATH`にあり、認証済みであること（`devin auth`）。
- 1 work packageにつき1セッション。cwdを担当worktreeに固定する（`--cd`相当のフラグはない）。
- セッションはディレクトリ単位で記録される。worktreeを1対1で割り当てることが、
  セッションを取り違えないための前提になる。

## 起動

```sh
cd <worktreeの絶対パス> && devin \
  [--model <model>] \
  --permission-mode dangerous \
  --prompt-file <指示書の絶対パス> \
  --export <会話ログの絶対パス> \
  -p > <stdoutログの絶対パス>
```

- `--permission-mode`は`auto`（読み取りのみ自動承認）、`accept-edits`（編集も自動承認）、
  `smart`、`dangerous`（全自動承認）。標準は`dangerous`とする。
  無人でローカルコミットまで到達させるには、gitコマンドの実行を承認なしで通す必要がある。
  `accept-edits`で足りるかは、最初のwork packageで`git commit`が通るかを実測して決める。
- モデルは`SKILL.md`側でハードコードしない。ユーザー指定があればそれを使い、
  使用したモデルを管理表へ記録する。
- `--export`で会話ログを保存する。stdoutと会話ログはどちらも証拠ではない。
  報告書は指示書で指定した絶対パスへ書かせる。

## 差し戻し

セッションIDを`devin list`（当該worktreeで実行）で取得し、管理表へ記録する。

```sh
cd <worktreeの絶対パス> && devin -r <SESSION_ID> \
  --permission-mode dangerous \
  -p "<差し戻し指示>"
```

`-c`（直近セッションの継続）はディレクトリ単位で解決されるため、
worktreeを1セッション専有にしている限りは安全だが、原則としてIDを明示する。

## 禁止の強制

強制レベルは低。`dangerous`では全ツールが自動承認され、禁止事項は指示書の文言だけで守られる。
Phase 4の越境監査（refs、`git ls-remote`、worktree構成、remote設定の起動前後比較）を
完了条件に含める。worktreeはセキュリティ境界ではない。

強制を上げる手段が2つある。使えるなら使う。

- `--agent-config <FILE>`でツールの可視性と権限を宣言的に絞る。
- `--sandbox`（research preview）でexecツールのプロセスをOSレベルで隔離し、
  書き込み可能ルートを付与済みスコープに限定する。

## 既知の落とし穴

- 非対話実行では`--respect-workspace-trust`が既定でfalseになる。
  信頼していないリポジトリで起動しない。
- Devin Cloudのセッションを使う場合、ローカルworktreeとの対応が切れる。
  このスキルはローカルworktree前提なので、cloud実行と混在させない。
