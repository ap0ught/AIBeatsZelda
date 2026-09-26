# skills/

Copies of the six opencode skills this project is built with. The canonical
copies live in `~/.config/opencode/skills/`; these are here so the reasoning
travels with the code, and so a reader who has never seen that directory can see
*why* the tooling looks the way it does.

Keep both. `~/.config/opencode/skills/` is what actually loads; this copy is
documentation. When you edit one, copy it across:

```bash
for s in skills/*/; do n=$(basename "$s"); cp "$s/SKILL.md" "$HOME/.config/opencode/skills/$n/SKILL.md"; done
```

To check they have not drifted:

```bash
for s in skills/*/; do n=$(basename "$s")
  diff -q "$s/SKILL.md" "$HOME/.config/opencode/skills/$n/SKILL.md" || echo "DIVERGED: $n"; done
```

## The six

| skill | what it is for |
|---|---|
| `oc-bizhawk-nes-harness` | driving BizHawk from Linux - the Mono build, the LuaSocket bridge, gtk2's silent X11 failure, why video never connects, the no-yield discipline that makes replays deterministic, RAM-fingerprint verification, detaching long runs |
| `oc-nes-rom-map-decode` | finding a game's map, rooms and item flags from the cartridge, then cross-validating the static tables against live RAM. Carries the encoding traps and the two authoritative references below |
| `oc-nes-rom-patching` | IPS decode and safe application, file offsets to CPU addresses across PRG banks, reading a hack's 6502, and deciding whether a modded ROM is usable with an automated player |
| `oc-heuristic-cost-audit` | auditing a scoring function for blind spots - future-state blindness, formulas applied by omission to a class they were never written for, two modules disagreeing about one predicate, and the reveal that a "table" is keyed on two things |
| `oc-emulator-run-fidelity` | proving a changed environment still produces the same machine state - the work-RAM-vs-cart-WRAM gate, why a counter sampled at coarse intervals lies, and retracting a shipped claim when a test contradicts it |
| `oc-run-journal` | keeping a working log of a long build - what was tried, what failed, and the rule left behind |

They cross-reference each other, so all six are needed for the "Related" sections
to resolve. They are ordered here roughly by how often they come up: the harness
and the map first, then the auditing skills, then the journal.

## The two references this project depends on

`oc-nes-rom-map-decode` treats these as authoritative for every RAM encoding used
here - when a byte disagrees with a guess, they win:

- <https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/RAM_map>
- <https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/Notes>

Both are Cloudflare-gated to scripted requests and return nothing to a tool. The
skill carries the archive.org snapshot timestamps and the `curl` recipe; known-good
snapshots are RAM map `20251116061046` and Notes `20250825035708`.

The standing rule, learned the hard way: **a documentation page tells you the
encoding; it does not tell you what a given run did.** Those are different claims.
See `oc-emulator-run-fidelity`.
