#!/usr/bin/env bash
# リポジトリ状態のスナップショットを取る。
# 実装セッションの起動前（Phase 3）と、push前ゲート（Phase 4）で同じものを実行し、
# 出力をdiffして実装者の越境を検出する。
#
# usage: bash scripts/snapshot.sh <repo> <remote>
#
# 出力行:
#   ref <refname> <sha>
#   remote <name> <url> (fetch|push)
#   lsremote <sha> <ref>
#   worktree <path> | worktree <path>
#   worktree <path> | HEAD <sha>
#   worktree <path> | branch <refname>     (または `| detached`)
#   status <path> | <XY> <file>
#
# 非ゼロで終了した場合、証跡は不完全である。実装セッションを起動せず、GOも出さない。
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "usage: bash $0 <repo> <remote>" >&2
  exit 2
fi

repo=$1; remote=$2
tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT

# `git ... | sed` はGitが失敗しても末尾のsedが成功する。pipefailなしでは
# 欠落した証跡のまま成功扱いになるため、set -euo pipefail を外さないこと。
git -C "$repo" for-each-ref --format='ref %(refname) %(objectname)' refs/heads refs/remotes
git -C "$repo" remote -v           | sed 's/^/remote /'
git -C "$repo" ls-remote "$remote" | sed 's/^/lsremote /'

# `--porcelain -z` をNUL区切りで読む。awk '{print $2}' は空白入りパスを切る。
# HEADのSHAだけでなくbranch行とdetached行も残す。残さないと、同じSHAを指す
# 別branchへの付け替えが差分に現れない。
git -C "$repo" worktree list --porcelain -z > "$tmp"
paths=(); wt=
while IFS= read -r -d '' f; do
  [ -n "$f" ] || continue
  case $f in worktree\ *) wt=${f#worktree }; paths+=("$wt") ;; esac
  printf 'worktree %s | %s\n' "$wt" "$f"
done < "$tmp"

# worktreeのdirty状態は `git worktree list` に含まれない。これがないと、
# コミットされていない他worktreeへの書き換えを検出できない。
for wt in "${paths[@]}"; do
  git -C "$wt" status --porcelain=v1 --untracked-files=all > "$tmp"
  while IFS= read -r line; do printf 'status %s | %s\n' "$wt" "$line"; done < "$tmp"
done
