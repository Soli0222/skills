#!/usr/bin/env python3
"""配布 skill を external/manifest.toml のとおりに導入・更新し、EXTERNAL.md を生成する。

install.sh から呼ばれる。単体でも動く。
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "external" / "manifest.toml"
DOCS = REPO / "EXTERNAL.md"

HOME = Path.home()
AGENTS_DIR = Path(os.environ.get("AGENTS_SKILLS_DIR", HOME / ".agents" / "skills"))
CLAUDE_DIR = Path(os.environ.get("CLAUDE_SKILLS_DIR", HOME / ".claude" / "skills"))
BACKUP_DIR = Path(os.environ.get("SKILLS_BACKUP_DIR", HOME / ".skills-backup"))
LOCK = Path(os.environ.get("SKILL_LOCK", AGENTS_DIR.parent / ".skill-lock.json"))

G, Y, R, DIM, RST = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"


def ok(s):   print(f"  {G}{s}{RST}")
def warn(s): print(f"  {Y}{s}{RST}")
def bad(s):  print(f"  {R}{s}{RST}")
def dim(s):  print(f"  {DIM}{s}{RST}")


# ---------------------------------------------------------------- manifest

def load() -> dict:
    with MANIFEST.open("rb") as f:
        return tomllib.load(f)


def entries(data, only=None):
    for e in data.get("entry", []):
        if only and e["id"] not in only and not (set(e["skills"]) & set(only)):
            continue
        yield e


def display_name(e):
    return e.get("title", e["id"])


def set_field(entry_id: str, key: str, value: str) -> bool:
    """manifest の該当 [[entry]] ブロック内の key を書き換える。

    TOML を再シリアライズするとコメントと整形が失われるので、行単位で置換する。
    """
    text = MANIFEST.read_text()
    blocks = re.split(r"(?m)^(\[\[entry\]\]\s*$)", text)
    # blocks = [前文, "[[entry]]", 本文, "[[entry]]", 本文, ...]
    for i in range(1, len(blocks), 2):
        body = blocks[i + 1]
        if not re.search(rf'(?m)^id\s*=\s*"{re.escape(entry_id)}"\s*$', body):
            continue
        pat = re.compile(rf'(?m)^(?P<pre>{re.escape(key)}\s*=\s*)"[^"]*"\s*$')
        if not pat.search(body):
            return False
        blocks[i + 1] = pat.sub(lambda m: f'{m.group("pre")}"{value}"', body, count=1)
        MANIFEST.write_text("".join(blocks))
        return True
    return False


# ---------------------------------------------------------------- gist

def api(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "skills-repo"})
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def gist_raw(e, revision: str) -> str:
    url = (f"https://gist.githubusercontent.com/{e['gist_owner']}/{e['gist_id']}"
           f"/raw/{revision}/{e['gist_file']}")
    req = urllib.request.Request(url, headers={"User-Agent": "skills-repo"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode()


def gist_latest(e) -> tuple[str, str]:
    d = api(f"https://api.github.com/gists/{e['gist_id']}")
    h = d["history"][0]
    return h["version"], h["committed_at"][:10]


def skill_path(name: str) -> Path:
    return AGENTS_DIR / name / "SKILL.md"


# ---------------------------------------------------------------- lock

def lock_hashes() -> dict:
    if not LOCK.exists():
        return {}
    try:
        d = json.loads(LOCK.read_text())
    except json.JSONDecodeError:
        return {}
    return {k: v.get("skillFolderHash", "") for k, v in d.get("skills", {}).items()}


# ---------------------------------------------------------------- backup

def backup(path: Path, label: str, stamp: str) -> Path:
    """path を退避先へ move する（元の場所からは消える）。"""
    dest = BACKUP_DIR / stamp / label
    dest.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dest / path.name))
    return dest / path.name


def backup_copy(path: Path, label: str, stamp: str, suffix: str = "") -> Path:
    """path を退避先へ copy する（元の場所には残す）。上書き前の保存用。"""
    dest = BACKUP_DIR / stamp / label
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / f"{path.parent.name}.{path.name}{suffix}"
    shutil.copy2(path, target)
    return target


# ---------------------------------------------------------------- status

def cmd_status(args):
    data = load()
    hashes = lock_hashes()
    rc = 0
    for e in entries(data, args.name):
        print(f"\n{display_name(e)}  {DIM}[{e['kind']} / {e['state']}]{RST}")

        if e["state"] == "planned":
            names = " ".join(e["skills"])
            missing = [n for n in e["skills"] if not (AGENTS_DIR / n).exists()]
            if missing:
                dim(f"導入予定 — 未導入: {names}")
            else:
                warn(f"導入予定と記録されているが実際には入っている: {names}（manifest の state を active に）")
                rc = 1
            continue

        if e["kind"] == "gist":
            p = skill_path(e["skills"][0])
            if not p.exists():
                bad(f"未導入 — {p}")
                rc = 1
                continue
            local = p.read_text()
            try:
                pinned = gist_raw(e, e["revision"])
            except urllib.error.URLError as ex:
                warn(f"pin の取得に失敗 ({ex}) — ローカルのみ確認")
                continue
            if local != pinned:
                bad(f"ローカルが pin ({e['revision'][:8]}) と一致しない")
                rc = 1
            else:
                ok(f"pin と一致 — {e['revision'][:8]}")
            if not args.offline:
                try:
                    latest, date = gist_latest(e)
                except urllib.error.URLError as ex:
                    warn(f"上流未確認 ({ex})")
                    continue
                if latest != e["revision"]:
                    warn(f"上流に新 revision — {latest[:8]} ({date})  `external update {e['id']}` で追従")
                    rc = 1
                else:
                    ok("上流も最新")

        elif e["kind"] == "skills-cli":
            for n in e["skills"]:
                if not (AGENTS_DIR / n).exists():
                    bad(f"未導入 — {n}")
                    rc = 1
                elif n in hashes:
                    ok(f"{n}  {DIM}{hashes[n][:8]}{RST}")
                else:
                    warn(f"{n} — 実体はあるが .skill-lock.json に記録がない")

        elif e["kind"] == "manual":
            loc = Path(os.path.expanduser(e["location"]))
            if loc.exists():
                ok(f"{loc}  {DIM}(自動管理の対象外){RST}")
            else:
                bad(f"見つからない — {loc}")
                rc = 1
    print()
    return rc


# ---------------------------------------------------------------- install

def link_into_claude(name: str, apply: bool):
    """~/.claude/skills/<name> -> ../../.agents/skills/<name> を張る。"""
    link = CLAUDE_DIR / name
    want = os.path.relpath(AGENTS_DIR / name, CLAUDE_DIR)
    if link.is_symlink():
        if os.readlink(link) == want:
            return
        warn(f"relink  ~/.claude/skills/{name} -> {want}")
        if apply:
            link.unlink()
            link.symlink_to(want)
        return
    if link.exists():
        bad(f"~/.claude/skills/{name} が実体として存在する。手で確認する")
        return
    ok(f"link    ~/.claude/skills/{name} -> {want}")
    if apply:
        CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
        link.symlink_to(want)


def cmd_install(args):
    data = load()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rc = 0
    for e in entries(data, args.name):
        if e["state"] != "active" and not args.name:
            continue
        print(f"\n{display_name(e)}  {DIM}[{e['kind']}]{RST}")

        if e["kind"] == "gist":
            name = e["skills"][0]
            p = skill_path(name)
            try:
                want = gist_raw(e, e["revision"])
            except urllib.error.URLError as ex:
                bad(f"取得に失敗: {ex}")
                rc = 1
                continue
            if p.exists() and p.read_text() == want:
                ok(f"ok      {name} — pin {e['revision'][:8]} と一致")
            else:
                if p.exists():
                    warn(f"replace {name} — 既存を退避して pin {e['revision'][:8]} に置き換え")
                    if args.apply:
                        backup(p.parent, "external", stamp)
                else:
                    ok(f"install {name} — pin {e['revision'][:8]}")
                if args.apply:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(want)
            link_into_claude(name, args.apply)

        elif e["kind"] == "skills-cli":
            missing = [n for n in e["skills"] if not (AGENTS_DIR / n).exists()]
            if not missing:
                ok(f"ok      {' '.join(e['skills'])}")
                continue
            cmd = ["npx", "skills", "add", e["repo"], "-g", "-y"]
            for a in e["agents"]:
                cmd += ["-a", a]
            for n in missing:
                cmd += ["--skill", n]
            ok(f"install {' '.join(missing)}")
            dim(" ".join(cmd))
            if args.apply:
                r = subprocess.run(cmd)
                if r.returncode != 0:
                    bad(f"npx skills add が失敗 (exit {r.returncode})")
                    rc = 1

        elif e["kind"] == "manual":
            loc = Path(os.path.expanduser(e["location"]))
            if loc.exists():
                ok(f"ok      {loc}  {DIM}(手動管理){RST}")
            else:
                warn(f"未導入だが自動導入の対象外 — {e['origin']}")
    if not args.apply:
        print(f"\n{DIM}dry-run。実際に導入するには --apply{RST}")
    print()
    return rc


# ---------------------------------------------------------------- update

def cmd_update(args):
    data = load()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rc = 0
    for e in entries(data, args.name):
        if e["state"] != "active" and not args.name:
            continue
        print(f"\n{display_name(e)}  {DIM}[{e['update']}]{RST}")

        if e["update"] == "manual" and e["kind"] == "gist":
            try:
                latest, date = gist_latest(e)
            except urllib.error.URLError as ex:
                bad(f"上流の確認に失敗: {ex}")
                rc = 1
                continue
            if latest == e["revision"]:
                ok(f"最新 — {latest[:8]}")
                continue
            name = e["skills"][0]
            p = skill_path(name)
            cur = p.read_text() if p.exists() else ""
            new = gist_raw(e, latest)
            warn(f"新 revision — {e['revision'][:8]} -> {latest[:8]} ({date})")
            d = list(difflib.unified_diff(cur.splitlines(True), new.splitlines(True),
                                          f"{name} {e['revision'][:8]}",
                                          f"{name} {latest[:8]}"))
            sys.stdout.writelines("    " + l for l in d)
            if args.apply:
                if p.exists():
                    backup_copy(p, "external", stamp, f".{e['revision'][:8]}")
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(new)
                if not set_field(e["id"], "revision", latest):
                    bad("manifest の revision を書き換えられなかった")
                    rc = 1
                if "revision_date" in e:
                    set_field(e["id"], "revision_date", date)
                ok(f"更新した — {latest[:8]}")

        elif e["update"] == "skills-cli":
            installed = [n for n in e["skills"] if (AGENTS_DIR / n).exists()]
            if not installed:
                dim("未導入。先に install する")
                continue
            cmd = ["npx", "skills", "update", *installed, "-g", "-y"]
            dim(" ".join(cmd))
            if args.apply:
                before = lock_hashes()
                r = subprocess.run(cmd)
                if r.returncode != 0:
                    bad(f"npx skills update が失敗 (exit {r.returncode})")
                    rc = 1
                    continue
                after = lock_hashes()
                for n in installed:
                    if before.get(n) != after.get(n):
                        warn(f"{n}  {before.get(n, '?')[:8]} -> {after.get(n, '?')[:8]}")
                    else:
                        ok(f"{n} 変化なし")

        else:
            dim("更新方針が pinned のため何もしない")
    if not args.apply:
        print(f"\n{DIM}dry-run。実際に更新するには --apply{RST}")
    print()
    return rc


# ---------------------------------------------------------------- add

GIST_RE = re.compile(r"(?:gist\.github\.com/(?:([\w-]+)/)?)?([0-9a-f]{20,})")
REPO_RE = re.compile(r"(?:github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def cmd_add(args):
    src = args.source
    m = GIST_RE.search(src)
    if m and ("gist.github.com" in src or re.fullmatch(r"[0-9a-f]{20,}", src)):
        gid = m.group(2)
        d = api(f"https://api.github.com/gists/{gid}")
        files = list(d["files"])
        if len(files) != 1:
            print(f"gist に SKILL.md が一意に定まらない: {files}", file=sys.stderr)
            return 2
        name = args.name_override or Path(files[0]).stem
        if name == "SKILL":
            print("--name で skill 名を指定する（gist のファイル名が SKILL.md のため）", file=sys.stderr)
            return 2
        block = f'''
[[entry]]
id       = "{name}"
category = "{args.category}"
summary  = "{d.get('description') or 'TODO'}"
state    = "active"
kind     = "gist"
skills   = ["{name}"]
agents   = ["claude-code", "codex"]
update   = "manual"
local_changes = "なし"
license  = "TODO — gist のコメントも確認する"
gist_owner = "{d['owner']['login']}"
gist_id    = "{gid}"
gist_file  = "{files[0]}"
revision   = "{d['history'][0]['version']}"
revision_date = "{d['history'][0]['committed_at'][:10]}"
'''
    else:
        m = REPO_RE.search(src)
        if not m:
            print(f"gist でも GitHub リポジトリでもない: {src}", file=sys.stderr)
            return 2
        repo = f"{m.group(1)}/{m.group(2)}"
        skills = args.skill or discover_skills(repo)
        if not skills:
            print(f"{repo} に skill が見つからない。--skill で明示する", file=sys.stderr)
            return 2
        name = args.name_override or m.group(2)
        block = f'''
[[entry]]
id       = "{name}"
category = "{args.category}"
summary  = "TODO"
state    = "planned"
kind     = "skills-cli"
repo     = "{repo}"
skills   = [{", ".join(f'"{s}"' for s in skills)}]
agents   = ["claude-code", "codex"]
update   = "skills-cli"
local_changes = "なし"
license  = "TODO"
'''
    MANIFEST.write_text(MANIFEST.read_text().rstrip("\n") + "\n" + block)
    load()  # 壊れた TOML を書いていないか確かめる
    print(block)
    print(f"{Y}external/manifest.toml に追記した。TODO を埋めてから "
          f"`install.sh external install --apply` と `install.sh docs`{RST}")
    return 0


def discover_skills(repo: str) -> list[str]:
    for branch in ("main", "master"):
        try:
            t = api(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1")
        except urllib.error.URLError:
            continue
        found = []
        for n in (x["path"] for x in t.get("tree", [])):
            mm = re.fullmatch(r"(?:skills/)?([^/]+)/SKILL\.md", n)
            if mm:
                found.append(mm.group(1))
        if found:
            return sorted(set(found))
    return []


# ---------------------------------------------------------------- docs

HEADER = """# 配布 skill の台帳

