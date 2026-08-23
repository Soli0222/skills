# 実装者アダプター: Codex CLI

`SKILL.md`の実装者契約と「実装エージェントへの禁止事項」が正本。ここには起動方法だけを書く。
フラグは変わりうるので、初回起動前に`codex exec --help`と`codex exec resume --help`で実在を確認する。
以下はcodex-cli 0.146.0での実測に基づく。

## 前提

- `codex`が`PATH`にあること。
- 1 work packageにつき1つの`codex exec`セッション。
- `codex exec`は非対話実行で、承認プロンプトを待たない。承認が必要な操作は実行されずに失敗する。

## 起動

標準は全解放とする。無人でローカルコミットまで到達させるために必要になる。

```sh
codex exec \
  --cd <worktreeの絶対パス> \
  --yolo \
  [--model <model>] \
  --json \
  --output-last-message <最終メッセージの絶対パス> \
  - < <指示書の絶対パス> \
  > <JSONLイベントログの絶対パス>
```

- `--yolo`は`--dangerously-bypass-approvals-and-sandbox`のエイリアス。
  スクリプトでは意図が明確な長い正式名を使ってもよい。
- `--cd`で担当worktreeを固定する。
- `--json`で実行イベントとセッションIDをJSONLへ記録する。
- `--output-last-message`は最終メッセージの保存であり、報告書の代わりではない。
  報告書は指示書で指定した絶対パスへ書かせる。
- モデルは`SKILL.md`側でハードコードしない。ユーザー指定があれば`--model`で固定し、
  なければCodexの設定に任せ、使用したモデルまたは設定を管理表へ記録する。

## 差し戻し

JSONLの最初のイベント（`thread.started`）に含まれるスレッド/セッションIDを、
work packageと対応づけて管理表へ保存する。フィールド名は実際のログで確認する。

`codex exec resume`は`--cd`と`--sandbox`を受け付けない（`error: unexpected argument '--cd' found`）。
cwdを担当worktreeにして実行する。

```sh
cd <worktreeの絶対パス> && codex exec resume <SESSION_ID> \
  --yolo \
  --json \
  "<差し戻し指示>" \
  >> <JSONLイベントログの絶対パス>
```

`--last`は使わない。並列実行時に別セッションを再開する可能性があるため。

## 禁止の強制

標準構成（`--yolo`）では強制レベルは無。禁止事項は指示書の文言だけで守られる。
安全性はworktreeではなく、外部隔離と事後監査で確保する。

- worktreeはセキュリティ境界ではない。worktreeは親リポジトリの`.git`を共有するため、
  他branch、他worktree、remoteへ干渉できる。
- `--yolo`は、ユーザーが信頼するリポジトリと実行環境でのみ使う。
  未知の外部PR、未信頼コード、秘密情報を持つホストでは使わない。その場合は
  隔離されたVM、コンテナ、専用ユーザー、または下記の制限モードを使う。
- Phase 4の越境監査（refs、`git ls-remote`、worktree構成、remote設定の起動前後比較）を
  完了条件に含める。

### 制限モード

未信頼リポジトリでは`--yolo`の代わりに`--sandbox workspace-write`を使う。
ただし次の2点を確認してから採用する。

- `.git`への書き込みが制限され、ローカルコミットが失敗しうる。
  最初のwork packageで`git commit`が通ることを実測する。通らなければ、
  コミットをオーケストレーター側の作業として切り出す。
- 既定でネットワークが遮断される。依存インストールやネットワークを要する検証は、
  オーケストレーターが起動前に済ませたworktreeを渡す。
- 報告書の保存先がworktree外なら`--add-dir <scratchpad>`で書込先に追加する。

## 既知の落とし穴

- `codex exec --help`に`--yolo`は表示されないが、実際には受理される（0.146.0で確認）。
- `codex exec resume`のオプション集合は`codex exec`と異なる。起動時のフラグをそのまま
  resumeへ流用しない。
