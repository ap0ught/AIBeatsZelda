# skills/

Copies of the opencode skills written while working on this repo. The canonical
copies live in `~/.config/opencode/skills/`; these are here so the reasoning
travels with the code, and so a reader who has never seen that directory can see
*why* the tooling looks the way it does.

Keep both. `~/.config/opencode/skills/` is what actually loads; this copy is
documentation. When you edit one, copy it across:

```bash
for s in skills/*/; do n=$(basename "$s"); cp "$s/SKILL.md" "$HOME/.config/opencode/skills/$n/SKILL.md"; done
```

## The three written here

| skill | what it is for |
|---|---|
| `oc-emulator-run-fidelity` | proving a changed environment still produces the same machine state; the work-RAM-versus-cart-WRAM gate; why a counter sampled at coarse intervals lies; retracting a shipped claim when a test contradicts it |
| `oc-heuristic-cost-audit` | auditing a scoring function for blind spots - future-state blindness, formulas applied by omission, two modules disagreeing about one predicate, and the "actually it's a 2D table" reveal |
| `oc-nes-rom-patching` | IPS decode and safe application, file-offset-to-CPU-address mapping, reading a hack's 6502, and deciding whether a modded ROM is usable with an automated player |

## The three that predate this repo's current state

`oc-bizhawk-nes-harness`, `oc-run-journal` and `oc-nes-rom-map-decode` were written
earlier and installed in the skills directory. The last of those has since been
extended with the two Data Crystal pages this project relies on:

- <https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/RAM_map>
- <https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/Notes>

Those are the authoritative source for every RAM encoding used here, and they are
Cloudflare-gated to scripted requests - the skill carries the archive.org snapshot
timestamps and the `curl` recipe.
