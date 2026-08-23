#!/usr/bin/env bash
#
# install.sh と external.py の回帰テスト。
#
# ネットワークには出ない。gist の取得先は GIST_RAW_BASE と GITHUB_API_BASE で
# ローカルのフィクスチャ（file:// URL）に差し替える。
#
#   ./tests/run.sh            全部
#   ./tests/run.sh link       名前に link を含むものだけ

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FILTER="${1:-}"
PASS=0
FAIL=0
T=""

# gist id は 20 桁以上の 16 進。フィクスチャも実物と同じ形にする。
GID1="1111111111111111111111111111aaa1"
GID8="8888888888888888888888888888aaa8"
GID9="9999999999999999999999999999aaa9"

G=$'\033[32m'; R=$'\033[31m'; DIM=$'\033[2m'; RST=$'\033[0m'

pass() { PASS=$((PASS + 1)); printf '  %sok%s   %s\n' "$G" "$RST" "$1"; }
fail() {
  FAIL=$((FAIL + 1))
  printf '  %sFAIL%s %s\n' "$R" "$RST" "$1"
  [ $# -gt 1 ] && printf '%s\n' "$2" | sed 's/^/         /'
  return 0
}

assert_rc() {  # assert_rc <期待> <実際> <説明>
  if [ "$1" = "$2" ]; then pass "$3"; else fail "$3" "期待した終了コード $1、実際は $2"; fi
}
assert_has() {  # assert_has <文字列> <対象> <説明>
  case "$2" in *"$1"*) pass "$3" ;; *) fail "$3" "「$1」が出力に無い:
$2" ;; esac
}
assert_lacks() {
  case "$2" in *"$1"*) fail "$3" "「$1」が出力にあってはいけない:
$2" ;; *) pass "$3" ;; esac
}
assert_link() {  # assert_link <リンク> <期待するリンク先> <説明>
  if [ -L "$1" ] && [ "$(readlink "$1")" = "$2" ]; then pass "$3"
  else fail "$3" "$1 -> $(readlink "$1" 2>/dev/null || echo '(symlinkでない)')（期待: $2）"; fi
}

# ---------------------------------------------------------------- 足場

setup() {
  T="$(mktemp -d)"
  mkdir -p "$T"/{agents,claude,backup,repo/scripts,repo/external,api/gists,api/repos,raw}
  cp "$REPO/scripts/external.py" "$T/repo/scripts/"
  cp "$REPO/scripts/install.sh"  "$T/repo/scripts/"
  export AGENTS_SKILLS_DIR="$T/agents" CLAUDE_SKILLS_DIR="$T/claude" \
         SKILLS_BACKUP_DIR="$T/backup" SKILL_LOCK="$T/skill-lock.json" \
         GIST_RAW_BASE="file://$T/raw" GITHUB_API_BASE="file://$T/api"
  EXT="$T/repo/scripts/external.py"
}
teardown() { [ -n "$T" ] && rm -rf "$T"; }

# fixture_gist <id> <owner> <rev> <file> <本文> [description]
fixture_gist() {
  local id="$1" owner="$2" rev="$3" file="$4" body="$5" desc="${6:-テスト用}"
  mkdir -p "$T/raw/$owner/$id/raw/$rev"
  printf '%s' "$body" > "$T/raw/$owner/$id/raw/$rev/$file"
  python3 - "$T/api/gists/$id" "$owner" "$rev" "$file" "$desc" <<'PY'
import json, sys
out, owner, rev, f, desc = sys.argv[1:6]
json.dump({"description": desc, "public": True, "owner": {"login": owner},
           "files": {f: {"filename": f}},
           "history": [{"version": rev, "committed_at": "2026-08-01T00:00:00Z"}]},
          open(out, "w"))
PY
}

manifest() { printf 'inventoried = "2026-08-23"\n%s\n' "$1" > "$T/repo/external/manifest.toml"; }

gist_entry() {  # gist_entry <name> <id> <rev> [state] [追加行]
  cat <<EOF

[[entry]]
id       = "$1"
category = "テスト"
summary  = "テスト用"
state    = "${4:-active}"
kind     = "gist"
skills   = ["$1"]
agents   = ["claude-code", "codex"]
update   = "manual"
local_changes = "なし"
license  = "Unlicense"
gist_owner = "tester"
gist_id    = "$2"
gist_file  = "SKILL.md"
revision   = "$3"
${5:-}
EOF
}

