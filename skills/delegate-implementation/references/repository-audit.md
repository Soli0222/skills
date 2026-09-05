# Git状態の補助監査

外部実装者が広いGit権限を持つなど、担当外のref・worktree・remote変更を調べる必要がある場合に使う。
通常のネイティブ委譲やローカル編集の必須手順ではない。

```sh
bash <skill>/scripts/snapshot.sh <repo> <remote> > <before-snapshot>
# 実装終了後
bash <skill>/scripts/snapshot.sh <repo> <remote> > <after-snapshot>
diff <before-snapshot> <after-snapshot>
```

スクリプトはlocal/remote-tracking refs、remote設定、ls-remote、worktree構成、statusを記録する。
ネットワーク接続とremoteへの読み取り権限が必要。
非ゼロ終了なら比較資料が不完全なので、監査成功と報告しない。
監査が完了条件なら原因を解消するか、必要な観測を別の方法で取得する。

差分ゼロを合格条件にしない。
担当branchのcommitや担当ファイルのstatus変化は正常でも起こる。
並行する別担当やユーザーの変更もあり得るため、変更の所有者と期待範囲に照らして判定する。
想定外の変更は調査し、自動で巻き戻さない。

この比較は完全な越境検知ではない。
statusはファイル内容を保存しないため、同じstatusのまま内容が変わると検知できない。
操作後に元へ戻された状態、Git外の変更、外部サービスへの操作も証明できない。
必要なら対象を絞った差分保存や実行環境の監査ログを併用する。
権限による予防と、状態比較による事後確認を混同しない。
