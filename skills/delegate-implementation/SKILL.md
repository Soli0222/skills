---
name: delegate-implementation
description: >
  オーケストレーターを計画者・レビュアー・git/GitHub管理者、実装エージェント（Devin CLI、
  Claude CLI、Codex CLIなど）を実装者として開発タスクを進める手順。大きな実装、複数Issue、
  親子・依存Issue、Issue単位のPR作成、CI確認、依存順のsquash mergeまでを実装エージェントへ
  委譲して進める依頼で使用する。実装者の選択と起動、複数実装セッションの並列実行、指示書、
  差し戻し、命名規約、push前検証、GitHub上の完了監査、一時worktreeの安全な清掃を定める。
---

# Implementation Orchestrate

オーケストレーターとして要件、計画、レビュー、GO/NOGO、git/GitHub操作を管理する。
コードとテストの実装は実装エージェントへ委譲する。1ファイル数行の自明な修正だけは直接直してよい。

実装エージェントは交換可能なバックエンドとして扱う。バックエンド固有の起動方法は
`references/implementer-*.md`に置き、本文の手順はどの実装者でも同一とする。

## 守るべき責務

| 責務 | 担当 |
| --- | --- |
| 要件確定、正本仕様・外部仕様の確認 | オーケストレーター |
| Issue分類、依存DAG、作業分割、並列度 | オーケストレーター |
| 実装者の選択、branch・worktree・指示書の準備 | オーケストレーター |
| コード・テストの実装、ローカル検証、ローカルコミット | 実装エージェント |
| 検証の再実行、差分レビュー、GO/NOGO | オーケストレーター |
| rebase、push、PR、CI、merge、Issue監査 | オーケストレーター |
| 作成したworktreeとscratchpadの清掃 | オーケストレーター |

### 実装エージェントへの禁止事項

実装者が誰であっても同一とする。指示書へ必ず明記する。

- push、force-push
- PR作成・編集、Draft/Ready変更
- CI操作（再実行、キャンセル、workflow編集）
- merge
- rebase、base変更、他branchへのcheckout
- branchの作成・削除
- worktreeの作成・削除
- remote設定の変更
- Issue、その他GitHubリソースの操作

## Phase 0: 到達点、リポジトリ規約、実装者を固定する

1. ルートから適用される`AGENTS.md`、設計文書、Issue、PRテンプレートを読む。
2. テストコマンド、PRタイトル、ブランチ、コミット、merge methodのリポジトリ規約を収集する。
3. ユーザーが求める到達点を固定する。
   - 指定がなければ、GitHub Issueの対応は`Ready PR + 最新HEADのCI成功`までとする。
   - mergeは明示的な許可がある場合だけ行う。
   - mergeまで依頼されたら、Issue closeと一時リソース清掃までを到達点に含める。
4. 実装バックエンドを決める。
   - ユーザーが実装者を指定した場合はそれを使う。
   - 指定がなければ、利用可能な実装者からオーケストレーターが選ぶ。
   - 実装途中で別のバックエンドへ無断で切り替えない。切り替える場合は新しい実装セッションとして管理表へ記録する。
   - 複数Issueでは work packageごとに異なる実装者を使ってよい。ただし1 work packageの差し戻しは同じ実装者の同じセッションへ返す。
5. 到達点、対象数、除外規則、実行予定の検証、選択した実装者を最初の進捗報告に出す。

```text
実装者: Codex CLI
モデル: Codex設定を使用
権限: --yolo（全解放）
隔離: タスク専用worktree、信頼済みリポジトリ、起動前後の越境監査
到達点: Ready PR + 最新HEADのrequired CI成功
```

`実装済み`、`push済み`、`PR作成済み`、`CI成功`、`merged`、`Issue closed`を同じ状態として扱わない。

## Phase 1: Issue inventoryと依存DAGを作る

複数Issueを扱う場合、実装前に全Issueの本文、親子関係、依存関係を読み、scratchpadに管理表を作る。

| Issue | 種別 | 依存先 | branch | PR | local checks | GitHub CI | merge | close |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Issueを次へ分類する。

- actionable Issue
- 親・メタIssue
- SubIssue
- ユーザーが明示した除外Issue
- Renovateが作成したDependency Dashboard

### Renovate Dependency Dashboard

`全open Issue`という依頼でも、Renovateが作成したDependency Dashboardはデフォルトで無視する。
Issue番号をハードコードせず、作成者・GitHub App、タイトル、本文やRenovate設定から意味的に識別する。