run() { echo "$1"; }

# ---------------------------------------------------------------- テスト

test_link_install_in_tempdir() {
  mkdir -p "$T/repo/skills/demo"
  printf -- '---\nname: demo\ndescription: x\n---\n\nbody\n' > "$T/repo/skills/demo/SKILL.md"
  manifest ""

  out="$("$T/repo/scripts/install.sh" link 2>&1)"; rc=$?
  assert_rc 0 "$rc" "link: dry-run は成功する"
  assert_has "create" "$out" "link: create を予告する"
  [ -e "$T/agents/demo" ] && fail "link: dry-run で作ってしまった" || pass "link: dry-run は何も作らない"

  out="$("$T/repo/scripts/install.sh" link --apply 2>&1)"
  assert_link "$T/agents/demo" "$T/repo/skills/demo" "link: agents 側は原本を指す"
  assert_link "$T/claude/demo" "../agents/demo" "link: claude 側は agents を指す"

  out="$("$T/repo/scripts/install.sh" link --apply 2>&1)"
  assert_has "ok:2" "$out" "link: 二度目は冪等"
}

test_link_broken_symlink() {
  mkdir -p "$T/repo/skills/demo"
  printf -- '---\nname: demo\ndescription: x\n---\n\nbody\n' > "$T/repo/skills/demo/SKILL.md"
  manifest ""
  "$T/repo/scripts/install.sh" link --apply >/dev/null 2>&1

  rm "$T/agents/demo"                       # claude 側のリンクが宙に浮く
  out="$("$T/repo/scripts/install.sh" link 2>&1)"
  assert_has "broken" "$out" "link: 壊れた symlink を検出する"

  ln -sfn /nowhere "$T/agents/demo"         # 別の場所を指す
  out="$("$T/repo/scripts/install.sh" link 2>&1)"
  assert_has "relink" "$out" "link: 誤ったリンク先を検出する"

  "$T/repo/scripts/install.sh" link --apply >/dev/null 2>&1
  assert_link "$T/agents/demo" "$T/repo/skills/demo" "link: --apply で張り直す"
}

test_link_conflict_exec_bit() {
  mkdir -p "$T/repo/skills/demo/scripts"
  printf -- '---\nname: demo\ndescription: x\n---\n\nbody\n' > "$T/repo/skills/demo/SKILL.md"
  printf '#!/bin/sh\n' > "$T/repo/skills/demo/scripts/s.sh"
  chmod +x "$T/repo/skills/demo/scripts/s.sh"
  manifest ""

  cp -a "$T/repo/skills/demo" "$T/agents/demo"
  chmod -x "$T/agents/demo/scripts/s.sh"    # 内容は同じ、実行ビットだけ違う
  out="$("$T/repo/scripts/install.sh" link 2>&1)"; rc=$?
  assert_rc 1 "$rc" "link: 実行ビット差分で終了コード 1"
  assert_has "CONFLICT" "$out" "link: 実行ビット差分を CONFLICT にする"

  out="$("$T/repo/scripts/install.sh" link --apply --force 2>&1)"
  assert_link "$T/agents/demo" "$T/repo/skills/demo" "link: --force で置換する"
  [ -n "$(find "$T/backup" -name 's.sh' -print -quit)" ] \
    && pass "link: 置換前に退避する" || fail "link: 退避されていない"
}

test_link_frontmatter_validation() {
  mkdir -p "$T/repo/skills"/{no-md,mismatch,good}
  echo hi > "$T/repo/skills/no-md/readme.md"
  printf -- '---\nname: other\ndescription: x\n---\n' > "$T/repo/skills/mismatch/SKILL.md"
  printf -- '---\nname: good\ndescription: x\n---\n' > "$T/repo/skills/good/SKILL.md"
  manifest ""

  out="$("$T/repo/scripts/install.sh" link 2>&1)"; rc=$?
  assert_rc 1 "$rc" "link: name 不一致で終了コード 1"
  assert_has "skip" "$out" "link: SKILL.md が無いものは skip"
  assert_has "CONFLICT" "$out" "link: name 不一致を CONFLICT にする"
  assert_has "good" "$out" "link: 正常なものは処理する"
}

