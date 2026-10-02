# Findings: getting AIBeatsZelda running on Linux

A report of what it actually took, written 2026-09-25 on CachyOS (Arch), kernel
7.2, Mono 6.12, BizHawk 2.11.1. It is deliberately a report of the *investigation*
rather than a setup guide — `SETUP-LINUX.md` is the operational version, and this
is the part that took the work to work out.

Everything here is reproducible from a clean checkout. The end state: the shipped
37:02 run replays byte-exact, plays back in realtime with sound, and the harness
can search with parallel scouts.

---

## 1. What the project is, before touching it

`bearsgaming-ui/AIBeatsZelda` is a video project. Claude, as a coding agent,
wrote a player for *The Legend of Zelda* (NES) and then played the game through
it. Two distinct artefacts matter and it is worth keeping them apart:

- **The harness** — `bridge.lua` talks to BizHawk over TCP; `zelda/` is the
  Python side (perception, path planning, combat lookahead, brute-force search);
  `fullgame.py` holds the 341-segment route. This is the code.
- **The run** — `runs/run6/` is the input log of the finished 37:02 attempt, plus
  a `.bk2` movie and a verification note.

The repo ships the harness as a single `release.zip` rather than as files, so the
first real job is unpacking it. Everything except the three files listed in
`SETUP-LINUX.md` is byte-identical to that zip.

### The ROM is the first real decision

The harness only works on one specific dump: No-Intro
`Legend of Zelda, The (USA) (Rev 1)`, md5 `614fb3085826e62f3be3a3fe0b931689`.

This is easy to get wrong. The local ROM collection contains **three** dumps of
the same game side by side — `(USA)`, `(USA) (Rev A)` and the `(USA) (Rev 1)`
zip — and the filename is the only thing distinguishing them. A Rev A or European
dump produces a run that looks plausible and is subtly wrong. `setup_linux.sh`
refuses to install a ROM whose md5 does not match, which is worth more than a
comment.

---

## 2. Three blockers, in the order they surfaced

### 2.1 The emulator binary is not what the release name suggests

BizHawk publishes `BizHawk-2.11.1-linux-x64.tar.gz`, which reads like a native
Linux build. It is not. Unpacked, it contains `EmuHawk.exe` and a shell wrapper:

```sh
export LD_LIBRARY_PATH="$PWD/dll:$PWD:$libpath"
export MONO_WINFORMS_XIM_STYLE=disabled
exec mono EmuHawk.exe "$@"
```

It is the Windows build under Mono. `zelda/emulator.py` hardcoded
`EMUHAWK = BIZHAWK_DIR / "EmuHawk.exe"` as the thing to `subprocess.Popen`, so
the harness tried to exec a PE binary directly.

The folder is still called `BizHawk-2.11.1-win-x64` on purpose. `emulator.py`
derives it as `ROOT / "BizHawk-2.11.1-win-x64"`, and keeping the name means the
linux-x64 tree drops in without touching any other code path. Only the *launcher*
needed to become platform-aware.

**Non-obvious:** the wrapper picks its `libpath` from `lsb_release`, and CachyOS
is not in its table, so it prints `Unknown distro, assuming system-wide libraries
are in /usr/lib` and carries on. That is harmless here (Arch does use `/usr/lib`)
but it is the kind of line that would be fatal on a distro that does not.

### 2.2 LuaSocket — the real blocker, and the most interesting one

The first smoke test produced this, twice per launch:

```
NLua.Exceptions.LuaScriptException: [string "main"]:15: module 'socket.core' not found
  no file '.../BizHawk-2.11.1-win-x64/Lua/socket/core.lua'
  ...
  no file '/usr/lib/lua/5.4/socket/core.so'
```

`bridge.lua` opens with `require('socket.core')` and connects a TCP socket back
to Python. BizHawk ships `Lua/socket/core.dll` — a Windows native DLL — and no
Linux equivalent. So the bridge dies on line 15, and the harness sits for 60
seconds waiting for a connection that will never arrive.

The obvious move — install `luasocket` from the distro — does not exist on Arch
for Lua 5.4 (`pacman -Ss luasocket` only offers `lua51-*` builds). So the module
has to be built.

**The part that needed actual investigation** was whether a Linux `.so` would
load and work at all, and against which Lua. Guessing here wastes time, so I
wrote a throwaway C# harness against BizHawk's own `NLua.dll` to answer it
directly:

```csharp
Lua lua = new Lua();                       // NLua's own embedded runtime
lua.DoString("package.cpath = '/tmp/.../?.so;' .. package.cpath");
lua.DoString("return require('testmod')"); // a trivial C module
```

That established three things:

- NLua embeds **Lua 5.4** (`_VERSION` = `Lua 5.4`, no JIT) — so the system
  `lua54` headers are the right ABI.
- Native `.so` modules **do** load through NLua on Mono.
- The host **exports the `lua_*` symbols**, so a module with undefined
  `lua_*` references resolves them at `dlopen`.

That last point is why the build deliberately omits `-llua54`:

```sh
gcc -O2 -fPIC -shared -std=gnu99 -DLUASOCKET_INET \
    -DLUASOCKET_API='__attribute__((visibility("default"))) extern' \
    -I/usr/include/lua5.4 -o Lua/socket/core.so \
    luasocket.c auxiliar.c buffer.c compat.c except.c inet.c io.c mime.c \
    options.c select.c timeout.c tcp.c udp.c usocket.c unix.c unixstream.c unixdgram.c
```

Linking liblua54 would be the reflexive thing to do and would be **wrong**: it
would give the module its own private copy of the Lua runtime while NLua holds
another. A missing flag that looks like a bug — hence the comment in
`setup_linux.sh`.

Verified end to end with a real TCP round trip through NLua before touching the
harness: Lua connected, sent, received, and correctly reported a timeout as
`nil`.

### 2.3 `gtk2`, which presents as a crash and is not

This one cost the most time and is the most important to write down, because
**nothing about it looks like a missing dependency.**

With a plain `BizHawk(fast=False)` launch, everything worked: the emulator booted
the ROM, the bridge connected, audio appeared in PipeWire. Then about thirty
seconds into play:

```
RuntimeError: bridge connection lost at 17:38:10: EmuHawk still running
```

`EmuHawk still running` is the tell. The process was alive and its window was up,
but the Lua bridge had stopped being serviced. The harness reported a lost
connection, which reads exactly like the silent emulator death that
`run_until.sh` exists to handle — so the first instinct is to go looking at Mono,
at EGL, at the process dying.

The real cause was in the launcher log, buried under the ROM chatter:

```
X11 Error encountered:
  Error: BadMatch (invalid parameter attributes)
  ...
  Control: BizHawk.Bizware.Graphics.Controls.OpenGLControl
  at BizHawk.Client.EmuHawk.Input.UpdateThreadProc ()
```

