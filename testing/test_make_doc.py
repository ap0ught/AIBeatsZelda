"""The doc generator must describe what scripts DO, and must not police files git has not taken.

make_doc.py renders every testing/*.md from the script it belongs to: the module docstring verbatim,
then what the script writes, whether it drives the emulator, which savestates it loads, which
production comments cite it, and its neighbours. Two of those were asked of the SOURCE TEXT rather
than of the program, and both produced false claims at scale:

1. "drives BizHawk" fired on the WORD. `re.search(r"\bBizHawk\b|...", src)` cannot tell a script that
   constructs `BizHawk(...)` from a docstring that mentions the name while explaining that the script
   needs no emulator at all. 129 scripts were labelled as driving BizHawk; 117 of them do. Seven
   committed docs carried the claim about themselves.

2. "writes logs/, runs/, shots/" fired on any mention of those paths. Most scripts in testing/ open
   with

       _os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative

   so 196 of them were documented as writing all three directories when the honest answer for most was
   that they write nothing at all. The claim also ran the other way: `Path("runs/run6/inputs.txt")` is
   where an input CAME FROM, and it was reported as a write.

And the gate itself was a global lock with no owner. --check walked testing/*.py on disk, so on a
machine where several people work at once, any agent with a half-written script on disk failed every
other agent's commit with "MISSING <stem>.md" until somebody generated a doc for a file that was not
supposed to be committed yet. It now asks git which scripts are real - staged counts as tracked, so
`git add script.py` without its doc still fails the check, which is the case the gate exists for.

WHAT THIS CHECKS, all four of them against the real generator rather than a copy of its logic:
  * an untracked script is not drift; the same script staged is
  * a doc whose script is gone is an orphan and IS drift (journal 48 had 182 of them)
  * a script that only MENTIONS BizHawk is not labelled as driving it, and one that constructs it is
  * a path passed to a non-writing call is a read, and a path passed to a writing call is a write

Run it:  python3 testing/test_make_doc.py
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)          # testing/ and git/ are relative

_spec = importlib.util.spec_from_file_location("make_doc", str(_ROOT / "testing" / "make_doc.py"))
assert _spec and _spec.loader
make_doc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_doc)


def info(name: str, body: str) -> dict:
    return make_doc.analyse(body, name, make_doc.parse(body))


# 1. The word is not a use. A script that explains the emulator in its docstring and never touches it
#    is not a driver; a script that constructs BizHawk is, and the distinction is the whole point.
prose = '"""Why this is not like probe_walls: it never opens BizHawk, it only reads RAM."""\nprint(1)\n'
assert info("t.py", prose)["drives"] is False, "a mention in prose must not claim an emulator"
assert info("t.py", "from zelda.emulator import BizHawk\nemu = BizHawk()\n")["drives"] is True
# a CALL, not an import: a script that imports a driver without calling it is not one, and a false
# negative in this direction is a missing claim rather than a false one
assert info("t.py", "import random_search\n")["drives"] is False
assert info("t.py", "import random_search\nrandom_search(emu, s)\n")["drives"] is True
assert info("t.py", "import zelda.replay\nreplay.verify(path)\n")["drives"] is True

# 2. The chdir comment does not make a script a writer, and a read is not a write.
chdir_boilerplate = (
    '_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative\n'
    'def main():\n    print(main())\n'
)
assert info("t.py", chdir_boilerplate)["writes"] == [], "the chdir comment claimed three writes"
assert info("t.py", 'p = Path("runs/run6/inputs.txt")\n')["writes"] == [], "a read is not a write"
assert [k for k, _ in info("t.py", 'Path("shots/x.png").write_text("hi")\n')["writes"]] == ["shots/"]
# the harness's own writers take a NAME, not a path, so the call is the only evidence there is
assert [k for k, _ in info("t.py", "emu.screenshot('frame')\n")["writes"]] == ["shots/"]
assert [k for k, _ in info("t.py", "emu.save('probe_x')\n")["writes"]] == ["states/"]
assert [k for k, _ in info("t.py", "emu.save_inputs('r')\n")["writes"]] == ["logs/"]

# 3. A script that does not parse is described as little as possible rather than crashing the render.
assert make_doc.analyse("def (:\n", "broken.py", None)["drives"] is False

# 4. The gate's scope is git's, not the disk's - and that is the fix, asserted by running it.
tracked = make_doc.tracked_scripts()
assert tracked, "git should know about testing/*.py in this repo"
assert "make_doc.py" in tracked, "the generator itself must be tracked"
on_disk = {p.name for p in Path("testing").glob("*.py")}
stray = on_disk - tracked
assert stray, ("this test is only meaningful while some script on disk is untracked; if the tree is "
               "clean, skip rather than assert nothing")

# an untracked script with no doc: not drift
with tempfile.TemporaryDirectory() as td:
    scratch = Path("testing") / "test_zz_make_doc_scratch.py"
    doc = Path("testing") / "test_zz_make_doc_scratch.md"
    scratch.write_text('"""Scratch, untracked, no doc."""\nprint(1)\n')
    try:
        out = subprocess.run([sys.executable, "testing/make_doc.py", "--check"],
                             capture_output=True, text=True).stdout
        # not "the gate passes" - other drift may exist and is somebody else's business - but this
        # file is never named, whatever else is wrong
        drift_lines = [l for l in out.splitlines() if l.startswith(("MISSING", "STALE", "ORPHAN"))]
        assert not any("test_zz_make_doc_scratch" in l for l in drift_lines), out
        assert "not tracked by git" in out, out     # and it is reported as skipped, not silently dropped
        assert scratch.name not in make_doc.tracked_scripts()
        # and it is never rendered, so nobody inherits a doc for a file that is not being committed
        assert not doc.exists()
        # the same file, STAGED, is drift - that is the case the gate is for
        subprocess.run(["git", "add", str(scratch)], capture_output=True)
        try:
            assert scratch.name in make_doc.tracked_scripts()
            out = subprocess.run([sys.executable, "testing/make_doc.py", "--check"],
                                 capture_output=True, text=True)
            assert out.returncode == 1, "a staged script with no doc must fail the gate"
            assert "MISSING" in out.stdout, out.stdout
        finally:
            subprocess.run(["git", "rm", "--cached", "-q", str(scratch)], capture_output=True)
    finally:
        scratch.unlink(missing_ok=True)
        doc.unlink(missing_ok=True)

# 5. An orphan - a committed doc whose script is gone - is drift, which is journal 48's failure class.
with tempfile.TemporaryDirectory() as td:
    orphan = Path("testing") / "probe_zz_make_doc_orphan.md"
    body = make_doc.render("probe_zz_make_doc_orphan.py", info("probe_zz_make_doc_orphan.py", ""), [], [], "")
    orphan.write_text(body)
    subprocess.run(["git", "add", str(orphan)], capture_output=True)
    try:
        assert "probe_zz_make_doc_orphan.md" in make_doc.tracked_orphans(make_doc.tracked_scripts()), \
            "a committed doc with no script beside it must be reported as an orphan"
    finally:
        subprocess.run(["git", "rm", "--cached", "-q", str(orphan)], capture_output=True)
        orphan.unlink(missing_ok=True)

# 6. A hand-written README in testing/ is not an orphan. It has no script and never will.
assert "README.md" not in make_doc.tracked_orphans(make_doc.tracked_scripts()), \
    "testing/README.md is hand-written; it must not be reported as a generated orphan"

# 7. The generator's own path table is not a declaration that it writes those paths.
assert make_doc.analyse(Path("testing/make_doc.py").read_text(), "make_doc.py",
                        make_doc.parse(Path("testing/make_doc.py").read_text()))["writes"] == [], \
    "make_doc.py holds the path prefixes as data; it must not claim to write them"

print("all checks passed")