test_external_install_in_tempdir() {
  fixture_gist $GID1 tester rev001 SKILL.md "# 本文v1"
  manifest "$(gist_entry demo $GID1 rev001)"

  out="$("$EXT" install 2>&1)"; rc=$?
  assert_rc 0 "$rc" "external: dry-run は成功する"
  [ -e "$T/agents/demo" ] && fail "external: dry-run で作ってしまった" \
                          || pass "external: dry-run は何も作らない"

  out="$("$EXT" install --apply 2>&1)"; rc=$?
  assert_rc 0 "$rc" "external: install --apply が成功する"
  [ "$(cat "$T/agents/demo/SKILL.md")" = "# 本文v1" ] \
    && pass "external: pin した内容を置く" || fail "external: 内容が違う"
  assert_link "$T/claude/demo" "../agents/demo" "external: claude 側に symlink を張る"
  assert_has "sha256 を記録した" "$out" "external: sha256 を manifest に記録する"

  out="$("$EXT" status --offline 2>&1)"; rc=$?
  assert_rc 0 "$rc" "external: status --offline が通る"
  assert_has "sha256" "$out" "external: sha256 で照合する"

  printf 'こわす' > "$T/agents/demo/SKILL.md"
  out="$("$EXT" status --offline 2>&1)"; rc=$?
  assert_rc 1 "$rc" "external: 改変を offline で検出する"
  assert_has "sha256 と一致しない" "$out" "external: sha256 不一致を報告する"
}

test_external_claude_symlink_repair() {
  fixture_gist $GID1 tester rev001 SKILL.md "# 本文v1"
  # skills-cli の実体を CLI が入れた状態に見立てる
  mkdir -p "$T/agents/cli-skill"
  printf -- '---\nname: cli-skill\n---\n' > "$T/agents/cli-skill/SKILL.md"
  cat > "$T/skill-lock.json" <<'EOF'
{"version":3,"skills":{"cli-skill":{"source":"owner/repo",
 "sourceUrl":"https://github.com/owner/repo.git",
 "skillPath":"skills/cli-skill/SKILL.md","skillFolderHash":"abc123"}}}
EOF
  manifest "$(cat <<'EOF'

[[entry]]
id       = "cli-skill"
category = "テスト"
summary  = "テスト用"
state    = "active"
kind     = "skills-cli"
repo     = "owner/repo"
skills   = ["cli-skill"]
agents   = ["claude-code", "codex"]
update   = "skills-cli"
local_changes = "なし"
license  = "MIT"
EOF
)"

  out="$("$EXT" status 2>&1)"; rc=$?
  assert_rc 1 "$rc" "skills-cli: claude 側 symlink の欠落を検出する"
  assert_has "symlink を作る" "$out" "skills-cli: 欠落した symlink を報告する"

  "$EXT" install --apply >/dev/null 2>&1
  assert_link "$T/claude/cli-skill" "../agents/cli-skill" "skills-cli: symlink を張る"

  ln -sfn /nowhere "$T/claude/cli-skill"
  out="$("$EXT" status 2>&1)"; rc=$?
  assert_rc 1 "$rc" "skills-cli: 誤った symlink で終了コード 1"

  "$EXT" install --apply >/dev/null 2>&1
  assert_link "$T/claude/cli-skill" "../agents/cli-skill" "skills-cli: 誤った symlink を張り直す"

  rm "$T/claude/cli-skill"; mkdir -p "$T/claude/cli-skill"
  out="$("$EXT" status 2>&1)"; rc=$?
  assert_rc 1 "$rc" "skills-cli: claude 側が実体なら終了コード 1"
  assert_has "CONFLICT" "$out" "skills-cli: claude 側の実体を CONFLICT にする"
}

test_external_origin_mismatch() {
  mkdir -p "$T/agents/cli-skill"
  printf -- '---\nname: cli-skill\n---\n' > "$T/agents/cli-skill/SKILL.md"
  ln -s ../agents/cli-skill "$T/claude/cli-skill"
  manifest "$(cat <<'EOF'

[[entry]]
id       = "cli-skill"
category = "テスト"
summary  = "テスト用"
state    = "active"
kind     = "skills-cli"
repo     = "owner/repo"
skills   = ["cli-skill"]
agents   = ["claude-code", "codex"]
update   = "skills-cli"
local_changes = "なし"
license  = "MIT"
EOF
)"

  # 同名だが別リポジトリ由来
  cat > "$T/skill-lock.json" <<'EOF'
{"version":3,"skills":{"cli-skill":{"source":"someone-else/skills",
 "sourceUrl":"https://github.com/someone-else/skills.git",
 "skillPath":"skills/cli-skill/SKILL.md","skillFolderHash":"deadbeef"}}}
