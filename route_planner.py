"""Which order should the errands go in?  A whole-game route search over the decoded overworld.

An ERRAND is a dungeon, a sword cave, a shop purchase, a rupee secret or an overworld heart container. A route is
an ordered list of errands; evaluate() walks it with the overworld router (zelda/owroute.py), the whirlwind (after
the recorder; it sets Link down on the LEFT EDGE of a finished dungeon's screen), the raft and the ladder, and adds
what each errand costs. Dungeon times are the third run's own measurements, split into walking and fighting, with
the fighting scaled by the sword Link would be carrying (wood 1, white 2, magical 4 damage).

Everything here is planning arithmetic on the cartridge's map - no emulator. usage: python route_planner.py"""
from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

from zelda import owroute

CACHE = Path("knowledge/ow_legs.json")

# ---- places: (screen, x, y) where Link stands to do the thing ------------------------------------------------
P = {
    "start": (0x77, 64, 93), "L1": (0x37, 112, 141), "L2": (0x3C, 112, 141), "L3": (0x74, 128, 141),
    "L4": (0x45, 128, 141), "L5": (0x0B, 112, 141), "L6": (0x22, 112, 141), "L7": (0x42, 112, 157),
    "L8": (0x6D, 160, 125), "L9": (0x05, 80, 173), "WS": (0x0A, 32, 93), "MS": (0x21, 144, 165),
    "candle_0C": (0x0C, 128, 93), "candle_5E": (0x5E, 112, 93), "candle_66": (0x66, 112, 93),
    "arrows_25": (0x25, 160, 93), "arrows_44": (0x44, 64, 93), "arrows_4A": (0x4A, 176, 93), "arrows_6F": (0x6F, 48, 93),
    "bait_34": (0x34, 64, 125), "bait_26": (0x26, 48, 93), "bait_46": (0x46, 144, 189), "bait_4D": (0x4D, 208, 173),
    "r100_0F": (0x0F, 128, 141), "r100_62": (0x62, 128, 109), "r100_6B": (0x6B, 128, 173),
    "r30_13": (0x13, 32, 93), "r30_28": (0x28, 208, 173), "r30_2D": (0x2D, 80, 93), "r30_3D": (0x3D, 144, 125),
    "r30_48": (0x48, 208, 109), "r30_67": (0x67, 112, 93), "r30_71": (0x71, 80, 93),
    "h_2C": (0x2C, 144, 173), "h_2F": (0x2F, 96, 141), "h_47": (0x47, 176, 189), "h_7B": (0x7B, 144, 93),
    "h_5F": (0x5F, 192, 141),
    "bracelet": (0x24, 224, 125),
    "warp_1D": (0x1D, 48, 157), "warp_23": (0x23, 48, 157), "warp_49": (0x49, 48, 157), "warp_79": (0x79, 128, 157),
}
WARPS = ["warp_1D", "warp_23", "warp_49", "warp_79"]
WARP = 520                             # push the rock, in, the right staircase, out (estimate: cave in/out is ~400)
BRACELET = 260                         # wake the Armos, step aside, pick the bracelet up
DOOR_SCREEN = {1: 0x37, 2: 0x3C, 3: 0x74, 4: 0x45, 5: 0x0B, 6: 0x22, 7: 0x42, 8: 0x6D}
WHIRL_Y = 141                          # the wind sets Link down at x=0 at the height he played the recorder
WHIRL = 600                            # subscreen aside: one note, the wait, the ride, the landing (549-565 measured)

# ---- what errands cost (frames; third run) -------------------------------------------------------------------
ENTER = {1: 294, 2: 272, 3: 303, 4: 269, 5: 265, 6: 272, 7: 177 + 268, 8: 429, 9: 673}
LEAVE = 182                                                     # Triforce warp back to the door
#            walk   fight  boss   sword the measurement was made with, boss scales with the sword?
DUNGEON = {1: (3236, 5601, 0, 1, False), 2: (3225, 1342, 592, 2, False), 3: (8338, 0, 0, 1, False),
           4: (6147, 6671, 697, 2, True), 5: (4503, 9688, 463, 2, True), 6: (2735, 5991, 721, 2, False),
           7: (6052, 4509, 1241, 2, True), 8: (4030, 4923, 1252, 2, True), 9: (6723, 11547, 1145, 4, True)}
