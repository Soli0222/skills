#!/usr/bin/env python3
"""配布 skill を external/manifest.toml のとおりに導入・更新し、EXTERNAL.md を生成する。

install.sh から呼ばれる。単体でも動く。

EXTERNAL.md は manifest だけから決まる。端末の導入状況は読まないので、
どの環境で生成しても同じものになる。現在の状況は `external status` で見る。
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

# テストから差し替えるための取得先
GIST_RAW_BASE = os.environ.get("GIST_RAW_BASE", "https://gist.githubusercontent.com")
GITHUB_API_BASE = os.environ.get("GITHUB_API_BASE", "https://api.github.com")

G, Y, R, DIM, RST = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"

OK, CHANGED, CONFLICT, MISSING = "ok", "changed", "conflict", "missing"


def ok(s):   print(f"  {G}{s}{RST}")
def warn(s): print(f"  {Y}{s}{RST}")
def bad(s):  print(f"  {R}{s}{RST}")
def dim(s):  print(f"  {DIM}{s}{RST}")


# ---------------------------------------------------------------- manifest

def load(path: Path = None) -> dict:
    with (path or MANIFEST).open("rb") as f:
        return tomllib.load(f)


def entries(data, only=None):
    for e in data.get("entry", []):
        if only and e["id"] not in only and not (set(e["skills"]) & set(only)):
            continue
        yield e


def display_name(e):
    return e.get("title", e["id"])


def toml_str(s: str) -> str:
    """任意の文字列を TOML の基本文字列にする。"""
    out = s.replace("\\", "\\\\").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    out = "".join(c if c >= " " and c != "\x7f" else f"\\u{ord(c):04x}" for c in out)
    return f'"{out}"'


def set_field(entry_id: str, key: str, value: str) -> bool:
    """manifest の該当 [[entry]] ブロック内の key を書き換える。

    TOML を再シリアライズするとコメントと整形が失われるので、行単位で置換する。
    key が無いときは末尾に足す。
    """
    text = MANIFEST.read_text()
    blocks = re.split(r"(?m)^(\[\[entry\]\]\s*$)", text)
    for i in range(1, len(blocks), 2):
        body = blocks[i + 1]
        if not re.search(rf'(?m)^id\s*=\s*"{re.escape(entry_id)}"\s*$', body):
            continue
        pat = re.compile(rf'(?m)^(?P<pre>{re.escape(key)}\s*=\s*)"[^"]*"[^\S\n]*$')
        if pat.search(body):
            body = pat.sub(lambda m: f'{m.group("pre")}{toml_str(value)}', body, count=1)
        else:
            body = body.rstrip("\n") + f"\n{key} = {toml_str(value)}\n\n"
        blocks[i + 1] = body
        write_manifest("".join(blocks))
        return True
    return False


def write_manifest(text: str):
    """tomllib で読めることを確かめてから置き換える。壊れた manifest を残さない。"""
    with tempfile.NamedTemporaryFile("w", dir=MANIFEST.parent, suffix=".toml",
                                     delete=False) as f:
        f.write(text)
        tmp = Path(f.name)
    try:
        load(tmp)
    except tomllib.TOMLDecodeError as ex:
        tmp.unlink()
        raise SystemExit(f"{R}生成した TOML が壊れている。manifest は変更していない: {ex}{RST}")
    os.replace(tmp, MANIFEST)


# ---------------------------------------------------------------- 取得

def api(path: str):
    req = urllib.request.Request(GITHUB_API_BASE + path,
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": "skills-repo"})
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok and GITHUB_API_BASE.startswith("https://api.github.com"):
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def gist_raw(e, revision: str) -> str:
    url = f"{GIST_RAW_BASE}/{e['gist_owner']}/{e['gist_id']}/raw/{revision}/{e['gist_file']}"
    req = urllib.request.Request(url, headers={"User-Agent": "skills-repo"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode()


def gist_latest(e) -> tuple[str, str]:
    d = api(f"/gists/{e['gist_id']}")
    h = d["history"][0]
    return h["version"], h["committed_at"][:10]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def skill_path(name: str) -> Path:
    return AGENTS_DIR / name / "SKILL.md"


# ---------------------------------------------------------------- lock

def lock_records() -> dict:
    """~/.agents/.skill-lock.json の記録を skill 名で引けるようにして返す。"""
    if not LOCK.exists():
        return {}
    try:
        return json.loads(LOCK.read_text()).get("skills", {})
    except (json.JSONDecodeError, AttributeError):
        return {}


def check_origin(name: str, repo: str, rec: dict | None) -> tuple[str, str]:
    """lock の記録が manifest の出所と合っているか見る。

    同名の別 skill を「導入済み」と誤認しないための照合。
    """
    if rec is None:
        return CHANGED, f"{name} — 実体はあるが .skill-lock.json に記録がない"
    src = rec.get("source", "")
    url = rec.get("sourceUrl", "")
    path = rec.get("skillPath", "")
    if src and src.lower() != repo.lower() and repo.lower() not in url.lower():
        return CONFLICT, f"{name} — 出所が違う: 記録は {src or url}、台帳は {repo}"
    if path and not re.fullmatch(rf"(?:.*/)?{re.escape(name)}/SKILL\.md", path):
        return CONFLICT, f"{name} — skillPath が名前と食い違う: {path}"
    if not rec.get("skillFolderHash"):
        return CHANGED, f"{name} — skillFolderHash が記録されていない"
    return OK, f"{name}  {DIM}{rec['skillFolderHash'][:8]}{RST}"


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


# ---------------------------------------------------------------- 配置

def check_placement(name: str, apply: bool) -> tuple[str, str]:
    """~/.agents/skills/<name> の実体と ~/.claude/skills/<name> の symlink を見る。

    gist / skills-cli のどちらで入れたものでも同じ規則で確かめる。
    """
    origin = AGENTS_DIR / name
    if not origin.exists():
        return MISSING, f"未導入 — {origin}"

    link = CLAUDE_DIR / name
    want = os.path.relpath(origin, CLAUDE_DIR)
    if link.is_symlink():
        cur = os.readlink(link)
        if cur == want and link.exists():
            return OK, f"{name}"
        why = "リンク先が存在しない" if cur == want else f"{cur} を指している"
        if apply:
            link.unlink()
            link.symlink_to(want)
        return CHANGED, f"{name} — ~/.claude/skills の symlink を張り直す（{why}）"
    if link.exists():
        return CONFLICT, f"{name} — ~/.claude/skills/{name} が実体として存在する。手で確認する"
    if apply:
        CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
        link.symlink_to(want)
    return CHANGED, f"{name} — ~/.claude/skills の symlink を作る"


def report(state: str, msg: str, mode: str = "check") -> int:
    """表示して、終了コードへの寄与を返す。

    mode によって「望ましくない状態」の重みが変わる。

      check   点検するだけ。あるべき状態でなければ 1（status）
      dryrun  これから直す予告。衝突だけが 1（install/update の dry-run）
      apply   直した後。直せなかったものだけが 1（install/update の --apply）
    """
    if state == OK:
        ok(f"ok      {msg}")
        return 0
    if state == CONFLICT:
        bad(f"CONFLICT {msg}")
        return 1
    if state == CHANGED:
        warn(f"fix     {msg}")
        return 1 if mode == "check" else 0
    bad(msg)  # MISSING
    return 0 if mode == "dryrun" else 1


# ---------------------------------------------------------------- status

def cmd_status(args):
    data = load()
    recs = lock_records()
    rc = 0
    for e in entries(data, args.name):
        print(f"\n{display_name(e)}  {DIM}[{e['kind']}]{RST}")

        if e["kind"] == "gist":
            name = e["skills"][0]
            p = skill_path(name)
            if not p.exists():
                bad(f"未導入 — {p}")
                rc = 1
                continue
            local = p.read_text()
            digest = sha256(local)
            if e.get("sha256"):
                if digest == e["sha256"]:
                    ok(f"pin と一致 — {e['revision'][:8]} / sha256 {digest[:8]}")
                else:
                    bad(f"ローカルが pin ({e['revision'][:8]}) の sha256 と一致しない")
                    rc = 1
            else:
                warn(f"sha256 が manifest に未記録 — `external install {e['id']} --apply` で記録する")
                rc = 1
            rc |= report(*check_placement(name, apply=False), mode="check")
            if not args.offline:
                try:
                    latest, date = gist_latest(e)
                except urllib.error.URLError as ex:
                    warn(f"上流未確認 ({ex})")
                    continue
                if latest != e["revision"]:
                    warn(f"上流に新 revision — {latest[:8]} ({date})  "
                         f"`external update {e['id']}` で追従")
                    rc = 1
                else:
                    ok("上流も最新")

        elif e["kind"] == "skills-cli":
            for n in e["skills"]:
                state, msg = check_placement(n, apply=False)
                if state != OK:
                    rc |= report(state, msg, "check")
                    continue
                rc |= report(*check_origin(n, e["repo"], recs.get(n)), mode="check")
    print()
    return rc


# ---------------------------------------------------------------- install

def cmd_install(args):
    data = load()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    mode = "apply" if args.apply else "dryrun"
    rc = 0
    for e in entries(data, args.name):
        print(f"\n{display_name(e)}  {DIM}[{e['kind']}]{RST}")
        entry_rc = 0

        if e["kind"] == "gist":
            name = e["skills"][0]
            p = skill_path(name)
            try:
                want = gist_raw(e, e["revision"])
            except urllib.error.URLError as ex:
                bad(f"取得に失敗: {ex}")
                rc = 1
                continue
            digest = sha256(want)
            if e.get("sha256") and e["sha256"] != digest:
                bad(f"取得した内容が manifest の sha256 と一致しない。"
                    f"記録 {e['sha256'][:8]} / 取得 {digest[:8]}")
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
            if args.apply and not e.get("sha256"):
                set_field(e["id"], "sha256", digest)
                ok(f"sha256 を記録した — {digest[:8]}")
            entry_rc |= report(*check_placement(name, args.apply), mode=mode)

        elif e["kind"] == "skills-cli":
            missing = [n for n in e["skills"] if not (AGENTS_DIR / n).exists()]
            if missing:
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
                        continue
            recs = lock_records()
            for n in e["skills"]:
                state, msg = check_placement(n, args.apply)
                if state == MISSING and not args.apply:
                    dim(f"        {n} — 導入後に配置を確かめる")
                    continue
                if state != OK:
                    entry_rc |= report(state, msg, mode)
                    continue
                entry_rc |= report(*check_origin(n, e["repo"], recs.get(n)), mode=mode)

        rc |= entry_rc

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
                set_field(e["id"], "sha256", sha256(new))
                ok(f"更新した — {latest[:8]}")

        elif e["update"] == "skills-cli":
            installed = [n for n in e["skills"] if (AGENTS_DIR / n).exists()]
            if not installed:
                dim("未導入。先に install する")
                continue
            cmd = ["npx", "skills", "update", *installed, "-g", "-y"]
            dim(" ".join(cmd))
            if args.apply:
                before = {k: v.get("skillFolderHash", "") for k, v in lock_records().items()}
                r = subprocess.run(cmd)
                if r.returncode != 0:
                    bad(f"npx skills update が失敗 (exit {r.returncode})")
                    rc = 1
                    continue
                recs = lock_records()
                for n in installed:
                    after = recs.get(n, {}).get("skillFolderHash", "")
                    if before.get(n, "") != after:
                        warn(f"{n}  {before.get(n, '?')[:8]} -> {after[:8]}")
                    else:
                        ok(f"{n} 変化なし")
                    rc |= report(*check_placement(n, args.apply), mode="apply")

        else:
            dim("更新方針が pinned のため何もしない")
    if not args.apply:
        print(f"\n{DIM}dry-run。実際に更新するには --apply{RST}")
    print()
    return rc


# ---------------------------------------------------------------- add

GIST_RE = re.compile(r"(?:gist\.github\.com/(?:[\w-]+/)?)?([0-9a-f]{20,})")
REPO_RE = re.compile(r"(?:github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def cmd_add(args):
    data = load()
    known_ids = {e["id"] for e in data.get("entry", [])}
    known_skills = {s: e["id"] for e in data.get("entry", []) for s in e["skills"]}
    src = args.source

    m = GIST_RE.search(src)
    if m and ("gist.github.com" in src or re.fullmatch(r"[0-9a-f]{20,}", src)):
        gid = m.group(1)
        d = api(f"/gists/{gid}")
        files = list(d["files"])
        if len(files) != 1:
            print(f"gist に SKILL.md が一意に定まらない: {files}", file=sys.stderr)
            return 2
        name = args.name_override or Path(files[0]).stem
        if name == "SKILL":
            print("--name で skill 名を指定する（gist のファイル名が SKILL.md のため）",
                  file=sys.stderr)
            return 2
        rev = d["history"][0]["version"]
        fields = [
            ("id", name), ("category", args.category),
            ("summary", d.get("description") or "TODO"), ("kind", "gist"),
        ]
        tail = [
            ("update", "manual"), ("local_changes", "なし"),
            ("license", "TODO — gist のコメントも確認する"),
            ("gist_owner", d["owner"]["login"]), ("gist_id", gid),
            ("gist_file", files[0]), ("revision", rev),
            ("revision_date", d["history"][0]["committed_at"][:10]),
        ]
        skills = [name]
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
        fields = [
            ("id", name), ("category", args.category), ("summary", "TODO"),
            ("kind", "skills-cli"), ("repo", repo),
        ]
        tail = [("update", "skills-cli"), ("local_changes", "なし"), ("license", "TODO")]

    if name in known_ids:
        print(f"id が既にある: {name}", file=sys.stderr)
        return 2
    for s in skills:
        if s in known_skills:
            print(f"skill 名が既に {known_skills[s]} で使われている: {s}", file=sys.stderr)
            return 2

    lines = [f"{k:8} = {toml_str(v)}" for k, v in fields]
    lines.append(f"skills   = [{', '.join(toml_str(s) for s in skills)}]")
    lines.append('agents   = ["claude-code", "codex"]')
    lines += [f"{k:8} = {toml_str(v)}" for k, v in tail]
    block = "\n[[entry]]\n" + "\n".join(lines) + "\n"

    # tomllib で読めることを確かめてから置き換える
    write_manifest(MANIFEST.read_text().rstrip("\n") + "\n" + block)
    print(block)
    print(f"{Y}external/manifest.toml に追記した。TODO を埋めてから "
          f"`install.sh external install {name} --apply`{RST}")
    return 0


def discover_skills(repo: str) -> list[str]:
    for branch in ("main", "master"):
        try:
            t = api(f"/repos/{repo}/git/trees/{branch}?recursive=1")
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

ここに書いてあるのは台帳の内容だけで、いま実際に何が入っているかは含まない。
手元の導入状況は `./scripts/install.sh external status` で見る。
`npx skills` が書く機械側の記録は `~/.agents/.skill-lock.json` にある。

gist はライセンスがファイルではなくコメントで示されることがある。リポジトリのファイル一覧だけを見て「明示なし」と判断しない。

```bash
curl -s https://api.github.com/gists/<id>/comments | jq -r '.[].body'
```

最終棚卸し: {inventoried}
"""

