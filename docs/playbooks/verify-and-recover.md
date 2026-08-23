---
type: Playbook
title: 状態を検査して復旧する
description: 宣言と導入済み状態の差異を調べ、安全な範囲で配置を修復する。
tags: [verification, recovery, troubleshooting]
generated: { by: codex/gpt-5.6-sol, at: 2026-08-23T18:03:28+09:00 }
verified: { by: human:Soli0222, at: 2026-08-23T19:16:43+09:00 }
sources:
  - id: install-sh
    resource: ../../scripts/install.sh
    title: 配置スクリプト
    last_modified: 2026-08-23T17:29:24+09:00
  - id: external-py
    resource: ../../scripts/external.py
    title: 配布 skill 管理スクリプト
    last_modified: 2026-08-23T17:57:22+09:00
  - id: tests-run
    resource: ../../tests/run.sh
    title: 回帰テスト
    last_modified: 2026-08-23T17:57:22+09:00
---

# 変更前に差異を確認する

自作 skill と配布 skill では検査コマンドが異なる。

```bash
./scripts/install.sh link
./scripts/install.sh external status
./scripts/install.sh docs --check
```

ネットワークを使えない場合、gist は `status --offline` で revision の SHA-256 と手元の実体だけを照合できる。
skills CLI 由来の依存は、取得元を確かめるために `~/.agents/.skill-lock.json` も参照する。

# 表示から対応を決める

| 表示 | 意味 | 対応 |
| --- | --- | --- |
| `ok` | 宣言と現実が一致している | 変更しない |
| `create`、`install` | 宣言された配置がない | dry-run の対象を確認して `--apply` |
| `broken`、`relink`、`fix` | symlink が壊れているか、別の場所を指している | 期待するリンク先を確認して `--apply` |
| `replace` | 一致する実ディレクトリを symlink へ置換できる | バックアップ先を確認して `--apply` |
| `CONFLICT` | 実体の内容、種別、取得元のいずれかが宣言と異なる | 差分の所有者を確認し、手動で方針を決める |

`CONFLICT` は自動修復の対象ではない。
自作 skill に `--force` を使うと配置先がバックアップ後に原本へのリンクへ置き換わるため、配置先だけの変更が不要だと確認できた場合に限る。

# 復旧後を検証する

適用後は同じ検査コマンドをもう一度実行し、差異が解消したことを確認する。
続いて回帰テストと生成文書の検査を行う。

```bash
./tests/run.sh
./scripts/install.sh docs --check
python3 skills/okf/scripts/validate_okf.py --strict docs
```

このバンドルは自分で保守しているので、validator は `--strict` で走らせる。
警告が出た時点で落ちるので、v0.2 の推奨事項からの逸脱を残さずに済む。
validator は PyYAML を必要とし、無ければ終了コード 2 で止まる。
