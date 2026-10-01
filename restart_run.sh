#!/bin/bash
# Restart the live run so it re-reads fullgame.py, losing as little search as possible:
# wait for the next "[segment] N frames" commit line, stop the wrapper, python and EmuHawk (in that
# order - a wrapper left alive respawns python), clear the lock, re-stamp the checkpoints against the
# current segment list (restamp.py refuses if the newest checkpoint is not the resume point).
#
#   bash restart_run.sh [LOG] [MAX_RESTARTS]
#
# The caller relaunches, and MUST detach it - see FINDINGS.md 3.2. A background job of a shell that
# then goes away takes its process group with it, and that presents as every emulator exiting at once
# with no traceback and healthy-looking scout logs. The documented form is the one zelda.sh uses:
#
#   setsid nohup env ZELDA_ROUTE=5 bash run_until.sh logs/gleeok_from.launch.log 40 >/dev/null 2>&1 </dev/null &
#
# Cross-platform since 2026-09-30. It was Windows-only: powershell.exe for the kills, tasklist to
# count what was left, and `python restamp.py`, which does not exist - restamp.py is at
# testing/restamp.py. So on this box the script could not run at all, and every restart was done by
# hand - which is how the launch mistake in FINDINGS.md 3.2 kept happening.
set -uo pipefail
cd "$(dirname "$0")"

LOG=${1:-logs/run_until.log}
MAX=${2:-40}
COMMIT_RE='^\[[[:alnum:]_]+\] [0-9]+ frames, hearts'

# ---------------------------------------------------------------- platform
case "$(uname -s 2>/dev/null || echo Windows)" in
  Linux)  PLATFORM=linux ;;
  Darwin) PLATFORM=darwin ;;
  *)      PLATFORM=windows ;;
esac

# Kill by command line, but ONLY processes whose executable name matches, so this can never kill the
# shell that invoked it. That is not hypothetical: `pkill -f fullgame.py` run from a tool call whose
# own command line contains the string "fullgame.py" matches the tool's shell and takes the session
# down with the run. Checking comm first is what makes the pattern safe.
kill_matching() {                     # kill_matching <comm-regex> <cmdline-regex>
  local comm_re=$1 line_re=$2 pid comm
  if [ "$PLATFORM" = windows ]; then
    powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match '$line_re' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }" >/dev/null 2>&1
    return
  fi
  for pid in $(pgrep -f "$line_re" 2>/dev/null); do
    [ "$pid" = "$$" ] && continue
    comm=$(cat "/proc/$pid/comm" 2>/dev/null) || continue
    # grep -E, NOT `case "$comm" in $comm_re`. A case pattern list is parsed before expansion, so an
    # expanded "bash|sh|zsh" is the LITERAL string bash|sh|zsh and matches no comm value at all -
    # verified on this machine, where `case bash in bash|sh|zsh` does not match "bash". Two of the four
    # calls here passed an alternation, so those two lines had never killed anything: the wrapper was
    # never stopped and the emulators were never stopped, and the wrapper went on to respawn python.
    # The visible symptom was this machine ending up with two run_until.sh wrappers, two fullgame.py
    # and ELEVEN emulators - the exact contention run_until.sh's lock exists to prevent, produced by
    # the script whose job is to clean up before a run starts.
    if printf '%s' "$comm" | grep -qE "$comm_re"; then
      kill -9 "$pid" 2>/dev/null
    fi
  done
}

count_emulators() {
  if [ "$PLATFORM" = windows ]; then
    tasklist 2>/dev/null | grep -ci emuhawk
  else
    pgrep -fc 'EmuHawk\.exe' 2>/dev/null || echo 0
  fi
}

# ---------------------------------------------------------------- 1. wait for a commit
if [ -f "$LOG" ]; then
  n0=$(grep -cE "$COMMIT_RE" "$LOG")
  for _ in $(seq 1 900); do
    n=$(grep -cE "$COMMIT_RE" "$LOG")
    if [ "$n" -gt "$n0" ]; then
      grep -E "$COMMIT_RE" "$LOG" | tail -1 | cut -c1-110
      break
    fi
    sleep 2
  done
else
  echo "restart_run: $LOG does not exist; not waiting for a commit line"
fi

# ---------------------------------------------------------------- 2. stop, in order
echo "restart_run: platform=$PLATFORM"
kill_matching 'bash|sh'        'run_until\.sh'    # wrapper first, or it respawns python
kill_matching 'python.*'       'fullgame\.py'
kill_matching 'mono.*|EmuHawk.*' 'EmuHawk\.exe'
sleep 3
echo "emulators left: $(count_emulators)"

# ---------------------------------------------------------------- 3. lock and stamps
rm -rf /tmp/zelda_run.lock
python testing/restamp.py

echo "restart_run: relaunch detached, or the process group dies with this shell (FINDINGS.md 3.2):"
echo "  setsid nohup env ZELDA_ROUTE=${ZELDA_ROUTE:-5} bash run_until.sh $LOG $MAX >/dev/null 2>&1 </dev/null &"
