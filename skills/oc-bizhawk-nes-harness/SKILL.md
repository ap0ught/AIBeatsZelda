---
name: oc-bizhawk-nes-harness
description: Drive BizHawk from Linux for TAS-style automated play, replay verification, and parallel search. Covers the Mono-based linux-x64 build, building LuaSocket core.so for NLua's embedded Lua 5.4, the mandatory gtk2 dependency and its silent X11 failure, why video recording never connects, the no-yield bridge discipline that makes replays deterministic, and detaching long runs. Use when automating BizHawk, scripting a Lua bridge over TCP, verifying an input log by RAM fingerprint, or searching NES gameplay with multiple emulator instances.
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
  itself contains `<pattern>` returns a false positive. Use
  `ps -eo args | grep -c '[E]muHawk.exe'`.

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

## Checklist for a new BizHawk harness

1. `mono`, `gtk2`, `lua5.4` headers present.
2. Download the `linux-x64` tarball; launch `EmuHawkMono.sh`, not `EmuHawk.exe`.
3. Build `Lua/socket/core.so` **without** `-llua54`; place it in `Lua/socket/`.
4. Put the ROM in `roms/`, verify the hash, keep it gitignored.
5. Bridge: block for commands, never yield. Disable sound only on the fast path.
6. Add a recording kill switch; do not debug the ffmpeg writer.
7. Prove determinism early: short fixed-input run, replay, compare RAM SHA-1.
8. `setsid` for anything long. Suppress the emulator stdout, keep the input logs.