RED_CANDLE_DETOUR = 2400               # Level 7's candle cellar, only walked if no candle has been bought
CAVE = 750                             # a secret: open it, in, take, out
SHOP = 820
HEART_CAVE = 800
SWORD_CAVE = {"WS": 973, "MS": 900}
DROPS_PER_DUNGEON = 7                  # rupees picked up along the way (195 at Level 5 with 160 from caves)


def fight_scale(measured_with: int, carrying: int) -> float:
    """Fights are part approach, part hits. Hits scale with damage; the approach does not."""
    return 0.45 + 0.55 * (measured_with / carrying)


def dungeon_time(level: int, sword: int, have_candle: bool) -> float:
    walk, fight, boss, s0, boss_scales = DUNGEON[level]
    k = fight_scale(s0, sword)
    t = walk + fight * k + boss * (k if boss_scales else 1.0) + ENTER[level] + (LEAVE if level < 9 else 0)
    if level == 7 and not have_candle:
        t += RED_CANDLE_DETOUR
    return t


# ---- legs ----------------------------------------------------------------------------------------------------
def _install_special_edges(raft: bool):
    base = owroute.neighbors

    def neighbors(node, ladder):
        yield from base(node, ladder)
        room, x, y = node
        if raft:
            if node == (0x55, 128, 125):
                yield (0x45, 128, 221), 200.0
            if node == (0x45, 128, 221):
                yield (0x55, 128, 125), 200.0
            if node == (0x3F, 96, 125):
                yield (0x2F, 96, 221), 200.0
            if node == (0x2F, 96, 221):
                yield (0x3F, 96, 125), 200.0
        # the 100-rupee screen: up through the "rock" at x=128 from 0x1F (walked twice by the third run)
        # (the wall above (128,93) on 0x1F is drawn as rock and is not: the game's own hidden road)
        if node == (0x1F, 128, 93):
            yield (0x0F, 128, 221), 150.0
        if node == (0x0F, 128, 221):
            yield (0x1F, 128, 93), 150.0
    owroute.neighbors = neighbors
    return base


def build_legs() -> dict:
    """legs[variant][a][b] = frames, for variant in base / raft / ladder (= raft + ladder)."""
    out = {}
    t0 = time.time()
    for variant, (raft, ladder) in {"base": (False, False), "raft": (True, False), "ladder": (True, True)}.items():
        owroute.free.cache_clear()
        base = _install_special_edges(raft)
        nodes = {}
        for name, (r, x, y) in P.items():
            nodes[name] = owroute.nearest_free(r, x, y, ladder, radius=64)
        for lvl, r in DOOR_SCREEN.items():
            n = owroute.nearest_free(r, 0, WHIRL_Y, ladder, radius=120)      # the wind's landing, walked out of the rock
            nodes[f"wind{lvl}"] = n
        table = {}
        for a, na in nodes.items():
            if na is None:
                continue
            dist, _, _ = owroute.dijkstra(na, ladder)
            table[a] = {b: round(dist[nb], 1) for b, nb in nodes.items() if nb is not None and nb in dist}
        out[variant] = table
        owroute.neighbors = base
        missing = [n for n, v in nodes.items() if v is None]
        print(f"  {variant}: {len(table)} sources, unplaced {missing}, {time.time() - t0:.0f}s", flush=True)
    CACHE.write_text(json.dumps(out), encoding="utf-8")
    return out


def legs() -> dict:
    if CACHE.exists() and "--rebuild" not in sys.argv:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return build_legs()


