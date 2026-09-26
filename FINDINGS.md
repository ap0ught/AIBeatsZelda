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
- **`fairy_policy` is dead code.** `fullgame.py:860` is a complete, carefully
  written policy — it reads the fairy's live position from RAM and works around
  the pond trap where the path planner cannot route Link out. No route
  references it. The harness otherwise takes fairies reactively
  (`combat.py:618`, "only while hurt"), and `patch_single_l8_l9.py:10` records
  that a fairy detour was tried and cut as a net loss. Tracked as issue #1.
- **Upstream's credits contain a literal `[add]` placeholder** where the
  disassembly link belongs. Left alone, since it is upstream's file.
- **`route5.py` is specced but not built** — issue #2, and see `RUN-IDEAS.md`.