EOF
  out="$("$EXT" status 2>&1)"; rc=$?
  assert_rc 1 "$rc" "出所照合: 別リポジトリ由来で終了コード 1"
  assert_has "出所が違う" "$out" "出所照合: 出所の違いを報告する"

  # skillPath が名前と食い違う
  cat > "$T/skill-lock.json" <<'EOF'
{"version":3,"skills":{"cli-skill":{"source":"owner/repo",
 "sourceUrl":"https://github.com/owner/repo.git",
 "skillPath":"skills/totally-other/SKILL.md","skillFolderHash":"deadbeef"}}}
EOF
  out="$("$EXT" status 2>&1)"; rc=$?
  assert_rc 1 "$rc" "出所照合: skillPath 不一致で終了コード 1"
  assert_has "skillPath" "$out" "出所照合: skillPath の食い違いを報告する"

  # 正しい記録なら通る
  cat > "$T/skill-lock.json" <<'EOF'
{"version":3,"skills":{"cli-skill":{"source":"owner/repo",
 "sourceUrl":"https://github.com/owner/repo.git",
 "skillPath":"skills/cli-skill/SKILL.md","skillFolderHash":"abc12345"}}}
EOF
  out="$("$EXT" status 2>&1)"; rc=$?
  assert_rc 0 "$rc" "出所照合: 一致していれば通る"
}

test_external_planned_to_active() {
  fixture_gist $GID1 tester rev001 SKILL.md "# 本文v1"
  manifest "$(gist_entry demo $GID1 rev001 planned)"

  out="$("$EXT" install --apply 2>&1)"
  assert_lacks "install demo" "$out" "state遷移: 名前なしは planned を飛ばす"
  [ -e "$T/agents/demo" ] && fail "state遷移: planned を導入してしまった" \
                          || pass "state遷移: planned は導入されない"

  out="$("$EXT" install demo --apply 2>&1)"; rc=$?
  assert_rc 0 "$rc" "state遷移: 名前を渡せば導入する"
  assert_has "state を active にした" "$out" "state遷移: state を書き換える"
  grep -q 'state    = "active"' "$T/repo/external/manifest.toml" \
    && pass "state遷移: manifest が active になる" || fail "state遷移: manifest が planned のまま"

  out="$("$EXT" status --offline 2>&1)"; rc=$?
  assert_rc 0 "$rc" "state遷移: 後続の status が不整合にならない"

  # dry-run では書き換えない
  manifest "$(gist_entry demo2 $GID1 rev001 planned)"
  "$EXT" install demo2 >/dev/null 2>&1
  grep -q 'state    = "planned"' "$T/repo/external/manifest.toml" \
    && pass "state遷移: dry-run では書き換えない" || fail "state遷移: dry-run で書き換えた"
}

test_external_add_hostile_description() {
  local nasty='彼は "こう" 言った \ そして
改行'
  fixture_gist $GID9 tester rev009 skill-x.md "# body" "$nasty"
  manifest ""

  out="$("$EXT" add "https://gist.github.com/tester/$GID9" --category テスト 2>&1)"; rc=$?
  assert_rc 0 "$rc" "add: 引用符・改行・バックスラッシュ入り description を受け付ける"

  python3 - "$T/repo/external/manifest.toml" "$nasty" <<'PY' && pass "add: TOML として読め、summary が壊れない" || fail "add: manifest が壊れた"
import sys, tomllib
d = tomllib.load(open(sys.argv[1], "rb"))
assert d["entry"][0]["summary"] == sys.argv[2], (d["entry"][0]["summary"], sys.argv[2])
PY

  # 重複は弾く
  out="$("$EXT" add "https://gist.github.com/tester/$GID9" --category テスト 2>&1)"; rc=$?
  assert_rc 2 "$rc" "add: id の重複を弾く"
  assert_has "既にある" "$out" "add: 重複の理由を出す"

  before="$(cat "$T/repo/external/manifest.toml")"
  "$EXT" add "https://gist.github.com/tester/$GID9" --category テスト >/dev/null 2>&1
  [ "$before" = "$(cat "$T/repo/external/manifest.toml")" ] \
    && pass "add: 弾いたときは manifest を変えない" || fail "add: 弾いたのに manifest が変わった"

  # SKILL.md という名前の gist は --name を要求する
  fixture_gist $GID8 tester rev008 SKILL.md "# body"
  out="$("$EXT" add "https://gist.github.com/tester/$GID8" 2>&1)"; rc=$?
  assert_rc 2 "$rc" "add: 名前が決まらない gist を弾く"
}

