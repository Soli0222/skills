#!/usr/bin/env bash
#
# 自作 skill と配布 skill をまとめて面倒を見る。
#
#   install.sh                     すべて dry-run（link と external install）
#   install.sh --apply             すべて適用
#
#   install.sh link [--apply]      自作: skills/* を symlink する
#   install.sh external status     配布: 導入状況と pin の一致を見る
#   install.sh external install    配布: 台帳のとおりに導入する
#   install.sh external update     配布: 上流に追従し pin を書き換える
#   install.sh external add <src>  配布: manifest に項目を足す
#   install.sh docs [--check]      EXTERNAL.md を manifest から生成する
#
# 自作 skill の配置:
#   <repo>/skills/<name>          原本
#   ~/.agents/skills/<name>   ->  原本（Codex などが読む）
#   ~/.claude/skills/<name>   ->  ../../.agents/skills/<name>（Claude Code が読む）
#
# 既定は dry-run。実際に変更するには --apply を付ける。
#
# 環境変数で差し替え可能（テスト用）:
#   AGENTS_SKILLS_DIR / CLAUDE_SKILLS_DIR / SKILLS_BACKUP_DIR

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$REPO_ROOT/skills"

AGENTS_SKILLS_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
CLAUDE_SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
SKILLS_BACKUP_DIR="${SKILLS_BACKUP_DIR:-$HOME/.skills-backup}"

EXTERNAL_PY="$SCRIPT_DIR/external.py"

# 先頭のコメントブロックだけを説明として出す
usage() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"; }

SUBCMD=link
RUN_EXTERNAL=1
case "${1:-}" in
  link)     SUBCMD=link; RUN_EXTERNAL=0; shift ;;
  external) shift; exec "$EXTERNAL_PY" "$@" ;;
  docs)     shift; exec "$EXTERNAL_PY" docs "$@" ;;
  -h|--help) usage; exit 0 ;;
esac

APPLY=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --force) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

BACKUP_RUN="$SKILLS_BACKUP_DIR/$(date +%Y%m%d-%H%M%S)"
EXIT_CODE=0
N_OK=0 N_CHANGE=0 N_CONFLICT=0

log()  { printf '%s\n' "$*"; }
act()  { printf '  \033[32m%s\033[0m %s\n' "$1" "$2"; }
warn() { printf '  \033[33m%s\033[0m %s\n' "$1" "$2"; }
bad()  { printf '  \033[31m%s\033[0m %s\n' "$1" "$2"; }

# ---- frontmatter の name を取り出す -------------------------------------
frontmatter_name() {
  awk '
    NR==1 && $0!="---" { exit 1 }
    NR>1 && $0=="---"  { exit }
    NR>1 && /^name:[[:space:]]*/ {
      sub(/^name:[[:space:]]*/, "")
      gsub(/^["'"'"']|["'"'"']$/, "")
      print; exit
    }
  ' "$1"
}

# ---- ディレクトリ木を「種別・実行ビット・パス」で要約 --------------------
snapshot_tree() {
  ( cd "$1" && find . -mindepth 1 -print | LC_ALL=C sort | while IFS= read -r p; do
      if [ -L "$p" ]; then
        printf 'l - %s -> %s\n' "$p" "$(readlink "$p")"
      elif [ -d "$p" ]; then
        printf 'd - %s\n' "$p"
      elif [ -x "$p" ]; then
        printf 'f x %s\n' "$p"
      else
        printf 'f - %s\n' "$p"
      fi
    done )
}

# 実ディレクトリが原本と完全に同一か（内容・種別・実行ビット）
same_tree() {
  diff -rq "$1" "$2" >/dev/null 2>&1 \
    && diff <(snapshot_tree "$1") <(snapshot_tree "$2") >/dev/null 2>&1
}

backup_and_remove() {
  local path="$1" label="$2"
  if [ "$APPLY" -eq 1 ]; then
    mkdir -p "$BACKUP_RUN/$label"
    mv "$path" "$BACKUP_RUN/$label/"
  fi
}

