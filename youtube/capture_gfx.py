"""Emulator captures for the documentary graphics. Everything here replays REAL inputs of the verified fourth run
from its own checkpoint states (states/run4), or evaluates the real lookahead branches - nothing is staged.

  ramvision : Level 1's five-Stalfos room, frame by frame: screenshot + what the bot reads from RAM
  lookahead : one decision point in Level 3's Darknut room: the root frame and all nine futures with their scores
  tilelearn : an overworld screen: screenshot + the tile grid + the planned path

usage (from harness/): python youtube/capture_gfx.py [ramvision] [lookahead] [tilelearn]"""
import json
import pathlib
import shutil
import sys

sys.path.insert(0, ".")
from zelda import replay, lookahead                                     # noqa: E402
from zelda.emulator import BizHawk                                       # noqa: E402
from zelda.overworld import Navigator, read_enemies, read_cells, TileKB, enemy_name, plan  # noqa: E402

import os
RUN = os.environ.get("ZELDA_CAP_RUN", "run6")
ARCH = pathlib.Path({"run4": "logs/archive/fourth_run_20260919", "run5": "logs/archive/fifth_run_20260921", "run6": "logs/archive/sixth_run_20260922"}[RUN])
OUT = pathlib.Path("youtube/capture") / RUN
INPUTS = replay.load_inputs(ARCH / "fullgame.inputs.txt")


def frames_of(seg):
    names = sorted(((json.load(open(f))["frames"], f.stem[9:]) for f in (ARCH / "checkpoints").glob("fullgame_*.json")))
    prev = 0
    for fr, n in names:
        if n == seg:
            return prev, fr
        prev = fr
    raise KeyError(seg)


def prev_seg(seg):
    names = [n for _, n in sorted(((json.load(open(f))["frames"], f.stem[9:]) for f in (ARCH / "checkpoints").glob("fullgame_*.json")))]
    return names[names.index(seg) - 1]


def shot(emu, dest):
    p = emu.screenshot("_cap_tmp")
    shutil.copyfile(p, dest)


def ramvision(emu):
    seg = "l1_53_key"
    d = OUT / "ramvision"
    d.mkdir(parents=True, exist_ok=True)
    a, b = frames_of(seg)
    s = emu.load(f"{RUN}/ckpt_fullgame_{prev_seg(seg)}")
    meta = []
    for k in range(a, b):
        s = emu.step(INPUTS[k], 1)
        shot(emu, d / f"{k - a:04d}.png")
        ens = [(e[0], e[1], enemy_name(e[1]), e[2], e[3], e[4]) for e in read_enemies(emu)]
        meta.append({"x": s.x, "y": s.y, "hearts": s.hearts, "keys": s.keys, "bombs": s.bombs, "room": s.room,
                     "buttons": list(INPUTS[k]), "enemies": ens,
                     "ram": {"70": list(emu.ram(0x70, 12)), "84": list(emu.ram(0x84, 12)), "34F": list(emu.ram(0x34F, 12)),
                             "485": list(emu.ram(0x485, 12))}})
    (d / "meta.json").write_text(json.dumps(meta))
    print("ramvision:", len(meta), "frames", flush=True)


def _branches(emu, s0, hp0, n0, tl, save_dir=None):
    root = emu.msave()
    res = []
    for m in lookahead.macros_for("fight"):
        emu.mload(root)
        lookahead.run_macro(emu, m)
        s2 = emu.step((), 14)
        hp1, n1 = lookahead.enemy_hp_total(emu)
        sc = lookahead.fight_score(s0, s2, hp0, n0, hp1, n1, {"hold": 8, "wait": 6}.get(m[0], 14))
        if m[0] == "swing" and hp1 >= hp0 and n1 >= n0:          # the planner's price for cutting the air
            dx, dy = {"Right": (1, 0), "Left": (-1, 0), "Down": (0, 1), "Up": (0, -1)}[m[1]]
            reach = any((dx and abs(e[3] - s0.y) < 16 and 0 < (e[2] - s0.x) * dx <= 28) or
                        (dy and abs(e[2] - s0.x) < 16 and 0 < (e[3] - s0.y) * dy <= 28) for e in tl)
            sc -= 150 if reach else 400
        if m[0] == "wait":
            sc -= 25
        name = f"{m[0]}_{m[1] or 'none'}"
        if save_dir is not None:
            shot(emu, save_dir / f"{name}.png")
        res.append({"macro": m[0], "dir": m[1], "file": f"{name}.png", "score": round(sc, 1), "x": s2.x, "y": s2.y,
                    "hearts": s2.hearts, "hp": hp1, "n": n1})
    emu.mload(root)
    emu.mfree(root)
    return res


