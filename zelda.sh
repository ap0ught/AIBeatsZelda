#!/usr/bin/env bash
# zelda.sh - pick a run and launch it, with honest estimates for each.
#
#   ./zelda.sh          list everything
#   ./zelda.sh 1        run milestone 1 (foreground, seconds)
#   ./zelda.sh 3        run milestone 3 (searched; 4 scouts by default)
#   ./zelda.sh watch    watch the shipped 37:02 run realtime, with sound
#   ./zelda.sh plan 300 let the route planner search for 300s
#   ./zelda.sh help     this list
#
# Frame counts and wall-clock figures are MEASURED on this machine, not guessed.
# Every "verified" run replays from power-on in a fresh emulator and compares a
# SHA-1 of all 2 KB of RAM before reporting success. A run that reports MATCH has
# been proved deterministic; one that reports a mismatch has not.
#
# Long runs are detached with setsid on purpose. A background job of a shell
# that waits on it gets its whole process group killed when that shell goes away,
# which looks exactly like the emulator crashing - see FINDINGS.md section 3.2.
set -uo pipefail

cd "$(dirname "$(realpath "$0")")"

# BizHawk's ffmpeg video writer never reaches the Lua bridge under Mono, so every
# runnable thing here turns recording off. See FINDINGS.md section 3.1.
export ZELDA_RECORD=0
SCOUTS="${ZELDA_SCOUTS:-4}"
LOGS="${TMPDIR:-/tmp}/zelda"

# name|description|frames|game time|wall|kind
#   kind: quick = seconds, searched = foreground minutes, long = detached,
#         tool = no emulator
CATALOGUE=$(cat <<'EOF'
milestone1|Sword out of the start cave, and back out again|1,043|0:17|~5 s|quick
milestone2|Add the overworld walk: sword, then into Level 3|2,978|0:50|~7 s|quick
milestone3|Clear Level 3 and take the Triforce piece|12,191|3:23|~9 m|searched
verify|Replay the shipped 37:02 run and check its RAM fingerprint|136,526|37:52|~4 m|searched
watch|Watch the shipped run in realtime, with sound|136,526|37:52|~38 m|long
plan|Model dungeon orders and their cost - no emulator needed|-|-|90-150 s|tool
fullgame|Search the whole game from power-on (341 segments)|136,526|37:52|~4.5 h|long
EOF
)

menu() {
    cat <<'EOF'

  AI plays The Legend of Zelda (NES) - BizHawk harness

  Frames are NES frames at 60.0988 Hz. "game" is what the run is worth; "wall"
  is how long it takes here. Both measured on this machine, not estimated.

EOF
    local n=0 name desc frames game wall kind key
    while IFS='|' read -r name desc frames game wall kind; do
        # A short row would silently inherit the previous row's key - which is how
        # `plan` ended up listed as [w] and would have launched the wrong run.
        if [[ -z "${kind:-}" || -z "${name:-}" ]]; then
            echo "  !! malformed catalogue row: $name" >&2
            return 1
        fi
        n=$((n + 1))
        case "$kind" in
            quick|searched) key="$n" ;;
            tool)           key="p" ;;
            long)           key="w" ;;
            *) echo "  !! unknown kind '$kind' for $name" >&2; return 1 ;;
        esac
        printf '   %-4s %-11s %-54s %8s  %6s  %7s\n' "[$key]" "$name" "$desc" \
            "$frames" "$game" "$wall"
    done <<<"$CATALOGUE"
    cat <<'EOF'

  [n]   run it in this terminal
  [w]   run it detached (setsid), for the long ones
  ZELDA_SCOUTS=<k>   scout emulators for the searched runs (default 4)

  Specced in RUN-IDEAS.md but NOT built yet:
    route5      Gleeok (Level 4) then Level 1 - the reverse of run6's order.
                Legal: Gleeok needs the White Sword, not the bow, and 5 hearts
                is reachable without L1. Stops at 14:06 in-game, ~1.6 h search.

EOF
}

detach() { # detach <logfile> <cmd...>
    local log="$1"; shift
    mkdir -p "$LOGS"
    setsid nohup "$@" >"$log" 2>&1 < /dev/null &
    disown
    echo
    echo "  running detached. log: $log"
    echo "  follow:  tail -f $log"
}

confirm() { # confirm <minutes>
    local a
    read -r -p "  about $1. run it? [y/N] " a
    [[ "$a" == [yY] ]]
}

run_one() { # run_one <name> [extra]
    case "$1" in
        milestone1) python3 -u milestone1.py ;;
        milestone2) python3 -u milestone2.py ;;
        milestone3) ZELDA_SCOUTS="$SCOUTS" python3 -u milestone3.py ;;
        verify)
            python3 -u -c '
from pathlib import Path
from zelda import replay
WANT = "3115e31ff1a9b16e732160f81fe478a5052668ff"
print("replaying runs/run6/inputs.txt from power-on in a fresh emulator...")
_, fp = replay.verify(Path("runs/run6/inputs.txt"), WANT)
raise SystemExit(0 if fp == WANT else 1)
' ;;
        watch) python3 -u watch_run.py ;;
        plan)   python3 -u route_planner.py "${2:-90}" ;;
        fullgame) bash run_until.sh "logs/run_until.log" 40 ;;
        *) echo "unknown run: $1" >&2; return 2 ;;
    esac
}

case "${1:-}" in
    ""|help|-h|--help) menu ;;
    1) run_one milestone1 ;;
    2) run_one milestone2 ;;
    3) run_one milestone3 ;;
    4) run_one verify ;;
    w|watch)
        confirm "38 minutes"
        detach "$LOGS/watch.log" python3 -u watch_run.py ;;
    p|plan) run_one plan "${2:-90}" ;;
    f|fullgame)
        confirm "4.5 hours"
        detach "$LOGS/fullgame.log" bash run_until.sh "logs/run_until.log" 40 ;;
    milestone1|milestone2|milestone3|verify|watch|fullgame) run_one "$1" ;;
    *) echo "unknown selection: $1   (try ./zelda.sh for the list)" >&2; exit 2 ;;
esac
