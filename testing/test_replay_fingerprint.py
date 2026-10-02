"""Which bytes make the fingerprint, and which lines make the frame count?

    python3 testing/test_replay_fingerprint.py

Two small functions carry the entire evidence that a run is reproducible, and both are
load-bearing for the next job in this repo: replaying `runs/gleeok_dragon/inputs.txt`
(60,589 frames, work-RAM sha1 575771d9bd7ca936b157d6c6f5d9ae43aa5e9331) against a
patched cartridge.

  * `fingerprint(emu)` is sha1 over work RAM $0000-$07FF. Nothing else. That range and
    that algorithm are not incidental - every fingerprint in the repo was computed that
    way, `runs/gleeok_dragon/VERIFICATION.txt` records one, and
    `skills/oc-emulator-run-fidelity/SKILL.md` and `testing/compare_roms.py` both
    reason about it. If it starts hashing $0000-$0FFF, or switches to sha256, then
    575771d9... stops being a claim about anything: the same run would produce a
    different number and every recorded MATCH would be a coincidence that never repeats.
    So the range and the algorithm are asserted here against an independently computed
    digest, and the fake emulator records exactly which addresses were asked for.

  * `load_inputs(path)` splits non-comment lines into frame tuples, and `fingerprint`
    is only ever called with `expected_fp` supplied by hand - which is why the count of
    lines matters as much as the digest. `load_inputs` DISCARDS the `#` header entirely.
    The header `# frames=60589 valid_from_poweron=True` is write-only prose: nothing
    parses it, nothing compares it to the body, nothing notices a file that says 60,589
    and holds 10. That is audit finding #5, and it is journal 47 one layer down: replay
    a truncated `inputs.txt`, get a MISMATCH on the fingerprint, and read it as "the
    patched ROM changed the game" - when what changed is the number of frames fed in.
    This file pins the hole rather than closing it, because closing it is a production
    change (see WHAT IT DOES NOT CLAIM).

Nine checks:

   1. the digest is sha1 of exactly the 2048 bytes returned
   2. ...and not md5 or sha256 of the same bytes, so a silent algorithm swap fails here
   3. the fake is asked for $0000..$07FF and nothing else, exactly once
   4. one flipped bit in work RAM changes the digest (a fingerprint of nothing at all
      would pass checks 1-3)
   5. a header claiming 999 frames over a 10-line body loads as 10 frames
   6. the same holds with a header claiming 3 - the loader does not even look
   7. comment lines are dropped wherever they are, mid-body included
   8. a BLANK line is a frame of no buttons, not a skipped line - the run logs are full
      of them and dropping them would shorten every replay
   9. the real 60,589-frame run file loads as 60,589 frames, and its header agrees -
      checked HERE, in the test, because the loader does not

WHAT IT DOES NOT CLAIM.

  * No emulator runs and no frame is stepped. `run_inputs()` is not exercised: the claim
    is about which bytes get hashed and which lines get counted, not about how the
    frames are delivered. A test of a copy of `fingerprint` would prove nothing, so this
    one calls the real one, through a fake whose `.ram()` records what it was asked.
  * The header is not validated, and this file deliberately does not add that validation
    to the test's own contract - checks 5 and 6 assert the CURRENT behaviour, that a
    lying header is ignored. If someone makes `load_inputs` check the header, checks 5
    and 6 will fail and that is the correct outcome: it would be a behaviour change and
    it would need its own gate, exactly as the profile's refusal does.
  * The fake emulator is not a `BizHawk`. `fingerprint` takes an object with one method,
    so a stub is enough; `test_cartridge_gate.py` is where the emulator class itself is
    stood in for.
  * Nothing here proves a replay is deterministic. It proves the number is computed from
    a stated range with a stated algorithm, which is a precondition for determinism and
    not a substitute for it.

WHAT IT NEEDS: Python, and `runs/gleeok_dragon/inputs.txt` for check 9 only. No display,
no socket, no BizHawk.

Run:  python3 testing/test_replay_fingerprint.py
"""

import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda.replay import fingerprint, load_inputs

TMP = Path("/tmp/opencode/replay_fingerprint")
TMP.mkdir(parents=True, exist_ok=True)