UPDATE_JA = {"manual": "手動追従", "skills-cli": "`npx skills update`", "pinned": "固定"}
AGENT_JA = {"claude-code": "Claude", "codex": "Codex"}


def agents_ja(e):
    a = [AGENT_JA.get(x, x) for x in e["agents"]]
    return "両方" if len(a) > 1 else a[0]


def render(data) -> str:
    out = [HEADER.format(inventoried=data["inventoried"])]
    by_cat: dict[str, list] = {}
    for e in data.get("entry", []):
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
                n = e["skills"][0] if len(e["skills"]) == 1 else "<name>"
                where += f"（`~/.agents/skills/{n}` に実体、`~/.claude/skills` から symlink）"
            rows = [f"- 使用先: {where}"]
            if e["kind"] == "gist":
                url = f"https://gist.github.com/{e['gist_owner']}/{e['gist_id']}"
                rows.append(f"- 出所: {e['gist_owner']} / gist [`{e['gist_id']}`]({url})")
            else:
                rows.append(f"- 出所: [{e['repo']}](https://github.com/{e['repo']})")
            rows.append(f"- ライセンス: {lic}")
            if e["kind"] == "gist":
                d = f" ({e['revision_date']})" if e.get("revision_date") else ""
                rows.append(f"- revision: `{e['revision']}`{d}")
                if e.get("sha256"):
                    rows.append(f"- SKILL.md の sha256: `{e['sha256']}`")
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
                out.append(f"\n```bash\nnpx skills add {e['repo']} -g {agents} \\\n"
                           f"  {sk}\n```\n")
                if e.get("not_installed"):
                    out.append("\n未導入: " +
                               ", ".join(f"`{s}`" for s in e["not_installed"]) + "\n")

            if e.get("notes"):
                out.append("\n" + e["notes"].strip() + "\n")
    return "".join(out)


def cmd_docs(args):
    text = render(load())
    if args.check:
        cur = DOCS.read_text() if DOCS.exists() else ""
        if cur != text:
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
    s.add_argument("--offline", action="store_true",
                   help="上流に問い合わせない。manifest の sha256 とだけ照合する")
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
