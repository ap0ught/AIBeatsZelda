# Running this on Linux

Verified on CachyOS (Arch), 2026-09-25, against BizHawk 2.11.1 and Mono 6.12.

## Provenance

- Upstream: `bearsgaming-ui/AIBeatsZelda` — a video project in which Claude, as a
  coding agent, wrote a player for *The Legend of Zelda* (NES) and then played the
  game through it. The harness and its journal are the point; the game is not ours
  to ship.
- Our fork: `ap0ught/AIBeatsZelda`.
- Local checkout: `~/code/games/aibeatszelda/`, harness in `src/`, emulator and
  ROM in the sibling `BizHawk-2.11.1-win-x64/`.
- The ROM came from the local collection at
  `/extdrive/backups/SHARE/roms/nes/Legend of Zelda, The (USA) (Rev 1).zip`. That
  directory also holds `(USA)` and `(USA) (Rev A)` dumps of the same game; only
  Rev 1 works here, which is why the md5 is pinned rather than the filename.

Upstream ships the source as a single `release.zip` rather than as files, so the
first commit here unpacks it. Everything except the three files below is
byte-identical to `release.zip` — verified with a recursive diff.

## Changes to upstream

Only three files are modified, 26 lines added and 4 removed:

- `zelda/emulator.py` — the emulator launch is platform-aware (`EmuHawkMono.sh`
  on Linux) and `ZELDA_BIZHAWK_DIR` / `ZELDA_ROM` can override the paths.
- `bridge.lua` — `normal` restores sound; new `sound 0|1` command.
- `.gitignore` — ignore `shots/` and `.bridge_port`.

Added: `setup_linux.sh`, `watch_run.py`, and this file.

## The four things that block it on Linux

1. **The emulator binary.** BizHawk does publish a `linux-x64` build, but it is
   not native — it is the same `EmuHawk.exe` run under Mono via the bundled
   `EmuHawkMono.sh` wrapper. `zelda/emulator.py` hardcoded `EmuHawk.exe` as the
   thing to exec, so it now picks the launcher by platform, and
   `ZELDA_BIZHAWK_DIR` / `ZELDA_ROM` can override the paths.

   The wrapper wants the folder named `BizHawk-2.11.1-win-x64` only because that
   is what `emulator.py` derives from `ROOT`; we keep that name for the
   `linux-x64` tree so nothing else has to change.

2. **LuaSocket.** `bridge.lua` opens with `require('socket.core')`. BizHawk ships
   `Lua/socket/core.dll` — a Windows native DLL — and no Linux equivalent, so the
   bridge dies at line 15 and the harness times out waiting for a connection.
   We build the same module from LuaSocket 3.1.0 as `Lua/socket/core.so`.

   The build deliberately omits `-llua54`. NLua embeds Lua 5.4 and exports the
   `lua_*` symbols, so the module's undefined `lua_*` references bind to the host
   at `dlopen` time. Linking liblua54 would hand the module a second, private
   copy of the runtime. `setup_linux.sh` comments this in place, because it looks
   like a missing flag at a glance.

3. **The ROM.** The harness only works on the exact No-Intro
   `Legend of Zelda, The (USA) (Rev 1)` dump, md5 `614fb3085826e62f3be3a3fe0b931689`
   — not the USA Rev A, not the European dumps that sit next to it in the ROM
   collection. `setup_linux.sh` refuses to install a ROM whose md5 differs.

4. **gtk2, for anything with a window.** Covered under "Watching it with sound"
   below because it only bites once you run interactively — the headless
   searches and the smoke test are fine without it.

## Setup

```
./setup_linux.sh /path/to/your/zelda-rom.nes
```

Then:

```
python3 smoke_test.py     # boot, 300 frames, screenshot
```

## Watching it with sound

The search harness runs unthrottled and silent on purpose, so `replay.verify()`
gets through 136,526 frames in about three minutes. To actually watch the run:

```
python3 watch_run.py                  # the whole 37:02 run, realtime, with sound
python3 watch_run.py --seconds 300    # first five minutes only
python3 watch_run.py --from 40000     # emulate the first 40000 frames silently, then watch
```