def look(emu):
    """Scan the real Darknut fight for the decision point whose nine futures differ the most (one gets Link hurt,
    another lands a hit), then save that root frame and all nine outcomes."""
    seg = "5b_bombs"
    d = OUT / "lookahead"
    d.mkdir(parents=True, exist_ok=True)
    a, b = frames_of(seg)
    emu.load(f"{RUN}/ckpt_fullgame_{prev_seg(seg)}")
    best = danger = None
    k = a
    while k < b - 40:
        for _ in range(8):
            emu.step(INPUTS[k], 1)
            k += 1
        s0 = emu.state()
        tl = [e for e in read_enemies(emu) if lookahead.killable(e)]
        if not tl or min(max(abs(e[2] - s0.x), abs(e[3] - s0.y)) for e in tl) > 40:
            continue
        hp0, n0 = lookahead.enemy_hp_total(emu)
        res = _branches(emu, s0, hp0, n0, tl)
        hurt = any(r["hearts"] < s0.hearts for r in res)
        base = max(r["hp"] for r in res if r["macro"] == "hold")
        hit = any(r["macro"] == "swing" and r["hp"] < base for r in res)        # a swing that itself lands
        kinds = len({round(r["score"] / 20) for r in res})
        key = (hurt and hit, hit, kinds)
        if best is None or key > best[0]:
            best = (key, k)
        dkey = (hurt, max(r["score"] for r in res) - min(r["score"] for r in res))
        if danger is None or dkey > danger[0]:
            danger = (dkey, k)
    for tag, at in (("strike", best[1]), ("danger", danger[1])):
        dd = d / tag
        dd.mkdir(parents=True, exist_ok=True)
        emu.load(f"{RUN}/ckpt_fullgame_{prev_seg(seg)}")
        for j in range(a, at):
            emu.step(INPUTS[j], 1)
        shot(emu, dd / "root.png")
        s0 = emu.state()
        tl = [e for e in read_enemies(emu) if lookahead.killable(e)]
        hp0, n0 = lookahead.enemy_hp_total(emu)
        res = _branches(emu, s0, hp0, n0, tl, save_dir=dd)
        (dd / "meta.json").write_text(json.dumps({"frame": at - a, "link": [s0.x, s0.y], "hearts": s0.hearts, "hp0": hp0, "n0": n0,
                                                  "enemies": [(e[1], enemy_name(e[1]), e[2], e[3]) for e in read_enemies(emu)],
                                                  "branches": res}))
        print(tag, "at frame", at - a, [(r["macro"], r["dir"], r["score"], r["hearts"], r["hp"]) for r in res], flush=True)


def tilelearn(emu):
    d = OUT / "tilelearn"
    d.mkdir(parents=True, exist_ok=True)
    seg = "ow_66"
    a, b = frames_of(seg)
    s = emu.load(f"{RUN}/ckpt_fullgame_{prev_seg(seg)}")
    shot(emu, d / "screen.png")
    cells = read_cells(emu)
    kb = TileKB()
    kb.use(s.level, s.mode)
    walk = sorted(kb.walkable)
    solid = sorted(kb.solid)
    track = []
    for k in range(a, b):
        s = emu.step(INPUTS[k], 1)
        track.append((s.x, s.y, s.mode))
        if (k - a) % 4 == 0:
            shot(emu, d / f"f{(k - a) // 4:04d}.png")
    ev = json.loads(pathlib.Path("knowledge/tiles.json").read_text(encoding="utf-8"))["ow"].get("evidence", {})
    (d / "meta.json").write_text(json.dumps({"cells": cells, "walkable": walk, "solid": solid, "track": track, "start": [track[0][0], track[0][1]],
                                             "evidence": ev}))
    print("tilelearn:", len(track), "frames; evidence entries", len(ev), flush=True)


if __name__ == "__main__":
    want = sys.argv[1:] or ["ramvision", "lookahead", "tilelearn"]
    emu = BizHawk(log_name="capture_gfx.log", clean_sram=False)
    Navigator(emu)
    try:
        if "ramvision" in want:
            ramvision(emu)
        if "lookahead" in want:
            look(emu)
        if "tilelearn" in want:
            tilelearn(emu)
    finally:
        emu.close()
