#!/bin/bash
# The emulator process dies silently every so often (no traceback, no EmuHawk left running).
# Every segment is checkpointed, so a restart loses nothing: resume and keep going. A real
# segment failure raises RuntimeError, and that stops the loop instead of retrying forever.
LOG=${1:-/tmp/run.log}
MAX=${2:-40}
# Only ever one run at a time. Three of these wrappers were once alive at once, all
# resuming the same checkpoint and all writing the same files; the emulators fought for
# the CPU and every search crawled. mkdir is atomic, so it makes a usable lock.
LOCKDIR=/tmp/zelda_run.lock
# A lock is only useful if it cannot be waved away. The first version had to be deleted by hand
# whenever a run was killed (the EXIT trap never fires on a kill -9), and deleting it by hand is
# exactly how three runs ended up alive at once. So record the holder's PID and treat the lock as
# stale only when that process is genuinely gone.
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  holder=$(cat "$LOCKDIR/pid" 2>/dev/null)
  if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null; then
    echo "=== run $holder already holds $LOCKDIR; refusing to start ===" >> "$LOG"
    exit 3
  fi
  echo "=== stale lock from pid ${holder:-unknown}; taking it over ===" >> "$LOG"
fi
echo $$ > "$LOCKDIR/pid"
trap 'rm -rf "$LOCKDIR" 2>/dev/null' EXIT
for i in $(seq 1 "$MAX"); do
  echo "=== attempt $i ($(date '+%F %T')) ===" >> "$LOG"
  python fullgame.py >> "$LOG" 2>&1
  code=$?
  if [ $code -eq 0 ]; then
    echo "=== finished cleanly ($(date '+%F %T')) ===" >> "$LOG"; exit 0
  fi
  if tail -40 "$LOG" | grep -q "RuntimeError: segment"; then
    echo "=== a segment genuinely failed; stopping ($(date '+%F %T')) ===" >> "$LOG"; exit 1
  fi
  echo "=== died silently (exit $code, $(date '+%F %T')); resuming ===" >> "$LOG"
  sleep 5
done
echo "=== gave up after $MAX restarts ($(date '+%F %T')) ===" >> "$LOG"
exit 2
