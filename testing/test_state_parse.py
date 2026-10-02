"""Every number in this repository arrives through `State.parse`, and this is the only place it can
be checked without BizHawk.

`zelda/emulator.py:196-212` builds every state object in the project. `search.value_of` prices an
attempt from `a.hearts`; `runner.HEART_FLOOR` gates a search on the heart floor; the
`_flag_for_improvement` ledger records the hearts a segment ended at; and every `hp=` line in every
VERIFICATION.txt and every replay fingerprint line in `runs/` is `str(State)`, which renders hearts
and containers and nothing else. A regression in these seventeen lines moves all of them at once,
and it moves them SILENTLY - a heart that reads one too low is not a crash, it is a run that is
1,800 frames per half-heart poorer than it should be and no line anywhere says so.

There is also a second thing here, which is a bug the project already paid for. `BadReply`
(`emulator.py:76-93`) records that a garbled reply reached `State.parse`, which does `int(v)` on the
right of every `k=v` token, so a token with no `=` raised `ValueError: invalid literal for int()
with base 10: ''` - a message naming neither the command nor the emulator nor the reply, measured at
12 attempts in 590 over a four-hour log. The fix was NOT to make `parse` more careful; it was a
guard in front of it (`_is_state_line`) so the failure arrives as something readable. Both halves of
that are tested here, because the guard is only worth having if it catches exactly what `parse`
would have choked on.

Eleven checks, each printing the number or the string it established:

  1. hearts: three branches, both boundaries, eight values    7. a short line parses to defaults
  2. containers is the high nybble plus one                   8. a mid-token truncation raises
  3. hearts and containers come out of ONE byte                ValueError, and the guard catches it
  4. all 22 fields land where they should                    9. `str()` renders `hp=4.0/5`, which is
  5. an unknown key stays in `raw` and off the object            the format every VERIFICATION.txt
  6. a duplicated key takes the LAST value                       line is written in
                                                             10. the guard accepts a traced step
  (and 11: the guard is per-command, and `ram` wants hex)

WHAT IT DOES NOT CLAIM.

* **Nothing here reads a RAM byte.** These are the parser and the two arithmetic properties built on
  it. Whether `$066F` really packs hearts that way is the claim of `zelda/ram.py:14` and the
  observation behind it; this file only checks that the code implements the claim the docstring
  makes, boundary by boundary. A wrong encoding is not a parse bug and would not be caught.

* **`hearts` is not clamped, and does not need to be.** `hp=$0F` with `hpfrac=$FF` reads 16.0 out of
  1 container. The cartridge cannot set that - the fraction fills the *next* heart and stops - so
  the arithmetic is deliberately unclamped, and check 1 pins that it is unclamped rather than
  pretending otherwise. A clamping change would be a behaviour change, not a fix.

* **The guard is coarse on purpose, so it accepts some replies it should not.** `_is_state_line`
  checks that *every* token is `name=digits`; a reply truncated cleanly at a token boundary is a
  valid-looking prefix of a state line and passes. Check 8 pins that honestly rather than claiming
  the guard catches truncation generally - it catches truncation *mid-token*, which is the case
  `BadReply`'s docstring describes, and check 8's fixture is that exact case.

* **`_reply_answers` is not the bridge's contract.** Checks 10 and 11 pin two shapes it is
  deliberately slack about (a traced multi-frame `step`, and anything not `state`/`step`/`ram`),
  because `_reply_answers` returns True for everything else rather than guessing: "a check that is
  wrong in the strict direction costs a whole emulator" (`emulator.py:118-124`).

* **No socket, no emulator, no ROM.** `BizHawk.__init__` is never reached; the only thing borrowed
  from the real class is `cmd`, which `testing/test_search_machinery.py` check 10 already covers
  with a fake wire.

Run:  python3 testing/test_state_parse.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import drops, ram
from zelda.emulator import State, _is_state_line, _reply_answers

# A real reply, in the order bridge.lua's state_str() emits it (bridge.lua:262-279): frame, then
# FIELDS in order, then bhp, bmax, lag. EVERY value is a decimal `read_u8` concatenated straight to
# the name - `parse` does int(v), so a hex digit here is a ValueError, which check 8 pins.
# Written longhand so the test says what the bridge says rather than comparing the parser to itself.
LINE = ("frame=98204 mode=5 sub=0 level=4 room=19 x=120 y=141 dir=8 hp=67 hpfrac=0 rupees=48 "
        "keys=1 bombs=7 sword=2 bitem=1 triforce=5 paused=0 scroll=0 retroom=0 anim=15 "
        "kills=42 bhp=6 bmax=10 lag=10947")
FIELDS = ("frame", "mode", "sub", "level", "room", "x", "y", "dir", "hp", "hpfrac", "rupees",
          "keys", "bombs", "sword", "bitem", "triforce", "paused", "scroll", "retroom", "anim",
          "kills", "lag")
assert len(FIELDS) == 22 and len(set(FIELDS)) == 22, len(FIELDS)

# ------------------------------------------------------------------ 1. hearts: three branches
#
# `hpfrac` is one of three things and the boundaries are what matters: $00 empty, $01-$7F a half
# heart, $80-$FF full (ram.py:15). The two boundaries are where an off-by-one hides, so both are
# named explicitly rather than folded into a loop over a range.
full = (0, 0x00, 0.0), (1, 0x00, 1.0), (3, 0x00, 3.0), (0x0F, 0x00, 15.0), (4, 0x00, 4.0)
half = (3, 0x01, 3.5), (3, 0x7F, 3.5), (0, 0x7F, 0.5), (0x0F, 0x40, 15.5)
whole = (3, 0x80, 4.0), (3, 0xFF, 4.0), (0, 0x80, 1.0), (0x0F, 0x80, 16.0)
for hp, frac, want in full:
    assert State(hp=hp, hpfrac=frac).hearts == want, (hex(hp), hex(frac), want)
for hp, frac, want in half:
    assert State(hp=hp, hpfrac=frac).hearts == want, (hex(hp), hex(frac), want)
for hp, frac, want in whole:
    assert State(hp=hp, hpfrac=frac).hearts == want, (hex(hp), hex(frac), want)
# the boundaries, named: $7F is half and $80 is full. Getting these backwards costs a half heart on
# every state read, which at HEART_VALUE 1800 is a frame count nobody would find.
assert State(hp=0, hpfrac=0x7F).hearts == 0.5 and State(hp=0, hpfrac=0x80).hearts == 1.0
assert State(hp=0, hpfrac=0x00).hearts == 0.0 and State(hp=0, hpfrac=0x01).hearts == 0.5
# ...and it is a float even when it is whole, because every consumer does float arithmetic on it
assert isinstance(State(hp=0x03, hpfrac=0x00).hearts, float), "an int here breaks value_of's tiers"
assert State(hp=0x03, hpfrac=0x00).hearts == 3.0, "3, not 3.0, prints as `hp=3` in a VERIFICATION line"
print(f"hearts: {len(full)} whole, {len(half)} half, {len(whole)} full-heart fraction; "
      f"$7F->0.5 $80->1.0, and $03/$00 reads 3.0 (a float, always)")

# ------------------------------------------------------------------ 2. containers
#
# The high nybble of the same byte is containers MINUS ONE (ram.py:14, ram.py:67). The +1 is the
# whole of it: `$066F = $40` is four containers, not five and not zero.
for hp, want in ((0x00, 1), (0x03, 1), (0x0F, 1), (0x10, 2), (0x13, 2), (0x23, 3), (0x4F, 5),
                 (0xC3, 13)):
    assert State(hp=hp).containers == want, (hex(hp), State(hp=hp).containers, want)
assert State(hp=0x4F).containers == 5 and State(hp=0x4F).hearts == 15.0, \
    "$4F is 15 hearts in 5 containers - a byte the cartridge can reach mid-bar but never over"
print("containers: (hp >> 4) + 1, so $00->1 through $C3->13; $4F gives 5 containers")

# ------------------------------------------------------------------ 3. one byte, two fields
#
# `hearts` and `containers` are the two halves of `$066F`, so they cannot disagree about which byte
# they came from. Walking all 256 values of that byte and checking the two are consistent is the
# version of this that would notice a future refactor moving one of them to a different byte.
bad = []
for hp in range(256):
    s = State(hp=hp, hpfrac=0x80)
    expect = (hp & 0x0F) + 1.0
    if s.hearts != expect or s.containers != (hp >> 4) + 1:
        bad.append((hex(hp), s.hearts, s.containers))
    # the low nybble must not leak into the container count and vice versa
    if s.containers < 1 or s.containers > 16:
        bad.append((hex(hp), "containers out of range", s.containers))
assert not bad, bad[:4]
assert State(hp=0xFF, hpfrac=0x00).containers == 16, "the high nybble is 0-15, so 1-16 containers"
# Full health is `hearts >= containers` (lookahead.py:290-291), which the sword beam is gated on
# (`Fighter._beam_ready`). With no fraction in $0670 the bar is exactly full when the low nybble is
# one more than the high one, and there are 15 such byte values: $01, $12, $23, ... $EF.
just_full = [hp for hp in range(256) if State(hp=hp).hearts == State(hp=hp).containers]
assert just_full == [0x01, 0x12, 0x23, 0x34, 0x45, 0x56, 0x67, 0x78, 0x89, 0x9A, 0xAB, 0xBC,
                     0xCD, 0xDE, 0xEF], [hex(hp) for hp in just_full]
assert State(hp=0x45).hearts == 5.0 and State(hp=0x45).containers == 5, "the archived `hp=5.0/5`"
assert State(hp=0x4F).hearts == 15.0 and State(hp=0x4F).containers == 5, "over-full is not a state"
print(f"all 256 values of $066F agree between hearts and containers; exactly {len(just_full)} of them "
      f"mean a bar that is full with no fraction in $0670 - $01, $12, ... $EF - which is the beam's gate")

# ------------------------------------------------------------------ 4. every field lands
s = State.parse(LINE)
want = dict(frame=98204, mode=5, sub=0, level=4, room=19, x=120, y=141, dir=8, hp=67,
            hpfrac=0, rupees=48, keys=1, bombs=7, sword=2, bitem=1, triforce=5, paused=0,
            scroll=0, retroom=0, anim=15, kills=42, lag=10947)
assert len(want) == len(FIELDS) == 22, (len(want), len(FIELDS))
for k, v in want.items():
    assert getattr(s, k) == v, (k, getattr(s, k), v)
    assert type(getattr(s, k)) is int, f"{k} is {type(getattr(s, k)).__name__}, not int"
assert set(State.__dataclass_fields__) == set(FIELDS) | {"raw"}, sorted(
    set(State.__dataclass_fields__) - set(FIELDS) - {"raw"})
assert set(s.raw) == set(FIELDS) | {"bhp", "bmax"}, sorted(set(s.raw) - set(FIELDS))
assert len(LINE.split()) == 24, "the bridge emits 24 tokens; 22 of them are fields"
assert s.hearts == 3.0 and s.containers == 5, (s.hearts, s.containers)
assert "level" in State.__dataclass_fields__ and not hasattr(s, "mode_"), "the names are the bridge's"
# `kills` reads $50, which is the KILL STREAK - drops.py calls it STREAK and a hit on Link resets it.
# So `s.kills` is not a tally and reading it as one is a mistake worth naming here.
assert ram.KILL_TALLY == drops.STREAK == 0x50 and s.kills == 42
print(f"{len(FIELDS)} fields parsed and all int; hp=$43 -> {s.hearts} hearts / {s.containers} "
      f"containers; bhp/bmax (the boss HP the trace needs) land in raw only; `kills` is $50, the "
      f"STREAK drops.py names, not a total")

# ------------------------------------------------------------------ 5. an unknown key
#
# A key the dataclass has no field for is kept in `raw` and NOT set on the object. That is the
# behaviour that lets bridge.lua gain a field without breaking this parse - and the trap beside it,
# which is that a MISSPELLED key is also silently dropped. `raw` is the only place either shows up.
u = State.parse(LINE + " boss_hp=10 lagcount=3")
assert u.raw["boss_hp"] == 10 and u.raw["lagcount"] == 3, u.raw
assert not hasattr(u, "boss_hp") and not hasattr(u, "lagcount"), "an unknown key became an attribute"
assert u.lag == 10947, "a second 'lag'-shaped key must not overwrite the real field"
typo = State.parse(LINE.replace("bitem=", "b_item="))
assert "b_item" in typo.raw and not hasattr(typo, "b_item"), "a misspelt key vanishes silently"
assert typo.bitem == 0, "the default, with no warning anywhere - this is what raw is for"
assert not hasattr(State, "raw"), "raw is a per-instance field, not a class attribute"
print("unknown keys stay in raw and off the object (2 of them); a MISSPELT key does the same and "
      "leaves the field at 0 - visible only through raw")

# ------------------------------------------------------------------ 6. a duplicated key
#
# `kv[k] = int(v)` in a loop, so the last one wins. The bridge does not emit duplicates; a garbled
# or concatenated reply might, and "last wins" is the answer that happens, so it is pinned.
d = State.parse("frame=1 frame=2 room=10 frame=3")
assert (d.frame, d.room) == (3, 10), (d.frame, d.room)
assert d.raw["frame"] == 3 and len(d.raw) == 2
print("a duplicated key takes the LAST value (frame=1 2 3 -> 3); nothing warns, and raw collapses "
      "the duplicate so the count of keys is smaller than the count of tokens")

# ------------------------------------------------------------------ 7. a short line
#
# Fewer tokens is not an error: every field the bridge did not send keeps its dataclass default of
# 0. That is what makes `State.parse` usable on a partial reply at all, and it is also why a
# truncated-but-token-aligned reply is dangerous - check 8's guard is the only thing standing
# between that and a state that reads as "power-on, no keys, no sword".
sh = State.parse("frame=5")
assert sh.frame == 5 and sh.raw == {"frame": 5}
assert all(getattr(sh, k) == 0 for k in FIELDS if k != "frame"), "a missing field is 0, not None"
assert sh.hearts == 0.0 and sh.containers == 1, "and the two derived fields still compute"
assert State.parse("") is not None and State.parse("").raw == {}, "an empty line is an empty state"
print(f"a short line parses to defaults: 'frame=5' -> frame=5 and {len(FIELDS) - 1} zeroes, "
      f"hearts 0.0 / containers 1; an empty line is an empty state, not an error")

# ------------------------------------------------------------------ 8. a mid-token truncation
#
# The exact reply `BadReply`'s docstring describes: the first token intact, a later one cut short.
# `parse` raises ValueError with a message that names nothing; `_is_state_line` rejects the same
# string, so `cmd` raises BadReply with the command, the reply and the three replies before it.
GARBLED = LINE[: LINE.index("lag=")] + "la"
# Same token COUNT as the good line - one token replaced, not one dropped. So a length check could
# never have caught this; only the per-token shape check does, which is what `_is_state_line` is.
assert GARBLED.endswith(" la") and len(GARBLED.split()) == len(LINE.split()) == 24, (
    "this fixture is LINE with its last token replaced, not with one dropped")
assert not _is_state_line(GARBLED), "the guard missed the reply that started this"
assert not _reply_answers("state", GARBLED)
try:
    State.parse(GARBLED)
except ValueError as e:
    assert str(e) == "invalid literal for int() with base 10: ''", str(e)
    # the message that cost 12 attempts in 590: no command, no reply, no frame
    assert "frame" not in str(e) and "mode" not in str(e), str(e)
else:
    raise AssertionError("a truncated token parsed without raising")
# every shape the parser cannot take must be one the guard rejects, or the guard is decorative
for bad in ("frame=1 mode=", "frame=1 mode", "frame=1 mode=5 junk", "garbage", "frame=1 mode=0x05",
            "frame=1 mode= 5", "frame=1 mode=5.0"):
    try:
        State.parse(bad)
        raised = None
    except ValueError as e:
        raised = type(e).__name__
    assert raised == "ValueError", (bad, raised)
    assert not _is_state_line(bad), f"the guard accepts {bad!r}, which parse then rejects with ValueError"
    assert not _reply_answers("state", bad), bad
# ...and one shape where the guard is STRICTER than the parser, which is a choice rather than an
# accident: `int('-1')` works, so parse accepts `frame=-1`, while `_is_state_line` rejects it
# because '-1'.isdigit() is False. Every value in the line is a read_u8 or a framecount, so a minus
# sign cannot occur, and a reply that has one has come out of step with the bridge. Worth knowing
# that the guard would discard such a line rather than pass it on.
assert State.parse("frame=-1 mode=5").frame == -1, "parse accepts a negative value"
assert not _is_state_line("frame=-1 mode=5"), "the guard does not"
print("a mid-token truncation raises ValueError('invalid literal for int() with base 10: \\'\\'') - "
      "a message naming nothing - and the guard rejects all 7 malformed shapes first, so cmd() "
      "raises BadReply with the command and the last three replies instead")

# ------------------------------------------------------------------ 9. str() is the VERIFICATION line
#
# Every `hp=` in every VERIFICATION.txt and every replay line is this format string, and it is the
# only place hearts and containers are ever written down. The shape is pinned by looking at the
# archived run rather than at the code: 794 `hp=3.0/3` lines and so on.
out = str(s)
assert out.startswith("f98204 mode=05/00 L4 room=13 pos=(120,141) dir=8 hp=3.0/5 rup=48"), out
assert "hp=3.0/5" in out and "lag=10947" in out, out
# the float is a float, so a whole number of hearts prints as `4.0` and not `4`. $43 is 3 full plus
# a FULL fraction ($80) = 4.0, in the 5 containers its high nybble names; $C4 is 4 full in 4
# containers. Both are bar-full, and they print the same shape, which is what `hearts_full` compares.
assert "hp=4.0/5" in str(State(hp=0x43, hpfrac=0x80)), str(State(hp=0x43, hpfrac=0x80))
assert "hp=4.0/4" in str(State(hp=0x34, hpfrac=0x00)), str(State(hp=0x34, hpfrac=0x00))
assert "hp=0.0/1" in str(State()), str(State())
assert "hp=1.5/3" in str(State(hp=0x21, hpfrac=0x40)), str(State(hp=0x21, hpfrac=0x40))
assert "hp=2.5/3" in str(State(hp=0x22, hpfrac=0x40)), str(State(hp=0x22, hpfrac=0x40))
# and the unclamped arithmetic prints honestly if the cartridge ever hands over an impossible byte
assert "hp=16.0/1" in str(State(hp=0x0F, hpfrac=0xFF)), "no clamping, and no pretending"
# room is hex two-digit (19 -> 13) and hpfrac is NOT printed at all, so the two archived shapes
# `hp=3.0/5` (bar down) and `hp=3.5/5` (a fraction in it) are distinguishable only by the `.5`.
assert "room=13" in out and "L4 " in out and "mode=05/00" in out, out
assert "frac" not in out, "the fraction never reaches a log line; only its effect on hearts does"
assert str(State(hp=0x22, hpfrac=0x40)).endswith("lag=0"), str(State(hp=0x22, hpfrac=0x40))
# $0670 can only be empty / half / full, so a quarter heart cannot occur - which is what makes
# "hp=3.5" unambiguous in a log. Say so rather than leave it as luck.
for frac in (0x00, 0x40, 0x80):
    assert f"hp={State(hp=0x22, hpfrac=frac).hearts}/3" in str(State(hp=0x22, hpfrac=frac))
print(f"str(State) renders hp=3.0/5 from $43 - a whole number of hearts always prints with its .0, "
      f"which is why the archived logs are full of `hp=3.0/3`; $0670 has three states so `.5` is "
      f"never ambiguous")

# ------------------------------------------------------------------ 10. the guard is per-command
#
# `step` with the trace on answers with several state lines joined by `;`, and those are not tokens.
# The code deliberately only checks the single-frame form, which is the form a search uses.
assert _reply_answers("step", LINE), "a single-frame step answer is a state line"
assert _reply_answers("step", "frame=1 mode=05 sub=00;" + LINE), "a traced step is exempt"
assert not _reply_answers("step", "ok"), "'ok' is not an answer to step"
assert _reply_answers("state", "frame=1"), "a one-token state line is still a state line"
assert _reply_answers("load", "ok") and _reply_answers("quit", ""), "unknown commands are left alone"
assert _reply_answers("attempt", "frame=9 mode= mode="), "only state/step/ram are checked at all"
print("the guard checks state and single-frame step answers, skips traced steps, and returns True "
      "for everything else - a wrong strict check costs a whole emulator")

# ------------------------------------------------------------------ 11. `ram` wants hex
assert _reply_answers("ram", "0a0b0c"), "hex bytes"
assert _reply_answers("ram", ""), "zero bytes is even and in-set"
assert not _reply_answers("ram", "0a0b0"), "an odd number of hex digits is not a byte string"
assert not _reply_answers("ram", "0a0bzz"), "non-hex"
assert not _reply_answers("ram", "frame=1"), "a state line is not hex"
assert _reply_answers("ramd", "deadbeef")
# `ram 847 12` is the command the BadReply check in test_search_machinery.py sends; 12 bytes = 24
# hex digits, so the answer the bridge gives is checked here as a shape and nowhere else as a value
assert _reply_answers("ram", "0" * 24) and not _reply_answers("ram", "0" * 25)
print("ram/ramd answers must be an even-length hex string; '0'*24 yes, '0'*25 no, '0a0bzz' no")

print("all checks passed")