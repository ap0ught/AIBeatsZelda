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
import subprocess
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

# Production file contents, read at most once. The first version of this script
# re-read every production file once per script, via cited_by() inside the
# neighbours() loop -- O(scripts^2 x prod_files) reads. At 183 scripts a full
# --check took 2m50s, which is far too slow for a pre-commit hook; people reach
# for --no-verify instead, which is worse than no hook. Caching the reads makes
# the check fast enough to run on every commit that touches a source file.
_PROD_LINES: dict[str, list[str]] = {}


def prod_lines() -> dict[str, list[str]]:
    """Every production file's lines, read once, keyed by path string."""
    if not _PROD_LINES:
        for p in prod_files():
            try:
                _PROD_LINES[str(p)] = p.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
            except OSError:
                _PROD_LINES[str(p)] = []
    return _PROD_LINES


def prod_files() -> list[Path]:
    out = []
    for g in PROD_GLOBS:
        out.extend(sorted(Path(".").glob(g)))
    return [p for p in out if p.parent.name != "testing" and p.name != SELF]


def cited_by(name: str, prod: list[Path]) -> list[tuple[str, str]]:
    """Production files that mention this script by name, with the citing line."""
    hits = []
    lines = prod_lines()
    for p in prod:
        key = str(p)
        for i, line in enumerate(lines.get(key, []), 1):
            if name in line:
                hits.append((f"`{p}`:{i}", line.strip()))
    return hits


def parse(src: str):
    """The script's module tree, or None if it does not parse.

    Parsed once per script and used for the docstring, for what the script WRITES and for what it
    CALLS. The previous version asked those questions with `in` and `re.search` over the source
    text, which means it read the prose: a docstring saying "no emulator needed, but see BizHawk"
    put "drives BizHawk - replays, searches or steps frames" into the generated doc of a script that
    never opens an emulator, and seven such docs shipped. A doc is a claim about what a script does,
    so it has to be derived from what the script does.
    """
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


def docstring_of(tree) -> str:
    if tree is None:
        return ""
    return (ast.get_docstring(tree) or "").strip()


def string_nodes(tree) -> list:
    """Every string constant in the module EXCEPT the module docstring, as NODES.

    Nodes rather than values, because whether a literal is a destination or a source depends on where
    it sits in the tree, and an id() lookup on a string you have already copied does not work.

    Excluding the docstring is the whole point of one of the two bugs this file had: the docstrings in
    testing/ talk about logs/, states/ and shots/ constantly, and the substring test read all of it.
    Comments need no exclusion - ast never sees one, and that is why the `_os.chdir(_ROOT)  # logs/,
    shots/, runs/ are repo-relative` line at the top of most scripts stopped being evidence the moment
    the analysis stopped being a text search.
    """
    if tree is None:
        return []
    skip = set()
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        skip.add(id(tree.body[0].value))
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip]


def call_name(node) -> str:
    """How a call is written: `save`, `emu.save`, `replay.verify` -> its last attribute."""
    f = node.func if isinstance(node, ast.Call) else None
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def called(tree) -> set[str]:
    """Names this module calls, as written: `BizHawk`, `random_search`, `replay.verify`."""
    if tree is None:
        return set()
    out = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name):
            out.add(f.id)
        elif isinstance(f, ast.Attribute):
            out.add(f.attr)
            if isinstance(f.value, ast.Name):
                out.add(f"{f.value.id}.{f.attr}")
    return out


# The harness's own writers, and where each one lands. A literal-prefix test cannot see these at all -
# `emu.screenshot("frame")` writes into shots/ whatever path it is handed - and the alternative that
# CAN see them is reading the source text, which is what put "writes logs/, runs/, shots/" on 196
# scripts that write none of them, on the strength of one comment:
#
#     _os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
#
# Sixty years of that comment sit at the top of most scripts in this directory. So: literals passed to
# a writing call, PLUS the harness's own writers whose destination is known from emulator.py
# (save -> STATES_DIR, screenshot -> SHOTS_DIR, save_inputs -> LOGS_DIR) - those three take a NAME,
# not a path, so there is no literal to read and the call itself is the evidence.
WRITES_WHERE = {"screenshot": "shots/", "save_inputs": "logs/", "save": "states/"}

# What counts as driving the emulator, asked of the CALLS rather than of the text. `BizHawk` is the
# constructor, so any script that opens an emulator has it; the search entry points and
# replay.verify cover the scripts that are handed one to drive. An import is not a call and does not
# count - a script that imports random_search without calling it is not driving anything, and being
# wrong in this direction costs a missing claim rather than a false one.
DRIVES_CALLS = {"BizHawk", "random_search", "parallel_search", "run_segment",
                "replay.verify", "zelda.replay.verify"}