# 2048 bytes of known work RAM: not zeros (a fingerprint of a page of zeroes would pass a
# test that only checked "it hashed 0x800 bytes") and not random (so the digest is
# reproducible from this file's own text).
WORK_RAM = bytes(((i * 37 + 11) ^ (i >> 3)) & 0xFF for i in range(0x800))
# A wider image, so that asking for a LARGER range than $0000-$07FF returns something
# different rather than an IndexError - the digest then fails check 1 instead of the
# fake blowing up, and the recorded call fails check 3 with a readable address.
WIDER = WORK_RAM + bytes((i * 91 + 5) & 0xFF for i in range(0x1800))


class RecordingEmu:
    """Records every `.ram(addr, length)` it is asked for and serves from a fixed image."""

    def __init__(self, image=WIDER):
        self.image = image
        self.calls = []

    def ram(self, addr, length=1):
        self.calls.append((addr, length))
        if addr + length > len(self.image):
            raise AssertionError(
                f"fingerprint asked for ${addr:04X}+{length} which is past the end of the "
                f"{len(self.image)}-byte image this fake holds")
        return self.image[addr:addr + length]


# =====================================================================================
# 1. The digest is sha1 of exactly the 2048 bytes at $0000, computed here independently.
# =====================================================================================
emu = RecordingEmu()
got = fingerprint(emu)                     # type: ignore[arg-type]
want = hashlib.sha1(WORK_RAM).hexdigest()
assert got == want, (
    f"fingerprint is {got}, sha1 of work RAM $0000-$07FF is {want}. Every fingerprint in "
    f"this repo - including 575771d9bd7ca936b157d6c6f5d9ae43aa5e9331 in "
    f"runs/gleeok_dragon/VERIFICATION.txt - was computed over that range with that "
    f"algorithm; a different answer here makes all of them unfalsifiable.")
assert len(got) == 40, got
print(f"fingerprint: {got} == sha1(work RAM $0000-$07FF, {len(WORK_RAM)} bytes)")

# =====================================================================================
# 2. ...and it is not some other hash of the same bytes, so a swap to md5 or sha256 fails
#    here rather than showing up as a MISMATCH on a 16-hour replay.
# =====================================================================================
assert got != hashlib.md5(WORK_RAM).hexdigest(), "fingerprint is md5, not sha1"
assert got != hashlib.sha256(WORK_RAM).hexdigest(), "fingerprint is sha256, not sha1"
assert got != hashlib.sha1(WIDER).hexdigest(), "fingerprint is hashing past $07FF"
assert got != hashlib.sha1(WORK_RAM[:0x700]).hexdigest(), "fingerprint stopped short of $07FF"
print(f"fingerprint: differs from md5 ({hashlib.md5(WORK_RAM).hexdigest()[:12]}...), "
      f"sha256 and every other length - the algorithm is pinned, not merely 'a hash'")

# =====================================================================================
# 3. The fake was asked for $0000..$07FF, once, and for nothing else. Both halves matter:
#    the range says which memory the claim covers, and the "once" says the digest is of
#    that range rather than of an accumulation of reads.
# =====================================================================================
assert emu.calls == [(0x0000, 0x800)], (
    f"fingerprint asked for {[(hex(a), hex(n)) for a, n in emu.calls]}, not exactly "
    f"[(0x0000, 0x800)]")
print(f"fingerprint: asked the emulator for {[(f'${a:04X}', f'{n} bytes') for a, n in emu.calls]}"
      f" and nothing else")

# =====================================================================================
# 4. One bit of work RAM changes the digest - so check 1 is not the digest of nothing.
# =====================================================================================
flipped = bytearray(WORK_RAM)
flipped[0x0668] ^= 0x01        # $0668 is the byte journal 47 went looking for
_alt_emu = RecordingEmu(bytes(flipped) + WIDER[len(WORK_RAM):])
alt = fingerprint(_alt_emu)          # type: ignore[arg-type]
assert alt != got, (alt, got)
print(f"fingerprint: one bit flipped at $0668 -> {alt[:12]}... instead of {got[:12]}...")

