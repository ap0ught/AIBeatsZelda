---
name: oc-nes-rom-patching
description: Work with NES ROM hacks and mod rips - decode an IPS patch, apply it safely, tell code from data from tiles, and prove a patched ROM still plays the same game. Covers the IPS record format including RLE runs and the missing truncate field, why a patch may not fit the ROM you have, mapping file offsets to CPU addresses across PRG banks, reading 6502 in a patch to learn what the hack does, CHR-RAM vs CHR-ROM uploads, and the work-RAM gate that decides whether a "cosmetic" hack changed the game. Use when given a .ips/.ups/.bps patch or a ROM hack, when deciding whether to use a modded ROM with an automated player, or when reverse-engineering what a hack touches.
license: MIT
metadata:
  tags: nes, rom, ips, patch, ips-patcher, 6502, ines, prg, chr, chr-ram, mapper, hack, homebrew, mod, disassembly, checksum, md5
  category: reverse-engineering
  requires_toolsets: terminal
---

# NES ROM Patching

Working example: `Automap0.2.IPS` (2011, 1520 bytes) - a Zelda 1 hack that draws
the automap. Found while asking whether the bot could run with the hack enabled.
The answer involved decoding the patch, reading its 6502, and gating it on a
state diff - all of which this skill covers.

## Legal and practical posture

A patch transforms a ROM you have into a ROM you had. That is fine locally; the
output is still not redistributable, and a hack author's work is theirs. Keep
patched ROMs **outside** any repo (`*.nes`, `*.zip` in `.gitignore`), never
overwrite the canonical ROM, and say plainly in any writeup that a run used a
modified cartridge - a fingerprint means nothing without knowing what produced it.

## The IPS format

Five literal bytes `PATCH`, then a stream of records, then `EOF`:

| field | size | meaning |
|---|---|---|
| offset | 3, big-endian | file offset to write at |
| length | 2, big-endian | byte count; **0 means an RLE record** |
| data | `length` | replacement bytes |
| RLE instead | 2 + 1 | run length, then the byte to repeat |
| `EOF` | 3 | end of records |
| truncate | 0 or 3 | optional new file length |

The RLE escape is the part people get wrong: `length == 0` is not an empty write,
it is "the next two bytes are a count, the byte after is the value".

```python
def decode(blob):
    assert blob[:5] == b"PATCH"
    recs, i = [], 5
    while blob[i:i+3] != b"EOF":
        off = int.from_bytes(blob[i:i+3], "big")
        ln  = int.from_bytes(blob[i+3:i+5], "big")
        i += 5
        if ln == 0:
            run, val = int.from_bytes(blob[i:i+2], "big"), blob[i+2:i+3]
            i += 3
            recs.append((off, val * run))
        else:
            recs.append((off, blob[i:i+ln])); i += ln
    trunc = int.from_bytes(blob[i:], "big") if len(blob) - i == 3 else None
    return recs, trunc
```

BPS and UPS exist too; if the magic is not `PATCH`, do not improvise a parser -
read the format spec or the author's notes.

## The patch may not fit the ROM you have

An IPS addresses the **file** and declares no length. A hack authored against a
different revision can write past the end of your ROM. Check before applying:

```
base   Legend of Zelda, The (USA) (Rev 1).nes  131088 bytes  ($20010)
patch  Automap0.2.IPS  31 records, highest write $20012
       base is short by 2 byte(s)
```

Extending with zeros to cover the highest write is what every patcher does, and 2
bytes is not a problem. **A shortfall of thousands is a different message**: the
hack expects a ROM with a larger CHR bank, a translation, or an expanded
overworld, and applying it to stock will produce garbage that still boots. Say so
rather than forcing it.

## File offsets are not CPU addresses

An iNES file is a 16-byte header, then PRG in 16 KiB banks, then CHR.

```
file 0x0000-0x000F  iNES header
file 0x0010 + n*0x4000   PRG bank n   -> CPU $8000-$BFFF when bank n is mapped
file 0x0010 + prg_size    CHR (or CHR RAM if the header says 0)
```

The fixed bank at CPU `$8000` is the *last* 16 KiB of PRG (bank `prg/16K - 1`);
the switchable bank at `$8000` is whatever the mapper has paged in. So:

```
file 0x6518 -> PRG bank 1 -> CPU $8000 + (0x6518 - 0x4010) = $A508
file 0x6751 -> CPU $A741, and the patch writes 4C 42 BD  = JMP $BD42
```

Those 1-3 byte writes into the fixed bank are almost always **hooks** - a `JMP` or
`JSR` retargeted into new code living in a switchable bank. Reading them as data
is a category error; they are the patch's entry points, and they tell you which
existing routines the author considered theirs to change.

## Read the 6502 to learn intent

