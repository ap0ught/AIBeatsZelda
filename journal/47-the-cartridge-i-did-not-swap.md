# 47 - The cartridge I did not swap

2026-09-26

**Goal.** Settle issue #5. `$0668` changes two bits in run6 with no rupee movement
and no purchase, and the only way to know what *writes* that byte is to read the
game's own map-drawing code. Any automap hack has to read the map and compass out
of RAM to draw it, so the addresses `Automap Plus.IPS` touches are the game's map
code. Decode the IPS (`testing/ips_decode.py`), apply it to a scratch copy
(`testing/patch_rom_ips.py`), and read the 6502. A cheap question with an expensive
alternative: an hour of disassembly.

That part worked. The IPS needed `$20012` bytes and stock Rev 1 is `$20010`, so the
file was extended by exactly 2 with zeros, and the result is 131,090 bytes.

**Symptom.** The next day's replay of the verified run died at frame 98,204 of
136,526:

```
DIED after 98204 frames (83s, 1180 f/s)
  last good state: f98204 mode=05/00 L0 room=78 pos=(20,141) dir=1 hp=3.0/3 rup=0 sword=1 lag=258
  RuntimeError: bridge connection lost: EmuHawk exit code 0 (0x00000000)
  reached 71.9% of the log
```

`EmuHawk exit code 0` is the line that costs the hour. Exit code 0 is BizHawk's
*orderly* shutdown, not a crash - the harness says so in its own comment at
`zelda/emulator.py:198`, where it lists `0xC0000005` and `0xE0434352` as the crash
codes. So this is not an emulator fault; something ended the bridge cleanly, in the
middle. The two candidate explanations are "the ROM is different" and "the harness
gave up", and the instinct - correctly, because it has been right before - is Mono,
then EGL, then OOM. 31 GB of RAM, 10 GB free, nothing in `dmesg`.

**Diagnosis.** One command:

```
$ md5sum roms/*.nes /tmp/opencode/hacked/automap.nes
a6d95f620d67c52b16686e382a219a27  roms/Legend of Zelda, The (USA) (Rev 1).nes
a6d95f620d67c52b16686e382a219a27  /tmp/opencode/hacked/automap.nes
```

`roms/` held the patched Automap ROM, under the stock filename. I had put it there
the day before, to watch the hack, and never put it back. Nobody swapped the
cartridge - that is what makes it worth writing down. A patch was applied to the
conventional-looking path, the filename stayed the correct one, and the patched file
is 2 bytes *longer* than the cartridge it replaced, which is not a shape any check
in this repo was looking for.

Every guard in the project read the filename. `setup_linux.sh` hashes the ROM at
install time - correct, and three sessions too early. `roms/README.md` states the
hash. The `.gitignore` keeps the bytes out of git. None of them look at the file
again after the install, and the mutation happened in the middle, by a helper
script, in a directory whose whole purpose is "the one true cartridge".

**The save.** `../rom-backup/Rev1.stock.nes` existed, md5
`614fb3085826e62f3be3a3fe0b931689`, made at 13:12 the day before for no reason I can
now reconstruct except that I was about to do something to `roms/`. It turned a
re-download hunt into `cp -p`. That is the entire return on keeping a copy of a
131 KB file outside the working tree.

**Fix, and the part that is not the restore.** The restore is one line and I would
not write an entry about it. Three things are worth keeping:

1. *Re-prove the environment.* `cp -p` is a guess until the fingerprint agrees:

   ```
   replayed 136526 frames -> f136526 mode=13/04 L9 room=32 pos=(136,136) dir=2 hp=8.5/13 rup=29 sword=3 lag=23405
     ram sha1 3115e31ff1a9b16e732160f81fe478a5052668ff
     MATCH
   ```

   Same frame, same state, same sha1 as `runs/run6/VERIFICATION.txt`. The claim is
   back, and it is back because it was re-run, not because the file is the right
   size.

2. *Check the hash at launch, in the code, every launch.* `zelda/emulator.py` now
   carries `VERIFIED_ROM_MD5`, `rom_md5()` and `unverified_rom_reason()`, and
   `BizHawk.__init__` writes the verdict into every run: a banner on stderr, and the
   same text as the second line of that run's own log. The log line is the one that
   matters. A warning scrolls past; the log is what a reader meets weeks later, and
   it is the only artefact that still says what a run was played on.

3. *Make the verification path refuse.* `replay.verify()` now raises unless the
   cartridge hashes to the verified value, because a fingerprint is only meaningful
   next to the bytes it was computed from. Comparing a replay against a known-good
   fingerprint on an unverified cartridge yields a confident, meaningless number -
   strictly worse than no check, because `MISMATCH` looks like a result.
   `ZELDA_ALLOW_UNVERIFIED_ROM=1` is the override, and it exists for exactly the task
   I was doing: `testing/compare_roms.py` proves a patch cosmetic *by* replaying both
   ROMs and diffing work RAM, and that comparison is nonsense unless it can run.

Verified on real launches, both directions, reported verbatim rather than as "the
guard works": the patched ROM warns and still plays, the stock ROM is silent, and
`emu.unverified_rom` is a four-line string in one case and `None` in the other. A
detail worth keeping - the two ROMs produce a byte-identical state line after 30
frames, `f30 ... lag=27`. The patch is not visible early. It is invisible until
frame 98,204, which is precisely why a boot-and-play smoke test would never have
caught this and why the hash has to be checked without reference to how the game
behaves.

**And the process fix, from the owner, mid-diagnosis:** a full replay is two
minutes of wall clock and a search is four and a half hours, so a main session that
owns the emulator owns the clock. He was right, and the earlier loss in
`3.2` - a run killed by a tool timeout - is the same lesson arriving from the other
direction. Long emulator work now goes to a subagent whose only job is to launch
detached, poll, and hand back the numbers verbatim; a rounded "looks fine" is worth
nothing, because the number *is* the deliverable. Both rules are now in
`oc-bizhawk-nes-harness` and `oc-emulator-run-fidelity`, so the next session inherits
them instead of rediscovering them.

**The rule left behind.** *A guard placed only at the entry point protects the entry
point.* The environment is mutated in the middle, by a tool nobody was thinking
about, so the check has to live where the mutation happens - and when the thing you
changed is the ground truth every measurement stands on, the check must be able to
say no, not merely to say something.