- 実装対象、PR対象、close対象に含めない。
- 編集、close、コメントをしない。
- 最終報告で`無視: Renovate Dependency Dashboard`と明記する。
- ユーザーがDashboard自体の操作を明示した場合だけ対象にする。

他のbot Issueや依存更新PRまで一律に除外してはならない。

### IssueとPRの単位

原則を`1 actionable Issue = 1 branch = 1 worktree = 1 PR`とする。

- 複数のactionable Issueを1 PRへまとめるには事前にユーザーの許可を得る。
- 親・メタIssueだけの空PRは作らない。
- 親Issueは全SubIssue完了後、最後の関連PRまたは許可されたIssue操作でcloseする。
- Issueを閉じるPRを管理表へ一意に記録する。
- 独立Issueだけを並列化し、依存Issueはトポロジカル順のwaveで進める。
- 強い依存や競合が見込まれるPRは、原則として依存元のmerge後に初回pushする。
- stacked PRが必要ならbaseと依存を明記し、最終baseへ更新後に全検証をやり直す。

## Phase 2: branch、worktree、scratchpadを作る

タスク専用scratchpadを一意な絶対パスで作り、そこへ次を記録する。

- Issue inventoryと依存DAG
- 作成したbranchとworktreeの正確なパス
- 実装者指示書と実装者報告書
- 実装セッションのログ
- 検証したHEAD SHAと実測結果
- PR番号、CI、merge、Issue closeの状態

実装セッションの管理表も作る。

| work package | implementer | model | session id | worktree | 指示書 | 報告書 | ログ | round |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

実装セッション1つにつきworktreeを1つ割り当てる。共有worktreeで並列実装しない。
同時実行は2〜3セッションまでとし、重なるファイル集合を並列化しない。

### 命名規約

リポジトリにより厳しい規約があれば優先する。規約がなければ次を使う。

PRタイトルとコミットsubject:

```text
feat(frontend): ふるさと納税シミュレーションを追加
fix(backend): 部分精算済みの振替を候補に残す
chore(ci): テスト用ネットワークを分離
```

```regex
^(feat|fix|enhance|chore)\((frontend|backend|shared|db|mcp|docs|ci|e2e)\): .+
```

branch:

```text
feat/furusato-simulation
fix/partial-settlement-candidates
chore/test-network-isolation
```

```regex
^(feat|fix|enhance|chore)/[a-z0-9]+(?:-[a-z0-9]+)*$
```

次を禁止する。

- PRタイトル、branch、ローカルコミットへのIssue番号の記載
- `fix-issue-*`、`issue-*`、`issues-except-*`、`agent/issue-*`
- 内容を表さない`wp1`などの名前
- `コミットメッセージの品質は問わない`という運用

## Phase 3: 実装者指示書と実行

1. work packageごとに共通形式の指示書を作り、scratchpadへ置く。
2. 選択した実装者の`references/implementer-<backend>.md`を読む。
3. 起動前のリポジトリ状態を保存する。Phase 4で同じスクリプトを再実行して突き合わせるため、
   スナップショットを取らずに起動しない。

```bash
bash <このスキル>/scripts/snapshot.sh <repo> <remote> > <before-snapshot>
```

スナップショットが非ゼロで終了したら、不完全な証跡で監査を続けない。
実装セッションを起動せず、原因（ネットワーク、認証、worktree破損など）を解消してからやり直す。
Phase 4で非ゼロ終了した場合はGOを出さない。

このスクリプトは次を記録する。いずれも欠くと監査が成立しないため、簡略化しない。

- `ref`、`remote`、`lsremote`（remoteの実体）
- 各worktreeのパス、`HEAD`、`branch`または`detached`
- 各worktreeの`git status --porcelain=v1 --untracked-files=all`

理由はスクリプト内のコメントに書いてある。
4. 専用worktreeで実装セッションを起動する。
5. 実装者名、モデル、権限モード、セッションID、ログと報告書の絶対パスを管理表へ記録する。
6. 完了後、tree、diff、commit、検証結果を取得する。
7. 自己申告だけで完了判定しない。
8. NOGOの場合は同じ実装セッションへ差し戻す。

共通契約と実装者アダプターが衝突する場合、共通の安全規則とgit/GitHub操作禁止を優先する。

### 実装者契約

バックエンドを問わず、次を満たす実装者だけを使う。