and, at the very top of every launch, a line that looks like cosmetics:

```
Gtk not found (missing LD_LIBRARY_PATH to libgtk-x11-2.0.so.0?), using built-in colorscheme
```

That line is not cosmetic. Without `libgtk-x11-2.0.so.0`, Mono's
System.Windows.Forms falls back to its built-in X11 driver, which is less robust
and throws on BizHawk's input thread. `sudo pacman -S gtk2` fixes it. After that:
zero X11 errors across a ten-minute continuous soak, and the `Gtk not found`
warning gone.

The lesson generalises: **on this stack, a Mono WinForms X11 error does not kill
the process, it kills the thread quietly.** A window that stays up is not evidence
that things are fine.

---

## 3. Three things that are broken in a way that wastes time

### 3.1 Video recording never connects

Anything passing `record=<name>` to `BizHawk()` fails at startup. The launcher log
stops dead after the GTK theme warning — no exception, no EGL error, no bridge:

```
parsing command-line flags: --lua=... --userdata=port:39799 --dump-type=ffmpeg --dump-name=.../video/rec_test.mkv ...nes
(mono:...): Gtk-WARNING **: Unable to locate theme engine in module_path: "adwaita"
<end of log>
```

`--dump-type=ffmpeg` takes BizHawk's display/GL path *before* the Lua bridge
does, and it never gets as far as the bridge. A minimal
`BizHawk(record="x")` reproduces it in about 60 s; the identical launch without
`record` connects in under 2 s. ffmpeg itself is present and fine — it is
BizHawk's writer path, not ffmpeg.

An earlier, more confusing sighting of the same fault surfaced as
`EGL_BAD_ACCESS: Unable to make EGL context current` inside
`DisplayManagerBase.Dispose` — i.e. the real error was happening at *teardown*,
which is a genuinely misleading place to be pointed at.

A search does not need the video; it is only for rendering the documentary. So
`ZELDA_RECORD=0` now forces recording off regardless of what the caller asked
for, and every runnable thing in `zelda` passes it.

### 3.2 Launching a long run will kill it silently

This one is worth recording because **it cost about an hour and it impersonates a
real bug.**

I launched milestone3 as a background job of a shell that then slept on it:

```
nohup env ZELDA_SCOUTS=4 python3 -u milestone3.py > out.log 2>&1 &
sleep 90; tail out.log
```

The run died partway through with:

- no traceback, no `FAILED:`, no exception of any kind
- all five emulators gone
- the scout logs ending **mid-segment, looking completely healthy** — savestates
  still loading, no errors, timestamps current to the last second

That is the exact signature of the emulator crash `run_until.sh` handles, so I
went looking for it in Mono, then EGL, then OOM (31 GB RAM, 10 GB free, nothing
in `dmesg` or `journalctl`). The actual cause: the tool call hit its timeout, the
shell was torn down, and the **process group went with it**.

The fix is to detach properly:

```sh
setsid nohup env ZELDA_SCOUTS=4 ZELDA_RECORD=0 python3 -u milestone3.py \
    > /tmp/run.log 2>&1 < /dev/null & disown
```

`python3 -u` matters independently: with output piped and the process killed, the
buffer is lost and you get nothing at all.

Same family of self-inflicted wound, cheaper: `pkill -f "EmuHawk.exe"` kills the
shell running it, because that shell's own command line contains the pattern. It
presents as BizHawk hanging. A third member of the family: counting processes with
`pgrep -f EmuHawk` inside a command that itself contains the string. Match the
executable column instead (`ps -eo pid,comm | grep -i mono`) — a shell's argv cannot
fake that.

### 3.3 The cartridge in `roms/` was a patched ROM, under the stock filename

This is the one that nearly cost the run's central claim, and it is here because
**nothing in the repo was checking.**

