"""Python side of the BizHawk bridge. Launches EmuHawk with bridge.lua and drives it over TCP."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

IS_WINDOWS = os.name == "nt"

HARNESS_DIR = Path(__file__).resolve().parent.parent
ROOT = HARNESS_DIR.parent
# The upstream layout puts BizHawk beside the harness dir. On Linux the official
# BizHawk-2.11.1-linux-x64 tarball unpacks the same tree (including EmuHawk.exe,
# run through Mono) but with a different folder name, so the dir is overridable.
BIZHAWK_DIR = Path(os.environ.get("ZELDA_BIZHAWK_DIR") or (ROOT / "BizHawk-2.11.1-win-x64"))
EMUHAWK = BIZHAWK_DIR / "EmuHawk.exe"
# Linux ships EmuHawk.exe as well, but it only runs under Mono: the wrapper sets
# LD_LIBRARY_PATH for dll/ and the WinForms workarounds BizHawk needs on X11.
EMUHAWK_MONO = BIZHAWK_DIR / "EmuHawkMono.sh"
# The cartridge belongs in roms/ beside the harness - see roms/README.md for why
# the path is part of the interface but the file is never committed. Fall back to
# the BizHawk folder for setups that keep it there, and to roms/ when it is missing
# everywhere, so the "no such file" error points somewhere sensible.
ROM_NAME = "Legend of Zelda, The (USA) (Rev 1).nes"
_ROM_CANDIDATES = (HARNESS_DIR / "roms" / ROM_NAME, BIZHAWK_DIR / ROM_NAME)
ROM = Path(os.environ.get("ZELDA_ROM")
           or next((p for p in _ROM_CANDIDATES if p.exists()), _ROM_CANDIDATES[0]))
# The one cartridge every number in this repo was measured against. The run6
# fingerprint (3115e31f...) is a sha1 over work RAM produced by *these* bytes, so a
# different cartridge is a different game: same title, same controls, different
# result, and nothing in a replay or a search report says so.
VERIFIED_ROM_MD5 = "614fb3085826e62f3be3a3fe0b931689"


def rom_md5(rom: Path) -> str:
    import hashlib
    return hashlib.md5(Path(rom).read_bytes()).hexdigest()


def unverified_rom_reason(rom: Path) -> str | None:
    """Why this cartridge is not the verified one, or None if it is.

    A patched ROM is a legitimate thing to run here - testing/compare_roms.py exists
    to prove one is cosmetic - so this reports rather than refuses. What it must not
    do is stay quiet: on 2026-09-26 the Automap Plus patch was left sitting in roms/
    under the stock filename, and 136,526 frames of "the verified run" were replayed
    against it before anyone noticed. It booted, it played, and it died at frame
    98,204 with "EmuHawk exit code 0", which reads like an emulator fault rather than
    a wrong cartridge. Never write a patched ROM over roms/ - use ZELDA_ROM.
    """
    try:
        got = rom_md5(rom)
    except OSError:
        return f"{rom} cannot be read"
    if got == VERIFIED_ROM_MD5:
        return None
    return (f"{rom}\n  md5 {got}\n  expected {VERIFIED_ROM_MD5} (No-Intro USA Rev 1)"
            f"\n  this is not the cartridge the run6 fingerprint was computed on;"
            f" anything measured with it is a different game")
BRIDGE_LUA = HARNESS_DIR / "bridge.lua"
STATES_DIR = HARNESS_DIR / "states"
SHOTS_DIR = HARNESS_DIR / "shots"
LOGS_DIR = HARNESS_DIR / "logs"
VIDEO_DIR = HARNESS_DIR / "video"

BUTTONS = ("Up", "Down", "Left", "Right", "Select", "Start", "B", "A")


def _click_really_quit(timeout: float = 4.0) -> bool:
    """Find EmuHawk's 'Really quit?' A/V dialog and click its Yes button (Windows only)."""
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        BM_CLICK = 0x00F5
        EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        t0 = time.time()
        while time.time() - t0 < timeout:
            dlg = u.FindWindowW(None, "Really quit?")
            if dlg:
                found = []

                def cb(h, _):
                    buf = ctypes.create_unicode_buffer(64)
                    u.GetWindowTextW(h, buf, 64)
                    if "yes" in buf.value.replace("&", "").lower():
                        found.append(h)
                    return True
                u.EnumChildWindows(dlg, EnumProc(cb), 0)
                if found:
                    u.PostMessageW(found[0], BM_CLICK, 0, 0)
                    return True
            time.sleep(0.1)
    except Exception:
        pass
    return False


