"""Append the closing captions to the recorded run's events file (the per-room captions are already written at
record time from zelda/captions.py). Idempotent: earlier closing lines are replaced.
usage: python closing_captions.py"""
import pathlib

import fullgame
import record_run

LOGS = pathlib.Path("logs")
ev_path = LOGS / "fullgame_run.events.txt"
marks = record_run.boundaries("fullgame")
names = [s[0] for s in fullgame.segments()]
lines = [l for l in ev_path.read_text(encoding="utf-8").splitlines()
         if "\tTHE END||" not in l and " FRAMES - " not in l]
last = max(int(l.split("\t")[0]) for l in lines)
total = len(record_run.replay.load_inputs(LOGS / "fullgame.inputs.txt"))
rescue = next(f for f, s in marks.items() if s == "g9_credits")


def fmt(f):
    return f"{int(f / 60.0988 // 60)}m{int(f / 60.0988 % 60):02d}s"


lines.append(f"{max(last + 400, total - 1600)}\tTHE END||Beaten from power-on: no cheats, no memory writes, no save states "
             f"in the playing. Zelda rescued at {fmt(rescue)} of game time.")
lines.append(f"{max(last + 800, total - 400)}\t{total:,} FRAMES - {fmt(total)}||{len(names)} searched segments, replayed "
             f"from power-on and verified (MATCH). Earlier runs: 1h43m, 58m30s, 42m05s, 40m05s, 38m09s.")
ev_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"closing lines added; rescue {fmt(rescue)}, total {fmt(total)} ({total} frames)")