# ---- errands -------------------------------------------------------------------------------------------------
MONEY = {"r100_0F": 100, "r100_62": 100, "r100_6B": 100, "r30_13": 30, "r30_28": 30, "r30_2D": 30, "r30_3D": 30,
         "r30_48": 30, "r30_67": 30, "r30_71": 30}
NEEDS_CANDLE = {"r100_62", "r100_6B", "r30_28", "r30_48", "h_47", "bait_46", "bait_4D"}
NEEDS_BOMB = {"r30_13", "r30_2D", "r30_67", "r30_71", "h_2C", "h_7B", "bait_26"}
PRICE = {"candle": 60, "arrows": 80, "bait_34": 60, "bait_26": 100, "bait_46": 100, "bait_4D": 100}


class Infeasible(Exception):
    pass


def evaluate(seq, L, explain: bool = False):
    """Total frames for doing `seq` in order from the start cave, or raises Infeasible."""
    t = 1037.0                                     # power-on to sword in hand (measured; fixed)
    at = "start"
    done = set()
    rupees, hearts, sword = 0, 3, 1
    candle = arrows = bait = recorder = raft = ladder = bow = bombs = bracelet = False
    levels = set()
    lines = []
    if len(set(seq)) != len(seq):
        raise Infeasible("an errand twice")
    for e in seq:
        variant = "ladder" if ladder else "raft" if raft else "base"
        tab = L[variant]
        walk = tab.get(at, {}).get(e)
        best, how = (walk, "walk") if walk is not None else (None, None)
        if recorder:
            for lvl in levels - {9}:
                w = tab.get(f"wind{lvl}", {}).get(e)
                if w is not None and (best is None or WHIRL + w < best):
                    best, how = WHIRL + w, f"wind to L{lvl}"
        if bracelet:
            for wa in WARPS:
                for wb in WARPS:
                    if wa == wb:
                        continue
                    a1, b1 = tab.get(at, {}).get(wa), tab.get(wb, {}).get(e)
                    if a1 is not None and b1 is not None and (best is None or a1 + WARP + b1 < best):
                        best, how = a1 + WARP + b1, f"{wa[5:]}>{wb[5:]}"
        if best is None:
            raise Infeasible(f"cannot reach {e} from {at}")
        cost = 0.0
        if e.startswith("L"):
            lvl = int(e[1])
            need = {4: raft, 5: ladder, 6: bow and arrows, 7: recorder and bait and ladder, 8: candle and ladder,
                    9: len(levels) == 8 and bow and arrows and bombs}.get(lvl, True)
            if not need:
                raise Infeasible(f"{e} before its key item")
            red = lvl == 7 and not candle
            cost = dungeon_time(lvl, sword, candle)
            levels.add(lvl)
            hearts += 1 if lvl < 9 else 0
            rupees += DROPS_PER_DUNGEON
            if lvl == 3:
                raft = bombs = True
            if lvl == 4:
                ladder = True
            if lvl == 1:
                bow = True
            if lvl == 5:
                recorder = True
            if red:
                candle = True
        elif e in ("WS", "MS"):
            if hearts < (5 if e == "WS" else 12) or (e == "MS" and False):
                raise Infeasible(f"{e} with {hearts} hearts")
            sword = max(sword, 2 if e == "WS" else 4)
            cost = SWORD_CAVE[e]
        elif e.startswith("candle"):
            if candle or rupees < 60:
                raise Infeasible("candle: no money or already owned")
            rupees -= 60
            candle = True
            cost = SHOP
        elif e.startswith("arrows"):
            if arrows or rupees < 80:
                raise Infeasible("arrows: no money or already owned")
            rupees -= 80
            arrows = True
            cost = SHOP
        elif e.startswith("bait"):
            if bait or rupees < PRICE[e]:
                raise Infeasible("bait: no money or already owned")
            rupees -= PRICE[e]
            bait = True
            cost = SHOP
        elif e in MONEY:
            rupees = min(255, rupees + MONEY[e])
            cost = CAVE
        elif e == "bracelet":
            if bracelet:
                raise Infeasible("bracelet twice")
            bracelet = True
            cost = BRACELET
        elif e.startswith("warp_"):
            raise Infeasible("a warp cave is a road, not an errand")
        elif e.startswith("h_"):
            hearts += 1
            cost = HEART_CAVE if e != "h_5F" else 60
        if e in NEEDS_CANDLE and not candle:
            raise Infeasible(f"{e} needs a candle")
        if e in NEEDS_BOMB and not bombs:
            raise Infeasible(f"{e} needs bombs")
        if e == "h_5F" and not ladder:
            raise Infeasible("h_5F needs the ladder")
        if e == "h_2F" and not raft:
            raise Infeasible("h_2F needs the raft")
        t += best + cost
        if explain:
            lines.append(f"   {e:10s} {how:12s} leg {best:6.0f}  errand {cost:6.0f}   t={t / 3606:5.2f} min  "
                         f"hearts {hearts} rupees {rupees} sword {sword}")
        at = e
    if 9 not in levels:
        raise Infeasible("no Level 9")
    return (t, lines) if explain else t


