#!/bin/bash
# Restart the live run so it re-reads fullgame.py, losing as little search as possible:
# wait for the next "[segment] N frames" commit line, stop the wrapper, python and EmuHawk (in that
# order - a wrapper left alive respawns python), clear the lock, re-stamp the checkpoints against the
# current segment list (restamp.py refuses if the newest checkpoint is not the resume point).
# The caller relaunches:  bash run_until.sh logs/run_until.log 40   (in the background)
cd "$(dirname "$0")"
LOG=logs/run_until.log
n0=$(grep -cE "^\[\w+\] [0-9]+ frames, hearts" "$LOG")
for k in $(seq 1 900); do
  n=$(grep -cE "^\[\w+\] [0-9]+ frames, hearts" "$LOG")
  if [ "$n" -gt "$n0" ]; then
    grep -E "^\[\w+\] [0-9]+ frames, hearts" "$LOG" | tail -1 | cut -c1-110
    break
  fi
  sleep 2
done
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'bash\.exe\"? run_until\.sh' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }; Get-CimInstance Win32_Process | Where-Object { \$_.Name -like 'python*' -and \$_.CommandLine -like '*fullgame.py*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }; Get-Process EmuHawk -ErrorAction SilentlyContinue | Stop-Process -Force"
sleep 3
echo "emulators left: $(tasklist | grep -ci EmuHawk)"
rm -rf /tmp/zelda_run.lock
python restamp.py