# A path literal is a DESTINATION if it is inside a call that writes, and a SOURCE if it is inside one
# that reads. `Path("shots/x.png").write_text(...)` is the first and `Path("runs/run6/inputs.txt")` is
# the second, and the two differ by nothing you can see in the literal - so the question is asked of
# the tree, carrying the enclosing call down as it walks. The old text test could only answer "the
# directory name appears", which is how 196 scripts were documented as writing three directories on
# the strength of one comment, and how one script was documented as WRITING the run it reads.
WRITER_CONTEXT = {"write_text", "write_bytes", "writelines", "dump", "save", "screenshot",
                  "save_inputs", "copy", "copy2"}
READER_CONTEXT = {"read_text", "read_bytes", "exists", "is_file", "iterdir", "glob", "rglob",
                  "unlink", "rename", "load", "loads", "open_read"}


def path_literals(tree) -> tuple[list[str], list[str]]:
    """(destination, source) path-ish literal values, decided by the call each one sits inside."""
    if tree is None:
        return [], []
    skip = set()
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        skip.add(id(tree.body[0].value))
    dest, src = [], []

    def visit(node: ast.AST, in_writer: bool) -> None:
        for child in ast.iter_child_nodes(node):
            here = in_writer
            if isinstance(child, ast.Call):
                name = call_name(child)
                if name in WRITER_CONTEXT:
                    here = True
                elif name in READER_CONTEXT:
                    here = False
            if (isinstance(child, ast.Constant) and isinstance(child.value, str)
                    and "/" in child.value and id(child) not in skip):
                (dest if here else src).append(child.value)
            visit(child, here)

    for stmt in tree.body:
        visit(stmt, False)
    return dest, src


def analyse(src: str, name: str, tree=None) -> dict:
    if name == SELF:
        # This generator holds the path prefixes as DATA (the PATHS table above). Reading them as
        # "writes logs/, shots/, states/" would be the same mistake one level down: a claim about a
        # table, treated as a claim about behaviour.
        return dict(writes=[], mutates=[], drives=True, loads=[], usage=[])
    writes, mutates, drives, loads = [], [], False, []
    dest, _src = path_literals(tree)
    names = called(tree)
    hits = {k for k in PATHS if any(t.startswith(k) for t in dest)}
    hits |= {where for call, where in WRITES_WHERE.items() if call in names}
    for key, human in PATHS.items():
        if key in hits:
            writes.append((key, human))
    if re.search(r"\.write_text\(|\.write_bytes\(", src):
        mutates.append("writes a file")
    # a patch script that rewrites a tracked source is not safe to re-run
    if name.startswith("patch_") and re.search(r"\.replace\(|write_text", src):
        mutates.append("**edits a tracked source file in place**")
    drives = bool(called(tree) & DRIVES_CALLS)
    for m in re.finditer(r'emu\.load\(\s*["\']([^"\']+)["\']', src):
        loads.append(m.group(1))
    for m in re.finditer(r'load_inputs\(\s*(?:Path\()?f?["\']([^"\']+)["\']', src):
        pass
    argv = re.findall(r"usage:\s*(\S+)", src)
    return dict(writes=sorted(set(writes)), mutates=sorted(set(mutates)),
                drives=drives, loads=sorted(set(loads)), usage=argv[:1])


