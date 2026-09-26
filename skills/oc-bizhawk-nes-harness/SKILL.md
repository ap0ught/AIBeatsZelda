---
name: oc-bizhawk-nes-harness
description: Drive BizHawk from Linux for TAS-style automated play, replay verification, and parallel search. Covers the Mono-based linux-x64 build, building LuaSocket core.so for NLua's embedded Lua 5.4, the mandatory gtk2 dependency and its silent X11 failure, why video recording never connects, the no-yield bridge discipline that makes replays deterministic, detaching long runs and delegating them to a subagent, and the launch-time ROM hash check that a patched cartridge in roms/ defeats. Use when automating BizHawk, scripting a Lua bridge over TCP, verifying an input log by RAM fingerprint, or searching NES gameplay with multiple emulator instances.
license: MIT
metadata:
  tags: bizhawk, tas, emulator, nes, mono, nl, lua, luasocket, nlua, gtk2, x11, automation, replay, determinism, search, parallel, rom, md5
  category: emulation
  requires_toolsets: terminal
---

# Driving BizHawk from Linux

Everything here was established against BizHawk 2.11.1 on CachyOS (Arch), Mono
6.12, and a Python harness for *The Legend of Zelda* (NES). The worked example is
in `~/code/games/aibeatszelda` (`ap0ught/AIBeatsZelda`) — read its
`FINDINGS.md` for the full narrative and `zelda/emulator.py` for the reference
implementation.

## The "linux-x64" build is the Windows build under Mono

`BizHawk-<ver>-linux-x64.tar.gz` unpacks to a tree containing `EmuHawk.exe` and
`EmuHawkMono.sh`. There is no native binary. The wrapper is:

```sh
export LD_LIBRARY_PATH="$PWD/dll:$PWD:$libpath"
export MONO_WINFORMS_XIM_STYLE=disabled
exec mono EmuHawk.exe "$@"
```

So a harness must exec the **wrapper**, not `EmuHawk.exe`. If you keep the
upstream folder name (`BizHawk-<ver>-win-x64`) you only have to change the launch,
not every path that derives the emulator directory.

Its `libpath` comes from `lsb_release`, and unknown distros fall through to
`/usr/lib` with a printed warning. Harmless on Arch; fatal on a distro that does
not use `/usr/lib`. Check that line if the emulator cannot find its own DLLs.

## LuaSocket: build it, and do not link liblua

`bridge.lua` typically opens with `require('socket.core')` to talk to the
controlling process over TCP. BizHawk ships `Lua/socket/core.dll` — a Windows
native DLL — and **no Linux equivalent**, so the script dies on the require and
the harness waits out its full connect timeout for a peer that will never arrive.

Do not guess whether a native Lua module can even load here. Answer it in ninety
seconds with a throwaway C# program against BizHawk's own `NLua.dll`:

```csharp
Lua lua = new Lua();                        // NLua's own embedded runtime
lua.DoString("package.cpath = '/tmp/probe/?.so;' .. package.cpath");
lua.DoString("return require('testmod')");  // a trivial C module: open a socket, send, receive
```

That establishes the three things that matter: which Lua NLua embeds
(`_VERSION` — it was 5.4, so use the `lua5.4` headers), whether `.so` modules load
at all under Mono, and whether the host exports the `lua_*` symbols. It did, so
the module is built **without** `-llua54` and its undefined `lua_*` references
bind to the host at `dlopen`:

```sh
gcc -O2 -fPIC -shared -std=gnu99 -DLUASOCKET_INET \
    -DLUASOCKET_API='__attribute__((visibility("default"))) extern' \
    -I/usr/include/lua5.4 -o BizHawk-*/Lua/socket/core.so \
    luasocket.c auxiliar.c buffer.c compat.c except.c inet.c io.c mime.c \
    options.c select.c timeout.c tcp.c udp.c usocket.c unix.c unixstream.c unixdgram.c
```

Linking `liblua54` would be the reflexive move and is **wrong**: it gives the
module a private second copy of the Lua runtime while NLua holds another. It
reads like a forgotten flag. LuaSocket's own `makefile` also omits `unixstream.c`
and `unixdgram.c` from some targets and the link fails on `unixstream_open`.