The new code is plain 6502 and often heavily commented by construction - the
opcode choices tell you what it does.

```asm
A5 10        LDA $10          ; level
D0 20        BNE +$20         ;   not the overworld -> skip
AD 54 02     LDA $0254
C9 FF        CMP #$FF
F0 03        BEQ
8D 29 7F     STA $7F29        ; stash into cart WRAM
```

`$10` is the level byte, so this is a hook that only fires in the overworld.
`$7F29` is cartridge WRAM, which is where a map buffer would live. A useful
decode table:

| bytes | instruction |
|---|---|
| `A5 nn` / `85 nn` | `LDA`/`STA` zero page |
| `A9 nn` | `LDA #nn` |
| `AD nn nn` / `8D nn nn` | `LDA`/`STA` absolute |
| `29/09/49 nn nn` | `AND`/`ORA`/`EOR` absolute |
| `BD/9D nn nn` | `LDA`/`STA` absolute,X / ,Y |
| `20/4C nn nn` | `JSR`/`JMP` absolute |
| `EE nn nn` | `INC` absolute |
| `4A` | `LSR A` (shift right) - repeated = divide by 2^n |
| `C9 nn` / `D0 nn` / `F0 nn` | `CMP` / `BNE` / `BEQ` |

Repeated `4A` is how a value gets divided, e.g. `A5 15 4A 4A 4A 4A 4A` is
`$15 >> 5` - a cheap way to get a coarse index without a divide routine.

**Do not scan for opcode bytes naively.** Operands and opcodes share byte values,
so a substring search reports nonsense. Disassemble, or match whole instructions.

## Data tables hide as CHR uploads

A chunk of low, ascending bytes is usually a tile-index or font table, not code:

```
$19361: 48 F5 20 82 48 F5 20 A2 48 F5 20 C2 48 F5 ...
         -> $82 '0'..'9'  space  $82 '8'..'?'  space  $A2 'A'..'G'  space  $C2 'H'..'O'
```

Digits, a colon, and letters A-O: a **font**, for labelling rooms on a map. If
the header says `CHR: 0K` the game has CHR **RAM**, so the hack must upload tiles
at runtime - and those upload routines plus their index tables are a large part of
the patch. Confirm by booting it and looking, not by assuming.

## The gate: is it still the same game?

A patch that draws something is *probably* cosmetic. "Probably" is not a
measurement. Replay identical inputs on both ROMs to the same frame and diff:

| range | verdict if different |
|---|---|
| `$0000-$07FF` work RAM | **the game changed** - not cosmetic |
| `$6000-$7FFF` cart WRAM | expected; this is the draw buffer |
| CHR RAM | expected; invisible to a RAM-reading bot |

Then, and this is the part that gets skipped: **even a provably cosmetic patch
stays out of the verification path.** Use it to watch and to record video. If a
modded ROM can produce an input log, the log's provenance is ambiguous and the
fingerprint no longer means what it says. See `oc-emulator-run-fidelity`.

## Is it even useful?

Ask before wiring it in. An on-screen automap is worth nothing to a bot that reads
RAM - it gains no new information. The valuable outcomes from a hack are
different:

- **It reveals the game's own map-reading code**, which is a lead for a
  long-standing RAM question. Any automap hack must read the map state to draw
  it, so the addresses it touches are exactly the routines you were reverse
  engineering.
- **It reveals a data table** the game keeps (room layouts, labels) that a
  planner could read directly instead of walking to discover.
- **It is a debugging aid** - watching a route with a map is genuinely clearer
  than watching it blind, and a wrong turn is obvious at a glance.

If none of those apply, the correct outcome is a clean "runs, cosmetic, no
benefit, not adopted" - which is a result, and worth writing down.

## Checklist

- [ ] `PATCH` magic confirmed; RLE records and truncate field handled
- [ ] Highest write compared against the ROM length; shortfall characterised
- [ ] Base ROM MD5 unchanged after the experiment
- [ ] Patched ROM outside the repo, `*.nes` gitignored
- [ ] Offsets mapped to CPU addresses through the PRG banks before interpreting
- [ ] New code disassembled, not substring-matched
- [ ] Booted and screenshotted - the title screen proves nothing about the feature
- [ ] Identical inputs replayed on both ROMs; work RAM diffed
- [ ] Verdict stated: cosmetic or not, and therefore usable for what
- [ ] Whether it is actually *useful* to this consumer, answered separately from
      whether it *works*

## Related

- `oc-nes-rom-map-decode` - the addresses, tables and encodings a hack is likely to
  touch, and the RAM-map traps
- `oc-emulator-run-fidelity` - the fingerprint discipline, and the ROM-swap rules
- `oc-bizhawk-nes-harness` - booting a specific ROM, screenshots, and per-frame
  state reads