def tracked_scripts() -> set[str]:
    """The testing/*.py files git has in the index, as bare names.

    Falls back to every script on disk when git cannot answer (a tarball, a fresh clone with no
    index): the old all-of-disk behaviour, which is right when there is nothing else to go on.
    """
    try:
        out = subprocess.run(["git", "ls-files", "--", "testing/*.py"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return {p.name for p in HERE.glob("*.py")}
    if out.returncode != 0:
        return {p.name for p in HERE.glob("*.py")}
    names = {Path(line).name for line in out.stdout.splitlines() if line.endswith(".py")}
    return names or {p.name for p in HERE.glob("*.py")}


def tracked_orphans(tracked: set[str]) -> set[str]:
    """Tracked testing/*.md with no script beside them, in the index or on disk."""
    try:
        out = subprocess.run(["git", "ls-files", "--", "testing/*.md"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    if out.returncode != 0:
        return set()
    orphans = set()
    for line in out.stdout.splitlines():
        if not line.endswith(".md"):
            continue
        p = Path(line)
        if p.stem + ".py" in tracked:
            continue
        if (HERE / (p.stem + ".py")).exists():
            continue                            # tracked late, or a doc whose script is untracked
        # Only generated docs can be orphans. testing/README.md is hand-written and has no script.
        try:
            if "Generated by `testing/" not in (HERE / p.name).read_text(encoding="utf-8"):
                continue
        except OSError:
            continue
        orphans.add(p.name)
    return orphans


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


def all_citations(allscripts: dict[str, dict],
                  prod: list[Path]) -> dict[str, list[tuple[str, str]]]:
    """One pass over the cached production lines for every script.

    cited_by() scans each production file for the script's own name, so the
    naive form inside the neighbours() loop reads the whole tree once per
    (script, other-script) pair. Doing it once up front is the difference
    between a check you run and a check you skip.
    """
    return {name: cited_by(name, prod) for name in allscripts}


def neighbours(name: str, allscripts: dict[str, dict],
               cites: dict[str, list[tuple[str, str]]]) -> list[str]:
    mine = allscripts[name]
    mine_paths = {p for p, _ in mine["writes"]}
    mine_cited = {c.split(":")[0].strip("`") for c, _ in cites[name]}
    out = []
    for other, info in allscripts.items():
        if other == name:
            continue
        op = {p for p, _ in info["writes"]}
        oc = {c.split(":")[0].strip("`") for c, _ in cites[other]}
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
            # The doc file is <stem>.md, so the link has to be the stem too. Linking
            # <script>.py.md pointed at a file that was never written - every "See also"
            # in all 180-odd docs was dead, and the repo's whole argument is that these
            # cross-references resolve.
            L.append(f"- [`{n}`]({n[:-3]}.md)")
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
    ap.add_argument("--all", action="store_true",
                    help="cover every script in testing/, including ones git does not track")
    a = ap.parse_args()

    prod = prod_files()
    # THE GATE POLICES WHAT GIT KNOWS ABOUT, NOT WHAT HAPPENS TO BE ON DISK.
    #
    # It used to walk testing/*.py, so on a machine where several people are working at once any
    # agent who had a script half-written on disk blocked EVERY other agent's commit with
    # "MISSING <stem>.md" until somebody generated a doc for a file that was not even supposed to be
    # committed yet. A hook that fires on other people's scratch files is a global lock with no owner,
    # and the fix is not to argue about it in the commit message - it is to ask git which scripts are
    # real. Staged counts as tracked: `git add script.py` without its .md still fails the check, which
    # is exactly the case the gate exists for.
    tracked = tracked_scripts()
    on_disk = {p.name for p in HERE.glob("*.py")}
    stray = sorted(on_disk - tracked)
    untracked = stray if a.all else []
    scripts = {}
    for name in sorted(tracked):
        p = HERE / name
        if not p.exists():
            continue                            # deleted in the working tree; the doc is checked below
        src = p.read_text(encoding="utf-8", errors="replace")
        tree = parse(src)
        scripts[name] = analyse(src, name, tree)
    for name in untracked:
        p = HERE / name
        src = p.read_text(encoding="utf-8", errors="replace")
        tree = parse(src)
        scripts[name] = analyse(src, name, tree)
    if not scripts:
        raise SystemExit("no scripts found in testing/")

    cites = all_citations(scripts, prod)

    written = drift = skipped = 0
    for name, info in sorted(scripts.items()):
        script = HERE / name
        md = HERE / (name[:-3] + ".md")

        if not a.check and not a.force and md.exists() \
                and md.stat().st_mtime >= deps_mtime(script, prod):
            skipped += 1
            continue

        src = script.read_text(encoding="utf-8", errors="replace")
        body = docstring_of(parse(src))
        mine = cites[name]
        text = render(name, info, mine, neighbours(name, scripts, cites), body)
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

    # A doc whose script is gone is a dead cross-reference, and this tree once had 182 of them:
    # journal/48. The loop above can only see docs it has a script for, so orphans are counted here.
    for orphan in sorted(tracked_orphans(tracked)):
        print(f"  ORPHAN   {orphan}")
        drift += 1

    if a.check:
        print(f"compared {len(scripts)} docs against a fresh render: {drift} drifted")
        if stray and not a.all:
            print(f"  {len(stray)} script(s) not tracked by git, not checked: "
                  + ", ".join(n[:-3] for n in stray[:6]) + (", ..." if len(stray) > 6 else ""))
        if drift:
            raise SystemExit(1)
        return
    print(f"{len(scripts)} docs: {written} written, {skipped} up to date"
          + ("" if written or not a.force else "  (--force with nothing stale)")
          + "  -> testing/*.md")


if __name__ == "__main__":
    main()
