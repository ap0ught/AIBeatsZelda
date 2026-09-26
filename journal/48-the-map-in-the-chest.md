# 48 - The map in the chest

2026-09-26

**Cartridge:** `Legend of Zelda, The (USA) (Rev 1).nes` — md5 `614fb3085826e62f3be3a3fe0b931689`, the verified one, the only one this entry's numbers are about. (This line is new from here on, per the owner's note: every entry should say which cartridge it was measured against. Entries 1–47 are all Rev 1.)

**Goal.** Close issue #5, which has been open since the pickup tracker landed: `$0668` — "map in inventory, one bit per level" — changes twice in the verified run with no rupee movement, and the bits latch. Three readings had been proposed and none confirmed: *revealed rather than owned*, *a dual-purpose byte reusing dungeon state*, and *a drop or bonus item*. The tracker was labelling both events `unverified`, which is honest but which also means the acquisition count was quietly short by two.

**The answer: a treasure chest inside that dungeon.** On run6, Link takes a map out of the chest in Level 3 room `$4C` at f9804, and out of the chest in Level 7 room `$18` at f92997. Free, because a chest has no price — which is the whole reason the rupee count never moved, and why every hypothesis that assumed a transaction was wrong.

## Why it was so hard to see

Not because the evidence was weak. Because the one routine that writes `$0668` reaches it through an **indexed store shared with three other variables**, so *no instruction in the cartridge names `$0668` as an operand*:

```
TakeClass0Complex:                    ; Z_01.asm:4604
    LDA CurLevel                      ; $10
    BEQ @Exit                         ; in the overworld, do nothing
    CPY #$11                          ; the MAP item slot
    BNE :-
    LDX #$01
    STX StatusBarMapTrigger
    SEC / SBC #$01                    ; level - 1
    CMP #$08 / BCC / INY / INY         ; level 9 uses $669/$66A instead
    AND #$07 / TAX
    LDA Items, Y                      ; Items = $0657, so Y = $11 lands on $0668
    ORA LevelMasks, X                 ; 01 02 04 08 10 20 40 80
    STA Items, Y
```

`Y` is an item slot from `ItemIdToSlot` (Z_01.asm:4318): id `$16` → slot `$10` (compass, `$0667`), id `$17` → slot `$11` (map, `$0668`), and the same three lines also set `$0667`, `$0669`, `$06A` and `$0671`. One store, four variables. A byte-pattern search for the operand pair `68 06` across the whole of PRG-ROM returns **zero hits**, and that is not a failure of the search — it is the correct answer. I had that result earlier in the session and printed it as "no direct stores", which was right; what I got wrong afterwards was labelling the addresses I printed alongside it, see below.

The second reason it was hard: the caller is a **dungeon, not a shop**. The one `JSR TakeItem` at Z_01.asm:833 is the cave/shop handler, which is what made "it must be a purchase" the obvious reading. But `TakeItem` is also reached from `TryTakeItem` (Z_01.asm:4432), which is what `TryTakeRoomItem` calls with `X = $13` — the room item. In a dungeon the room item is a chest.

## Three observables on the same frame

Not one, which would have been a coincidence:

1. `$00AB` is already `$17` — the room's contents, from the frame the room was *created*, not the frame the chest was opened.
2. `$00BF` and `$0097` (ObjState/ObjY for slot `$13`) both go to `$FF` — the signature at Z_01.asm:4432-4434, with `X = $13`.
3. `$04E5` `StatusBarMapTrigger` pulses `00 → 01 → 00`. That byte has **exactly two references in the entire disassembly**: the write at Z_01.asm:4616, reachable only through the map slot, and a read-and-clear. Nothing else can set it.

And the geometry settles the frame independently, because it is off by one pixel:

```
L3  f9803  LinkX 119 -> |119 - 128| = 9   rejected
    f9804  LinkX 120 -> |120 - 128| = 8   accepted   <- $0668 changes here
L7  f92996 LinkY 150 -> |150 + 3 - 144| = 9  rejected
    f92997 LinkY 149 -> |149 + 3 - 144| = 8  accepted  <- $0668 changes here
```

`TryTakeRoomItem` wants `|LinkX - $83| < 9`. Both transitions land on the frame the inequality flips. The static ROM room table independently says those rooms hold a map, and it agrees with the live RAM byte.

## The mistake worth writing down

My first version of `testing/probe_map_chest.py` sampled RAM **at batch boundaries** — it stepped through runs of identical input and read only on the frame a run ended. It printed nothing at all, and the reason is a good one: **f9796–f9812 sits entirely inside a 103-frame hold of `Right`**, so there is no boundary in the window to sample. Zero of seventeen frames captured, and the block came back empty and the script died on `rows[0]`.

This is the sampling trap from §3 of the fidelity skill, in a form I had not anticipated: not *reading a counter too coarsely*, but **choosing sample points from a structure that has nothing to do with where the interesting frames are**. A held input is a long run precisely when the bot is walking somewhere deliberate, which is exactly when a chest is likely to be opened. The fix is to advance *to* each wanted frame and stop the batch there, rather than to batch and hope.

A subagent caught it and named the cause from the input log without touching the code. Worth noting, because the failure mode was a clean-looking run that reported 1111 f/s and printed a plausible header before producing no data — exactly the shape of a measurement that is confidently wrong.

## Also fixed, and also mine

**A wrong address label, printed with confidence.** In the exploratory store-scan I printed "CPU addresses" as `0x8000 + prg_index`, which overflows past `$FFFF` for anything in the switchable banks. So the labels I showed alongside the (correct) zero-hit result — `$1a349`, `$2104e` — were not addresses. The conclusion never depended on them; the byte search needed no mapping, and the disassembly plus the live trace confirmed the writer independently. But a number printed in a table gets reused, so it is retracted here.

**Every "See also" link in the repo was dead.** `make_doc.py` emitted `<script>.py.md` while writing `<stem>.md`, so all 182 docs pointed at files that were never created. Zero `*.py.md` files have ever existed in this tree. One line, and in a repo whose entire argument is that provenance cross-references resolve, that is not a small thing.

**And one that is not a bug at all:** `probe_map_window.md` lost its "Why this still matters" section on this change, because `zelda/pickups.py` no longer cites it — it cites `probe_map_chest.py` now. The provenance index followed the citation to a different script. That is the system working.

## The rule left behind

*Before proposing what a number means, find the instruction that writes it — and if a byte-pattern search for its address comes back empty, that is a finding about the code, not a failure of the search.* A shared indexed store is invisible to a reader looking for a named operand, and it made a dungeon chest look like a shop purchase for as long as it did.
