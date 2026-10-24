---
name: misskey-upgrade
description: Soli0222/misskey の upstream 更新を取り込み、競合解消、psr バージョン統一、develop → master の PR、Release、GHCR 公開確認、PKE の Helm 設定対応と Flux 本番反映を進める。Misskey のアップグレード実行・再開に使う。
---

# Misskey upgrade

手動の依頼を起点に、Soli0222/misskey と Soli0222/pke をまたぐ更新を進める。

```text
$misskey-upgrade 最新リリースを取り込んで、PR作成まで
$misskey-upgrade 2026.10.1 を取り込んで、本番更新まで
$misskey-upgrade 前回の更新を続きから
```

## 到達点と作業場所

- 「PR作成まで」は Misskey の push と PR 作成、PKE の互換性調査・必要なローカル修正まで。「リリースまで」は Misskey PR のマージ、Release、イメージ公開確認まで。「本番更新まで」は PKE PR の作成・CI確認・マージと本体の稼働確認も含む。
- 到達点が省略された初回は PR 作成まで。再開時は以前の明示された到達点を引き継ぐ。既に依頼された範囲の push・PR・merge・Release・反映について、工程ごとの再承認を求めない。設計相談やスキル作成だけの依頼では更新を実行しない。
- cwd、近隣ディレクトリ、git remote から両リポジトリを見つける。この環境では `~/work/misskey` と `~/work/pke` が候補。実パスと remote を確認し、絶対パスを固定の前提にしない。
- 両 repo の `AGENTS.md` と対象ディレクトリの追加指示を読む。Misskey の変更箇所に応じた backend/frontend スキル、出荷前の `shipping-misskey-change`、PR 前の `creating-issues-and-prs` を対象 repo 内から読む。ユーザーが明示した更新フローを優先し、上流への投稿ルールを fork のリリース PR に機械的に当てはめて余分な Issue や承認を作らない。
- 既存の未コミット変更を退避・混入させない。必要なら別 worktree と専用ローカルブランチを使う。GitHub の操作は利用可能な connector、足りない操作は `gh`、マージと競合解消は git を使う。

## 1. 対象を固定する

再開の依頼では、最初に「再開・失敗時・完了報告」の記録を読み、保存済みの version/SHA と実態を照合して未完了工程へ進む。以下の対象選択をやり直さない。

1. origin と upstream を取得し、`origin/develop`、`origin/master`、`upstream/master` を SHA に解決する。upstream が `misskey-dev/misskey`、origin が fork であることを確認する。
2. 指定リリース、または最新の非 draft・非 prerelease のリリースを調べ、tag の実コミットと `package.json` の version を読む。prerelease は明示指定時だけ対象にする。リリース済み version と upstream master の version/SHA が違えば、その差分を調べる。別 version や未リリースの変更まで入る場合は取り込み範囲を質問し、黙って master または tag に置き換えない。現在の fork が指定版より先に進んでいる場合も、ダウングレードせず確認する。
3. 合意された upstream SHA を今回の取り込み対象として固定する。処理中に動いた master の先端を再採用しない。通常は確認済みの `upstream/master` を使う。
4. 取り込み前の develop SHA と2つの package version を保存し、以前取り込んだ upstream commit を履歴・共通祖先から特定する。設定差分の比較範囲はこの旧 upstream commit → 今回の upstream SHA。
5. 最終 version は `<upstream version>-psr.x.y`。空白を入れず、既存の `psr.x.y` は保持する。upstream に prerelease がある場合も文字列を保つ（例: `2026.10.1-alpha.1-psr.9.11`）。`psr` 自体の更新は明示された場合だけ行う。
6. 同じ version の PR・tag・Release・イメージと進行中の更新を調べる。同じ成果物なら再利用し、異なる SHA に同名 tag がある場合は再作成・付け替えをしない。

## 2. 取り込みと互換性確認

1. 固定した develop SHA から作業し、`git merge --no-ff --no-commit <upstream-sha>` で取り込む。競合では fork 独自機能と上流変更の両方を調べて解消する。一律の ours/theirs 選択はしない。仕様を決めないと解消できない箇所だけ具体的に質問する。
2. JSON の競合を解消した後、次の helper で2つの version を統一する。`SKILL_DIR` はこのスキルの所在、`MISSKEY_WORKTREE` は作業先。ref は手順1で固定した SHA を渡す。

   ```bash
   python3 "$SKILL_DIR/scripts/update_versions.py" --repo "$MISSKEY_WORKTREE" \
     --base "$DEVELOP_SHA" --upstream "$UPSTREAM_SHA"
   python3 "$SKILL_DIR/scripts/update_versions.py" --repo "$MISSKEY_WORKTREE" \
     --base "$DEVELOP_SHA" --upstream "$UPSTREAM_SHA" --apply
   ```

   helper は root と `packages/misskey-js/package.json` の version だけを更新する。独立した backend/frontend package の version を揃えない。依存変更がある場合は repo 指定の package manager で lockfile を整合させる。