# =====================================================================================
# 5. A header that lies about the frame count is ignored. `frames=999` over a 10-line
#    body loads as 10 frames, silently, with no warning and no attribute anyone can read.
# =====================================================================================
lying = TMP / "lying_header.inputs.txt"
lying.write_text("# frames=999 valid_from_poweron=True\n"
                 + "".join("A\n" if i % 2 else "\n" for i in range(10)), encoding="utf-8")
frames = load_inputs(lying)
assert len(frames) == 10, (
    f"a header saying 999 frames over a 10-line body loaded as {len(frames)} frames. The "
    f"header is not parsed by load_inputs, so this can only change by someone adding "
    f"validation - which is a behaviour change, not a bug fix to slip in here.")
assert "999" not in str(frames), frames[:3]
print(f"load_inputs: header says frames=999, body has 10 lines -> {len(frames)} frames, "
      f"header ignored, no warning")

# =====================================================================================
# 6. The same with a header that understates: 3 frames claimed, 10 present, 10 loaded.
#    Together with check 5 this says the loader does not so much as open the header -
#    it is not that a large count is trusted or that a small one is rejected.
# =====================================================================================
under = TMP / "understated_header.inputs.txt"
under.write_text("# frames=3 valid_from_poweron=False\n" + "\n" * 10, encoding="utf-8")
assert len(load_inputs(under)) == 10, len(load_inputs(under))
print("load_inputs: header says frames=3 over 10 blank lines -> 10 frames, header ignored")

# =====================================================================================
# 7. Comment lines go wherever they are, mid-body included, and the count is of the rest.
# =====================================================================================
comments = TMP / "comments.inputs.txt"
comments.write_text("# frames=4\n"
                    "Start\n"
                    "# a note somebody left mid-file\n"
                    "A\n"
                    "B\n"
                    "# another\n", encoding="utf-8")
cf = load_inputs(comments)
assert cf == [("Start",), ("A",), ("B",)], cf
print(f"load_inputs: 3 comments anywhere in 6 lines -> {len(cf)} frames {cf}")

# =====================================================================================
# 8. A blank line is a frame of NO BUTTONS, not a skipped line. This is the one that
#    would quietly shorten a replay: `''.split(',')` filters to nothing, and the tuple
#    that is left is an empty tuple - one frame, no input. The run logs are full of them.
# =====================================================================================
blanks = TMP / "blanks.inputs.txt"
blanks.write_text("Start\n\n\nA\n", encoding="utf-8")
bf = load_inputs(blanks)
assert bf == [("Start",), (), (), ("A",)], bf
assert len(bf) == 4, bf
assert bf[1] == () and not bf[1], bf[1]
# a line of nothing but separators is the same thing, not a frame of empty button names
commas = TMP / "commas.inputs.txt"
commas.write_text(",,\nA,,\n", encoding="utf-8")
assert load_inputs(commas) == [(), ("A",)], load_inputs(commas)
print(f"load_inputs: 4 lines including 2 blank -> {len(bf)} frames; blank is (), and "
      f"'A,,' is ('A',) - empty button names are dropped, the frame is not")

# =====================================================================================
# 9. The real run. 60,589 frames load as 60,589, and its header says so - checked HERE,
#    because the loader does not. This is the one place the header is compared to the
#    body, and it is deliberately in the test rather than in production code.
# =====================================================================================
real = ROOT / "runs" / "gleeok_dragon" / "inputs.txt"
assert real.exists(), f"no recorded run at {real}, and check 9 is the only one that needs it"
assert real.read_text(encoding="utf-8").startswith("# frames=60589 valid_from_poweron=True")
rf = load_inputs(real)
assert len(rf) == 60589, len(rf)
header_n = int(real.read_text(encoding="utf-8").splitlines()[0].split("=")[1].split()[0])
assert header_n == len(rf), (header_n, len(rf))
# the sha1 this run must end on, for the record. Not asserted against a live machine -
# there is none here - but named so that a test reading this knows what it is protecting.
assert "575771d9bd7ca936b157d6c6f5d9ae43aa5e9331" in \
    (real.parent / "VERIFICATION.txt").read_text(encoding="utf-8")
print(f"runs/gleeok_dragon/inputs.txt: header {header_n} == {len(rf)} loaded frames, and "
      f"VERIFICATION.txt carries 575771d9... - checked here, not by the loader")

print("all checks passed")