- 割り当てられたworktreeの中だけで作業する。
- 「実装エージェントへの禁止事項」を行わない。
- コミットはローカルまでとし、命名規約に従う。
- 指示書にない外部仕様を発明しない。
- 指定された検証コマンドをすべて実行し、結果を報告書ファイルへ書く。
- 差し戻しは同じセッションを継続して受ける。

### 指示書の形式

1 work packageにつき1指示書。次の5節を必ず含める。

**目的**

- 何を実装するか
- どの外部挙動を変えるか
- 何を変えないか

**正本コンテキスト**

- Issue、適用される`AGENTS.md`、設計文書、関連ドキュメントの絶対パスまたはURL
- 外部仕様の一次情報源と、文書にない挙動を作らない旨
- 関連ファイル、再現手順
- branch、worktree、命名規約

規約ファイルは自動で読まれることを前提にせず、作業開始前に読ませる指示を必ず書く。
たとえばClaude CLIは`CLAUDE.md`を読むが`AGENTS.md`は読まない。

```text
次のAGENTS.mdを作業開始前にすべて読み、適用範囲を守る:
- <絶対パス>
```

内容は全文転記せず絶対パス参照でよい。

**制約**

- 割り当てられたworktreeだけで作業する
- 文書にない挙動を作らない
- テスト期待値を都合よく変更しない
- 対象外のリファクタリングをしない
- dependency patchや回避コードを勝手に追加しない
- 「実装エージェントへの禁止事項」を行わない（禁止の理由も書く）

**完了条件**

- 実装が要件を満たす
- 必要なテストが追加・更新される
- リポジトリ指定の検証コマンドがすべて成功する
- 最終差分を自己レビューする
- 規約準拠のローカルコミットを作成する
- worktreeがcleanになる
- 指定した絶対パスへ報告書を出力する（変更点、実行した検証と結果、既知差分）

**阻害時**

- 仕様を推測で埋めない
- 危険な回避を行わない
- 失敗したコマンドとエラーを記録する
- 未完了条件と必要な判断を報告する
- 部分的な成功を完了として報告しない

### 起動と差し戻しの共通規則

- 長時間実行はbackgroundで起動する。
- セッションIDを起動時に確定させ、管理表へ記録する。差し戻しは必ずそのIDへ返す。
- 並列実行中に「直近のセッションを再開」する指定を使わない。別セッションを掴む。
- stdoutや自己申告を完了の証拠にしない。tree、diff、コミット、検証結果で判定する。
- 中断時は未完了点を具体的に列挙して再開する。

差し戻し指示には次を書く。

1. 現状の`file:line`
2. 不適合となる仕様・一次情報源
3. 修正後に観測できる条件
4. 再実行する検証コマンド
5. 既存コミットを改変せず追加コミットにするか、コミットを作り直すか

### 実装者アダプター

| バックエンド | 参照 | 標準構成 | 禁止の強制レベル |
| --- | --- | --- | --- |
| Claude CLI | `references/implementer-claude.md` | `bypassPermissions` + deny rules | 中 |
| Codex CLI | `references/implementer-codex.md` | `--yolo`（全解放） | 無 |
| Devin CLI | `references/implementer-devin.md` | `--permission-mode dangerous` | 低 |

無人でローカルコミットまで到達させるには、`.git`への書き込みとgitコマンドの実行を
承認なしで通す必要がある。そのため標準構成はいずれも強い権限になる。
権限を絞った制限モードは、未信頼リポジトリを扱う場合に各アダプターの記述に従って使う。

強制レベルが「無」または「低」の場合、Phase 4の越境監査は任意ではなく完了条件である。

報告書の保存先は、その実装者が実際に書き込める場所にする。制限モードでscratchpadが
worktree外にある場合は、書込先として明示的に追加する。

## Phase 4: レビューとpush前ゲート

報告書とコミットは入力であり証拠ではない。オーケストレーターが次を実行する。

1. Issueと成果物を対応づけ、後半の要件落ちを機械的に確認する。
2. baseとの差分を読み、対象外変更、依存packageへのpatch、テスト期待値の改変などを探す。
3. 権限、gate、比較、境界値、安全性に関わるロジックを読む。
4. 変更したドメイン規則に対応する文書が更新されているか確認する。
5. push予定の正確なHEADで、`AGENTS.md`が指定する全検証を自分で再実行する。
6. worktreeがcleanで、検証後にHEADが変わっていないことを確認する。
7. 実装セッションの越境がないことを、Phase 3のスナップショットとの差分で監査する。

