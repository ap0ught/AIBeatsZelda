---
name: oc-emulator-run-fidelity
description: Prove that a changed emulator environment still produces the same machine state before trusting a replay, fingerprint or verified run - and catch the traps that make a "cosmetic" change quietly alter the game. Covers swapping a ROM without touching the verified copy, the work-RAM-versus-cart-WRAM gate for deciding whether a patch is cosmetic, why a counter sampled at coarse intervals lies (animated counters), the per-frame re-read that settles it, and the fingerprint consequences of any of it. Use when changing a ROM, applying a patch or IPS, altering emulator settings, comparing two ROMs, verifying an input log by RAM fingerprint, or when a value read from a replay disagrees with what the documentation says.
license: MIT
metadata:
  tags: emulator, determinism, fingerprint, ram, verification, replay, tas, bizhawk, nes, ips, patching, counter, sampling, cosmetic, md5, state-integrity
  category: emulation
  requires_toolsets: terminal
---

# Emulator Run Fidelity

The rule this exists to enforce:

> **A verified run is a claim about a specific byte-for-byte environment. Change any
> part of that environment and the claim is void until you have re-proven it.**

The failure mode is not dramatic. It is a plausible reading that nobody re-checks,
which then gets cited downstream until it is load-bearing.

## 1. Never mutate the verified artifact

A ROM (or config, or BIOS) that a fingerprint was computed against is evidence.
Keep it byte-identical and prove it.

```bash
md5sum roms/"Legend of Zelda, The (USA) (Rev 1).nes"     # before
# ... do the risky thing to a COPY, in a scratch dir, never in roms/
md5sum roms/"Legend of Zelda, The (USA) (Rev 1).nes"     # after - must match
```

Prefer an environment-variable indirection over editing paths in code, so the
override is visible at the call site and in logs:

```python
ROM = Path(os.environ.get("ZELDA_ROM")
           or next((p for p in _ROM_CANDIDATES if p.exists()), _ROM_CANDIDATES[0]))
```

Then `ZELDA_ROM=/tmp/scratch/automap.nes ./zelda.sh watch` and the canonical
`roms/` copy is never in play. Note that `*.nes` and `*.zip` belong in
`.gitignore`; a ROM cannot be un-shipped from git history cleanly.

## 2. The cosmetic-or-not gate

When you swap a ROM, the question is not "does it look right" but **does it change
the game**. There is a clean test, because the two live in different address
ranges:

| range | what it is | verdict if it differs |
|---|---|---|
| `$0000-$07FF` | the game's own work RAM - state, counters, positions | **the patch changed the game** |
| `$6000-$7FFF` | cartridge WRAM - where a map/plot buffer lives | expected for a cosmetic patch |
| CHR RAM | tile uploads | expected, invisible to the bot |

Replay **identical inputs** on both ROMs to the same frame and diff both regions.
Work RAM identical plus cart WRAM differing is the good outcome: same game,
different picture. That combination is what licenses "safe to watch, not safe to
verify against".

```python
a, ac = replay_to(stock,   frames, upto, "stock")
b, bc = replay_to(patched, frames, upto, "patched")
work = [i for i in range(0x800) if a[i] != b[i]]
cart = [i for i in range(0x2000) if ac[i] != bc[i]]
```

Report the first differing address and the state fields the bot navigates by
(`mode`, `level`, `room`, position, hearts, bombs, rupees, Triforce). A one-byte
work-RAM difference at frame 4000 becomes a different fingerprint at frame 136,526.

**Even a provably cosmetic patch should stay out of the verification path.** Keep
it for watching and for video. The moment a cosmetic ROM can be used to produce
an input log, the log's provenance becomes ambiguous.

## 3. The sampling trap that manufactures false evidence

This is the one that cost real time, and it is not emulator-specific.

> **A counter read at coarse intervals does not report what happened. It reports
> where the samples happened to land.**

An on-screen rupee counter *animates* on a transaction. Reading it once per run of
identical inputs gave this census over a whole 37-minute verified run:

```
decreases:  -1 x14,  -3 x2,  -16 x1,  -57 x2,  -64 x1
increases:  +1 x11,  +2 x4,  +3 x2,  +4 x2,  +5 x2,  +100 x2
```