# ---- リンク1本を目標状態に合わせる ---------------------------------------
# $1 = リンクを置く場所, $2 = リンク先に書き込む文字列, $3 = 解決後の絶対パス,
# $4 = 比較用の原本, $5 = バックアップのラベル
ensure_link() {
  local link="$1" link_text="$2" resolved="$3" origin="$4" label="$5"
  local rel="${link/#$HOME/~}"

  if [ -L "$link" ]; then
    local cur; cur="$(readlink "$link")"
    if [ "$cur" = "$link_text" ]; then
      if [ -e "$link" ]; then
        act "ok      " "$rel -> $cur"
        N_OK=$((N_OK + 1)); return 0
      fi
      bad "broken  " "$rel -> $cur (リンク先が存在しない)"
    else
      warn "relink  " "$rel -> $cur  =>  $link_text"
    fi
    N_CHANGE=$((N_CHANGE + 1))
    if [ "$APPLY" -eq 1 ]; then rm "$link"; ln -s "$link_text" "$link"; fi
    return 0
  fi

  if [ -d "$link" ]; then
    if same_tree "$link" "$origin"; then
      warn "replace " "$rel 実ディレクトリ（原本と一致）→ バックアップして symlink 化"
      N_CHANGE=$((N_CHANGE + 1))
      backup_and_remove "$link" "$label"
      if [ "$APPLY" -eq 1 ]; then ln -s "$link_text" "$link"; fi
      return 0
    fi
    bad "CONFLICT" "$rel 実ディレクトリが原本と異なる"
    # pipefail 下で diff の非ゼロ終了に巻き込まれないようにする
    { diff -rq "$origin" "$link" 2>&1 || true; } | sed 's/^/           /'
    { diff <(snapshot_tree "$origin") <(snapshot_tree "$link") 2>&1 || true; } | sed 's/^/           /'
    if [ "$FORCE" -eq 1 ]; then
      warn "  force " "--force によりバックアップして置換"
      N_CHANGE=$((N_CHANGE + 1))
      backup_and_remove "$link" "$label"
      if [ "$APPLY" -eq 1 ]; then ln -s "$link_text" "$link"; fi
    else
      N_CONFLICT=$((N_CONFLICT + 1)); EXIT_CODE=1
    fi
    return 0
  fi

  if [ -e "$link" ]; then
    bad "CONFLICT" "$rel がディレクトリでも symlink でもない"
    N_CONFLICT=$((N_CONFLICT + 1)); EXIT_CODE=1
    return 0
  fi

  act "create  " "$rel -> $link_text"
  N_CHANGE=$((N_CHANGE + 1))
  if [ "$APPLY" -eq 1 ]; then ln -s "$link_text" "$link"; fi
  return 0
}

# ---- 本体 ---------------------------------------------------------------
[ -d "$SRC_DIR" ] || { echo "skills/ がない: $SRC_DIR" >&2; exit 2; }

if [ "$APPLY" -eq 1 ]; then
  log "== apply (原本: $SRC_DIR)"
  mkdir -p "$AGENTS_SKILLS_DIR" "$CLAUDE_SKILLS_DIR"
else
  log "== dry-run（変更するには --apply）(原本: $SRC_DIR)"
fi

# ~/.claude/skills から ~/.agents/skills への相対パス。両方 $HOME 直下の
# 隠しディレクトリにある既存 symlink の流儀（../../.agents/skills/<name>）に合わせる。
claude_to_agents="$(python3 - "$CLAUDE_SKILLS_DIR" "$AGENTS_SKILLS_DIR" <<'PY'
import os, sys
print(os.path.relpath(sys.argv[2], sys.argv[1]))
PY
)"

found=0
for origin in "$SRC_DIR"/*/; do
  [ -d "$origin" ] || continue
  origin="${origin%/}"
  name="$(basename "$origin")"

  if [ ! -f "$origin/SKILL.md" ]; then
    warn "skip    " "$name (SKILL.md がない)"
    continue
  fi

  fm_name="$(frontmatter_name "$origin/SKILL.md" || true)"
  if [ -z "$fm_name" ]; then
    bad "CONFLICT" "$name: frontmatter に name がない"
    N_CONFLICT=$((N_CONFLICT + 1)); EXIT_CODE=1; continue
  fi
  if [ "$fm_name" != "$name" ]; then
    bad "CONFLICT" "$name: frontmatter の name が \"$fm_name\" で不一致"
    N_CONFLICT=$((N_CONFLICT + 1)); EXIT_CODE=1; continue
  fi

  found=$((found + 1))
  log ""
  log "$name"
  # ~/.agents/skills/<name> -> 原本（絶対パス。リポジトリの位置は任意なので）
  ensure_link "$AGENTS_SKILLS_DIR/$name" "$origin" "$origin" "$origin" "agents"
  # ~/.claude/skills/<name> -> ../../.agents/skills/<name>
  ensure_link "$CLAUDE_SKILLS_DIR/$name" "$claude_to_agents/$name" \
              "$AGENTS_SKILLS_DIR/$name" "$origin" "claude"
done

log ""
log "== $found skill / ok:$N_OK 変更:$N_CHANGE 衝突:$N_CONFLICT"
if [ "$N_CONFLICT" -gt 0 ]; then
  log "   衝突は自動では触らない。中身を確認し、置換してよければ --force を付ける。"
fi
if [ "$APPLY" -eq 1 ] && [ -d "$BACKUP_RUN" ]; then
  log "   バックアップ: $BACKUP_RUN"
fi
# 管理対象外の skill には一切触れない。

# 引数なし / --apply のみのときは、配布 skill の導入まで続けて行う。
if [ "$RUN_EXTERNAL" -eq 1 ]; then
  log ""
  log "== 配布 skill"
  ext_args=(install)
  if [ "$APPLY" -eq 1 ]; then ext_args+=(--apply); fi
  "$EXTERNAL_PY" "${ext_args[@]}" || EXIT_CODE=1
fi

exit "$EXIT_CODE"