test_external_update() {
  fixture_gist $GID1 tester rev001 SKILL.md "# 本文v1"
  manifest "$(gist_entry demo $GID1 rev001)"
  "$EXT" install --apply >/dev/null 2>&1

  out="$("$EXT" update 2>&1)"
  assert_has "最新" "$out" "update: 差が無ければ最新と言う"

  # 上流に新しい revision が出た状態にする
  mkdir -p "$T/raw/tester/$GID1/raw/rev002"
  printf '# 本文v2' > "$T/raw/tester/$GID1/raw/rev002/SKILL.md"
  python3 - "$T/api/gists/$GID1" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["history"].insert(0, {"version": "rev002", "committed_at": "2026-08-20T00:00:00Z"})
json.dump(d, open(p, "w"))
PY

  out="$("$EXT" update 2>&1)"
  assert_has "新 revision" "$out" "update: 新 revision を検出する"
  assert_has "本文v2" "$out" "update: 差分を表示する"
  [ "$(cat "$T/agents/demo/SKILL.md")" = "# 本文v1" ] \
    && pass "update: dry-run では書き換えない" || fail "update: dry-run で書き換えた"

  "$EXT" update --apply >/dev/null 2>&1
  [ "$(cat "$T/agents/demo/SKILL.md")" = "# 本文v2" ] \
    && pass "update: --apply で本体を更新する" || fail "update: 本体が古いまま"
  grep -q 'revision   = "rev002"' "$T/repo/external/manifest.toml" \
    && pass "update: manifest の pin を更新する" || fail "update: pin が古いまま"
  out="$("$EXT" status --offline 2>&1)"; rc=$?
  assert_rc 0 "$rc" "update: 更新後も sha256 が整合する"
  [ -n "$(find "$T/backup" -name '*rev001*' -print -quit)" ] \
    && pass "update: 更新前の内容を退避する" || fail "update: 退避されていない"
}

test_docs_deterministic() {
  fixture_gist $GID1 tester rev001 SKILL.md "# 本文v1"
  manifest "$(gist_entry demo $GID1 rev001)"
  "$EXT" install --apply >/dev/null 2>&1
  "$EXT" docs >/dev/null 2>&1

  out="$("$EXT" docs --check 2>&1)"; rc=$?
  assert_rc 0 "$rc" "docs: 生成直後は一致する"

  # 端末の状態を総取り替えしても生成物は変わらない
  rm -rf "$T/agents" "$T/claude" "$T/skill-lock.json"
  out="$(SKILL_LOCK=/nonexistent AGENTS_SKILLS_DIR=/nonexistent \
         CLAUDE_SKILLS_DIR=/nonexistent "$EXT" docs --check 2>&1)"; rc=$?
  assert_rc 0 "$rc" "docs: 導入状況に依存せず同じものを生成する"

  # manifest を変えれば差分として出る
  printf '\nnotes = "追記"\n' >> "$T/repo/external/manifest.toml"
  out="$("$EXT" docs --check 2>&1)"; rc=$?
  assert_rc 1 "$rc" "docs: manifest との食い違いを検出する"
}

# ---------------------------------------------------------------- 実行

TESTS=$(declare -F | awk '{print $3}' | grep '^test_')
for t in $TESTS; do
  [ -n "$FILTER" ] && case "$t" in *"$FILTER"*) ;; *) continue ;; esac
  printf '\n%s%s%s\n' "$DIM" "${t#test_}" "$RST"
  setup
  "$t"
  teardown
done

printf '\n%s\n' "----------------------------------------"
if [ "$FAIL" -eq 0 ]; then
  printf '%s%d passed%s\n' "$G" "$PASS" "$RST"
else
  printf '%s%d passed, %d failed%s\n' "$R" "$PASS" "$FAIL" "$RST"
fi
exit $((FAIL > 0))