Realtime is `emu.limitframerate(true)`; BizHawk paces itself inside `step()`, so
a batch of 900 frames takes 15 real seconds. Measured: 36,000 frames in 601 s of
wall clock, i.e. 59.9 fps sustained, against the NES's 60.0988 Hz. The ~0.3%
shortfall is the per-step socket round trip and the state string `bridge.lua`
builds on every step. A full watch therefore takes about 38 minutes.

`--from` is safe: the skipped frames are emulated with the same inputs by the
same deterministic emulator, just unthrottled, so the final fingerprint is
identical to a from-power-on watch. The script checks it and says MATCH.

### Two things that were in the way

**Sound had to be turned back on explicitly.** `bridge.lua`'s `fast` command does
`client.SetSoundOn(false)` to keep the search loop cheap, but the matching
`normal` command only called `emu.limitframerate(true)` — it never restored
sound, so coming back to realtime gave you a silent run. `normal` now turns
sound on, and a separate `sound 0|1` command exists. `config.ini` also ships
with `"SoundEnabled": false`, which `watch_run.py` overrides per launch.

**`gtk2` is required, and its absence is very confusing.** Without
`libgtk-x11-2.0.so.0`, Mono's System.Windows.Forms uses its built-in X11 driver,
which throws an XErrorEvent (`BadMatch`) from BizHawk's `Input.UpdateThreadProc`
about 30 seconds into play. The process does not exit: EmuHawk stays alive and
keeps its window, but the Lua bridge stops being serviced, so the harness sees
"bridge connection lost" and the run looks like it simply froze. BizHawk's own
launcher prints `Gtk not found ... using built-in colorscheme` at startup, which
looks cosmetic and is not. `sudo pacman -S gtk2` fixes it; `setup_linux.sh`
installs it.

Audio goes out through SDL2 (`SoundOutputMethod: 2`) to PipeWire, and lands on
whatever sink is default — check with `pactl list sink-inputs`, where the
BizHawk stream should show up uncorked while the run is playing.


## Verification performed

The shipped run was replayed from power-on in a fresh emulator:

```
python3 -c "
from pathlib import Path
from zelda import replay
replay.verify(Path('runs/run6/inputs.txt'),
              '3115e31ff1a9b16e732160f81fe478a5052668ff')"
```

```
replayed 136526 frames -> f136526 mode=13/04 L9 room=32 pos=(136,136) dir=2 hp=8.5/13 rup=29 sword=3 lag=23405
  ram sha1 3115e31ff1a9b16e732160f81fe478a5052668ff
  MATCH
```

That is byte-for-byte the fingerprint in `runs/run6/VERIFICATION.txt`, so the
37:02 run is reproducible on this machine.

A note on the numbers, since two of them do not agree: 136,526 frames at the
NES's 60.0988 Hz is 2271.7 s, or 37:52 of emulated time. The "37m02s" in the
filename is the game's own in-game timer, which runs behind real time — so
37:02 of game time is 37:52 of frames, not the other way round. Unthrottled, the
emulator sustains ~700 fps stepping and ~850 fps on single-frame round trips,
which is why the replay check takes about three minutes.

## Not verified

`fullgame.py` — a fresh 341-segment search. The harness ran this to produce
run6, but a search is seeded randomly, so it is a 4–6 hour run and we have not
executed it here.

The realtime+sound watch was soaked for 10 continuous minutes — 36,000 frames
in 601 s (59.9 fps), zero X11 or Lua errors, audio stream uncorked throughout —
rather than end-to-end. The unthrottled replay above does prove all 136,526
frames, and throttling changes no emulation, so the fingerprint is not in
question; but nobody has watched the last 28 minutes.

One thing to know before you start a watch: the harness wipes
`BizHawk*/NES/SaveRAM` on every launch so a from-power-on run starts clean, and
it has no per-instance lock. Two watchers at once will trample each other's
battery save, so run one at a time.
