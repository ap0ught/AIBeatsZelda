"""Replay the verified input log with A/V capture on, so the finished run can be rendered.

The run itself is played with recording off (it is thousands of searched attempts and hours of
wall clock). The artifact is the input log, so the video is made by replaying that log in a fresh
emulator from power-on - the same thing the verification does, with the camera running.

Segment boundaries come from the checkpoint files, so the overlay panel can say what the bot was
doing at each point in the run.

Usage: python record_run.py [name]      (default: fullgame)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from zelda.emulator import BizHawk, LOGS_DIR
from zelda import intent, replay

NARRATION = {
    "ms_sword": "THE MAGICAL SWORD - four times the wooden sword's damage",
    "s9_silver": "Cellar: THE SILVER ARROW. The only thing that can kill Ganon",
    "g9_04_bomb": "Out of bombs at a bombable wall. The drop table says a Red Wizzrobe killed FIRST can drop one",
    "g9_03_st": "Another hidden staircase: clear the room, push the block in the ring",
    "g9_52_patra": "A second PATRA, directly beneath Ganon",
    "g9_42": "GANON'S ROOM",
    "g9_ganon": "GANON. Invisible: four sword hits stun him, then one Silver Arrow. Read from the game's own code",
    "g9_power": "THE TRIFORCE OF POWER",
    "g9_32": "North, to the last room",
    "g9_zelda": "ZELDA. Put out the guard fires, stand in front of her",
    "g9_credits": "THE END - beaten from power-on, no cheats, no save states",
    "start": "Power on. Register a file, walk into the first cave, take the wooden sword",
    "enter_L3": "LEVEL 3 (the Manji). Raft is in here",
    "cellar": "Cellar: THE RAFT",
    "manhandla": "BOSS: Manhandla. Four heads, one bomb each",
    "L3_done": "TRIFORCE 1 of 3 taken (Level 3)",
    "enter_L1": "LEVEL 1 (the Eagle). Six keys, six locked doors, no bombs",
    "l1_bow": "Cellar: THE BOW",
    "l1_44_boom": "THE BOOMERANG",
    "aquamentus": "BOSS: Aquamentus. Sword beams from full health",
    "enter_L6": "LEVEL 6 (the Dragon)",
    "l6_mini": "A GLEEOK blocks the way - a mini-boss, not the boss. The sword only, point blank",
    "l6_3a_st": "The cartridge says Level 6 is two wings joined by a staircase. This is it",
    "gohma": "BOSS: GOHMA. Sword, bombs, boomerang: nothing. An arrow from underneath: two hits",
    "L6_done": "TRIFORCE 6 of 8",
    "l7_drain": "Playing the recorder on the pond - Level 7's door is underneath it",
    "l7_feed": "A Goriya who cannot be killed, only fed. That meat cost sixty rupees",
    "l7_candle": "THE RED CANDLE - the first candle of the whole run",
    "l7_38": "DIGDOGGER. The sword does nothing; the recorder splits it apart",
    "l7_aqua": "BOSS: Aquamentus again",
    "L7_done": "TRIFORCE 7 of 8",
    "enter_L8": "LEVEL 8 (the Lion). Every guide says burn the bush - that tile is drawn as mountain",
    "cave_6b": "A hundred rupees under a burnt tree. Measured, not read in a guide",
    "l8_4b": "Eight POLS VOICE. One arrow each - the sword kills Link every time",
    "l8_gleeok": "BOSS: a four-headed GLEEOK",
    "L8_done": "TRIFORCE 8 of 8. Every dungeon in the game is finished",

    "L1_done": "TRIFORCE 2 of 3, and the fifth heart container",
    "white_sword": "THE WHITE SWORD. Double damage - this is what beats Gleeok",
    "l4_sail": "The raft sails to the island dungeon",
    "enter_L4": "LEVEL 4 (the Snake)",
    "l4_ladder": "Cellar: THE STEPLADDER",
    "l4_00": "MANHANDLA, unavoidable without bombs",
    "l4_12": "Six blade traps. They cannot be killed, only dodged",
    "gleeok": "BOSS: GLEEOK. Two heads. This fight stopped the run five times with the wooden sword",
    "l4_heart": "Heart container: six hearts now",
    "L4_done": "TRIFORCE 3 of 3 (Level 4)",
}


def boundaries(name: str) -> dict[int, str]:
    """{start_frame: segment} for the run that actually happened.

    Two bugs lived here. The glob picked up EVERY checkpoint on disk, including ones left by
    abandoned branches (a dead "Level 4 before Level 1" attempt, six whirlwind retries, a raft dock
    probe), so the finished video announced rooms the bot never visited. And each caption was keyed
    to `frames`, the count AFTER the segment finished, so every caption named the room Link had just
    left. The ordered `segments` list inside the newest checkpoint is the authority on what ran, and
    a segment starts where the previous one ended.
    """
    saved: dict[str, dict] = {}
    for p in (LOGS_DIR / "checkpoints").glob(f"{name}_*.json"):
        d = json.loads(p.read_text())
        if d.get("segments"):
            saved[d["segments"][-1]] = d
    if not saved:
        return {}
    newest = max(saved.values(), key=lambda d: d["frames"])
    out: dict[int, str] = {}
    start = 0
    for seg in newest["segments"]:
        d = saved.get(seg)
        if d is None:
            continue
        out[start] = seg
        start = d["frames"]
    return out


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "fullgame"
    frames = replay.load_inputs(LOGS_DIR / f"{name}.inputs.txt")
    marks = boundaries(name)
    print(f"{len(frames)} frames, {len(marks)} segment boundaries")
    with BizHawk(log_name=f"{name}_record.log", record=f"{name}_run") as emu:
        def announce(seg: str) -> None:
            head, why = intent.for_segment(seg, NARRATION)
            facts = intent.facts_from(emu.state())          # counts are read live, never remembered from an old run
            emu.note(f"{intent.fill(head, facts)}||{intent.fill(why, facts)}")      # the overlay splits on ||

        i = 0
        while i < len(frames):
            if i in marks:
                announce(marks[i])
            j = i + 1
            while j < len(frames) and frames[j] == frames[i] and j not in marks:
                j += 1
            emu.step(frames[i], j - i)
            i = j
        for fr in sorted(f for f in marks if f >= len(frames)):
            announce(marks[fr])             # the final segment's caption lands on the last frame
        s = emu.state()
        print("replayed to", s)
        print("fingerprint", replay.fingerprint(emu))


if __name__ == "__main__":
    main()
