# `test_ips_patch.py`

Does the IPS path do what it claims, before the next phase runs 60,589 frames against it?

The next phase replays an already-verified run against a ROM built by applying "enhanced"
IPS patches. `testing/patch_rom_ips.py` is the first thing that phase runs, and it has never
been run in this tree against anything: there is no `.ips` file anywhere in the repository.
So every line of the patch path is unexercised code that a four-hour replay depends on.

The failure this file is shaped around is not a crash. It is a *misread*: a length decoded one
byte short, a record cursor off by one, a truncate field the parser does not know where to
look. Each of those yields a ROM that is the right SIZE, has a valid iNES header, and boots -
and is not the hack that was intended. It then fails its replay for reasons that look exactly
like emulator nondeterminism, which is the same class of error that cost an hour in
`journal/47-the-cartridge-i-did-not-swap.md` (there: a patched ROM under the stock filename;
here: a patched ROM that was never the patch). Nothing downstream of this file can tell those
apart, so the checks below are byte-exact rather than smoke tests.

Each check prints the number or the literal it established, in the order they run:

  PARSER    1. a plain record lands at the offset its header names
            2. the wire format, pinned as raw hex                  10. the truncate field, after EOF
            3. an RLE count of N writes N copies (65535 too)         10b. MISMATCH: the docstring
            4. the N==1 boundary: one byte, one place                    puts it in the wrong place
            5. the record cursor survives a mixed file               10c. a SHRINKING truncate works
            6. the RLE count of 0 is a zero-length record            10d. DEFECT: a GROWING truncate
            7. "EOF" inside record data is data                             is ignored
            7b. LIMITATION: a hunk at $454F46 is swallowed            10e. DEFECT: truncate to 0
            8. a patch with no "EOF" marker is accepted              11. DEFECT: a short record
            9. bad magic is rejected                                 12. apply_patch zero-extends
                                                                13. ... and a straddling write
                                                                14. ... and an empty record
  PATCHER  15. the base ROM is byte-identical afterwards (3 paths)   19. the zero-pad branch fires
            16. an existing output is never overwritten (3 paths)    20. DEFECT: empty patch dies
            17. "UNCHANGED" is pinned
            18. "*** CHANGED ***" is pinned
  END TO   21. the Automap0.2.IPS case: short by exactly 2           25. the iNES header survives
  END      22. output md5 differs, base copy does not                26. ... and is genuinely read
            23. the diff is EXACTLY the bytes written, nowhere else
            24. the damage table decodes identically on the patch
               24b. ... and one byte of it is caught, one is invisible

WHAT IT DOES NOT CLAIM. Four things, and the fourth is the important one.

1. **No emulator.** BizHawk is never launched. That is a deliberate constraint, not a
   limitation of the harness: the checks here are about whether the right BYTES landed, and a
   replay can only tell you the bytes were wrong after four hours. Check 24 is the strongest
   emulator-free statement about game behaviour available here - it says the navigator's damage
   model is byte-identical on the patched cartridge - and it is still not a boot test. A patch
   that changes a jump target and nothing this file reads would pass every check below. In
   particular nothing here proves a patched ROM REPLAYS: only that it is the bytes it claims.

2. **No real `.ips` file.** `Automap0.2.IPS` is reconstructed from the shape the docstrings
   describe (see check 21), not decoded from the artifact, because the artifact is not in this
   repository. So this file proves the parser agrees with the IPS format as documented at
   fileformats.archiveteam.org/wiki/IPS_(binary_patch_format) - and check 10b is where it
   disagrees with `ips_decode.py`'s OWN docstring, which puts the truncate field in the wrong
   place. That disagreement is reported rather than resolved here: the code is right and the
   documentation is wrong, and the fix belongs to the docstring.

3. **The `*** CHANGED ***` branch cannot be reached honestly.** No legitimate run of the
   patcher changes the base, which is the whole point of it, so the branch that prints
   `*** CHANGED ***` is dead code in normal use. Check 18 substitutes `patch_rom_ips.md5` to
   reach it. That is the one check here that does not measure the real function; it pins a
   human-facing string, and a string is all it can pin. The honest half of the guarantee is
   check 15, which is a real run against real bytes.

4. **Six checks pin something that is wrong, and one pins a format limitation.** 10b (a
   docstring that misplaces the truncate field), 10d (a growing truncate ignored), 10e (a
   truncate to zero ignored), 11 (a short record silently shortened), 20 (an empty patch raises
   `ValueError`) and the second half of 24b (88 of the damage table's 96 bytes unchecked) are
   marked `MISMATCH` or `DEFECT` in the output and spelled out above each one. Check 7b pins a
   limitation the IPS format itself documents and recommends generators avoid. They exist so
   these are visible in the test suite and not only in a commit message, and each one FAILS if
   the code is corrected - which is the intended signal here, and the opposite of the usual
   "test broke" meaning. Do not silence one by editing production code in the same change; fix
   the code or the docstring, then flip the assertion to what it now does and drop the marker.

Run:  python3 testing/test_ips_patch.py

---

    python3 testing/test_ips_patch.py          # any cwd; the bootstrap chdirs to the repo root

## What it touches

- nothing at runtime; it exists to be read, or to be applied once
- writes a file

---

*Generated by `testing/make_doc.py` from the script's own docstring and code. Regenerate with `python3 testing/make_doc.py`; do not hand-edit - `git log` on this file says when.*
