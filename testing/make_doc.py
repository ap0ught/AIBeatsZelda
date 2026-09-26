"""Generate one .md per script in testing/, from the script itself.

    python3 testing/make_doc.py            # rewrite every testing/*.md
    python3 testing/make_doc.py --check    # report drift, write nothing

Each doc is built from four sources, in decreasing order of how much the script
already tells you:

1. **The module docstring**, verbatim. These scripts document themselves well -
   that is the house style - so the doc is mostly the author's own words rather
   than a restatement of them.
2. **What the script touches**, read out of the code: the paths it writes
   (logs/, shots/, states/, ...), whether it drives the emulator, and whether it
   mutates a tracked source file. The mutation case matters, because most of the
   patch_*.py scripts edit a file in place and are *not* safe to re-run.
3. **Provenance**, which is the one thing the script cannot know about itself:
   grep the production code for its name. If zelda/fullgame.py cites
   probe_gleeok_ram.py in a comment, that script is where a tuned constant came
   from, and the number in the comment is only as good as the script behind it.
4. **Neighbours**, by shared output paths and shared citing files.

Run with --check in CI or before a commit: if a docstring changes and the .md is
not regenerated, --check says so.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib

import argparse
import ast
import re
import sys
from pathlib import Path

HERE = Path("testing")
SELF = "make_doc.py"

# Where a script's output lands, and what that implies about running it.
PATHS = {
    "logs/": "the log directory",
    "shots/": "the screenshot directory",
    "states/": "the savestate directory",
    "runs/": "a recorded run",
    "video/": "the video directory",
    "journal/": "the project journal",
    "knowledge/": "the knowledge notes",
}

# Files that count as production: the code a reader would actually be reading.
PROD_GLOBS = ("zelda/*.py", "*.py")


def prod_files() -> list[Path]:
    out = []
    for g in PROD_GLOBS:
        out.extend(sorted(Path(".").glob(g)))
    return [p for p in out if p.parent.name != "testing" and p.name != SELF]


def cited_by(name: str, prod: list[Path]) -> list[tuple[str, str]]:
    """Production files that mention this script by name, with the citing line."""
    hits = []
    for p in prod:
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if name in line:
                    hits.append((f"`{p}`:{i}", line.strip()))
        except OSError:
            continue
    return hits


def docstring_of(src: str) -> str:
    try:
        return (ast.get_docstring(ast.parse(src)) or "").strip()
    except SyntaxError:
        return ""


def analyse(src: str, name: str) -> dict:
    writes, mutates, drives, loads = [], [], False, []
    for key, human in PATHS.items():
        if key in src:
            writes.append((key, human))
    if re.search(r"\.write_text\(|\.write_bytes\(", src):
        mutates.append("writes a file")
    # a patch script that rewrites a tracked source is not safe to re-run
    if name.startswith("patch_") and re.search(r"\.replace\(|write_text", src):
        mutates.append("**edits a tracked source file in place**")
    if re.search(r"\bBizHawk\b|random_search|emu\.load\(", src):
        drives = True
    for m in re.finditer(r'emu\.load\(\s*["\']([^"\']+)["\']', src):
        loads.append(m.group(1))
    for m in re.finditer(r'load_inputs\(\s*(?:Path\()?f?["\']([^"\']+)["\']', src):
        pass
    argv = re.findall(r"usage:\s*(\S+)", src)
    return dict(writes=sorted(set(writes)), mutates=sorted(set(mutates)),
                drives=drives, loads=sorted(set(loads)), usage=argv[:1])


def deps_mtime(script: Path, prod: list[Path]) -> float:
    """Newest mtime among everything this doc is derived from.

    Not just the script. A doc also depends on the generator (the template lives
    there) and on the production files it greps for provenance, so editing a
    comment in zelda/fullgame.py can change a doc in testing/ without touching
    either the script or its own .md.
    """
    newest = max((script.stat().st_mtime, Path(__file__).stat().st_mtime), default=0.0)
    for p in prod:
        try:
            newest = max(newest, p.stat().st_mtime)
        except OSError:
            pass
    return newest


def neighbours(name: str, allscripts: dict[str, dict], prod: list[Path]) -> list[str]:
    mine = allscripts[name]
    mine_paths = {p for p, _ in mine["writes"]}
    mine_cited = {c.split(":")[0].strip("`") for c, _ in cited_by(name, prod)}
    out = []
    for other, info in allscripts.items():
        if other == name:
            continue
        op = {p for p, _ in info["writes"]}
        oc = {c.split(":")[0].strip("`") for c, _ in cited_by(other, prod)}
        score = len(mine_paths & op) * 2 + len(mine_cited & oc)
        if score:
            out.append((score, other))
    out.sort(reverse=True)
    return [o for _, o in out[:4]]


def render(name: str, info: dict, cites: list[tuple[str, str]],
           nbrs: list[str], body: str) -> str:
    stem = name[:-3]
    L = [f"# `{name}`", ""]
    L.append(body if body else "*(no docstring)*")
    L.append("")
    L.append("---")
    L.append("")
    L.append(f"    python3 testing/{name}          # any cwd; the bootstrap chdirs to the repo root")
    L.append("")

    L.append("## What it touches")
    L.append("")
    if info["drives"]:
        L.append("- **drives BizHawk** - replays, searches or steps frames")
    if info["writes"]:
        L.append("- writes " + ", ".join(f"`{p}`" for p, _ in info["writes"]))
    if info["loads"]:
        L.append("- loads savestate(s): " + ", ".join(f"`{s}`" for s in info["loads"]))
    if not info["drives"] and not info["writes"] and not info["loads"]:
        L.append("- nothing at runtime; it exists to be read, or to be applied once")
    for m in info["mutates"]:
        L.append(f"- {m}")
    L.append("")

    if cites:
        L.append("## Why this still matters")
        L.append("")
        L.append("Cited by production code. These comments are where the numbers came from,")
        L.append("so if this script's method is wrong, the constant is wrong too:")
        L.append("")
        for loc, line in cites:
            L.append(f"- `{loc}` - {line}")
        L.append("")

    if nbrs:
        L.append("## See also")
        L.append("")
        for n in nbrs:
            L.append(f"- [`{n}`]({n}.md)")
        L.append("")

    L.append("---")
    L.append("")
    # No timestamp here on purpose. An earlier version embedded today's date, which
    # made the content comparison in --check fail for all 180 docs the day after they
    # were written - the rendered text could never match a file carrying yesterday's
    # date. Git history already records when a doc changed; putting it in the file
    # only creates a second source of truth that is wrong by construction.
    L.append(f"*Generated by `testing/{SELF}` from the script's own docstring and code. "
             f"Regenerate with `python3 testing/{SELF}`; do not hand-edit - "
             f"`git log` on this file says when.*")
    L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="compare every doc against a fresh render; write nothing")
    ap.add_argument("--force", action="store_true", help="regenerate all, ignoring mtimes")
    a = ap.parse_args()

    prod = prod_files()
    scripts = {}
    for p in sorted(HERE.glob("*.py")):
        src = p.read_text(encoding="utf-8", errors="replace")
        scripts[p.name] = analyse(src, p.name)
    if not scripts:
        raise SystemExit("no scripts found in testing/")

    written = drift = skipped = 0
    for name, info in sorted(scripts.items()):
        script = HERE / name
        md = HERE / (name[:-3] + ".md")

        if not a.check and not a.force and md.exists() \
                and md.stat().st_mtime >= deps_mtime(script, prod):
            skipped += 1
            continue

        src = script.read_text(encoding="utf-8", errors="replace")
        body = docstring_of(src)
        cites = cited_by(name, prod)
        text = render(name, info, cites, neighbours(name, scripts, prod), body)
        if a.check:
            if not md.exists():
                print(f"  MISSING  {md.name}")
                drift += 1
            elif md.read_text(encoding="utf-8") != text:
                print(f"  STALE    {md.name}")
                drift += 1
        else:
            md.write_text(text, encoding="utf-8")
            written += 1

    if a.check:
        print(f"compared {len(scripts)} docs against a fresh render: {drift} drifted")
        if drift:
            raise SystemExit(1)
        return
    print(f"{len(scripts)} docs: {written} written, {skipped} up to date"
          + ("" if written or not a.force else "  (--force with nothing stale)")
          + "  -> testing/*.md")


if __name__ == "__main__":
    main()
