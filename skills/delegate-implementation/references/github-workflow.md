# Issue・PR・CI・merge

ユーザーが求めた到達点に必要な部分だけ適用する。
PRタイトル、branch、commit、merge methodはリポジトリ規約に従う。
規約がなければ変更内容が分かる名前を選び、特定のscopeや番号禁止を持ち込まない。

## 複数Issue

実装対象、親・メタIssue、依存関係、明示的な除外を整理する。
Renovate Dependency Dashboardは通常の実装Issueではないため、一括実装・closeの対象にしない。
Dashboard自体の操作が依頼されている場合はその依頼に従う。他のbot Issueまで一律に除外しない。

Issue、実装担当、branch、worktree、PRは別の単位である。
PRは独立してレビュー・検証・mergeできる変更を単位にする。
ユーザーがIssueごとのPRを指定した場合はその単位を守る。
依存が密なIssueをまとめる場合は対応関係を示し、親Issueだけの空PRは作らない。

依存元の契約が固まらなければ、依存先の実装を無理に並行させない。
PRの依存は本文に記録し、通常の順次PRかstacked PRかを変更の性質から決める。
base更新や競合解消後は影響するローカル検証と現在のSHAのCIを確認する。

## pushとPR

push前に実際の差分、意図するbranchとbase、検証状況を確認する。
Draftは早期レビューやCI検証に必要な場合に使える。未完了事項を明記する。
Readyへ移す前に、受け入れ条件と必要な検証が満たされていることを確認する。
PR作成が到達点でも、既知の失敗やCI pendingを成功として報告しない。

PR本文には変更の目的、結果、検証、対応Issueと依存関係を書く。
closing keywordは、そのPRで完了するIssueだけに使う。
親Issueは必要な子Issueがすべて完了したときに閉じる。

## CIとmerge

最新head SHAのrequired checksを確認する。
失敗したらログを読み、原因を実装、環境、一時的な障害に分けて対応する。
待ち時間を減らす目的で他のrunをキャンセルしない。
CIキャンセルは対象runへの明示的な許可がある場合だけ行う。
required checksの解除や管理者権限で失敗を迂回しない。
workflow自体の修正が依頼の範囲なら、通常の変更としてレビュー・検証する。

mergeが許可されている場合は、直前にPR状態、head/base、required checks、
レビュー要件、競合の有無、依存PRの完了を再取得する。
確認したheadと実際にmergeするheadを一致させる。headが変わったら再確認する。
リポジトリ指定のmerge methodに従う。
force-pushが必要なら対象と変更を確認し、--force-with-leaseを使う。

merge後はremoteのPR状態と対応Issueを確認する。
実装完了、PR作成、CI成功、merge、Issue closeを別々の状態として報告する。

## 一時worktreeの清掃

担当プロセスが終了し、必要な成果物が到達点に応じた保存先へ回収されていることを確認する。
PR作業ならremoteのbranch、ローカル作業なら保持するbranchや取り込み先を確認する。
必要なコミットを失うbranch削除はしない。

git statusで未回収の変更やファイルがないことを確認し、
このタスクで作成した正確なパスだけをgit worktree removeで削除する。
共有・既存のworktreeは残す。自動管理のworktreeは実行環境の回収・清掃手順に従う。
