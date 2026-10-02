"""Does the cartridge guard actually refuse, and does it refuse BEFORE an emulator exists?

    python3 testing/test_cartridge_gate.py

The next job in this repo is replaying the verified 60,589-frame run
(`runs/gleeok_dragon/inputs.txt`, work-RAM sha1 575771d9...) against a *patched*
cartridge. Its md5 will not be the verified one. That is a legitimate thing to do and
it is exactly what went wrong once: journal 47, where an Automap Plus patch was left
sitting at the stock filename in `roms/`, 136,526 frames of "the verified run" were
replayed against it, and the bridge died at frame 98,204 reporting `EmuHawk exit
code 0` - which reads like an emulator fault, so an hour went into the emulator. The
one question that would have answered it in a second was "what is this ROM's md5".

So there are two guards, and this file pins both of them plus the escape hatch:

  * `emulator.unverified_rom_reason(rom)` - reports, does not refuse. Pure function
    over a path.
  * `replay.verify(...)` - refuses: raises SystemExit, before `BizHawk` is
    constructed at all.

The order is the whole point and is asserted, not assumed. `verify()` calls the reason
function and raises in the gate *before* the `with BizHawk(...)` line; a gate that
fired after the emulator had booted would leave the 136,526 frames replayed and the
`exit code 0` in the log, which is the journal-47 shape exactly. So `BizHawk` is
replaced throughout by a stub that raises `AssertionError("the emulator must not be
launched")` if anything constructs it, and every refusal test is only allowed to pass
because that stub was never reached.

Twelve checks:

   1. rom_md5 is the md5 of the file's bytes           7. the refusal prints to stderr and exits 1
   2. the verified cartridge is the one roms/ holds    8. the refusal names both md5s
   3. a matching cartridge is not reported              9. ZELDA_ALLOW_UNVERIFIED_ROM=1 lets it through
   4. a wrong cartridge names both md5s and says the  10. ...and that path returns normally (exit 0)
      number is meaningless                         11. expected_fp=None does NOT fire the gate (a hole)
   5. an unreadable path reports, it does not raise   12. the env var is read per call, not once
   6. a directory is unreadable too

WHAT IT DOES NOT CLAIM.

  * Nothing here runs an emulator, so nothing here proves a patched cartridge really
    does change the fingerprint. It proves the guard that is supposed to notice fires,
    fires early, and says which cartridge it is looking at. Whether the divergence
    then happens is what `testing/compare_roms.py` and the replay itself are for.
  * The stubbed `BizHawk` returns 2048 bytes of whatever the fake holds, so every
    "MATCH"/"MISMATCH" printed in checks 9-11 is about *which branch was taken*, not
    about a real run. `test_replay_fingerprint.py` is where the fingerprint itself is
    pinned down.
  * Check 11 pins a HOLE, not a feature. `expected_fp=None` skips the cartridge check
    entirely (`reason = ... if expected_fp is not None else None`), so a verify with no
    expected fingerprint will happily replay 60,589 frames against whatever is in
    `roms/` and say nothing at all - not even the `*** UNVERIFIED CARTRIDGE ***` banner
    in the log, which only exists because `BizHawk.__init__` raises it, and does not
    fire when `expected_fp` is None. That is deliberate in the code (there is nothing
    to compare against, so a fingerprint is not being asserted) and it is also a way
    to spend an hour. It is asserted here so that changing it is a deliberate act.
  * Check 10 pins behaviour that is arguably WRONG: with the escape hatch set,
    `verify` reports `MISMATCH` and returns normally, and a caller that only checks
    the exit status reads that as success. It is tested and documented rather than
    fixed, because fixing it is a production change - see the report.

This file needs the verified cartridge for checks 2 and 3 only. It ASSERTS that it is
there rather than skipping: a missing fixture is a finding, and a test that goes
quietly green without the one file its central claim depends on is how a guard ends up
believed and not exercised. `setup_linux.sh "<your dump>.nes"` puts it back.

WHAT IT NEEDS: nothing but Python and the cartridge. No display, no socket, no BizHawk.
"""