@dataclass
class State:
    frame: int = 0
    mode: int = 0
    sub: int = 0
    level: int = 0
    room: int = 0
    x: int = 0
    y: int = 0
    dir: int = 0
    hp: int = 0
    hpfrac: int = 0
    rupees: int = 0
    keys: int = 0
    bombs: int = 0
    sword: int = 0
    bitem: int = 0
    triforce: int = 0
    paused: int = 0
    scroll: int = 0
    retroom: int = 0
    anim: int = 0
    kills: int = 0
    lag: int = 0
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def parse(cls, line: str) -> "State":
        kv = {}
        for tok in line.split():
            k, _, v = tok.partition("=")
            kv[k] = int(v)
        s = cls(**{k: v for k, v in kv.items() if k in cls.__dataclass_fields__})
        s.raw = kv
        return s

    @property
    def hearts(self) -> float:
        full = self.hp & 0x0F
        return full + (1.0 if self.hpfrac >= 0x80 else 0.5 if self.hpfrac > 0 else 0.0)

    @property
    def containers(self) -> int:
        return (self.hp >> 4) + 1

    def __str__(self) -> str:
        return (f"f{self.frame} mode={self.mode:02x}/{self.sub:02x} L{self.level} room={self.room:02x} "
                f"pos=({self.x},{self.y}) dir={self.dir} hp={self.hearts}/{self.containers} "
                f"rup={self.rupees} sword={self.sword} lag={self.lag}")


