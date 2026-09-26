# testing/

Scratch and investigation scripts. Nothing here is part of the harness, and
nothing here is imported by the bot or by the committed tools at the repo root.

They are kept, not deleted, because they are the provenance for a lot of the
numbers in `zelda/`. Comments through the production code cite them by name —
`probe_gleeok_ram.py`, `probe_s9_10.py`, `probe_money.py` and so on — to say
which measurement produced a figure or a tuned constant. Deleting the scripts
would leave those citations pointing at nothing.

## The convention

Scripts that are still being used live here, and new scratch goes here too.
Anything that a human runs regularly, or that another tool imports, stays at the
repo root: `pickup_scan.py`, `record_run.py`, `route4.py`, `milestone3.py`,
`render_overlay.py`, `panel_preview.py` and the rest of the entry points.

```
python3 testing/probe_map.py          # from the repo root
```

Each file carries a short bootstrap that puts the repo root on `sys.path` *and*
chdirs into it, so `from zelda import ...` resolves and `logs/`, `shots/`,
`runs/`, `states/` land in the right place no matter where it is invoked from:

```
python3 /anywhere/testing/probe_map.py     # same result as from the repo root
```

## What is worth reading rather than skipping

- `probe_map.py` — the compass/map bytes. Reads Data Crystal's per-level-bit
  reading against the verified run, then tries to falsify it by checking whether
  the rupee count moved by the 15 a map costs. It does not, which is the useful
  part.
- `probe_money.py` — where the rupee-count findings came from.
- `probe_gleeok_ram.py`, `probe_s9_10.py`, `probe_g9_41.py` — the Level 9 and
  Ganon-fight measurements the tail of `fullgame.py` is built on.
- `patch_*.py` — one-shot ROM/bot patches. They mutate a source file in place
  and are kept as a record of what was changed and why. Re-running one is
  usually wrong; the edit it made is already committed.