import os
import subprocess
import sys
from contextlib import contextmanager
from hashlib import md5 as _md5
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import replay
from zelda.emulator import ROM, ROM_NAME, VERIFIED_ROM_MD5, BizHawk, rom_md5, unverified_rom_reason

TMP = Path("/tmp/opencode/cartridge_gate")
TMP.mkdir(parents=True, exist_ok=True)


@contextmanager
def env(**kw):
    """Set env vars for the duration of one block and put them back exactly. The escape
    hatch is process-wide state; leaking `ZELDA_ALLOW_UNVERIFIED_ROM=1` into the rest of
    this file would quietly disable every other check that depends on it."""
    saved = {k: os.environ.get(k) for k in kw}
    try:
        for k, v in kw.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# -- fixtures: a cartridge that is not the verified one, and a fake emulator ------------

WRONG = TMP / "automap_plus.nes"          # journal 47's cartridge, by shape: right name,
WRONG.write_bytes(bytes(range(256)) * 512)   # wrong bytes, 131,072 of them
assert WRONG.exists()
# A three-frame input log. verify() reads it after the gate, so it has to exist for the
# checks where the gate is supposed to let the call through - but the emulator is fake,
# so these three frames never reach a machine.
INPUTS = TMP / "three_frames.inputs.txt"
INPUTS.write_text("# frames=3 valid_from_poweron=True\nStart\nA\n\n", encoding="utf-8")
wrong_md5 = rom_md5(WRONG)
assert wrong_md5 != VERIFIED_ROM_MD5, "the fixture accidentally IS the verified cartridge"

STUB_BUILT = []


def _no_emulator(*a, **kw):
    """Standing in for BizHawk. Constructing this at all is the failure this file is
    about: the gate must fire before an emulator exists, or the journal-47 hour happens
    with the gate's own blessing."""
    STUB_BUILT.append((a, kw))
    raise AssertionError("the emulator must not be launched")


STOCK_RAM = bytes((i * 7 + 3) & 0xFF for i in range(0x800))


class FakeEmu:
    """Enough of BizHawk for verify() to run to the end: a state, a step, a screenshot,
    and 2048 bytes of work RAM at $0000.

    The RAM it reports DEPENDS ON THE CARTRIDGE IT WAS HANDED, which is the whole point:
    a patched cartridge is a different machine, so it must produce a different work RAM
    and therefore a different sha1. A fake that returned the same 2048 bytes whatever it
    was given would make MISMATCH unreachable and checks 10 and 11 would be asserting
    nothing. Mixing the cartridge's own md5 into byte 0 makes the divergence explicit and
    keeps the other 2047 bytes readable in the output.
    """

    def __init__(self, rom=None, **kw):
        self.rom = Path(rom) if rom is not None else None
        self.kw = kw
        self.cmds = []
        self.steps = []
        mix = _md5(self.rom.read_bytes()).digest() if self.rom and self.rom.exists() \
            else bytes(16)
        self.ram_image = STOCK_RAM[:1] + mix[:15] + STOCK_RAM[16:] if self.ram_differs() \
            else STOCK_RAM

    def ram_differs(self) -> bool:
        """A cartridge that is not the verified one changes work RAM. So does one that
        cannot be read, so the third branch exists only for completeness."""
        return not (self.rom and self.rom.exists()
                    and rom_md5(self.rom) == VERIFIED_ROM_MD5)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cmd(self, line):
        self.cmds.append(line)
        return "ok"

    def state(self):
        return "f0 mode=00"

    def step(self, buttons=(), frames=1):
        self.steps.append((buttons, frames))
        return "f0 mode=00"

    def ram(self, addr, length=1):
        return self.ram_image[:length]

    def screenshot(self, name):
        self.shot = name
        return TMP / f"{name}.png"