Decoding `Automap Plus.IPS` (issue #5) means applying a patch, and the patch went to
`roms/Legend of Zelda, The (USA) (Rev 1).nes` — the conventional path, under the
correct name — and stayed there. Nobody chose to swap the cartridge; a helper wrote
to the path whose whole purpose is "the one true cartridge", and the filename, which
is what every check in the project reads, never changed. The patched file is 2 bytes
*longer* (131,090 vs 131,088: the IPS writes 2 bytes past the end of Rev 1 and
every patcher pads with zeros), so it is not even the shape a size check expects.

The next day's replay of run6 died at frame 98,204 of 136,526:

```
RuntimeError: bridge connection lost: EmuHawk exit code 0 (0x00000000)
```

`exit code 0` is BizHawk's **orderly** shutdown — the harness's own comment at
`zelda/emulator.py:198` lists `0xC0000005` and `0xE0434352` as what a crash looks
like. So this reads as an emulator fault, and Mono, EGL and OOM are all somewhere
you would reasonably go looking. The cause was one `md5sum`:

```
a6d95f620d67c52b16686e382a219a27  roms/Legend of Zelda, The (USA) (Rev 1).nes
a6d95f620d67c52b16686e382a219a27  /tmp/opencode/hacked/automap.nes
```

Two things are worth more than the incident.

**A guard at the entry point protects only the entry point.** `setup_linux.sh` hashes
the ROM at install and refuses a mismatch, which is right and was three sessions too
early: the file was replaced long after the install, by a tool nobody was thinking
about. So the check now also lives where the mutation happens — `zelda/emulator.py`
carries the hash, and `BizHawk.__init__` writes the verdict into every run, as a
stderr banner and as the second line of that run's own log. The log line is the
durable one: a warning scrolls past, the log is what a reader meets weeks later.

**The verification path says no, not just something.** `replay.verify()` refuses a
cartridge that is not the verified one. A RAM fingerprint is only meaningful next to
the bytes it was computed from, so replaying against an unverified cartridge and
reporting `MISMATCH` is strictly worse than no check — it looks like a result.
`ZELDA_ALLOW_UNVERIFIED_ROM=1` is the override, and it exists because
`testing/compare_roms.py` proves a patch cosmetic *by* replaying both ROMs and
diffing work RAM; that comparison is meaningless unless it is allowed to run.

Worth knowing how invisible this was: after 30 frames the patched and stock ROMs
produce a **byte-identical** state line, `f30 ... lag=27`. The patch announces itself
at frame 98,204. No boot-and-play smoke test could ever have caught it, which is the
argument for hashing the file rather than judging the game.

Recovery was one line, because `rom-backup/Rev1.stock.nes` existed — a copy of a
131 KB file outside the working tree, made the day before for reasons I cannot now
reconstruct except that I was about to do something to `roms/`. Then the environment
was re-proven rather than assumed:

```
replayed 136526 frames -> f136526 mode=13/04 L9 room=32 pos=(136,136) dir=2 hp=8.5/13 rup=29 sword=3 lag=23405
  ram sha1 3115e31ff1a9b16e732160f81fe478a5052668ff
  MATCH
```

`cp -p` is a guess until the fingerprint agrees. Journal 47 has the full account.

### 3.4 Long emulator work does not belong in the main session

The arithmetic makes this unavoidable. A full-game replay is 136,526 frames at
~1,180 f/s — **two minutes** of wall clock. A route search is **~4.5 hours**. Any
session that owns the emulator owns the clock, and the two available responses are
both bad: block on it, or detach it and poll by hand.

Blocking is what killed the run in §3.2 — the tool call times out and takes the
process group with it. So the answer is a subagent: it launches the work detached,
polls the log, and hands back the result. The main session goes on with the next
issue while a two-minute replay happens in the background, and a four-hour search
costs one tool call instead of the session.

The part that is easy to get wrong is the reporting. A subagent that reports
"verification passed" has told you nothing you can cite. One that pastes

```
replayed 136526 frames -> f136526 mode=13/04 L9 room=32 pos=(136,136) dir=2 hp=8.5/13
  ram sha1 3115e31ff1a9b16e732160f81fe478a5052668ff
  MATCH
```

has handed back evidence, and the numbers are the entire deliverable — a rounded
"looks good" is worth exactly nothing. Give the agent the command, the expected
fingerprint and the log path, and make it read the log rather than infer the outcome
from the exit status, which for this harness lies (§3.3).

One emulator per agent. Concurrent instances contend for the same bridge port file
(`.bridge_port`), and the loser hangs silently rather than failing.

---

## 4. What was verified, and what that does and does not prove

### The verification that matters

`runs/run6` replays from power-on in a fresh emulator and lands on a byte-exact
RAM fingerprint:

```
replayed 136526 frames -> f136526 mode=13/04 L9 room=32 pos=(136,136) dir=2 hp=8.5/13 rup=29 sword=3 lag=23405
  ram sha1 3115e31ff1a9b16e732160f81fe478a5052668ff
  MATCH
```

This proves the claim that is actually load-bearing: **the input log alone drives
the emulator from power-on to the ending, with no memory editing and no
savestates.** The final frame is the game's completion screen in Ganon's Tower
with the silver sword.

It does *not* prove the AI authored the inputs rather than a person. That rests
on the search artefacts, which are strong but are the repo's own testimony:

- `search_log.txt` records **10,257 emulator attempts** across 324 segments
  (median 24 per segment, max 90, 36 segments needing ≥60). You cannot fabricate
  10,257 emulator attempts in a text file.
- journal 45 independently states "10,257 rehearsals against 8,294", which
  matches the log exactly.
- The input log has a machine-generation tell: **two buttons are never held on the
  same frame, in 105,781 button frames.** Not once. No diagonals. A human TASing
  would use `Up,Right`.

### Two numbers that look like they disagree, and do not

136,526 frames at the NES's 60.0988 Hz is 2271.7 s — **37:52**. The "37m02s" in
the filename is the game's own in-game timer, which runs behind real time.
Journal 45 confirms both: "Zelda at 37:02 ... credits at 37:52".

### The planner is trustworthy, which is unusual

`route_planner.py` is planning arithmetic on the decoded overworld map with no
emulator. It predicted route 3 at 41.33 min against 41.26 actual — 0.2% error.
Re-run from scratch it independently rediscovers route 4's dungeon order
(`3-1-4-8-2-5-7-6-9`) over 4 seeds and ~1.4M candidate orders. So route 4 was the
planner's answer, not a hand-pick, and planner output can be used to screen ideas
in seconds instead of searching for hours.

---

## 5. Judgement calls worth arguing with

**Did the run really "straight for 9"?** No, and this is the game's gate rather
than a harness limitation. `route_planner.py:181` encodes
`9: len(levels) == 8 and bow and arrows and bombs`, and the planner rejects
`['L9']` with *L9 before its key item*. Each dungeon holds a piece of the Triforce
of Power. It is only possible in the real game with glitches — screen scroll,
block clipping, recorder wrong warp — which this project's rules forbid, and
which the repo's own `knowledge/wr_route_comparison.md` confirms are what the
27:40 record uses. There is no plain glitchless any% category on the board at
all; the closest is 1:08:07.

**Is a naive 1-2-3-…-9 worth trying?** It is legal, and it is 8.6 minutes worse.
The dependency graph does not block it. The *rupee budget* does:

```
1-9, one rupee cave        INFEASIBLE: arrows: no money or already owned
1-9, rupee cave before L3  INFEASIBLE: r30_67 needs bombs   (bombs are L3's)
1-9, two rupee caves       feasible, 47.87 min
```

**Which "the dragon"?** Genuinely ambiguous, and the options differ by hours. The
harness labels `Level 6 (the Dragon)`, but Gleeok is an actual dragon boss and
appears *twice* — L4 and L8. Worth settling before spending a search, not after.

---

## 6. Still open

- **The rupee counter: settled, and the route planner is right.** `$66D` is the
  **displayed** rupee count, not an internal encoding. Verified by screenshotting
  the HUD at frames where the byte changes: at byte 2 the HUD reads `x2`, at byte
  106 `x106`, at byte 155 `x155`. Exact agreement at both small and large values.

  This closes a question that had been open here on the strength of a bad
  recollection — that the Blue Candle's 200-rupee sticker meant the model was
  using different units from the game. It does not. Measured off run6's own log,
  the real spends are:

  | purchase | before | after | spent | planner charges |
  |---|---|---|---|---|
  | Blue Candle | 106 | 46 | **60** | 60 |
  | arrows | 161 | 81 | **80** | 80 |
  | bait | 81 | 21 | **60** | 60 |

  Every price in `route_planner.py`'s `PRICE` table is confirmed against the
  emulator. The candle costs 60 in this game; the 200 figure was my error, not a
  discrepancy in the harness. The correct lesson is narrower than the one I first
  wrote: the counter is plain, and the planner is calibrated — so route costs
  quoted from it can be trusted at the scale of tens of rupees.

  One caveat worth carrying, learned the hard way in issue #10's measurements: this
  is a fact about *this cartridge*, not about the harness. Redux raises the cap to
  999, which does not fit in a byte, so there `$066D` becomes a derived hex
  approximation of purchasing power rather than a displayed count. A proof this
  carefully established still needed its scope written down.
- **`$0668`: settled, and it is not a purchase.** It is a treasure chest inside the
  dungeon. On run6 Link takes a map out of the chest in Level 3 room `$4C` at
  f9804 and Level 7 room `$18` at f92997; the bits latch because the bit *is* the
  level, and no rupees move because a chest has no price.

  The reason this was so hard to settle is the interesting part. Exactly one
  routine writes `$0668`, and it does so through a **single indexed store shared
  with three other variables** — `STA Items, Y` with `Items = $0657` serves the
  compass at `$0667`, the map at `$0668`, the level-9 pair at `$669`/`$66A` and
  the Triforce at `$0671`. So **no instruction in the cartridge names `$0668` as
  an operand**: a byte-pattern search for the operand pair `68 06` across all of
  PRG-ROM returns zero hits, and that is the correct answer rather than a failed
  search. A reader looking for a named operand never finds it.

  Three observables agree on the same frame, which is what separates this from a
  plausible story. `$00AB` is already `$17`, the room's item, from the frame the
  room was created. `$00BF` and `$0097` — the room-item object's state and Y — go
  to `$FF`, the signature at `Z_01.asm:4432-4434` with `X = $13`. And `$04E5`
  `StatusBarMapTrigger` pulses `00 → 01 → 00`; that byte has exactly two
  references in the whole disassembly, the map-slot write and a read-and-clear.
  The geometry then lands on the frame from the other side, off by one pixel:
  `TryTakeRoomItem` wants `|LinkX - $83| < 9`, and at f9803 that is 9 (rejected)
  and at f9804 it is 8 (accepted).

  `zelda/pickups.py` now reports these as real acquisitions rather than
  `unverified`, which raises the run's count from 30 to 32.
  `testing/probe_map_chest.py` measures it per frame. Journal 48 has the full
  account, including the retraction of a wrong address label printed in the same
  session.
- **Every "See also" link in `testing/*.md` was dead until this commit.**
  `make_doc.py` emitted `<script>.py.md` while writing `<stem>.md`, so all 182
  docs pointed at files that were never created — zero `*.py.md` files have ever
  existed in this tree. Small thing, but in a repo whose whole argument is that
  provenance cross-references resolve, it is not nothing.
- **`fairy_policy` is dead code.** `fullgame.py:860` is a complete, carefully
  written policy — it reads the fairy's live position from RAM and works around
  the pond trap where the path planner cannot route Link out. No route
  references it. The harness otherwise takes fairies reactively
  (`combat.py:618`, "only while hurt"), and `patch_single_l8_l9.py:10` records
  that a fairy detour was tried and cut as a net loss. Tracked as issue #1.
- **Upstream's credits contain a literal `[add]` placeholder** where the
  disassembly link belongs. Left alone, since it is upstream's file.
- **`route5.py` is specced but not built** — issue #2, and see `RUN-IDEAS.md`.

---

## 7. Walls, and what was actually behind them (2026-09-30)

"Stop him running into walls and blocks" is two different bugs wearing one coat, and only one of
them is about walls. `testing/probe_walls.py` measures both on Level 3's room `$4A` — a
`make_clear_policy`, so the code under test is `Fighter`, not the lookahead planner — with the wall
gate on and off (`ZELDA_NO_WALLS=1`) and the same seeds on both sides.

**Walking into them: real, and fixed.** `Fighter._move` stepped by the sign of the difference and
never asked the tile map, so a step into a wall cost one frame, moved nobody, and repeated until
`max_frames`. Measured: **26 to 277 refused steps** on one side, **0** on the other, depending on
the trajectory. `zelda/overworld.py`'s new `Screen` is the one cached read of the tile pattern
behind it — the pattern is 960 bytes and a fight asks the question four or five times a frame — and
a refused step is now *evidence*: the tile is learned as solid in `knowledge/tiles.json` with the
room and the pixel that proved it, in the same shape as every other line in there. Unknown tiles do
**not** block, on purpose: a fighter that stands still in a room it has not classified is a stall,
and a stall in a fight is how a segment spends its budget doing nothing.

**Swinging into them: not what it looked like.** The wasted-shot instrument said `solid=YES` on
nothing, and it was the instrument that was wrong. It tested the **target's own cell**; the thing a
strike gate prevents is a wall **between** Link and the target. It tests the line now, and reports
three separate causes instead of one — and the line version also says zero on this room.

**The real cost was the same mistake wearing a different coat: swinging at things the game will not
let Link hit.** Six beam swings at *one dead Gel* from 103 to 142 px away — 144 frames — because
`read_enemies` filters on the type byte and nothing else, so a corpse keeps its type, its slot and
its position until the game clears it. A slot at 0 HP is not a target now. The same gate covers a
Leever or Peahat still in its burrow (`ObjState` `$AC` != 3), which the navigator has always known
and the fighter never asked.

**What is still open, and it is a wall question rather than a fight one:** whether the sword *beam*
stops at a wall. Nothing here establishes it either way, so `Fighter.reach_clear` deliberately
does not gate beams on geometry — a wrong "it stops" would refuse beams that land. The wasted-shot
line can now answer it on any room that has both: a beam at a target with a wall between them and
no damage taken.

---

## 8. The sword's reach was backwards (2026-09-30)

The largest single defect found in the fighter, and it was found by refusing to believe the
instrument for a third time.

`REACH = 10`, `ALIGN = 4` and a box model were a reasonable reading of "two 16 px boxes touch when
their centres are 16–26 px apart". **The game does not implement that.** Z_01 implements a fixed
threshold on the centre-to-centre distance:

| routine | what it says |
|---|---|
| `CheckMonsterStabbingCollision` | a threshold per axis, **swapped on Link's facing**: horizontal `$0D`=$10 (16) across, `$0E`=$0C (12) down; vertical 12 across, 16 down |
| `CheckMonsterSlenderWeaponCollision2` | the sword's centre is `a:ObjX+8, a:ObjY+6` facing horizontally, `+6, +8` vertically |
| `GetObjectMiddle` | the monster's centre is `ObjX+8, ObjY+8`, or `ObjX+4` when `ObjAttr` (`$4BF`) bit `$40` is set |
| `DoObjectsCollideWithThresholds` | `|dx| >= threshold` → no hit; `|dy| >= threshold` → no hit |

So a horizontal swing connects iff `|ObjX − LinkX| < 16` and `|ObjY − LinkY + 2| < 12`. Sixteen is
the whole reach. The old model **refused to swing inside 16 px and reached to 26** — inside the
sword's range at one end, outside it at the other.

Measured on Level 3 room `$4A`, same seeds, `ZELDA_SWORD_GEOM=0` for the old one:

| | hits / aimed swings | room |
|---|---|---|
| box model | 33 / 115 (29%) | 1,500–3,000 frames, usually not cleared |
| cartridge's rule | 8 / 12 (67%) | 324–1,468 frames, cleared every time |

Every one of the old model's 82 misses was a swing at something 16–32 px away — a swing the cartridge
had already refused. The hits that did land were monsters that walked into the blade during the
13 frames of the animation.

**What is deliberately not changed:** the two Darknut routines. `hunt_darknut` and `darknut_ambush`
stand off at `16 + REACH − 4 = 22` px and strike as a Darknut walks past, and that distance was
chosen against the box model. Correcting the reach without re-deriving that strategy would leave
them walking to a post they cannot swing from, and there is **no Darknut checkpoint in this tree** to
measure the re-derivation on. `reach_box_model()` is kept, named, for exactly those two callers.

**Still unexplained, and left as an open item rather than a guess.** The Zol takes damage at 12–15 px
(3 hits in 14 swings) and **never** at 4–11 px (0 in 5). `attr $01`, invincibility timer `$00`,
metastate `$00` — every byte the cartridge's own "can this be hit" path checks says it should land.
The reach histogram the instrument now prints (`type@px: hits/misses`) is how to find out: a room
where the same type is hit at one distance and not at another is the measurement that settles it,
and `$4A` only has one Zol in it.

## 9. Two ways a segment can waste the run without failing (2026-10-01)

The run sat on one segment for half an hour and was not stuck on it in any interesting sense. `59_fight`
(Level 3, room `$59` -> `$69`) had **already been solved twice** and was still searching. From
`logs/gleeok_run8.log`, attempt 1 of the wrapper at 10:49:

```
  attempt 4: success 503 frames, hearts 3.0
  attempt 3: success 509 frames, hearts 3.0
  attempt 1: over budget (509 frames)
  attempt 2: over budget (509 frames)
  attempt 8: over budget (509 frames)
  attempt 5: over budget (508 frames)
  attempt 7: over budget (505 frames)
  attempt 6: over budget (502 frames)
```

Two successes in eight attempts, the second six frames better than the first, and nothing after it
beat 503. That is not a hard segment. The stop rule is what kept it there: with a full-health best
the search allows `patience` (14) non-improving attempts, and the "long rooms vary most" tier for a
best of 500+ frames turns that into `patience * FIGHT_PATIENCE * 2.5` = 35. Attempts 5-8 came back
at 502-509 - inside the noise of the room - and the remaining 27 attempts were queued. At the ~3.7
minutes an attempt of this segment costs, the segment had ~1.5 hours of polishing left to do on a
fight it had already won.

So two changes, both in the search's stop rules rather than in any policy.

**Take what we have, and write down what was left.** `search.ACCEPT_AFTER` (default 8, env
`ZELDA_ACCEPT_AFTER`, 0 restores the old rule) caps attempts-since-last-improvement. It is not
`patience` and not `tries`: those answer "how long may a segment search before it has anything",
this answers "how long may it keep polishing what it has". A segment whose line keeps improving is
never cut off - the counter resets on every improvement - so the cap only ever truncates the
fruitless tail. When it fires, `parallel_search` records why on the returned `Attempt.accepted` and
the runner writes `logs/flagged.json`: segment, frames, hearts, run, total frames, reason. Without
that file the cost of the cap is invisible, because the run looks identical whether a segment stopped
at 503 frames because nothing better exists or because we stopped asking.

**Do not sit still.** A segment that genuinely fails has a worse habit: `run_until.sh` restarts the
process, the run resumes the same checkpoint, and the search draws seeds `1000, 1001, ...` again -
the identical search, plan for plan, once per wrapper attempt. Nothing recorded that it happened.
Three things changed:

- a failure is written to `logs/stuck.json` (`fails`, `backprops`, room, hearts, when), and a segment
  that later passes is cleared from it;
- a retry draws seeds from `1000 + 1000 * fails`, so attempt 5 of a segment that has failed four
  times is a different sample of plans and not the same search again. `parallel_search` grew a
  `seed_base` parameter for exactly this;
- after `BACKPROP_AFTER` (2) failures the runner raises `NeedsBackprop` instead of the plain
  "segment failed" error, and `main()` rewinds **one segment**: it loads the previous segment's
  checkpoint - state *and* input prefix - drops it from `done`, and re-searches it. The decision that
  produced the failing state is drawn again and the failed segment is retried from a different one.
  `fullgame.main()`'s segment loop is now a `while` over an index because a `for` loop cannot go
  backwards.

`NeedsBackprop` is deliberately not the string `run_until.sh` stops on (`RuntimeError: segment`): a
segment worth rewinding is not a segment worth stopping for. When a rewind is impossible - it is the
first segment, or `MAX_BACKPROP` (2) rewinds are already spent - `main()` re-raises the plain error
so an actually-stuck run still stops instead of spinning.

Both new files are advisory and live in `logs/`, not `knowledge/`: they are per-run mutable state, the
ledger can be deleted and the flag list rebuilt from the log, and neither is knowledge about the
game. `ZELDA_ACCEPT_AFTER=0`, `ZELDA_BACKPROP_AFTER` and `ZELDA_MAX_BACKPROP` turn the behaviour off
or retune it without an edit.

`59_fight` is additionally in `FIRST_SUCCESS`, on the same evidence as `5b_bombs`: it takes its first
success rather than searching for a faster line, which costs the 6 frames between attempt 3's 509 and
attempt 4's 503. That is the owner's call, not a measurement - the measurement above only says the
attempts after the second one were not better.

**What this does not claim.** Nothing here makes a hard segment easier. A segment that cannot be
solved still fails; it now fails into a ledger and a one-segment rewind instead of into an identical
retry. The tests for both rules are `search`-level fakes with no emulator (`tries`/patience/seed
behaviour) and runner-level ledger tests - the real proof for `59_fight` is that it passes.

## 10. The planner knew a Darknut was killable and not that it was shielded (2026-10-01)

Watching `69_stairs` run: all four scouts walked into a knight and swung at its face. The route's own
caption for that room says the opposite plan - "None of these eight Darknuts needs to die. Dash
through them to the staircase on the east side" - so this was not a room the planner could not solve.

The knowledge was in the tree and simply was not connected to the code making the decision.
`combat.shield_side` has said since the Darknut hunter was written that a swing along the axis a
knight faces is stopped by its shield and only a side or back hit lands. `lookahead.killable` says a
Darknut is killable - correctly, that is a fact about the monster. What nobody asked was whether
*this* swing would land, so `plan_reach` offered a swing in all four directions whenever anything
killable was within 36 px and scored the result by what happened afterwards. A swing into a shield
earns no kill credit and should have lost on the score, but it also *moves Link*, and movement is most
of what that score is made of.

`lookahead.swing_connects` now asks the missing question with the fact that already existed: a swing is
offered only in a direction where `sword_reach` finds something and, for a Darknut, `shield_side`
says the blade is not on the shield. `ZELDA_SHIELD_AWARE=0` restores the old question;
`testing/probe_69_stairs.py` A/Bs them on the real room from `ckpt_gleeok_59_fight`, four seeds a side:

| | passes | deaths | sword frames per attempt | frames of the passes |
|---|---|---|---|---|
| blind | 3/4 | 1 | 46, 26, 36, 18 | 818, 639, 394 |
| shield-aware | 2/4 | **0** | 0, 2, 0, 0 | 505, 559 |
| `transit=True` | 1/4 | 2 | 0 | 355 |

**The caption is not an argument for `transit`.** Taking "none of these eight needs to die" literally
- never offer the sword, stop pricing damage - is the *worst* of the three: 1 pass and 2 deaths in four
attempts, dead at 176 and 323 frames. `transit` deletes the damage term along with the swing, and a
Darknut hurts from every side; eight of them is not a corridor. So neither eight-Darknut leg asks for
`transit`, and the sword stays priced. The parameter is kept, with the measurement in its docstring,
because it is right for a leg that is only a journey and this room is not one.

Four seeds cannot rank 2/4 against 3/4. They can rank the deaths and the sword, and those are not
close. What is left open: two shield-aware attempts failed *without dying*, ending in mode `$10` and
mode `$07` instead of the cellar in mode `$09` - a stairwell transition that did not finish. That is
the next thing to look at in this room and it is not a shield problem.

## 11. What each window is for, and why a parked one is black (2026-10-01)

Two things came out of watching five emulator windows side by side.

**The windows now say what they are for.** Four scout windows showing the same room are the same
picture, and the room is not the interesting part: a search that has never found a line and a search
that has one and is trying to beat it look identical and want opposite things from the person
watching - the first needs more attempts, the second needs to be left alone. So `bridge.lua` grew a
`phase <label>` command and draws it right-aligned on the HUD line, coloured by phase, and
`parallel_search` sends one per attempt from the state it already keeps:

| label | meaning | colour |
|---|---|---|
| `BASELINE` | no success yet - every attempt is still looking for a line | green |
| `POLISH` | we have a line and are spending attempts trying to beat it | amber |
| `DONE` | decided: converged, capped by ACCEPT_AFTER, out of tries, or out of patience | grey |

MAIN gets `REPLAY` while it plays a winner in and `DONE` after the segment commits. Right-aligned
because the room line already grows rightward with the boss read-out, and a phase label in the middle
would be overwritten on exactly the segments where the phase matters most. This replaces the attempt
counter that used to be on that line and was removed as clutter - a number told you how many attempts
had run, not what the search was doing with them.

**What the label can and cannot do, measured rather than assumed.** `BASELINE` and `POLISH` both showed
up on the live run within a minute of each other, which is the case that matters: a scout is being
stepped constantly while it searches, so the label paints on its next frame. `DONE` mostly does not
appear, and the reason is the same one as the black MAIN window below: a parked window composites the
overlay only when it renders a real frame. Setting the phase does not repaint it (`pcall(hud)` in the
command handler: no), and neither does `step 0` - measured, on a real checkpoint in a parked window:

| after | phase visible |
|---|---|
| `step 40` (game painted) | no label set yet |
| `phase polish`, zero frames | no |
| `phase done` + `step 0` | no |
| one real frame (`step 1`) | **DONE**, in grey |

So a scout window freezes on the last phase it drew, which after a search is BASELINE or POLISH, and
between searches the window is a still of what the search was doing when it stopped. That is honest
enough to read - "POLISH" on all four windows with the log's `(early stop after N attempts)` is a
finished search - and the log is where the ending is actually stated. MAIN's labels do show, because
MAIN is stepped for every frame of the replay.

**The black window is not a Mono rendering bug.** This corrects section 9's guess. The bridge draws
the HUD from its `step` handler ("the bridge holds the main thread waiting for commands, so there is
no idle frame loop to draw from; `step` is the heartbeat"), which means an emulator nobody is stepping
does not repaint at all: MAIN sits parked and black through every search, and a scout that is resized
while parked shows a stale surface - black after a state load, or yesterday's colours - until its next
step. That explains every observation that was attributed to surface corruption, including the two
that looked most like corruption: a greyscale scout that healed on the next fullscreen round-trip
(it was stepping, so it repainted) and a MAIN that no Expose, workspace remap or resize would ever
paint (it was not stepping). i3 still floats the BizHawk windows rather than tiling them, so a parked
window is never resized into a stale surface and the mosaic stays deterministic - but the reason is
avoiding a stale surface, not surviving a broken one.

Consequence for reading the mosaic: a black MAIN window is normal between segments and says nothing
about the run. The phase label is the thing to read.

## 12. The old man could not be tested, and the reason is a checkpoint that was never saved (2026-10-01)

The owner, watching the run sit on the White Sword approach: *"you could test if the old man is in
there by going back and looking. btw if you had full life you would be in revenge mode. but since you
are not you will flee."* Two claims, one of them about behaviour, neither tested. `testing/probe_old_man.py`
goes back and looks, and what it found is mostly about what is missing.

**There is no state from inside that cave.** Every `*_white_sword` checkpoint is taken after the segment
succeeded - Link already has the sword (`$657 = 2`) and the item slot reads `$BF = FF`, nothing lying -
so in every saved state the old man has already been dealt with. And the harness cannot invent one:
`BizHawk` has no write primitive at all, deliberately, because the input log is the artifact and poking
`$66F` to give Link a heart bar would be a run that never happened. So the probe's other job is to
leave one behind: it watches for the frame Link is inside the cave with the sword still untaken and
saves `ckpt_probe_old_man_*_inside`. The first run died on a Fatal IO error against the nested X server
before it got there; the state does not exist yet.

**What two real states do say.** `ckpt_gleeok_ws_0a` (this route, 3.5/5) against `ckpt_fullgame_ws_0a`
(run6, 5.0/5), same screen, same policy, `white_sword`:

| side | hearts | attempts | result |
|---|---|---|---|
| gleeok | 3.5/5 | 2 | died on the approach both times, never got inside |
| fullgame | 5.0/5 | 2 | seed 1000 **took the sword** (3521 frames, no hearts lost); seed 1001 died |

So the segment is a heart-margin problem and not an old-man problem - which is what `search.py`'s
`HEART_VALUE` note and `testing/probe_white_sword_bomb.py` already said about this screen and its Blue
Lynel. Both sides die at y≈93 on the screen, hundreds of frames short of the cave mouth, so neither
run ever met the old man and this measurement says nothing about him either way. It is not the
experiment the owner's note asks for, and it is recorded as the negative result it is.

**What would make it an experiment.** Three things, in order: a saved state from inside the cave before
the pickup (the probe now produces one when it can get in); a way to vary the heart bar from a single
state, which needs a RAM write the harness deliberately does not have, so it wants two checkpoints
differing only in `$66F`; and a way to tell "the old man is blocking" from "Link is frozen typing his
line", because journal/15's 140-frame freeze and a man who will not move look identical from outside.
That third one is the detection the owner's "going back and looking" is really asking for: he is an
object in the same twenty slots as his torches (type 0x40) and the item, and nothing in the tree reads
that row - `read_room_item` reads one slot of it. Until something reads it, the harness can only tell
"this doorway will not open", which is the belief that cost sixty identical failures in journal/15.

## 13. A scout whose emulator died was dead for the rest of the search (2026-10-01)

Asked while watching the mosaic: *"are you restarting them if they go dead?"* No. `parallel_search`
caught the bridge loss, logged `scout k lost its emulator ... that worker is done`, and returned from
the worker thread. That scout was then dead until the whole `fullgame.py` process exited - which the
wrapper only does on a real failure. So a search that lost two of four workers spent its remaining
budget three-wide while the log line above it still said four scouts, and on a phase-locked boss
(`search.ENTER_SPREAD` divides the 0-90 frame entry window by the *configured* scout count) the dead
scout's quarter of the cycle went unsampled for the rest of that fight. Eight deaths in one session.

Three changes, and the middle one was found by the test rather than by reading:

1. **The worker asks for a replacement instead of stopping.** The runner owns the emulators, so
   `Run.respawn_scout(k)` constructs a fresh `BizHawk` and `Navigator` in that slot - in place, because
   `parallel_search` holds the same list objects - and `parallel_search` re-binds its *locals* and
   rebuilds the policy, which had closed over the dead Navigator. Capped by `search.RESPAWN` (2 per
   scout per search): a respawn builds a whole EmuHawk and waits up to 60s for its bridge, so with the
   display gone four scouts times 60s would turn a dead display into a slow one. Passing no callback
   keeps the old behaviour exactly, which is what the test asserts for the no-callback case.

2. **A death during `emu.load()` was not caught at all.** The error handling wrapped only the policy
   call, so an emulator that died while loading the segment's start state killed its worker thread
   outright - no `lost its emulator` line, no counter, no replacement, one fewer scout and nothing in
   the log to explain it. This is the failure mode the user was asking about, and the *worse* half of
   it was invisible. The whole attempt - load, settle steps, policy call - is inside the handling now,
   so all three read the same.

3. **The summary line now separates deaths from replacements.** `2 scout emulator(s) died mid-search,
   1 replaced; the search ran on 3 of 4 for at least part of it, so the phase window was covered
   unevenly`. "A scout died" and "a scout died and was replaced" are different things to read in an
   overnight log, and the old line could not tell them apart.

The tests for all three use fake scouts with no emulator: two that raise `RuntimeError` on their second
load, a respawn callback, and assertions that both were replaced, that the search still produced a
winner, and that without a callback both workers stop as before. One thing that test had to be taught:
a fake attempt that returns instantly lets one worker take every attempt index before the other thread
is ever scheduled - the GIL, not a bug - so the fake sleeps to hand it over. A real attempt spends
minutes inside the emulator with the GIL released, which is the case that matters.

## 14. The route, not the segment: `deliver` leaves Link in a cave and the next segment wanted a dock (2026-10-02)

The run named `gleeok` on route 5 stopped at `RuntimeError: segment l2_sail failed` on 2026-10-01
20:59:47 with 161 segments and 60,589 frames banked. Every one of `l2_sail`'s sixty attempts read
the same two lines:

```
  attempt 3: fail: no dock on this screen (3 frames)
  ...
  no success; most common: 58x fail: no dock on this screen @ room 0A L0
```

Sixty identical failures is the shape of a segment that was never going to succeed, and the
mechanism is in the shape of the route rather than in `dock_policy`. `head.deliver_policy` walks
**into** the sword cave - `delivered_test` insists on mode `$0B`, sub 0, on the item row, on the
White Sword's x, so that is exactly the state the segment is required to leave behind - and the next
segment in `route5.py` was `take("l2_sail")`, whose policy is `dock_policy`. There is no dock
inside a cave. The policy was right and the route was wrong, and it is wrong **one segment further
on as well**, which is the part that is easy to miss:

`route5.py`'s "NEW LEG 2" planned the walk to Level 1's door from **0x45, the island bank** -
`l2_sail` rides the raft to 0x55 and five lanes take 0x55 -> 0x56 -> 0x46 -> 0x47 -> 0x48 -> 0x38 ->
0x37. That is correct for route 4, where `warp_L4` leaves Link on the island. Route 5 is not on the
island when it gets there; it is on 0x0A having just walked fifty crossings home. Asked directly:

```
owroute.leg((0x0A, 192, 141), 0x55) -> NO PATH      # 12 crossings exist the other way
owroute.leg((0x0A, 192, 141), 0x45) -> NO PATH      # 0x45 is only reachable by the raft
owroute.leg((0x0A, 192, 141), 0x37) -> 2,038 frames, 8 crossings
```

So the entire raft leg was the wrong shape for where this route actually is, not one missing lane,
and no amount of search would have found it.

**The fix, and what it cost to be sure of.** Three things, in `zelda/head.py` and `route5.py`, all
measured from the run's own bookmark `states/ckpt_gleeok_deliver.State` (`testing/probe_head_exit.py`):

1. **A third phase to the head's route.** `head.LEAVE` / `leave_policy` / `left_test` walk back out
   of the cave, reusing route 4's own `bot.exit_cave_down`. Measured **172 frames** from (120,141)
   inside to (32,91) on 0x0A. Its hardcoded corridor `x=112` belongs to the candle cave at 0x0C and
   has never been checked against the sword cave; a bare hold of DOWN also works and is 13 frames
   quicker (159 frames, out at (32,77)), so the corridor is wider than the one column the routine
   walks to. Reuse beat a new routine by 13 frames and 13 frames is not the thing to spend a new
   function on - but the 112 is a measured fact now and was an assumption an hour ago.

2. **The obvious alternative was measured and rejected.**
   `Navigator.exit_screen` has a mode-`$0B` branch that walks out of a cave before crossing, so the
   obvious fix is to delete the exit segment and let the first lane do it. It does not work: the
   branch holds DOWN for up to 400 frames, and the overworld takes over mid-hold and keeps going
   south. Measured **739 frames, arriving in 0x1A** - it eats the lane it was supposed to enable.
   That is the kind of implicit behaviour worth knowing about rather than inheriting.

3. **Eight crossings, and seven of them were already walked.** `hd_0a_1a hd_1a_19 hd_19_18 hd_18_17
   hd_17_27 hd_27_28 hd_28_38 hd_38_37`, each pinned, every seam's two ends checked against
   `owroute.free()` before anything was written - the check the other two lane groups in this file
   record, because a wrong coordinate does not fail, it just searches slowly. Seven are the **reverse
   of legs this route walked on the way home** (`rv_leg_47..50`, `rv_leg_43..46`), so they are
   known-good in one direction; 0x38 -> 0x37 is the only new seam. Then walked for real, chained, from
   the bookmark: **all eight landed where they were asked to, 2,555 frames including the walk out**,
   four and a half hearts spent on Octoroks on the road. And run again through the actual search
   machinery (`Run.segment`, four scouts, jitter on): `head_exit` 176 frames, `hd_0a_1a` 575,
   `hd_1a_19` 411, `hd_19_18` 316, `hd_18_17` 296, `hd_17_27` 200 - the first success of each, not the
   best.

**What is deliberately not claimed.** The 2,038 and 2,555 are one walk with one seed's worth of
jitter, and a search beat both of them on five of the six segments above; they establish that the
road exists and is connected, not that it is quick. The eight lanes can still lose a search to an
Octorok, which is what the 1.5 hearts on this walk was. And nothing here says anything about the rest
of route 5 past Level 1's door, which has never been run.

**One thing found on the way.** Two attempts in the archived four-hour log end
`error: ValueError: invalid literal for int() with base 10: ''` from `State.parse`, and others end
`error: ValueError: non-hexadecimal number found in ...` from `BizHawk.ram`. Both are a malformed
bridge REPLY - a token with no `=` in it, or hex that is not hex - which is the signature of the
reply stream coming out of step with the commands, and `bridge.lua`'s `send()` does not check what
`conn:send` returned.

Measured over the whole of `gleeok_run8.log`: **12 error attempts in 590, or 2.0%**, seven of them the
`int('')` form and five the non-hex form. They are not spread evenly and they are not where I first
looked: the four segments that had any were `l4_61` (1 of 6), `l4_b30` (1 of 7), `l4_32` (2 of 22)
and `l4_70` (1 of 26) - all four are fights, not crossings, and a fight is where the search makes
the most `state` calls per attempt. My first estimate, from a scratch replay under heavy load, was
"one attempt in three of a crossing segment"; that was wrong by a factor of fifteen and it is
retracted here rather than left in a comment.

One of the twelve was not an attempt at all. At `search.py:479 s = emu.state()` - the state read
AFTER the policy returns, which is outside the error handling section 13 widened - an unreadable
reply killed the worker thread outright: no `lost its emulator` line, no counter, no replacement, and
a `ValueError` traceback in the middle of another segment's attempts. Same class of
uncaught-exception-in-the-worker, one line further on.

## 15. An unreadable bridge reply cost 2% of attempts and named nothing (2026-10-02)

Section 14 turned up an error in the archived run's log that has nothing to do with the route:
`error: ValueError: invalid literal for int() with base 10: ''`. Chased because two attempts were
wasted on it every hundred, and because one of the twelve was not an attempt at all.

**Where it comes from, as far as the evidence goes.** `State.parse` does `int(v)` on the right of
every `k=v` token in the bridge's `state` line, so a reply that is a state line **truncated
mid-token** raises exactly that - `mode=` gives `int('')`. And `BizHawk.ram` does
`bytes.fromhex(...)`, so a reply that is not hex at all - `non-hexadecimal number found in f`, where
the `f` is the first character of `frame=` - is a **state line arriving where a `ram` reply was
expected**. Both are the same thing: the request/reply stream came out of step, or one line was cut
short. Measured over the whole of `gleeok_run8.log`: **12 in 590 attempts, 2.0%**, seven the
`int('')` form and five the non-hex form, and all four segments that had any were fights.

**What it is not.** Not two writers on one socket: the run gives each scout its own emulator and one
thread. Not `msave`: `memorysavestate.savecorestate()` answers with a GUID
(`17f1db10-c491-4f26-b6f7-ffdf264c4608`, 36 characters, no newline), measured, and the stream stayed
in step across two of them. Not the socket in general: **65,149 commands against a live bridge on one
thread over 900s, zero malformed** (`testing/probe_bridge_replies.py`, first version - a synthetic
mix of `state`/`step`/`ram`). So the trigger is something about the run rather than about the socket.

**Then the check caught two, live, and named both sides.** Within four minutes of the run picking the
check up:

```
scout 1: the bridge's answer to 'step 12 -' is not an answer to it: 'ok'
scout 3: the bridge's answer to 'step 12 -' is not an answer to it: 'ok'
```

`'ok'` is what `load`, `mload`, `mfree`, `phase` and `attempt` answer, and a fight is a storm of
`mload`/`mfree` - `static_slots` alone does msave / step 10 / mload / mfree and `plan_fight` does it
per branch. So what these two say is narrower and more useful than "a reply was garbled": **a reply
that should have arrived did not, and the next command read it.** That is the same damage as the
`ValueError` and the same damage as the 115 `cannot read from timed out object` in one search - one
unanswered command - seen from three directions.

**The change, and what it is not.** `bridge.lua`'s `send()` set a 5s timeout, called
`conn:send(line .. "\n")` and **threw away the return value**, which in LuaSocket is the number of
bytes actually written. It now loops until the whole line is out. That is a mechanism-based fix and it
is labelled as one: it removes short writes, it does not explain what caused one, and it cannot fix a
send that writes nothing at all - that leaves Python blocked on `readline` until its own 120s timeout,
which is the other symptom in the same log. On loopback with a 5s timeout and a reply of a few hundred
bytes the loop runs exactly once, so the only behaviour it changes is the case that was broken.

**What is fixed is the invisibility, and the one place it was fatal.** `BizHawk.cmd` now checks the
reply against the command it sent and raises `BadReply` naming both - `the bridge's answer to 'state'
is not an answer to it: 'frame=43620 mode=05 sub=00 ... mode='` - instead of letting a parser three
frames downstream report `int('')`. The check is deliberately one-sided: only shapes that cannot
possibly be right are rejected, because a check that is wrong in the strict direction costs a whole
emulator. `testing/probe_bridge_replies.py` (second version) runs the **real** Gleeok fight from
`states/ckpt_gleeok_start.State` through `parallel_search`, four scouts wide with the 0-90 phase
spread, wrapping `cmd` so it sees every reply the harness asks for: **111,799 replies, 0 rejected.**
That is the whole claim, and it is the claim the check has to be able to make.

And the fatal one: `s = emu.state()` after an attempt - the state read that decides whether the
attempt succeeded - sits *outside* the error handling section 13 widened, so an unreadable reply there
killed the worker thread outright. The archived log has exactly that, at `search.py:479`, with a
`ValueError` traceback in the middle of another segment's attempts and no `lost its emulator` line. It
is read through the same handling now.

**Deliberately not done: replacing the emulator.** A garbled reply *might* mean the stream is out of
step - in which case that scout is finished - and it might be one truncated line, which 111,799 clean
replies say is commoner. Respawning costs an EmuHawk launch and up to 60s waiting for its bridge, at a
measured 2% of attempts, so it would buy a scout that usually did not need it. The attempt is lost,
the scout lives, and the count is on its own line at the end of every search -
`N attempt(s) lost to a bridge reply that could not be read (x% of them); the emulators were kept` -
because without it a search can sit at 98% of its attempts for hours with nothing in the log to say so.
