#!/usr/bin/env bash
# Set up AIBeatsZelda to run on Linux (CachyOS/Arch, tested on 2026-09-25).
#
# The upstream harness is Windows-only in three places. This script fixes all three:
#   1. BizHawk ships a linux-x64 tarball, but it is still EmuHawk.exe run under Mono.
#   2. bridge.lua needs require('socket.core'); BizHawk only ships the Windows
#      Lua/socket/core.dll, so we build the LuaSocket core as a .so for the Lua 5.4
#      that NLua embeds.
#   3. emulator.py hardcoded EmuHawk.exe as the launch binary; it is now
#      platform-aware and honours ZELDA_BIZHAWK_DIR / ZELDA_ROM.
#
# Usage:  ./setup_linux.sh <path-to-zelda-rom.nes>
set -euo pipefail

BIZHAWK_VERSION=2.11.1
BIZHAWK_DIR_NAME="BizHawk-2.11.1-win-x64"   # emulator.py's expected name; the tarball is linux-x64
EXPECTED_ROM_MD5=614fb3085826e62f3be3a3fe0b931689   # No-Intro "Legend of Zelda, The (USA) (Rev 1)"
ROM_NAME="Legend of Zelda, The (USA) (Rev 1).nes"

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HARNESS_DIR")"
BIZHAWK_DIR="$ROOT/$BIZHAWK_DIR_NAME"
# The cartridge lives beside the harness, not inside the emulator folder. See roms/README.md.
ROM_DIR="$HARNESS_DIR/roms"

need() { command -v "$1" >/dev/null || { echo "missing: $1" >&2; exit 1; }; }
need curl; need tar; need gcc; need mono; need unzip

# --- 0. dependencies ------------------------------------------------------
# gtk2 is not optional. Mono's System.Windows.Forms falls back to its built-in
# X11 driver when libgtk-x11-2.0.so.0 is missing, and that driver dies on an
# XErrorEvent (BadMatch) from BizHawk's input thread within ~30s of play. The
# symptom is nasty: EmuHawk stays alive but stops answering the bridge socket,
# so the run looks like it froze. With gtk2 present the driver is stable and the
# realtime+sound watch survives.
if ! pacman -Q lua54 >/dev/null 2>&1 || ! pacman -Q gtk2 >/dev/null 2>&1; then
  echo "==> installing lua54 (headers), mono and gtk2"
  sudo pacman -S --needed --noconfirm lua54 mono gtk2
fi

# --- 1. BizHawk -----------------------------------------------------------
if [[ ! -x "$BIZHAWK_DIR/EmuHawkMono.sh" ]]; then
  echo "==> downloading BizHawk $BIZHAWK_VERSION (linux-x64)"
  tmp=$(mktemp -d)
  curl -fL -o "$tmp/bh.tar.gz" \
    "https://github.com/TASVideos/BizHawk/releases/download/$BIZHAWK_VERSION/BizHawk-$BIZHAWK_VERSION-linux-x64.tar.gz"
  tar xzf "$tmp/bh.tar.gz" -C "$tmp"
  mv "$tmp/BizHawk-$BIZHAWK_VERSION-linux-x64" "$BIZHAWK_DIR"
  rm -rf "$tmp"
fi
chmod +x "$BIZHAWK_DIR/EmuHawkMono.sh"
echo "==> BizHawk ready: $BIZHAWK_DIR"

# --- 2. LuaSocket core.so for NLua's Lua 5.4 ------------------------------
# BizHawk's tarball ships only the Windows core.dll. NLua embeds Lua 5.4 and
# exports the lua_* symbols, so the module is built WITHOUT -llua54: its
# undefined lua_* symbols bind to the host at dlopen time. Linking liblua54
# would give the module a second, private copy of the runtime.
if [[ ! -f "$BIZHAWK_DIR/Lua/socket/core.so" ]]; then
  echo "==> building LuaSocket 3.1.0 core.so for Lua 5.4"
  tmp=$(mktemp -d)
  curl -fL -o "$tmp/ls.tar.gz" \
    "https://github.com/lunarmodules/luasocket/archive/refs/tags/v3.1.0.tar.gz"
  tar xzf "$tmp/ls.tar.gz" -C "$tmp"
  (
    cd "$tmp/luasocket-3.1.0/src"
    gcc -O2 -fPIC -shared -std=gnu99 \
      -DLUASOCKET_INET \
      -DLUASOCKET_API='__attribute__((visibility("default"))) extern' \
      -I/usr/include/lua5.4 \
      -o "$BIZHAWK_DIR/Lua/socket/core.so" \
      luasocket.c auxiliar.c buffer.c compat.c except.c inet.c io.c mime.c \
      options.c select.c timeout.c tcp.c udp.c usocket.c unix.c unixstream.c unixdgram.c
  )
  rm -rf "$tmp"
  echo "==> core.so built: $BIZHAWK_DIR/Lua/socket/core.so"
fi

# --- 3. the ROM -----------------------------------------------------------
if [[ $# -ge 1 && -f "$1" ]]; then
  got=$(md5sum "$1" | cut -d' ' -f1 | tr 'A-Z' 'a-z')
  if [[ "$got" != "$EXPECTED_ROM_MD5" ]]; then
    echo "ROM md5 mismatch: got $got, want $EXPECTED_ROM_MD5 (No-Intro USA Rev 1)" >&2
    echo "The harness and the shipped run only work on that exact dump." >&2
    exit 1
  fi
  mkdir -p "$ROM_DIR"
  cp "$1" "$ROM_DIR/$ROM_NAME"
  echo "==> ROM installed (md5 $got)"
else
  echo "!! No ROM given. Place your own legal dump of the (USA) (Rev 1) cartridge as:"
  echo "     $ROM_DIR/$ROM_NAME"
  echo "   expected md5: $EXPECTED_ROM_MD5"
  exit 0
fi

# --- 4. python deps -------------------------------------------------------
python3 - <<'PY'
import importlib.util, subprocess, sys
missing = [m for m in ("PIL", "numpy") if importlib.util.find_spec(m) is None]
if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pillow", "numpy"])
    print("==> installed", missing)
else:
    print("==> python deps present")
PY

cat <<'EOF'

Setup complete. Try it:

  python3 smoke_test.py                 # boot, 300 frames, screenshot

Full verification of the shipped 37:02 run (about 3 minutes, expects MATCH):

  python3 -c "
  from pathlib import Path
  from zelda import replay
  replay.verify(Path('runs/run6/inputs.txt'),
                '3115e31ff1a9b16e732160f81fe478a5052668ff')"

A fresh search takes 4-6 hours across 6 emulator instances:

  ZELDA_ROUTE=4 ZELDA_SCOUTS=6 bash run_until.sh logs/run_until.log 40
EOF