REAL_BIZHAWK = replay.BizHawk


def allow_emulator():
    """Let verify() actually construct the fake. Only from check 9 on, where the point is
    what happens AFTER the gate has let the call through."""
    replay.BizHawk = FakeEmu
    return FakeEmu


def forbid_emulator():
    """Any construction at all is a failure. Checks 7 and 8 run under this, which is what
    makes "the gate fires before the emulator boots" an assertion rather than a hope: if
    the gate were moved below the `with BizHawk(...)`, this would raise."""
    STUB_BUILT.clear()
    replay.BizHawk = _no_emulator


def restore_emulator():
    replay.BizHawk = REAL_BIZHAWK


# =====================================================================================
forbid_emulator()   # default: constructing an emulator is a failure until a check says otherwise

# 1. rom_md5 is the md5 of the bytes on disk, not of some region of them.
# =====================================================================================
payload = b"the cartridge I did not swap" * 7
sample = TMP / "sample.bin"
sample.write_bytes(payload)
assert rom_md5(sample) == _md5(payload).hexdigest(), "rom_md5 is not hashing the file"
assert len(payload) == 28 * 7
print(f"rom_md5: md5 of {len(payload)} known bytes == {rom_md5(sample)}")

# =====================================================================================
# 2. The cartridge in roms/ is the one every number in this repo was measured on. If the
#    fixture is missing this errors - see WHAT IT DOES NOT CLAIM, the last paragraph.
# =====================================================================================
assert Path(ROM).exists(), (
    f"no cartridge at {ROM} (expected the No-Intro dump, {ROM_NAME}). Put it back with "
    f"setup_linux.sh before trusting anything in this file.")
got = rom_md5(Path(ROM))
assert got == VERIFIED_ROM_MD5, (
    f"the cartridge at {ROM} is md5 {got}, not {VERIFIED_ROM_MD5}. That is the journal-47 "
    f"state exactly: something patched or swapped the file under the stock name. Restore "
    f"roms/ from rom-backup/ before reading anything else this file prints.")
print(f"roms/ holds the verified cartridge: md5 {got} ({len(Path(ROM).read_bytes())} bytes)")

# =====================================================================================
# 3. The matching cartridge is not reported - no reason, no text, nothing.
# =====================================================================================
assert unverified_rom_reason(Path(ROM)) is None, unverified_rom_reason(Path(ROM))
print("unverified_rom_reason(verified cartridge) -> None")

# =====================================================================================
# 4. A wrong cartridge says three things: which md5 it got, which one was expected, and
#    that a number measured with it means nothing. Asserted on substrings, because the
#    whole message is prose and pinning it whole makes this test a rename detector.
# =====================================================================================
reason = unverified_rom_reason(WRONG)
assert isinstance(reason, str) and reason, reason
assert wrong_md5 in reason, reason
assert VERIFIED_ROM_MD5 in reason, reason
assert "different game" in reason, reason
print(f"unverified_rom_reason(wrong cartridge) -> names md5 {wrong_md5} and "
      f"{VERIFIED_ROM_MD5}, and calls it a different game")

# =====================================================================================
# 5. A path that does not exist reports rather than raising. This arm had no test, and it
#    is the one that turns "the cartridge is missing" into a sentence instead of a
#    traceback out of a verify nobody was watching.
# =====================================================================================
missing = TMP / "no_such_cartridge.nes"
assert not missing.exists()
why = unverified_rom_reason(missing)
assert isinstance(why, str), (
    f"a cartridge that is not there returned {why!r} instead of saying so. 'cannot be read' is "
    f"the only honest answer: the fingerprint cannot be checked against a file that is not "
    f"there, and None here means the caller reads it as 'verified'.")
assert "cannot be read" in why, why
assert str(missing) in why, why
print(f"unverified_rom_reason(missing path) -> {why!r}")

