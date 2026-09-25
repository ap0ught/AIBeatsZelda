"""Try everything on a boss and report what actually hurts it.

Bosses in this game each ignore some weapons outright (the sword slides off Gohma, bombs bounce
off Dodongo unless he swallows them, Digdogger only splits for the recorder). Guessing from a
walkthrough has cost this run several dead ends, so this module does the obvious thing instead:
from one savestate, replay the same fight with every weapon and every aim point, watch the
boss's health byte, and rank what worked. It costs a couple of minutes and it is never wrong.
"""
from __future__ import annotations

from .emulator import BizHawk
from .overworld import read_enemies
from . import bot

# aim points relative to the boss, in pixels: where Link stands before attacking
AIMS = {
    "head":   (0, -48),     # above it, facing down
    "below":  (0, 48),
    "left":   (-56, 0),
    "right":  (56, 0),
    "far_left": (-100, 0),  # sword beams / arrows from across the room
    "far_right": (100, 0),
}
FACE = {"head": "Down", "below": "Up", "left": "Right", "right": "Left",
        "far_left": "Right", "far_right": "Left"}

WEAPONS = {            # name -> (b-slot item or None for the sword, button)
    "sword": (None, "A"),
    "bombs": (bot.B_BOMBS, "B"),
    "arrow": (bot.B_BOW, "B"),
    "boomerang": (bot.B_BOOMERANG, "B"),
    "recorder": (bot.B_RECORDER, "B"),
}


def _is_boss(types):
    """Which object ids count as the boss. The default 0x30-0x4F range fits the bosses this run
    has met so far; pass `types` for anything else. A Patra's core and orbiting eyes may sit
    outside that range, and a survey that cannot see its target reports "no damage" for every
    weapon - the same false negative the secret finder once gave."""
    return (lambda t: t in types) if types else (lambda t: 0x30 <= t < 0x50)


def boss_slot(emu: BizHawk, types=None) -> int | None:
    """The lowest-numbered live object that is not a projectile: bosses own slot 0 or 1."""
    ts = emu.ram(0x34F, 12)
    match = _is_boss(types)
    for i in range(12):
        if match(ts[i]):
            return i
    if types:
        return None
    for i in range(12):
        if ts[i] and ts[i] < 0x50:
            return i
    return None


def boss_health(emu: BizHawk, types=None) -> int:
    """Total health across the object slots (multi-head bosses spread it out).

    Types 0x50-0x5F are projectiles and 0x60+ are effects. They carry a health byte too, and
    counting them is how a survey ends up reporting that every weapon "did 15 damage" when what
    actually happened is that a fireball left the screen."""
    ts = emu.ram(0x34F, 12)
    hp = emu.ram(0x485, 12)
    match = _is_boss(types)
    return sum(hp[i] >> 4 for i in range(12) if match(ts[i]))


def _walk_to(emu: BizHawk, tx: int, ty: int, budget: int = 150) -> None:
    for _ in range(budget):
        s = emu.state()
        if abs(s.x - tx) <= 4 and abs(s.y - ty) <= 4:
            return
        d = ("Right" if s.x < tx - 4 else "Left" if s.x > tx + 4 else
             "Down" if s.y < ty - 4 else "Up")
        emu.step(d, 4)


def try_tactic(emu: BizHawk, snap: str, weapon: str, aim: str, swings: int = 12, types=None) -> dict:
    """Reload the boss room, stand at `aim`, attack with `weapon`, report the damage done."""
    emu.mload(snap)
    emu.wait(2)
    slot = boss_slot(emu, types)
    if slot is None:
        return {"weapon": weapon, "aim": aim, "damage": 0, "note": "no boss in the room"}
    bx, by = emu.byte(0x70 + slot), emu.byte(0x84 + slot)
    hp0 = boss_health(emu, types)
    item, button = WEAPONS[weapon]
    if item is not None and not bot.select_b_item(emu, emu.step, item):
        return {"weapon": weapon, "aim": aim, "damage": 0, "note": "item not in inventory"}
    dx, dy = AIMS[aim]
    best = 0
    for _ in range(swings):
        # Bosses move. Re-aim before every attack, or the survey measures nothing but misses -
        # which reads exactly like "this weapon does not work".
        sl = boss_slot(emu, types)
        if sl is None:
            break
        bx, by = emu.byte(0x70 + sl), emu.byte(0x84 + sl)
        tx = max(24, min(224, bx + dx))
        ty = max(80, min(200, by + dy))
        _walk_to(emu, tx, ty, budget=60)
        emu.step(FACE[aim], 1)
        emu.step(button, 2)
        emu.step((), 26)
        best = max(best, hp0 - boss_health(emu, types))
        if emu.byte(0x34D):
            return {"weapon": weapon, "aim": aim, "damage": hp0, "note": "ROOM CLEARED"}
    hearts = emu.state().hearts
    return {"weapon": weapon, "aim": aim, "damage": best, "note": f"{hearts} hearts left"}


def survey(emu: BizHawk, weapons=None, aims=None, log=print, types=None) -> list[dict]:
    """Try every weapon from every aim point against whatever is in this room."""
    weapons = weapons or list(WEAPONS)
    aims = aims or list(AIMS)
    s = emu.state()
    snap = emu.msave()
    ts = emu.ram(0x34F, 12)
    log(f"tactics survey in room {s.room:02X} level {s.level}: "
        f"objects {[f'{t:02X}' for t in ts if t]}, boss health {boss_health(emu, types)}")
    out = []
    try:
        for w in weapons:
            for a in aims:
                r = try_tactic(emu, snap, w, a, types=types)
                out.append(r)
                log(f"  {w:10s} from {a:10s} -> damage {r['damage']:2d}  ({r['note']})")
        emu.mload(snap)
    finally:
        emu.mfree(snap)
    out.sort(key=lambda r: -r["damage"])
    log("best: " + ", ".join(f"{r['weapon']}/{r['aim']}={r['damage']}" for r in out[:4]))
    return out