```bash
bash <このスキル>/scripts/snapshot.sh <repo> <remote> > <after-snapshot>
diff <before-snapshot> <after-snapshot>
```

   スナップショットが非ゼロで終了したらGOを出さない。

   差分がゼロであることを合格条件にしない。正常な実装でも担当branchと担当worktreeのHEADは
   変わる。行ごとに次の規則で判定する。

   | 差分 | 判定 |
   | --- | --- |
   | `ref`行: 担当local branchのSHA変更 | 期待差分 |
   | `worktree`行: 担当worktreeの`HEAD`のSHA変更 | 期待差分 |
   | 担当worktreeの`status`行が消える（cleanになった） | 期待差分 |
   | `ref`行: 担当以外のlocal branchのSHA変更・追加・削除 | NOGO |
   | `worktree`行の追加・削除 | NOGO |
   | `worktree`行: `branch`または`detached`の変化 | NOGO（付け替え） |
   | 担当以外のworktreeの`status`行の変化 | NOGO |
   | `remote`行の変化 | NOGO |
   | `lsremote`行に担当branchの新規作成・更新がある | NOGO（pushされている） |
   | `lsremote`行のその他の変化 | 調査。対象ref、更新時刻、実装セッション由来か外部のpushかを確認してから判定する |

   remote-tracking refは`git fetch`だけでも動く。pushされていないことの判定には、
   remote-tracking refではなく`lsremote`行またはGitHub上のbranch SHAを使う。

8. HEAD SHAと各コマンドの実測結果を管理表へ記録する。

レビューは実装セッションのコンテキストを引き継がず、diffと実測だけを根拠に行う。
実装者とオーケストレーターが同一モデルの場合でも、報告書の主張を検証の代替にしない。

1つでも失敗、未実行、仕様未達、越境があればNOGOとし、pushしない。

NOGOは1 roundにつき1〜3論点へ絞り、対応する実装セッションへ差し戻す。

rebase、競合解消、コミット追加、base変更、force-pushが発生したら、それ以前のlocal checksとCIを
すべて無効にし、最新HEADでPhase 4からやり直す。

## Phase 5: push、Ready PR、GitHub CI

GO後のオーケストレーターだけがpushする。レビュー途中のcheckpointをpushしない。
force-pushが必要なら`--force-with-lease`だけを使う。

PRはローカル全検証成功後にReadyで作る。Draftが必要ならユーザーの明示指示を得る。

### PR contract

- タイトルは命名規約に一致し、Issue番号を含まない。
- head branchは命名規約に一致する。
- baseは依存DAGと一致する。
- 本文に対応Issueを`Closes #<issue>`で記載する。
- 依存PRがある場合は本文に依存関係を書く。
- 親Issueを閉じる場合は、全SubIssue完了を確認してから最後のPR本文に記載する。

GitHub Actionsはpush後にしか確定しない。push前に保証するのは`同じHEADでローカル全検証が成功し、
既知の失敗がないこと`である。push後は最新HEADの全required checksが成功するまで待つ。

### CIの絶対規則

- runnerを空ける目的で、main、他PR、同じタスクの別PRのCIをキャンセルしない。
- `gh run cancel`やCI cancellation APIは、ユーザーが特定runのキャンセルを明示した場合だけ使う。
- 混雑、待ち時間、後続PRの都合はキャンセル理由にならない。そのまま待つ。
- workflow変更、`--admin`、required checkの解除で失敗や待機を迂回しない。
- code/base/HEADが変わったら、古いgreenを再利用しない。
- CI失敗時はログを読み、対応する実装セッションへ差し戻し、Phase 4から繰り返す。

## Phase 6: 依存順のsquash merge

merge許可がある場合だけ、依存DAGのトポロジカル順に1 PRずつ処理する。

merge直前に次をGitHubから再取得する。

- PRがReadyでOPEN
- title、head、base、bodyがPR contractに一致
- latest head SHAのrequired checksが全成功
- `mergeable=MERGEABLE`かつ`mergeStateStatus=CLEAN`
- 依存PRがすべてMERGED

スカッシュコミットsubjectを次へ固定する。

```text
<PR title> (#<actual PR number>)
```

Issue番号とPR番号を区別する。

- PRタイトルとローカルコミットにはIssue番号を入れない。
- Issue番号はPR本文のclosing keywordに置く。
- squash subject末尾には実際のPR番号を必ず付ける。
- squash bodyは空にし、PR本文のIssue番号をコミット本文へ混入させない。