# =====================================================================================
# 6. A directory is unreadable in exactly the same way, and by the same arm.
# =====================================================================================
d = TMP / "not_a_rom"
d.mkdir(exist_ok=True)
dir_why = unverified_rom_reason(d)
assert isinstance(dir_why, str) and "cannot be read" in dir_why, dir_why
print("unverified_rom_reason(directory) -> 'cannot be read', same arm as a missing file")

# =====================================================================================
# 7. The refusal itself. verify() against a wrong cartridge, with a real expected
#    fingerprint, must raise SystemExit - and must not construct an emulator to do it.
# =====================================================================================
log = []
forbid_emulator()
try:
    replay.verify(INPUTS, "0" * 40, log=log.append, rom=WRONG)
except SystemExit as e:
    # `raise SystemExit(msg)` puts the message in .code; the interpreter turns a string
    # code into stderr + exit status 1, which check 8 proves by running it for real.
    assert isinstance(e.code, str), type(e.code)
    assert "refusing to verify against an unverified cartridge" in e.code, e.code
    refused = e.code
else:
    raise AssertionError(
        "verify() replayed against an unverified cartridge and returned normally. This is "
        "the journal-47 failure: 136,526 frames of 'the verified run' against a patched ROM, "
        "and the only symptom is a MISMATCH nobody reads.")
assert STUB_BUILT == [], f"the emulator was constructed before the refusal: {STUB_BUILT}"
assert log == [], f"the refusal logged a result before refusing: {log}"
print(f"verify(wrong cartridge) -> SystemExit before BizHawk, message {len(refused)} chars; "
      f"no emulator constructed, nothing logged")

# =====================================================================================
# 8. ...and that refusal reaches stderr with exit status 1, in a real child process. The
#    in-process check above sees the exception; this sees what a shell wrapper would see,
#    which is what run_until.sh and zelda.sh actually branch on.
# =====================================================================================
child = TMP / "child_refusal.py"
child.write_text(f'''
import sys
sys.path.insert(0, {str(ROOT)!r})
from zelda import replay
from zelda.emulator import BizHawk as Real


class Boom:
    def __init__(self, *a, **kw):
        raise SystemExit("the emulator was launched before the refusal")


replay.BizHawk = Boom
replay.verify({str(INPUTS)!r}, "0" * 40, log=lambda *a: None, rom={str(WRONG)!r})
print("CHILD REACHED THE END, which it must not")
''', encoding="utf-8")
p = subprocess.run([sys.executable, str(child)], capture_output=True, text=True, timeout=120)
assert p.returncode == 1, (p.returncode, p.stdout, p.stderr)
assert "CHILD REACHED THE END" not in p.stdout, p.stdout
assert "refusing to verify against an unverified cartridge" in p.stderr, p.stderr
assert wrong_md5 in p.stderr and VERIFIED_ROM_MD5 in p.stderr, p.stderr
assert "ZELDA_ALLOW_UNVERIFIED_ROM=1" in p.stderr, p.stderr      # it says how to proceed
assert p.stdout.strip() == "", f"the reason went to stdout as well as stderr: {p.stdout!r}"
print(f"child process: exit {p.returncode}, reason on stderr only ({len(p.stderr)} chars), "
      f"stdout empty")

# =====================================================================================
# 9. The matching branch: the same cartridge, the same call, no refusal - because
#    unverified_rom_reason says nothing about it. The fake emulator returns 2048 known
#    bytes, so MATCH is chosen by handing verify the fingerprint those bytes produce.
# =====================================================================================
from zelda.replay import fingerprint                                     # noqa: E402
allow_emulator()
# The fingerprint the verified cartridge produces under this fake: work RAM is the 2048
# known bytes un-mixed, because the cartridge IS the verified one.
EXPECTED = fingerprint(FakeEmu(rom=Path(ROM)))                            # type: ignore[arg-type]
assert EXPECTED != fingerprint(FakeEmu(rom=WRONG)), (                    # type: ignore[arg-type]
    "the fake hands out the same work RAM for both cartridges, so MISMATCH is unreachable "
    "and checks 10 and 11 assert nothing")