CURRENT = ["L3", "r30_67", "L1", "WS", "L4", "L2", "r30_3D", "r100_0F", "L5", "arrows_44", "bait_34", "L6", "L7", "L8",
           "h_47", "MS", "L9"]
OPTIONAL = [e for e in P if e != "start" and not e.startswith("L") and not e.startswith("warp_")]


def search(L, seconds: float = 120.0, seed: int = 1):
    rng = random.Random(seed)
    best_seq, best_t = list(CURRENT), evaluate(CURRENT, L)
    cur, cur_t = list(best_seq), best_t
    t0 = time.time()
    n = 0
    while time.time() - t0 < seconds:
        n += 1
        temp = 1500.0 * (1.0 - (time.time() - t0) / seconds) + 20.0
        cand = list(cur)
        m = rng.random()
        if m < 0.35 and len(cand) > 2:
            i, j = rng.sample(range(len(cand)), 2)
            cand[i], cand[j] = cand[j], cand[i]
        elif m < 0.65:
            i = rng.randrange(len(cand))
            e = cand.pop(i)
            cand.insert(rng.randrange(len(cand) + 1), e)
        elif m < 0.85:
            e = rng.choice(OPTIONAL)
            if e not in cand:
                cand.insert(rng.randrange(len(cand) + 1), e)
        else:
            opt = [e for e in cand if not e.startswith("L")]
            if opt:
                cand.remove(rng.choice(opt))
        try:
            ct = evaluate(cand, L)
        except Infeasible:
            continue
        if ct < cur_t or rng.random() < math.exp((cur_t - ct) / temp):
            cur, cur_t = cand, ct
            if ct < best_t:
                best_seq, best_t = list(cand), ct
    return best_seq, best_t, n


if __name__ == "__main__":
    L = legs()
    t, lines = evaluate(CURRENT, L, explain=True)
    print(f"THE THIRD RUN'S ORDER, as the model sees it: {t:.0f} frames = {t / 3606:.2f} min (actual 148,766 = 41.26)")
    print("\n".join(lines))
    secs = float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].replace(".", "").isdigit() else 90.0
    results = []
    for seed in range(1, 5):
        seq, bt, n = search(L, seconds=secs / 4, seed=seed)
        results.append((bt, seq))
        print(f"seed {seed}: {bt:.0f} frames = {bt / 3606:.2f} min after {n} candidates", flush=True)
    bt, seq = min(results)
    t, lines = evaluate(seq, L, explain=True)
    print(f"\nBEST FOUND: {t:.0f} frames = {t / 3606:.2f} min   (model's saving against the current order: "
          f"{(evaluate(CURRENT, L) - t) / 60.1:.0f} s)")
    print("\n".join(lines))