Place the result where BizHawk already looks: `Lua/socket/core.so`.

## gtk2 is mandatory, and its absence does not look like a missing dependency

Without `libgtk-x11-2.0.so.0`, Mono's System.Windows.Forms falls back to its
built-in X11 driver, which throws an `XErrorEvent` (`BadMatch`) from the
application's input thread about thirty seconds into play.

**The process does not exit.** The window stays up, audio keeps flowing, and the
Lua bridge simply stops being serviced, so the controller reports a lost
connection. That is indistinguishable from the emulator crashing, which is what a
restart supervisor exists to handle — so you go hunting in the wrong place.

The actual clue is a startup line that looks like cosmetics:

```
Gtk not found (missing LD_LIBRARY_PATH to libgtk-x11-2.0.so.0?), using built-in colorscheme
```

`pacman -S gtk2` (or your distro's equivalent). Generalised lesson: **on this
stack a Mono WinForms X11 error kills the thread, not the process.** A window that
is still up is not evidence that things are fine.

## Video recording never reaches the bridge

Anything passing `record=<name>` dies at startup. `--dump-type=ffmpeg` takes
BizHawk's display/GL path *before* the Lua bridge, and under Mono it never gets
that far: the launcher log stops dead after the GTK theme warning, with no
exception and no EGL error. ffmpeg being installed is not the issue — it is
BizHawk's writer path.

A more confusing sighting of the same fault surfaced as
`EGL_BAD_ACCESS: Unable to make EGL context current` inside
`DisplayManagerBase.Dispose` — i.e. the real error was happening at *teardown*,
which is a genuinely misleading place to be sent.

Search and replay do not need video, so give the harness an explicit kill switch
(`ZELDA_RECORD=0`) rather than trying to repair the writer. The recorder also
triggers a Windows-only "Really quit?" dialog handler that is dead code here.

## The bridge discipline that makes replays provable

This is the single most important thing in the whole harness, and it is easy to
get wrong in a way that produces plausible-looking wrong runs.

**A Lua bridge must block for the next command, never yield back to the
emulator.** A bridge that yields on a timer lets the core keep running between
commands. Whenever the controller is busy — which is exactly what happens while a
search grinds through a room — the game advances with nobody holding any buttons
and enemies keep moving. The run still completes; it is just not the run you
think it is.

The symptom is "desync": a scout finds a clean solution, the main emulator plays
exactly those inputs from exactly that saved state, and gets a different result.
Same state, same inputs, different outcome, in a deterministic emulator.

Debug it in this order, because the emulator is innocent far more often than you
expect:

1. Replay the same inputs from the same bookmark twice, in one instance and in a
   second. Every hash matching exonerates the emulator.
2. **Count frames.** Compare how many times the controller stepped against the
   game's own frame counter. In the worked example: Python stepped 1690 times,
   the game was at 1987 — three hundred frames nobody asked for.

The rule that falls out and should be written into the harness: every frame of
the run must be one the script explicitly asked for.

## Verify by RAM fingerprint, not by exit code

For any run you intend to claim, replay the input log from power-on in a *fresh*
emulator and SHA-1 all 2 KB of work RAM. Match against the expected value:

```python
import hashlib
fp = hashlib.sha1(emu.ram(0, 0x800)).hexdigest()
```

This proves the load-bearing claim — the input log alone drives the emulator to
the stated end state, with no memory editing and no savestates — and it costs one
extra emulator launch. It does **not** prove who authored the inputs; say so
explicitly rather than letting the two blur.

Two traps around this:

- **A hybrid log still says MATCH.** Resuming a checkpoint from a different route
  keeps the old input prefix and skips matching segment names, and the result is
  self-consistent, so the fingerprint agrees. Refuse to resume across route
  changes rather than trusting the hash.
- **Savestates are version-locked.** A BizHawk `.State` only loads in the exact
  build that wrote it. Pin the emulator version anywhere states are shared.

## Unthrottled vs realtime, and the difference in what you are testing

`emu.limitframerate(true)` paces the core inside a step call, so a batch of 900
frames takes 15 real seconds. That is the whole mechanism behind realtime
playback — no special mode needed.

- **Unthrottled** (`limitframerate(false)`, usually with sound off) is for
  search and verification. NES cores sustain several hundred fps stepping, so a
  136k-frame replay takes minutes.
- **Throttled** is for watching. Measured 36,000 frames in 601 s = 59.9 fps
  against the NES's 60.0988 Hz; the sub-1% shortfall is the per-step socket round
  trip.

Be precise about frame arithmetic when reporting results: 136,526 frames at
60.0988 Hz is 2271.7 s = 37:52. A run described as "37:02" is quoting the *game's
own in-game timer*, which runs behind real time. Both numbers are correct and
they are not interchangeable.

If sound is off in throttled mode, check the bridge: a `fast` command that disables
sound for search must have a matching path that re-enables it, or realtime
playback comes back silent.

## Parallel search: emulation is socket I/O, so the GIL is not the bottleneck

One thread per scout, attempts handed out by seed. Because stepping is socket
traffic rather than computation, K scouts genuinely run K attempts in roughly the
time of one — not a linear speedup in CPU terms, a real one in attempts.

Practical notes:

- Scouts load copies of the main state; share the savestate on disk.
- Clean the battery save only on the main instance, or you will delete the
  savestate the scouts are about to load.
- Have the ranking include hearts, not just frames. A sentinel meaning "full
  health at zero frames" is a neat way to express it.
- When a segment genuinely fails (as opposed to the emulator dying), **stop**.
  A supervisor that retries forever will grind through a real bug all night.
- Six concurrent instances is a meaningfully different workload from one. Soak it
  before committing hours.
- There is usually no per-instance lock on the battery-save file, so two runs at
  once will trample each other. `mkdir` as a lock is atomic and worth adding.

## Long runs belong in a subagent, not in the main conversation

> **Anything that drives an emulator for more than a few seconds is delegated. The main
> session starts it detached and goes on with other work.**

The costs are concrete, not stylistic. A full-game replay here is 136,526 frames at
~1,180 f/s — about two minutes of wall clock. A search is ~4.5 hours. If the main
conversation owns that, then every minute of it is a minute of not working: the
alternatives are both bad. Block on it with `sleep`/`tail` and the tool call hits its
timeout — which is precisely how the run in the next section died. Detach it and poll
from the main session and you are re-implementing a job queue by hand, in a shell,
while the thing you actually wanted to work on sits untouched.

So: **subagent in, detached process out.** The agent's only job is to launch, poll,
and report the result *verbatim* — the frame count, the state line, the fingerprint,
and the MATCH/MISMATCH. It must not summarise those into a paraphrase, because the
number is the entire deliverable and a rounded "looks good" is worth nothing.

The reporting rule is the part that gets skipped and the part that matters. A
subagent that reports "verification passed" has told you nothing you can cite; one
that pastes

```
replayed 136526 frames -> f136526 mode=13/04 L9 room=32 pos=(136,136) dir=2 hp=8.5/13
  ram sha1 3115e31ff1a9b16e732160f81fe478a5052668ff
  MATCH
```

has handed back evidence. Give the agent the exact command, the exact expected
fingerprint, and the log path, and make it read the log rather than infer the
outcome from the exit status — for this harness the exit status lies (see below).

One emulator per agent unless the work is genuinely parallel. Concurrent BizHawk
instances contend for the same bridge port file, and the second launch to find a
held port is the one that hangs silently.

## Do not launch a long run as a background job of a waiting shell

```sh
# wrong: the tool/shell is torn down, the process group dies with it
nohup python3 run.py > out.log 2>&1 &
sleep 90; tail out.log

# right
setsid nohup python3 -u run.py > /tmp/run.log 2>&1 < /dev/null & disown
```

The failure is silent and convincing: no traceback, every emulator gone, and the
logs ending mid-segment looking perfectly healthy. That is the same signature as
the emulator crash your supervisor handles, so it sends you diagnosing Mono, EGL
and OOM instead of your own launch. `python3 -u` matters independently — with
output piped and the process killed, the buffer goes with it.

Two adjacent self-inflicted wounds worth memorising:

- `pkill -f "EmuHawk.exe"` **kills the shell running it**, because that shell's
  own command line contains the pattern. It presents as the emulator hanging.
- Counting matching processes with `pgrep -f '<pattern>'` inside a command that
  itself contains `<pattern>` returns a false positive. The bracket trick
  (`ps -eo args | grep -c '[E]muHawk.exe'`) fixes the common case but not all of
  it: it still matches if your own command line spells the name out somewhere else,
  as in `echo "NO EmuHawk RUNNING"`. Match on the executable column
  (`ps -eo pid,comm | grep -i mono`) instead, which your shell's argv cannot fake.

## Pin the ROM by hash, not by filename

Collections hold several dumps of the same game differing only in filename. A
wrong revision does not fail loudly — it boots, the bridge connects, the search
runs, and the run is subtly wrong. Verify before installing and refuse on
mismatch:

```
md5  614fb3085826e62f3be3a3fe0b931689   Legend of Zelda, The (USA) (Rev 1)
```

Keep the cartridge in a gitignored `roms/` inside the project with a README that
states the hash and why it is not optional. The path is part of the interface; the
bytes are not, and a ROM in git history cannot be cleanly un-shipped.

**Checking the hash at install time is not enough, and this is where it failed.**
A patched ROM left sitting in `roms/` under the stock filename is a different game
that boots, connects, plays plausibly, and then dies mid-run. On 2026-09-26 the
Automap Plus patch was left at `roms/Legend of Zelda, The (USA) (Rev 1).nes`
(131,090 bytes, md5 `a6d95f62…`, +2 bytes of IPS padding) over the real 131,088-byte
`614fb308…`. The 136,526-frame "verified run" was replayed against it and reported:

```
DIED after 98204 frames (83s, 1180 f/s)
  RuntimeError: bridge connection lost: EmuHawk exit code 0 (0x00000000)
  reached 71.9% of the log
```

Every part of that reads as an emulator fault. `exit code 0` is BizHawk's *orderly*
shutdown, not a crash; a patched ROM that breaks mid-run produces it, and so does a
harness that closed the bridge itself. Meanwhile the cause was a **filename** — the
one thing every check was reading.

Two rules that would have caught it:

- **Never write a patched ROM over `roms/`.** Use the `ZELDA_ROM` indirection; that
  is what it is for. Keep patches in a scratch dir. Verify the hash again *after* the
  risky operation, not only before it.
- **Check the hash at launch, in the code, every time.** An install-time check in the
  setup script cannot see a file replaced three sessions later. Warn loudly to stderr
  *and* write the md5 into the per-run log, because the log is what a reader meets
  weeks later. And make the verification path **refuse**: a RAM fingerprint is only
  meaningful next to the bytes it was computed from, so comparing a replay against a
  known-good fingerprint on an unverified cartridge produces a number that is
  confidently meaningless. Keep an explicit override (`ZELDA_ALLOW_UNVERIFIED_ROM=1`)
  for when finding the divergence *is* the task.

The recovery is worth having written down too: a correct copy elsewhere
(`rom-backup/`) turned a possible re-download into a one-line restore, and the
restored environment was then re-proven by replaying to the same fingerprint. A
restore you have not re-verified is a guess.

## Checklist for a new BizHawk harness

1. `mono`, `gtk2`, `lua5.4` headers present.
2. Download the `linux-x64` tarball; launch `EmuHawkMono.sh`, not `EmuHawk.exe`.
3. Build `Lua/socket/core.so` **without** `-llua54`; place it in `Lua/socket/`.
4. Put the ROM in `roms/`, verify the hash, keep it gitignored. Re-check it at
   launch in code, and refuse to *verify* against a cartridge that is not the
   verified one.
5. Bridge: block for commands, never yield. Disable sound only on the fast path.
6. Add a recording kill switch; do not debug the ffmpeg writer.
7. Prove determinism early: short fixed-input run, replay, compare RAM SHA-1.
8. `setsid` for anything long. Suppress the emulator stdout, keep the input logs.
9. Delegate anything over a few seconds to a subagent that reports the numbers
   verbatim; the main session starts it and moves on.