Two obvious conclusions, both wrong:

- "`-3` and `-57` are odd prices." They are the same 60-rupee purchase, sampled
  twice mid-animation. `-64` + `-16` is one 80-rupee purchase.
- "There is no `-15`, so the 15-rupee thing never happened." A 15-rupee purchase
  animating downward shows up as a scatter of `-1`s, and there were fourteen of
  them. The absence of `-15` in a list of deltas is **not** evidence of absence.

This nearly produced a wrong conclusion about a documented memory byte. The fix is
cheap and should be the default whenever a counter moves:

```python
# WRONG: one read per run of identical inputs
emu.step(frames[i], j - i); value = emu.byte(addr)

# RIGHT: bulk fast-forward to the window, then read EVERY frame inside it
while i < lo:                      # cheap: batch identical inputs
    j = i
    while j < len(frames) and frames[j] == frames[i]: j += 1
    emu.step(frames[i], min(j, lo) - i); i = min(j, lo)
while i <= hi:                    # 1801 single-frame reads is nothing
    emu.step(frames[i], 1)
    trace.append((i, emu.byte(addr), ...))
    i += 1
```

Then report the trajectory, not a delta: distinct values, how long each was held,
and the net over the whole window. Per-frame, the answer was unambiguous - a flat
`6` across 1801 frames, then a bit changing with no transaction at all.

## 4. Corroborate with an independent observable

Documentation tells you an **encoding**. It does not tell you **what a given run
did**. Those are different questions, and conflating them is how a plausible
label gets invented.

The pattern that works: find a second, causally-linked quantity that *must* move
if your reading is right, then check it.

> A map is bought in a shop for 15 rupees. The rupee count is the displayed
> count. So a map acquisition must show a 15-rupee drop on the same frame.

It did not - per-frame, over 1801 frames either side, the count never moved. The
screenshots put the transition mid-dungeon, one of them mid-fight, with no shop
and no item. So the byte changed, the change was free, and the label "map for
level 3" was **wrong**.

Corollary: pick corroborators that are causally linked and *independently
observed*, not ones that share code with the thing under test. Two views of the
same derived value prove nothing.

## 5. Retract loudly, and leave the evidence attached

When a test contradicts a shipped claim, the fix is not a quiet edit:

- **Say it in the commit subject**, not just the body. "retract the map reading"
  is findable; a reworded paragraph is not.
- **Keep the discredited claim visible in the code comment**, with the reason it
  failed and the test that failed it. A future reader who re-derives the same
  wrong idea should hit the corpse on the way.
- **Re-label the data honestly.** `kind="unverified"` with the evidence in the row
  beats a confident wrong name. An event log that says "map for level 3" when no
  map was bought is worse than one that admits it does not know - and the count
  must exclude the unverified rows, or the summary lies twice.
- **File the open question** with the evidence table, so the next session inherits
  a lead instead of a shrug.
- **Correct the reference too, if it was the source.** Often the address was right
  and the *reading* was wrong; say which, because "wrong address" sends the next
  person to the disassembly for nothing.

## 6. Checklist before trusting a number from a replay

- [ ] Inputs replayed from power-on in a fresh emulator, not resumed from a state
- [ ] The ROM/config under test is byte-identical to whatever the fingerprint used
      (or the fingerprint has been recomputed and the run re-verified)
- [ ] Any counter-derived figure was confirmed per-frame, not per sample-run
- [ ] The claim has a corroborator that does not share code with it
- [ ] Stated frame numbers, and the window around them, are reproducible
- [ ] The screenshots exist and were actually looked at - they settled a question
      RAM reads could not
- [ ] If it contradicts something already shipped: retracted in the open, with the
      failing test named

## Related

- `oc-bizhawk-nes-harness` - driving BizHawk from Linux, the Lua bridge, the
  no-yield discipline that makes replays deterministic, RAM-fingerprint
  verification, detaching long runs
- `oc-nes-rom-map-decode` - finding the addresses in the first place, and the
  encoding traps (count bytes next to status bytes, per-level bitmasks)
- `oc-nes-rom-patching` - applying an IPS and proving the result is the same game
- `oc-run-journal` - recording the reversal itself so it is not re-litigated