例:

```sh
gh pr merge "$pr" --squash --subject "$title (#$pr)" --body ''
```

各merge後にremoteのPR state、Issue state、mainのsquash subjectを確認する。
依存先をrebaseまたはretargetしたら、そのPRをPhase 4へ戻す。

## Phase 7: 状態報告

長時間タスクでは節目と待機中に、推測ではなくremoteとローカルの実測を報告する。

```text
対象: 12件
実装完了: 8件（Codex 4 / Devin 3 / Claude 1）
ローカル全検証済み: 6件
Ready PR: 5件
GitHub CI成功: 3件
マージ済み: 2件
Issueクローズ済み: 2件
無視: Renovate Dependency Dashboard 1件
現在: 依存元PRのCI待ち
次: merge後に依存先をrebaseし、全検証を再実行
```

状態遷移を飛ばして報告しない。状態名にバックエンド名を混ぜず、必要なら括弧で併記する。

```text
未着手
→ 実装中（Codex）
→ オーケストレーターレビュー中
→ ローカル全検証成功
→ Ready PR
→ GitHub CI成功
→ squash merge
→ Issue close確認
→ 一時リソース清掃済み
```

## Phase 8: remote監査と一時リソース清掃

到達点に応じてGitHubから再取得し、次を監査する。

- 対象PRのstate、Ready状態、latest CI
- 対象Issueと親Issueのstate
- Renovate Dependency Dashboardが変更されていないこと
- mainのsquash subjectが`PR title (#PR number)`と一致すること
- 未マージ、未クローズ、失敗、pendingが残っていないこと

push直後にworktreeを削除しない。対応PRが到達点へ達し、回収作業が不要になってから清掃する。
ただしタスク完了後まで放置してはならない。

管理表に記録した、このタスクで作成したリソースだけを個別に清掃する。

1. 各worktreeの`git status --porcelain`が空であることを確認する。
2. 必要なコミットがremoteにあり、PRが要求された到達点へ達していることを確認する。
3. dirty、未push、未回収ファイルがあれば削除せず、正確なパスと理由を報告する。
4. 安全なworktreeだけを`git worktree remove <exact-path>`で削除する。
5. `git worktree prune`を実行し、`git worktree list`で残存を確認する。
6. scratchpadの必要な記録を完了報告へ転記し、指示書、報告書、実装セッションのログを含む
   タスク専用一時ファイルを正確なパスで清掃する。

glob、未解決変数、広いディレクトリ、`rm -rf`でworktreeやscratchpadを削除しない。
既存または別タスクのworktreeを削除しない。清掃できないリソースがあれば完了扱いにせず明記する。

## 完了条件と報告

`pushした`だけで完了にしない。ユーザーが指定した到達点に必要な条件をすべて満たす。

Ready PRまでの場合:

- actionable Issueごとに規約準拠のReady PRがある。
- latest HEADのlocal checksとrequired CIが全成功している。
- 実装セッションの越境がないことを監査済みである。
- 依存と既知差分が明記されている。
- 不要になった一時リソースが清掃されている。

mergeまでの場合は、さらに次を満たす。

- 全対象PRが依存順にsquash mergeされている。
- squash subjectが`PR title (#PR number)`になっている。
- 対象Issueと、完了した親Issueがclosedである。
- Renovate Dependency Dashboardが無変更である。
- 作成したworktreeとscratchpadが残っていない。

完了報告には次を含める。

- 対象、完了、除外、無視したIssueの件数
- work packageごとの実装者とモデル
- PR URLと最終state、CI結果、merge結果
- round数と差し戻し理由の要約
- 仕様との既知差分・未解決事項
- 清掃したworktreeとscratchpad、または残した正確なパスと理由

## 付録: 実装者としてこのスキルを読んだ場合

このファイルはオーケストレーター向けである。指示書を受け取って実装する側として読んでいる場合、
上記のオーケストレーター手順を実行してはならない。次だけを行う。

- 渡された実装者指示書を最優先で読み、指定されたworktreeとbranchで作業する。
- コードとテストの実装、指定された検証コマンドの実行、規約準拠のローカルコミットだけを行う。
- 「実装エージェントへの禁止事項」を一切行わない。
- 検証結果と既知差分を、指定された絶対パスの報告書へ書く。
- 変更の証拠をtree、diff、commit log、検証結果で示す。stdoutや自己申告を証拠にしない。
- 判断が必要な点は推測で埋めず、未完了条件として報告する。
