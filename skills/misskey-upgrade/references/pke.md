# PKE の設定互換性と本番反映

実行時の repo を正とし、以下のパスが移動した場合は参照関係から探す。

| 対象 | 読む場所 |
| --- | --- |
| upstream の設定例・解釈 | Misskey `.config/example.yml`、`packages/backend/src/config.ts`、`packages/backend/scripts/compile_config.js` とそこから参照する schema/loader |
| DB と実行環境の変更 | `packages/backend/migration/`、`Dockerfile`、package manager/Node 設定、release notes |
| chart | PKE `charts/misskey/Chart.yaml`、`values.yaml`、`templates/config-secret.yaml`、`templates/web-deployment.yaml`、`templates/migrate-job.yaml` |
| 本番 values | `flux/clusters/natsume/apps/misskey/helmrelease-misskey.yaml` と参照する Secret の定義 |
| 適用元と反映規則 | `AGENTS.md`、FluxInstance/GitRepository、`flux/clusters/natsume/kustomizations/misskey.yaml` |
| DB 運用 | `CNPG.md`、対象 Cluster/ScheduledBackup 定義。別のメンテナンス手順は適用対象を確認して読む |

## 設定変更を吸収する

旧 upstream commit と今回の upstream SHA の差分から、設定キーごとに追加・削除・改名・型・既定値・意味の変更を整理する。
設定例だけに依存せず、loader と利用箇所も読む。merge 後の fork 独自設定が残っていることも確認する。

- `values.yaml` の公開項目と `config-secret.yaml` の出力を対応させる。必要な本番値は HelmRelease へ反映する。
- optional な追加項目を本番で使わない場合も、chart で指定できるようにするか、upstream 既定値へ委ねるかを判断して記録する。すべての新機能を勝手に有効化しない。
- 削除/改名された値を整理し、未指定・false・0・空文字の違いを保つ。Helm の `default` や `if` で意図した false/0 を失わないよう確認する。
- secret 値は既存の 1Password/Secret 参照で渡す。未知の本番値を捏造しない。調査結果や PR に secret を出力しない。
- 設定変更に応じて chart README を更新する。

`helm lint` と対象 values を使った `helm template` に加え、生成された Secret の `default.yml` を YAML として検査する。
外側の Kubernetes YAML が正しくても、内側の設定 YAML が正しいとは限らない。
ダミーの secret 値で未指定/false/0/ネスト構造の関係するケースを検証し、可能なら新しい Misskey の設定 loader で互換性も確認する。
本番 secret の展開結果をログや共有 artifact に保存しない。

## migration と設定の順序

現在の migration Job は `pre-upgrade` hook で、通常リソースの設定 Secret を読む。
したがって新 image の migration が旧設定で動く可能性がある。新設定を含む Helm render が成功しても、この順序問題の検証にはならない。

1. 新 migration と起動時の設定検証が、更新前 Secret で動くか確認する。
2. 旧設定で動かない場合は、旧版でも受け入れる設定を先に配布する段階更新、または Job 専用設定を hook より先に提供する chart 変更を設計・検証する。
3. 単純に hook を `post-upgrade` に変えて、DB migration 前に新 web を起動させない。
4. 破壊的 migration や旧 web と互換性のない DB 変更では、必要な停止順序と復旧方法を具体化する。DB の復元やデータ喪失を伴う対応は通常のアップグレードから自動で広げない。

## image 公開後の PKE 更新

1. PKE の remote/default branch と Flux が追う branch を確認する。現行は `Soli0222/pke` の `main`。既存の未コミット変更から分離した作業ブランチを使う。
2. `Chart.yaml` の `appVersion` を Misskey version と完全一致させ、chart `version` も更新する。通常の修正は patch、公開 values の互換性に影響する変更は内容に応じて決める。Flux が ChartVersion で artifact を更新するため、chart version 据え置きは不可。
3. `web.image.tag` の override がある場合はそちらも確認する。web と migration の image が確認済みの公開 image に一致するようにする。
4. 準備した設定対応と併せて、chart lint/render、対象クラスタの Kustomize build、repo 指定の検証を実行する。変更範囲外の meruto への影響も render 差分で確認する。
5. Conventional Commits で commit し、PKE PR を作成する。既存の同じ更新 PR があれば再利用する。Misskey Release、image digest、設定対応、migration 順序、検証結果を記載する。
6. PR の最新 head に対する必要な CI（`flux-diff`、`chart-version-guard` など）を確認する。Renovate 等が先に同じ appVersion を提案/反映していれば重複作成せず、設定対応と chart version が揃っているか確認する。

## 本番反映と確認

本番更新まで依頼されている場合のみ行う。PKE の Flux 追従 branch へのマージはデプロイ開始に相当する。
クラスタへ接続できること、現在の release/Pod 状態、必要な migration に備えた DB バックアップの成功と復旧経路を、マージ前に確認する。
既存の DB メンテナンス手順を丸ごと実行せず、今回の migration に必要な範囲を選ぶ。

1. CI 成功と head SHA を再確認して PKE PR をマージする。GitOps の定義を経由せず `helm upgrade` で上書きしない。
2. 現行の適用先は `natsume@soli`、namespace は `misskey`。実際の定義と照合し、すべての kubectl/flux 操作で context を明示する。別クラスタへ自動で切り替えない。
3. Flux の source → Kustomization → HelmRelease の順に対象 commit の反映を待つ。必要なら対象を限定して reconcile する。手動 suspend がある場合は理由を確認し、無条件に解除しない。
4. Ready だけでなく source/applied revision と observedGeneration を照合する。新 chart の適用、migration 成功、Deployment rollout と Pod imageID が確認済み digest/platform に対応することを確認する。hook Job が削除される設定なら Helm の処理結果等で成功を確認する。
5. 実環境の URL へ読み取りの health/meta リクエストを送り、version とアプリ応答を確認する。起動・DB・queue 接続のエラーも確認する。投稿や合成通知による確認はしない。
6. 失敗した場合は対象 Job/Pod/Flux の原因を調べ、適用済み migration と DB の状態を記録する。DB 互換性を確認せず旧 image へ戻さない。復元が必要なら具体的な復旧案を提示する。