自分で書いていない skill の記録。実体はこのリポジトリに置かず、導入元と確認した revision だけを残す。

> **このファイルは `external/manifest.toml` から生成している。手で編集しない。**
> 変更は manifest 側で行い、`./scripts/install.sh docs` で再生成する。

`npx skills` 経由のものの folder hash は台帳に持たず、`~/.agents/.skill-lock.json` を生成時に読んでいる。
台帳は人間向け、lock ファイルは導入ツールの機械記録として役割を分ける。

gist はライセンスがファイルではなくコメントで示されることがある。リポジトリのファイル一覧だけを見て「明示なし」と判断しない。

```bash
curl -s https://api.github.com/gists/<id>/comments | jq -r '.[].body'
```

最終棚卸し: {inventoried}
生成: {generated}
"""

STATE_JA = {"active": "使用中", "planned": "導入予定", "retired": "停止中"}
UPDATE_JA = {"manual": "手動追従", "skills-cli": "`npx skills update`", "pinned": "固定"}
AGENT_JA = {"claude-code": "Claude", "codex": "Codex"}


def agents_ja(e):
    a = [AGENT_JA.get(x, x) for x in e["agents"]]
    return "両方" if len(a) > 1 else a[0]


def render(data) -> str:
    hashes = lock_hashes()
    out = [HEADER.format(inventoried=data["inventoried"],
                         generated=datetime.now().strftime("%Y-%m-%d"))]
    by_cat: dict[str, list] = {}
    for e in data["entry"]:
        by_cat.setdefault(e["category"], []).append(e)

    for cat, es in by_cat.items():
        out.append(f"\n---\n\n## {cat}\n")
        for e in es:
            out.append(f"\n### {display_name(e)}\n")
            out.append(f"\n{e['summary']}\n\n")
            lic = e["license"]
            if e.get("license_note"):
                lic += "。" + e["license_note"].strip()
            where = agents_ja(e)
            if e["kind"] in ("gist", "skills-cli"):
                n = e["skills"][0]
                where += (f"（`~/.agents/skills/{n}` に実体、`~/.claude/skills` から symlink）"
                          if len(e["skills"]) == 1 else
                          "（`~/.agents/skills/<name>` に実体、`~/.claude/skills` から symlink）")
            rows = [
                f"- 状態: {STATE_JA[e['state']]}",
                f"- 使用先: {where}",
            ]
            if e["kind"] == "gist":
                url = f"https://gist.github.com/{e['gist_owner']}/{e['gist_id']}"
                rows.append(f"- 出所: {e['gist_owner']} / gist [`{e['gist_id']}`]({url})")
            elif e["kind"] == "skills-cli":
                rows.append(f"- 出所: [{e['repo']}](https://github.com/{e['repo']})")
            else:
                rows.append(f"- 出所: {e['origin']}")
                rows.append(f"- 場所: `{e['location']}`")
            rows.append(f"- ライセンス: {lic}")
            if e["kind"] == "gist":
                d = f" ({e['revision_date']})" if e.get("revision_date") else ""
                rows.append(f"- revision: `{e['revision']}`{d}")
            rows.append(f"- 更新方針: {UPDATE_JA[e['update']]}")
            rows.append(f"- ローカル変更: {e['local_changes']}")
            out.append("\n".join(rows) + "\n")

            if e["kind"] == "gist":
                raw = (f"https://gist.githubusercontent.com/{e['gist_owner']}/{e['gist_id']}"
                       f"/raw/{e['revision']}/{e['gist_file']}")
                out.append(f"\n```bash\ncurl -sfL {raw} \\\n  "
                           f"-o ~/.agents/skills/{e['skills'][0]}/SKILL.md\n```\n")
            elif e["kind"] == "skills-cli":
                agents = " ".join(f"-a {a}" for a in e["agents"])
                sk = " \\\n  ".join(f"--skill {s}" for s in e["skills"])
                when = f"# {e['installed_at']} に導入\n" if e.get("installed_at") else ""
                out.append(f"\n```bash\n{when}npx skills add {e['repo']} -g {agents} \\\n  {sk}\n```\n")
                got = [(s, hashes[s]) for s in e["skills"] if s in hashes]
                if got:
                    out.append("\n生成時点の `~/.agents/.skill-lock.json` の記録:\n\n")
                    out.append("| skill | skillFolderHash |\n| --- | --- |\n")
                    out += [f"| `{s}` | `{h}` |\n" for s, h in got]
                if e.get("not_installed"):
                    out.append("\n未導入: " + ", ".join(f"`{s}`" for s in e["not_installed"]) + "\n")

            if e.get("notes"):
                out.append("\n" + e["notes"].strip() + "\n")
    return "".join(out)


def cmd_docs(args):
    text = render(load())
    if args.check:
        cur = DOCS.read_text() if DOCS.exists() else ""
        # 生成日の行だけは差分から除く
        strip = lambda s: re.sub(r"(?m)^生成: .*$", "", s)
        if strip(cur) != strip(text):
            bad("EXTERNAL.md が manifest と食い違っている。`install.sh docs` で再生成する")
            sys.stdout.writelines(difflib.unified_diff(
                cur.splitlines(True), text.splitlines(True), "EXTERNAL.md", "生成結果"))
            return 1
        ok("EXTERNAL.md は manifest と一致している")
        return 0
    DOCS.write_text(text)
    ok(f"生成した — {DOCS}")
    return 0


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(prog="external")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status");  s.add_argument("name", nargs="*")
    s.add_argument("--offline", action="store_true", help="上流に問い合わせない")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("install"); s.add_argument("name", nargs="*")
    s.add_argument("--apply", action="store_true"); s.set_defaults(fn=cmd_install)

    s = sub.add_parser("update");  s.add_argument("name", nargs="*")
    s.add_argument("--apply", action="store_true"); s.set_defaults(fn=cmd_update)

    s = sub.add_parser("add"); s.add_argument("source")
    s.add_argument("--name", dest="name_override")
    s.add_argument("--category", default="未分類")
    s.add_argument("--skill", action="append")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("docs"); s.add_argument("--check", action="store_true")
    s.set_defaults(fn=cmd_docs)

    a = p.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