3. [PKE と設定互換性](references/pke.md) を読み、設定・migration・Node.js・DB/Redis 要件・起動コマンドの差分を確認する。必要な chart 修正を本体リリース前に準備し、PR 作成までの依頼でも互換性調査を省略しない。
4. 対象 repo の出荷検査、競合解消部分のテスト、型・生成物・migration の関連検証を行う。upstream から無変更で入った非日本語 locale と自分が編集した locale は区別する。出荷スクリプトが前者も拒否する場合、失敗と由来を報告し、上流翻訳を削除したり検査成功を偽装したりせず、検査の適用範囲を説明する。独自に非日本語 locale を編集しない。
5. 解消したファイルと version 更新を明示的に stage し、unresolved entry がないことと staged diff を確認する。最終 version をメッセージにして `git commit -m "$VERSION"` で merge を完了する。VS Code の UI 操作は不要。新規 merge commit の親が保存した develop SHA と upstream SHA であることを確認する。既に merge 済みの再開では別の merge を作らない。

## 3. develop → master の PR

1. push 直前に remote develop を再確認する。開始 SHA から動いていたら相手の変更を調べ、統合と検証をやり直す。force push は使わない。
2. 作業ブランチから `HEAD:develop` へ通常 push する。PR は同一 fork 内の head `develop`、base `master`、タイトルは version の完全一致。既存 PR があれば内容・head SHA を確認して再利用する。
3. repo の PR template を使い、取り込む release/SHA、競合解消の要点、検証結果、設定/migration と PKE 対応を簡潔に記載する。`gh` の複数行本文は一時ファイルを使う。
4. PR 作成までなら URL と PKE の準備結果を返す。それ以降が依頼されていれば続行する。

## 4. リリースと公開確認

1. 現在の PR head SHA に対する必要な check/status と branch rule を確認する。pending、失敗、check 未取得を成功扱いしない。CI が実行されていないなら workflow の trigger/filter を調べる。自動修正できる失敗は修正・再検証し、無関係な失敗や同じ原因の再試行を繰り返さない。
2. マージ直前にも head SHA を照合する。develop の履歴を保持する merge commit 方式を基本とし、repo の許可方式と一致するか確認する。head が変われば新しい差分と CI を確認する。継続利用する develop は削除しない。
3. マージ結果の正確な SHA を取得し、master 上に存在すること、2つの package version が一致することを確認する。その SHA に version と同名の tag/Release を作る。動き続ける `master` 名だけでリリース対象を決めない。既存 tag は peeled commit を比較し、不一致なら停止する。
4. Release 公開が `.github/workflows/docker.yml` を起動したことを確認し、その Release/tag/SHA に対応する実行を待つ。Actions から作成する場合は token による後続 workflow の起動制約を確認する。`workflow_dispatch` は現行設定では SHA タグになるため、version タグ公開の代替として無条件に使わない。
5. build job だけでなく manifest 公開 job の成功を確認し、`ghcr.io/soli0222/misskey:$VERSION` の digest と必要な platform（現行 amd64/arm64）を registry で確認する。tag の存在だけで別コミットの image を採用せず、workflow の SHA と結び付ける。
6. リリースまでなら Release と image digest を返す。本番更新までなら [PKE 手順](references/pke.md) の反映へ進む。

## 再開・失敗時・完了報告

- 作業ディレクトリ外からも再開できるよう、Misskey の git common dir 配下の `misskey-upgrade/<version>.json` に到達点、両 repo/worktree、旧 upstream/develop/対象 upstream SHA、version、PR URL/head SHA、merge SHA、tag、image digest、PKE PR/commit、検証済み工程を保存する。secret は含めず、リポジトリへ commit しない。
- この記録は手掛かりとし、再開時は GitHub・registry・Flux の実態と照合する。記録だけで完了判定しない。再開時に最新版を再選択しない。
- CI・公開・rollout の待機は短い間隔で状況を伝え、有限の期限を設ける（目安 CI/公開各30分、反映15分。既存 timeout があれば尊重）。期限切れは失敗と決め付けず、待機中の URL と再開点を保存する。無限 polling や無限 retry はしない。
- 権限不足や仕様判断待ちなら、完了工程と残りを具体的に示す。変更済み DB に対し古い image を戻すだけの rollback は行わない。
- 最後に version、完了した到達点、Misskey/PKE PR・Release、設定対応、検証結果、未完了の理由を短く報告する。本番完了は Flux revision・image digest・アプリの version と応答まで確認した場合だけ宣言する。