log = []
s, fp = replay.verify(INPUTS, EXPECTED, log=log.append, rom=Path(ROM))
assert fp == EXPECTED, (fp, EXPECTED)
assert any("MATCH" in l for l in log) and not any("MISMATCH" in l for l in log), log
print(f"verify(verified cartridge) -> ran, ram sha1 {fp[:12]}..., MATCH")

# =====================================================================================
# 10. The escape hatch. ZELDA_ALLOW_UNVERIFIED_ROM=1 does what the docstring says - it is
#     for working out WHY a patch diverges - and then verify prints MISMATCH and RETURNS
#     NORMALLY. There is no exception, no exit code, nothing a caller can branch on. In a
#     shell that is exit 0: "the verification succeeded". Pinned here so that changing it
#     is deliberate; it is reported as a production finding rather than fixed here.
# =====================================================================================
log = []
try:
    with env(ZELDA_ALLOW_UNVERIFIED_ROM="1"):
        s, fp = replay.verify(INPUTS, EXPECTED, log=log.append, rom=WRONG)
except SystemExit as e:
    raise AssertionError(
        f"ZELDA_ALLOW_UNVERIFIED_ROM=1 did not open the gate: {e}") from None
assert any("MISMATCH" in l for l in log), log
assert fp != EXPECTED, "the fake returned stock bytes, so MISMATCH here is the fake's doing"
assert len(log) == 2, log
print("verify(wrong cartridge, ZELDA_ALLOW_UNVERIFIED_ROM=1) -> MISMATCH printed, returned "
      f"normally ({len(log)} log lines, no exception): exit 0 to any caller")

# =====================================================================================
# 11. The hole. expected_fp=None means there is nothing to compare, so the cartridge is
#     not checked either - and no MATCH/MISMATCH line is printed, so there is no output at
#     all about which cartridge the frames were played on. Asserted as it is.
# =====================================================================================
log = []
try:
    s, fp = replay.verify(INPUTS, None, log=log.append, rom=WRONG)
except SystemExit as e:
    raise AssertionError(
        f"the cartridge gate fired even with expected_fp=None: {e}") from None
assert not any("MISMATCH" in l for l in log), log
assert not any("refusing" in l for l in log), log
assert "MISMATCH" not in "".join(log), log
print(f"verify(expected_fp=None) on the wrong cartridge -> no gate, no warning, "
      f"{len(log)} log line(s): {log[0][:46]!r}...")

# =====================================================================================
# 12. The escape hatch is read per call, not cached at import. Same process, same
#     function, env var on then off.
# =====================================================================================
log = []
try:
    with env(ZELDA_ALLOW_UNVERIFIED_ROM="1"):
        replay.verify(INPUTS, EXPECTED, log=log.append, rom=WRONG)
except SystemExit as e:
    raise AssertionError(
        f"the escape hatch was set for this call and the gate still refused: {e}") from None
log2 = []
try:
    replay.verify(INPUTS, EXPECTED, log=log2.append, rom=WRONG)
except SystemExit:
    pass
else:
    raise AssertionError("ZELDA_ALLOW_UNVERIFIED_ROM was read once at import and never "
                         "again, so the escape hatch cannot be taken back in one process")
# ...and it is gone from the environment afterwards, which is what makes check 7 mean
# something at all.
assert "ZELDA_ALLOW_UNVERIFIED_ROM" not in os.environ, os.environ.get("ZELDA_ALLOW_UNVERIFIED_ROM")
print("ZELDA_ALLOW_UNVERIFIED_ROM is honoured per call and left no residue in os.environ")

restore_emulator()
print("all checks passed")