class BizHawk:
    """One EmuHawk instance driven frame by frame."""

    def __init__(self, rom: Path = ROM, fast: bool = True, log_name: str | None = None,
                 clean_sram: bool = True, record: str | None = None):
        """record=<session name>: dump video live (savestate jumps included) and log every frame's
        input, state and notes to logs/<session>.* so the session can be rendered with the panel."""
        for d in (STATES_DIR, SHOTS_DIR, LOGS_DIR, VIDEO_DIR):
            d.mkdir(parents=True, exist_ok=True)
        # ZELDA_RECORD=0 forces recording off whatever the caller asked for. BizHawk's
        # --dump-type=ffmpeg writer takes the display/GL path earlier than the Lua bridge
        # does, and under Mono on Linux it never gets the bridge up at all - the launcher
        # log just stops after the GTK theme warning, with no exception. A search does not
        # need the video, so this is the switch that keeps the run usable.
        if os.environ.get("ZELDA_RECORD") == "0":
            record = None
        self.record = record
        self.trace_lines: list[str] = []
        if clean_sram:
            # The game's battery save persists across launches; a from-power-on run must start clean.
            for p in (BIZHAWK_DIR / "NES" / "SaveRAM").glob("*.SaveRAM*"):
                p.unlink()
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        (HARNESS_DIR / ".bridge_port").write_text(str(port))
        log_name = log_name or f"emuhawk_{int(time.time())}.log"
        # Keep the previous launch's log as <name>.prev: run_until.sh relaunches straight after a silent
        # death, and reopening with "w" used to destroy the one log that could say why it died.
        log_path = LOGS_DIR / log_name
        try:
            if log_path.exists() and log_path.stat().st_size > 0:
                log_path.replace(log_path.with_name(log_path.stem + ".prev" + log_path.suffix))
        except OSError:
            pass
        self._logfile = open(log_path, "w")
        # Say out loud, in the terminal and in this run's own log, when the cartridge
        # is not the verified one. The log line matters more than the warning: a log
        # read weeks later is the only place that still says what the run was played on.
        self.unverified_rom = unverified_rom_reason(rom)
        if self.unverified_rom:
            banner = ("\n*** UNVERIFIED CARTRIDGE ***\n"
                      + textwrap.indent(self.unverified_rom, "  ") + "\n")
            print(banner + "*** replay fingerprints and search results from this "
                           "emulator mean nothing ***\n", file=sys.stderr, flush=True)
            self._logfile.write(banner + "\n")
            self._logfile.flush()
        args = [f"--lua={BRIDGE_LUA}", f"--userdata=port:{port}"]
        if record:
            self.video_path = VIDEO_DIR / f"{record}.mkv"
            args += ["--dump-type=ffmpeg", f"--dump-name={self.video_path}"]
        args.append(str(rom))
        if IS_WINDOWS:
            args = [str(EMUHAWK), *args]
        elif EMUHAWK_MONO.exists():
            args = [str(EMUHAWK_MONO), *args]
        else:
            args = ["mono", str(EMUHAWK), *args]
        self.proc = subprocess.Popen(args, cwd=str(BIZHAWK_DIR), stdout=self._logfile, stderr=subprocess.STDOUT)
        srv.settimeout(60)
        try:
            self.conn, _ = srv.accept()
        except socket.timeout:
            self.proc.kill()
            raise RuntimeError("EmuHawk never connected to the bridge; see " + str(LOGS_DIR / log_name))
        finally:
            srv.close()
        self.conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.conn.settimeout(120)
        self._rf = self.conn.makefile("rb")
        self.inputs: list[tuple[str, ...]] = []   # one entry per emulated frame since power-on
        self.events: list[tuple[int, str]] = []   # (frame, text) notes from the bot, for overlays
        # Optional per-step observer, set by whoever wants to watch MAIN frame by frame.
        # Called as on_step(emu, buttons, frames, state) after every step(), so it sees every
        # frame MAIN advances no matter which policy advanced it - including from inside a
        # search's Recorder, which binds emu.step once at construction and would bypass
        # anything that patched the attribute afterwards. That trap is why this is a
        # first-class field rather than a monkey-patch.
        self.on_step: Callable | None = None
        self.input_log_valid = True                 # False once a savestate load breaks the frame chain
        assert self.cmd("ping") == "pong"
        if record:
            self.cmd("trace on")
        if fast:
            self.fast()

    # -- low level -------------------------------------------------------
    def cmd(self, line: str) -> str:
        self.conn.sendall((line + "\n").encode())
        resp = self._rf.readline()
        if not resp:
            # Say HOW the bridge died. An EmuHawk that ran its orderly Close() exits with 0; a crash or a
            # kill leaves 0xC0000005, 0xE0434352 or 1. A seven-agent diagnosis of six drops on 2026-09-15
            # could not tell those apart, because nothing recorded the exit code or the time.
            import time as _time
            code = None
            try:
                code = self.proc.wait(timeout=2)
            except Exception:
                pass
            how = "still running" if code is None else f"exit code {code} (0x{code & 0xFFFFFFFF:08X})"
            raise RuntimeError(f"bridge connection lost at {_time.strftime('%H:%M:%S')}: EmuHawk {how}; "
                               f"log {getattr(self._logfile, 'name', '?')}")
        resp = resp.decode().rstrip("\n")
        if resp.startswith("err "):
            raise RuntimeError(resp)
        return resp

    # -- control ---------------------------------------------------------
    def step(self, buttons: Iterable[str] | str = (), frames: int = 1) -> State:
        if isinstance(buttons, str):
            buttons = tuple(b for b in buttons.split(",") if b)
        btn = tuple(buttons)
        for b in btn:
            if b not in BUTTONS:
                raise ValueError(f"unknown button {b!r}")
        self.inputs.extend([btn] * frames)
        resp = self.cmd(f"step {frames} {','.join(btn) or '-'}")
        if self.record:
            lines = resp.split(";")
            self.trace_lines.extend(lines)
            s = State.parse(lines[-1])
        else:
            s = State.parse(resp)
        if self.on_step is not None:
            # Fires once per *call*, not once per frame. A caller that batches a
            # wait into `step((), 90)` gets one callback 90 frames later, so a
            # per-frame observer sees the end state rather than every intermediate
            # one. Detection still catches a state change that happened inside the
            # batch; only the attributed frame is late, by up to frames-1. Anything
            # reading this must record the span rather than assume 1.
            self.on_step(self, btn, frames, s)
        return s

    def press(self, *buttons: str, hold: int = 1, release: int = 1) -> State:
        """Tap buttons: hold for `hold` frames, then release for `release` frames."""
        s = self.step(buttons, hold)
        if release:
            s = self.step((), release)
        return s

    def state(self) -> State:
        return State.parse(self.cmd("state"))

    def ram(self, addr: int, length: int = 1) -> bytes:
        return bytes.fromhex(self.cmd(f"ram {addr} {length}"))

    def byte(self, addr: int) -> int:
        return self.ram(addr, 1)[0]

    def ram_domain(self, domain: str, addr: int, length: int) -> bytes:
        """Read from another BizHawk memory domain, e.g. 'WRAM' (cart RAM at $6000, offset 0) or 'System Bus'."""
        return bytes.fromhex(self.cmd(f"ramd {domain} {addr} {length}"))

    def bus(self, addr: int, length: int = 1) -> bytes:
        """Read CPU-address-space bytes: $0000-$07FF from RAM, $6000-$7FFF from cart WRAM."""
        if addr < 0x800:
            return self.ram(addr, length)
        if 0x6000 <= addr < 0x8000:
            return self.ram_domain("WRAM", addr - 0x6000, length)
        raise ValueError(f"unsupported bus address {addr:#x}")

    def save(self, name: str) -> Path:
        p = STATES_DIR / f"{name}.State"
        self.cmd(f"save {p}")
        return p

    def load(self, name: str) -> State:
        p = STATES_DIR / f"{name}.State"
        r = self.cmd(f"load {p}")
        if r != "ok":
            raise RuntimeError(f"savestate load failed: {p}")
        self.input_log_valid = False
        return self.state()

    # in-memory savestates for search (fast; not persisted)
    def msave(self) -> str:
        return self.cmd("msave")

    def mload(self, sid: str) -> State:
        self.cmd(f"mload {sid}")
        self.input_log_valid = False
        return self.state()

    def mfree(self, sid: str) -> None:
        self.cmd(f"mfree {sid}")

    def screenshot(self, name: str) -> Path:
        p = SHOTS_DIR / f"{name}.png"
        self.cmd(f"screenshot {p}")
        return p

    def fast(self) -> None:
        self.cmd("fast")

    def normal(self) -> None:
        self.cmd("normal")

    def reset(self) -> State:
        self.inputs.clear()
        self.input_log_valid = True
        return State.parse(self.cmd("reset"))

    def wait(self, frames: int) -> State:
        return self.step((), frames)

    def wait_until(self, pred, max_frames: int = 600, buttons: Sequence[str] = ()) -> State:
        s = self.state()
        for _ in range(max_frames):
            if pred(s):
                return s
            s = self.step(buttons, 1)
        raise TimeoutError(f"condition not met after {max_frames} frames; last state {s}")

    def note(self, text: str) -> None:
        """Record what the bot is doing right now (attached to the next frame)."""
        self.events.append((len(self.inputs) + 1, text))

    def save_inputs(self, name: str) -> Path:
        p = LOGS_DIR / f"{name}.inputs.txt"
        with open(p, "w") as f:
            f.write(f"# frames={len(self.inputs)} valid_from_poweron={self.input_log_valid}\n")
            for btn in self.inputs:
                f.write(",".join(btn) + "\n")
        with open(LOGS_DIR / f"{name}.events.txt", "w") as f:
            for frame, text in self.events:
                f.write(f"{frame}\t{text}\n")
        return p

    def save_session(self) -> None:
        """Write logs/<record>.{inputs,events,trace}.txt indexed by video frame (frames stepped since launch)."""
        name = self.record
        with open(LOGS_DIR / f"{name}.inputs.txt", "w") as f:
            f.write(f"# frames={len(self.inputs)} session=1\n")
            for btn in self.inputs:
                f.write(",".join(btn) + "\n")
        with open(LOGS_DIR / f"{name}.events.txt", "w") as f:
            for frame, text in self.events:
                f.write(f"{frame}\t{text}\n")
        with open(LOGS_DIR / f"{name}.trace.txt", "w") as f:
            for i, (btn, line) in enumerate(zip(self.inputs, self.trace_lines)):
                f.write(f"{i + 1}\t{','.join(btn)}\t{line}\n")

    def close(self) -> None:
        if self.record:
            try:
                self.save_session()
            except Exception as e:  # never lose the emulator shutdown over a log
                print("session save failed:", e)
        try:
            self.cmd("quit")
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass
        if self.record:
            _click_really_quit()   # BizHawk asks "Really quit?" while recording A/V; answer Yes for it
        try:
            self.proc.wait(timeout=12 if self.record else 3)
        except Exception:
            self.proc.kill()
        self._logfile.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
