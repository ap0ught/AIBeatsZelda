"""Sword combat from RAM.

Measured (probes/reach_trials.py, 40 swings at Zols): the wooden sword connects when the gap
between Link's box and the enemy's box is <= 10 px on the facing axis and the boxes overlap on the
other axis (we require |offset| <= 4). It misses at 13+ px. So fighting means getting nearly
touching-close, lining up, and swinging. Attacking is disabled while Link stands in a doorway.
"""
from __future__ import annotations

import os

from .emulator import BizHawk, State
from .overworld import (Navigator, NavError, LinkDied, read_enemies, read_room_item, enemy_name, snap,
                        DIRS, immune_to, DMG_SWORD, DMG_BOMB, read_ghost_objects)
from .lookahead import UNKILLABLE, killable
from . import drops
from . import ram

REACH = 10          # max box gap that still hits (measured)
ALIGN = 4           # max cross-axis offset between Link and the enemy

# ---------------------------------------------------------------- the dungeon clock
#
# All of this lives in zelda/drops.py now. It used to be a second hand-copy of the arithmetic that
# lookahead.py had already hardcoded for bombs, with its own ROWS and its own copy of the pre-kill
# -> post-kill rule, and the only thing that ever checked the two agreed was a probe. One table,
# one function: drops.prefer_target(emu, targets, item).
#
# Why a clock is worth steering for at all, and why there is no separate "is this room dangerous?"
# test: the clock sits in the drop rows of the two enemy families that FILL rooms (row 1: Ghini,
# Tektite, Leever, Zol, Stalfos, Pols Voice; row 2: blue Lynel/Moblin/Octorok, Vire, Gibdos, Red
# Darknut, Wizzrobe, Goriya). A room where a clock is reachable is therefore already a room worth
# fighting carefully, and the reachability condition IS the desire condition. It is also nearly
# free: every one of these kills was going to happen anyway, because the room is being cleared, so
# steering only chooses the ORDER and never adds a kill.
CLOCK_MIN_ROOM = 4
CLOCK_STEER = [True]          # module flag, so this can be turned off without editing clear_room

# The wall gate, as an A/B. Every other behaviour change in this file that was not obviously right
# got one of these, because "obviously right" is what a change that only ever runs on rooms with
# furniture in them looks like from the outside. ZELDA_NO_WALLS=1 puts the fighter back to walking
# by the sign of the difference and swinging whenever the box test passes, which is what it did
# for the whole of this project's history.
NO_WALLS = [bool(int(os.environ.get("ZELDA_NO_WALLS", "0")))]


def enemy_hp(e) -> int:
    return e[4] >> 4


# ---- where the sword actually reaches ----------------------------------------------------------------------
#
# THIS MODEL WAS BACKWARDS, and it is the largest thing wrong with the fighter.
#
# It used to be a pair of box sizes: REACH = 10 on the gap between the monster's half-width (16) and
# Link's, ALIGN = 4 across, so a swing was offered when the monster was 16 to 26 px away and lined
# up. It is a reasonable model of two boxes touching, and the game does not implement it. Measured on
# Level 3 room $4A: 33 hits in 115 aimed swings, and every one of the 82 misses was a swing at
# something 16 to 32 px away - i.e. every miss was a swing the cartridge had already refused, and the
# hits that did land were monsters that walked into the blade during the 13 frames of the animation.
#
# What the cartridge does (Z_01.asm, and it is four short routines with no guesswork in it):
#
#   CheckMonsterSwordCollision -> CheckMonsterStabbingCollision sets a threshold per axis and
#   SWAPS them on Link's facing: facing horizontally $0D = $10 (16) across, $0E = $0C (12) down;
#   facing vertically $0D = $0C (12) across, $0E = $10 (16) down.
#
#   CheckMonsterSlenderWeaponCollision2: the sword's own centre is a:ObjX + 8 / a:ObjY + 6 when
#   Link faces horizontally, + 6 / + 8 when he faces vertically. (The comment in the source asks
#   whether it should follow the weapon's direction rather than Link's facing. It does not, and that
#   is why a sword swung Left and a sword swung Right use the same 8/6.)
#
#   GetObjectMiddle: the monster's centre is ObjX + 8 and ObjY + 8 - or ObjX + 4 when ObjAttr ($4BF)
#   bit $40, "half width", is set.
#
#   DoObjectsCollideWithThresholds: |dx| >= threshold on X -> no hit; |dy| >= threshold on Y -> no
#   hit. Both are "nearer than", not "further than". So for a horizontal swing:
#
#       |ObjX - LinkX| < 16   and   |ObjY - LinkY + 2| < 12
#
# Sixteen is the whole reach. The old model refused to swing inside 16 px and reached to 26, which is
# outside the sword's actual range at one end and inside it at the other, and the fighter spent the
# room swinging at things it could not reach while standing next to things it could.
#
# One note on what is NOT in here: the beam (CheckMonsterSwordShotOrMagicShotCollision) uses a
# different box and a longer range, and is left alone. Nor is the Zol special-cased: UpdateZolState
# has three states - 0 Wander, 1 Shove, 2 Split - so "state 3" that hittable_now once tested for a
# Zol is a state a Zol cannot be in, which is why that gate made a room unclearable instead of
# clearing it faster. Z_04 Zol_CheckCollisions hits only in state 0 and turns the Zol around when it
# survives, which is the real reason a Zol is awkward: it does not stand still to be hit twice.
SWORD_ACROSS, SWORD_ALONG = 12, 16        # the smaller threshold, and the larger one
GEOM = [bool(int(os.environ.get("ZELDA_SWORD_GEOM", "1")))]
AXIS = {"Right": 0, "Left": 0, "Down": 1, "Up": 1}


def reach_box_model(s, e) -> str | None:
    """The model this file used until 2026-09-30, kept deliberately for two callers.

    A pair of box sizes: 16 for the monster's half-width, REACH = 10 of gap, ALIGN = 4 of line-up.
    It is wrong - see sword_reach - and it is NOT removed, because the two Darknut routines are built
    around it: they stand off at 16 + REACH - 4 = 22 px and strike as a Darknut walks past, and that
    distance was chosen against this reach. Correcting the reach without re-deriving that strategy
    would leave them walking to a post they can never swing from, and there is no Darknut checkpoint
    in this tree to measure the re-derivation on. So: measured correction for the ordinary path
    (attack_slot, fliers), and this kept, named, for the Darknuts until someone has a room for it.
    """
    dx, dy = e[2] - s.x, e[3] - s.y
    gx, gy = abs(dx) - 16, abs(dy) - 16
    if abs(dy) <= ALIGN and 0 <= gx <= REACH:
        return "Right" if dx > 0 else "Left"
    if abs(dx) <= ALIGN and 0 <= gy <= REACH:
        return "Down" if dy > 0 else "Up"
    return None


def sword_reach(emu: BizHawk, s, e) -> str | None:
    """Direction to swing at `e` and have the cartridge agree it landed, or None if nothing is in reach.

    ZELDA_SWORD_GEOM=0 restores the old box model, which is what the A/B in testing/probe_walls.py
    measures against.
    """
    if not GEOM[0]:
        return reach_box_model(s, e)
    half = 4 if emu.byte(0x4BF + e[0]) & 0x40 else 8
    mx, my = e[2] + half, e[3] + 8
    for d in ("Right", "Left", "Down", "Up"):
        vertical = AXIS[d] == 1
        sx = s.x + (6 if vertical else 8)
        sy = s.y + (8 if vertical else 6)
        across, along = (SWORD_ACROSS, SWORD_ALONG) if vertical else (SWORD_ALONG, SWORD_ACROSS)
        if abs(mx - sx) < across and abs(my - sy) < along:
            return d
    return None


def shield_side(facing: int, d: str, dx: int, dy: int) -> bool:
    """Is this swing into a Darknut's shield? Only a swing along its facing axis can be."""
    if AXIS[d] == 0:
        return (facing == 1 and dx < 0) or (facing == 2 and dx > 0)
    return (facing == 4 and dy < 0) or (facing == 8 and dy > 0)


# ---- wasted-shot instrument ---------------------------------------------------------------------------------
# A swing that was AIMED at a specific enemy and did no damage is a measurement, not a mood. It is
# the only signal that can tell "the fighter is aiming into a wall" apart from "the enemy moved" and
# "Link swung at nothing on purpose", and those three have been indistinguishable from the outside
# all session. One logged line with a tile coordinate settles it.
#
# The condition that keeps this from being noise: only swings committed to a TARGET count. Link
# swings at empty air constantly while repositioning, so an unconditional miss counter would be
# almost entirely legitimate swings and would drown the one line that matters.
#
# OFF by default - it notes, it never steers, but there is no reason to pay for it on a normal run.
WASTED = [bool(int(os.environ.get("ZELDA_WASTED", "0")))]
_wasted_stats = {"swings": 0, "hits": 0, "wasted": 0, "solid": 0, "in_wall": 0,
                  "buried": 0, "bumped": 0}
_wasted_log: list[str] = []


def hittable_now(emu: BizHawk, slot: int, t: int) -> bool:
    """Can this slot be hit AT ALL this frame, whatever Link does?

    Peahats ($0F) and Leevers ($10) spend most of their life in a burrow with state != 3, and the
    game will not damage them there - the navigator has known this for a long time (threats() leaves
    both out while st[slot] != 3, with the comment "neither is even drawn"), and the fighter never
    asked. So it walked up to a Peahat that was still underground, lined up on it and swung:
    measured on Level 3 room $4A, 82 aimed swings in six attempts that hit nothing, the top of the
    log the same two coordinates over and over with the enemy unmoved. Not one of them was a wall.
    They were a target the cartridge was refusing to let Link touch.

    $13, the ZOL, LOOKS like the same case and IS NOT, and it cost a run to find out. Every wasted
    swing the instrument reported on room $4A was a Zol at 2 HP, at a legal sword gap, reading state
    $00 - so the obvious extrapolation is that a Zol is unhittable until it comes out of the wall,
    the way a Leever is. Gating on that took the room from 82 wasted swings in six attempts to
    ZERO - and also from 33 hits to zero, and every attempt ended "died fighting" with the fighter
    never once swinging. A gate that makes a room unclearable has not removed wasted swings, it has
    removed the fight, and the two look identical in the counter that was supposed to tell them
    apart. There is no evidence anywhere in this project that a Zol's "out" state is 3; the Leever
    and Peahat rule is in production because threats() has always used it, and the Zol is left alone
    until someone reads UpdateZol rather than UpdateLeever.

    The Zora ($11) is the same shape with a different range: states 2, 3 and 4 are out of the water
    and 0, 1, 5 are not, so it is listed the way threats() lists it.
    """
    st = emu.byte(0xAC + slot)
    if t in (0x0F, 0x10):
        return st == 3
    if t == 0x11:
        return st in (2, 3, 4)
    return True


def _judge_swing(floor, here, slot: int, hp0: int, x: int, y: int, room: int) -> None:
    """Was the swing we just taken worth taking? Records it either way."""
    if not WASTED[0]:
        return
    emu = floor.emu
    e = find_enemy(emu, slot)
    _wasted_stats["swings"] += 1
    # Every aimed swing, hit or miss, binned by type and by how far away the target was. This is the
    # table that settles "how far does the sword reach" with evidence instead of arithmetic: the
    # disassembly gives the rule, and this says whether the rule is the one the cartridge is using.
    bucket = min(31, max(0, (abs(x - here[0]) + abs(y - here[1])) // 4 * 4))
    key = f"{e[1]:02X}@{bucket:02d}" if e is not None else f"--@{bucket:02d}"
    _wasted_stats.setdefault("reach", {})
    _wasted_stats["reach"].setdefault(key, [0, 0])[0 if (e is None or enemy_hp(e) < hp0) else 1] += 1
    # A dead enemy is a HIT, not a miss. The first version of this fell through to "wasted" here and
    # scored 1 swing / 0 hits / 1 wasted on a kill - a false positive on the most common event there
    # is, which would have made the instrument confidently wrong on almost every line it printed.
    if e is None or enemy_hp(e) < hp0:
        _wasted_stats["hits"] += 1
        return
    _wasted_stats["wasted"] += 1
    # THREE questions, because a miss has three different causes and only one of them is a wall.
    # The wall test is the LINE and not the target's own cell, because the first version asked the
    # cell and could therefore only ever report "the enemy is standing in a wall" - the rare case -
    # while the thing the strike gate prevents is a wall BETWEEN them. On room $4A the cell version
    # said "no" eighty-two times out of eighty-two, so it was measuring nothing at all.
    w = floor.wall_between(here[0], here[1], x, y)
    in_wall = floor.cell_solid(x, y) is not None
    buried = e is not None and not hittable_now(emu, slot, e[1])
    for key, on in (("solid", w is not None), ("in_wall", in_wall), ("buried", buried)):
        if on:
            _wasted_stats[key] += 1
    why = ("wall in the way" if w is not None else
           "target in a wall" if in_wall else
           f"still in its burrow (state {emu.byte(0xAC + slot):02X})" if buried else
           f"moved to ({e[2]},{e[3]})" if e is not None else "gone")
    # The type, the state byte and the gap, on the same line. A wasted swing that cannot say WHAT it
    # was aimed at is a wasted swing that has to be investigated again next time, and this one has
    # now cost two rounds of that: 82 of them on room $4A, none of them a wall, none of them a
    # burrow, and every one of them reported an enemy that stood still and took nothing.
    # Every byte the cartridge's own "can this be hit" path looks at, on the one line that has to
    # answer it: ObjAttr $4BF bit $20 Invincible (which skips ALL weapon collisions outright),
    # ObjInvincibilityTimer $4F0 (any value -> return), ObjMetastate $405 (nonzero -> dying).
    what = (f"type {e[1]:02X} {enemy_name(e[1])}" if e is not None else "type --")
    stt = emu.byte(0xAC + slot) if e is not None else 0
    attr = emu.byte(0x4BF + slot) if e is not None else 0
    inv = emu.byte(0x4F0 + slot) if e is not None else 0
    meta = emu.byte(0x405 + slot) if e is not None else 0
    _wasted_log.append(
        f"    wasted shot  room {room:02X}  aimed ({x},{y})  gap ({x - here[0]:+d},{y - here[1]:+d})"
        f"  {what}  hp {enemy_hp(e) if e is not None else 0}  state {stt:02X}  attr {attr:02X}"
        f"  inv {inv:02X}  meta {meta:02X}  {why}")


def wasted_report(emu: BizHawk) -> None:
    """Dump the instrument. Call once a segment has gone wrong, not every frame."""
    if not WASTED[0]:
        return
    st = _wasted_stats
    if not st["swings"] and not st["bumped"]:
        return
    if st["swings"]:
        emu.note(f"  [wasted] {st['wasted']} of {st['swings']} aimed swings did nothing"
                 + (f"; {st['solid']} had a wall in the way" if st["solid"] else "")
                 + (f"; {st['in_wall']} were aimed into a wall" if st["in_wall"] else "")
                 + (f"; {st['buried']} hit a target still in its burrow" if st["buried"] else ""))
    if st["bumped"]:
        emu.note(f"  [wasted] {st['bumped']} steps were refused as walls, blocks or water")
    if st.get("reach"):
        # type@distance: hits/misses. Printed because the sword's reach is the one number every
        # fighter decision leans on and it was wrong once already - see sword_reach.
        emu.note("  [reach] " + "  ".join(f"{k}:{v[0]}/{v[1]}"
                                          for k, v in sorted(st["reach"].items())))
    for line in _wasted_log[-12:]:
        emu.note(line)


def find_enemy(emu: BizHawk, slot: int):
    for e in read_enemies(emu):
        if e[0] == slot:
            return e
    return None


class Fighter:
    # The two ways off a wall, for a step that is blocked. Which one is tried first is decided by
    # how far each takes us from what we were walking towards, so going round a wall does not
    # double back the way it came.
    PERP_DIRS = {"Right": ("Down", "Up"), "Left": ("Down", "Up"),
                 "Up": ("Right", "Left"), "Down": ("Right", "Left")}
    GO_AROUND = 24          # frames to keep sliding along a wall before the geometry is re-read

    def __init__(self, nav: Navigator):
        from .overworld import Screen
        self.nav, self.emu = nav, nav.emu
        self.jitter = None       # (rng, probability) random pauses while positioning, used by search
        # One cached read of the screen's tiles per room, shared by every question the fighter asks
        # of the map: may I step there, is the sword's path clear, was that swing aimed at a wall.
        # See overworld.Screen for why the fighter needs one at all.
        self.floor = Screen(nav.emu, nav.kb)
        self.bumped = 0          # consecutive refused steps, for the note and the instrument
        self._around: tuple[str, int] | None = None

    def _around_candidates(self, d: str, s, toward=None) -> list[str]:
        """Sideways options off a blocked step, the one that closes on the target first."""
        a, b = self.PERP_DIRS[d]
        if toward is None:
            return [a, b]
        ax, ay = DIRS[a]
        bx, by = DIRS[b]
        da = abs(s.x + ax - toward[0]) + abs(s.y + ay - toward[1])
        db = abs(s.x + bx - toward[0]) + abs(s.y + by - toward[1])
        return [a, b] if da <= db else [b, a]

    def _move(self, d: str, target_slot: int | None = None, toward=None) -> State:
        """One step toward d, unless another enemy is about to be walked into; then step away from it.

        And now: unless there is a wall, a block or water in the way, in which case go round it.

        The navigator never walks into a wall, because `plan()` walks over `legal()`. This did:
        the approach was "step by the sign of the difference", so a Gibdo on the far side of a
        block cost one frame of nothing, per frame, until the budget ran out - the same invisible
        waste the wasted-shot instrument was built to find on the swing side, and the reason a
        room with furniture in it fought slower than the same room bare.

        Three things make the escape a route round rather than a refusal:
          * the tile is ASKED, with optimistic=True, so an unclassified tile never blocks - a
            fighter that stands still in a room it has not classified is a stall, and a stall in a
            fight is how a segment spends its whole budget doing nothing;
          * the slide is held for GO_AROUND frames rather than re-chosen every frame, because
            re-choosing every frame is a one-frame oscillation that never gets past a wall that is
            thicker than one pixel;
          * being refused is EVIDENCE. The tile goes into knowledge/tiles.json as solid, with the
            room and the pixel that proved it, in the same shape as every other line in there.
        """
        emu = self.emu
        if self.jitter and self.jitter[0].random() < self.jitter[1]:
            emu.step((), self.jitter[0].choice([1, 2, 4]))
        s = emu.state()
        dx, dy = DIRS[d]
        nx, ny = s.x + dx, s.y + dy
        ens = read_enemies(emu)
        # blade traps: crossing their line is fine (they take ~50 frames to arrive from a corner);
        # what kills is lingering. Only react to a trap that is actually sliding and close. First,
        # before the geometry below, because it is the only one of the three that is about this
        # frame rather than about where we are going.
        for e in ens:
            if e[1] != 0x49:
                continue
            parked = e[2] in (32, 208) and e[3] in (93, 189)
            if not parked and max(abs(e[2] - nx), abs(e[3] - ny)) < 36:
                if abs(e[3] - s.y) < 16:
                    return emu.step("Up" if s.y > e[3] or s.y > 141 else "Down", 1)
                return emu.step("Left" if s.x < e[2] and s.x > 40 else "Right", 1)
        tid = None if NO_WALLS[0] else self.floor.blocked(s, nx, ny)
        if tid is not None:
            tid = self.floor.confirm(s, nx, ny)          # one bus read, only on this path
        if tid is not None:
            self.floor.learn_blocked(s, d, tid, nx, ny)
            _wasted_stats["bumped"] += 1
            cands = ([self._around[0]] if self._around and self._around[1] > 0
                     else self._around_candidates(d, s, toward))
            for c in cands:
                cdx, cdy = DIRS[c]
                if self.floor.blocked(s, s.x + cdx, s.y + cdy) is not None:
                    continue
                self._around = (c, self.GO_AROUND)
                self.bumped += 1
                if self.bumped == 24:
                    emu.note(f"a wall (tile ${tid:02X}) is in the way of {d} at ({nx},{ny}); going round it")
                return emu.step(c, 1)
            self._around = None
            self.bumped += 1
            return emu.step((), 1)                 # boxed in on both sides: hold, do not lean on it
        if self._around:
            self._around = (self._around[0], self._around[1] - 1)
        self.bumped = 0
        for e in ens:
            if e[0] == target_slot or e[1] == 0x49:
                continue
            if max(abs(e[2] - nx), abs(e[3] - ny)) < 22:
                # something else is right there: step out of its line (perpendicular), not straight away
                ax, ay = s.x - e[2], s.y - e[3]
                if abs(ax) >= abs(ay):
                    away = "Up" if ay <= 0 else "Down"
                else:
                    away = "Left" if ax <= 0 else "Right"
                return emu.step(away, 1)
        return emu.step(d, 1)

    def reach_clear(self, s, e, d: str) -> bool:
        """Is the sword's path to this enemy clear of walls? If not, do not swing.

        The box test says the enemy is 16 to 26 px away and lined up. It says nothing about what
        is between them, and a wall in between is the whole content of a wasted swing: the swing
        plays, the enemy does not move, the fighter counts a miss and tries again from the same
        place. Sampled every 8 px - one cell - from Link's centre to the enemy's, which at that
        range is the sword's own reach and nothing more, and which also catches an enemy standing
        inside a wall rather than one hidden behind it.

        The beam is deliberately NOT gated here. Whether the sword beam stops at a wall is not
        established anywhere in this project, and a guess in either direction is worth less than
        the question: a wrong "it stops" would refuse beams that land, and a wrong "it passes"
        would only cost the same frames this gate saves.
        """
        if NO_WALLS[0]:
            return True
        return self.floor.wall_between(s.x, s.y, e[2], e[3]) is None


    def swing(self, d: str, back_off: bool = False) -> State:
        """Face d and swing. Link is committed for ~12 frames. Optionally step back afterwards."""
        emu = self.emu
        from .lookahead import face
        face(emu.step, d)
        emu.step("A", 2)
        s = emu.step((), 11)
        if back_off:
            opp = {"Left": "Right", "Right": "Left", "Up": "Down", "Down": "Up"}[d]
            s = emu.step(opp, 6)
        return s

    DARKNUTS = (0x0B, 0x0C)
    # Targets worth approaching from the right rather than head-on. Gleeok's head (0x43) is the
    # measured case: its hitbox is flawed on the right, so a swing from just off-centre right lands
    # while Link stays out of the fire line. Kept as a per-type set rather than a special case in the
    # approach, so a second boss with the same shape is one entry here and not another branch.
    RIGHT_FLANK = {0x43}
    BEAM_IMMUNE = {0x16, 0x1E, 0x2B, 0x2C, 0x2D}   # Pols Voice, Armos, Bubbles. Darknuts: beam works from side/back

    # A Vire is 4 HP and it does not die - it divides. Z_04 CheckVireCollisions:
    #
    #     ; If it was killed, then return.
    #     LDA ObjMetastate, X
    #     BNE @Exit                     <- died outright: no split
    #     ; If temporarily invincible, then it was harmed.
    #     ; Advance the state to split up.
    #     LDA ObjInvincibilityTimer, X
    #     BEQ @Exit
    #     INC ObjState, X                <- hurt but alive: state 1, which creates two Keese
    #
    # The trigger is BEING HURT, not dying. So the damage table decides everything (Z_01):
    #
    #     SwordDamagePoints:  .BYTE $10, $20, $40      wood 1, white 2, magical 4
    #     "Use $20 damage points for wooden arrows, and $40 for silver ones."
    #     bomb $40, fire rod $10, boomerang $00 (stun only, 160 frames)
    #
    # and the Vire's own 4 HP is ObjectTypeToHpPairs[9] = $42, masked &$F0 by ExtractHitPointValue
    # because type 0x12 is even, i.e. $40.
    #
    # So: kill it in ONE hit or do not touch it. A wooden or white sword swing and a wooden arrow all
    # leave a live Vire that immediately becomes two Blue Keese - a strict loss, and the harness was
    # doing exactly that, because 0x12 had no special case anywhere.
    #
    # A bomb is $40 and one-shots it, so bombs work. A Silver Arrow is $40 and one-shots it. And the
    # boomerang deals $00 while setting a $10 stun timer, which is the only way to hold one still long
    # enough to line up a real weapon - but note the Vire case in Z_01 @CheckZolVire: a boomerang goes
    # straight to DealDamage, while any OTHER hit first copies the weapon's direction into the Vire.
    VIRE = 0x12
    KEEZE = (0x1B, 0x1C, 0x1D)          # what a split Vire leaves behind
    # damage points by weapon, straight out of the disassembly
    DMG_WOOD, DMG_WHITE, DMG_MAGICAL = 1, 2, 4
    DMG_ARROW, DMG_SILVER_ARROW, DMG_BOMB, DMG_FIRE, DMG_BOOMERANG = 2, 4, 4, 1, 0

    def sword_damage(self) -> int:
        """What this sword is worth in HP, in the disassembly's own units. The beam is a sword swing."""
        return {1: self.DMG_WOOD, 2: self.DMG_WHITE, 3: self.DMG_MAGICAL}.get(self.emu.state().sword, 0)

    def vire_splittable(self) -> bool:
        """True if the sword in hand cannot finish a Vire in one hit, so swinging would split it.

        This is the whole of the Vire problem: there is no such thing as a safe partial hit, so the
        fighter has to know before it swings rather than after."""
        return self.sword_damage() < 4

    def stun_with_boomerang(self, slot: int, max_frames: int = 1200) -> bool:
        """Throw the boomerang at a Vire to hold it still ($10 = 160 frames) without hurting it.

        The one weapon that cannot split a Vire and does no damage at all, which makes it the correct
        first move when the sword is too weak: line the Vire up, freeze it, then hit it with something
        that finishes it. Returns True if the Vire is stunned, False if the boomerang is not available,
        not owned, or could not be thrown - and the caller then LEAVES THE VIRE ALONE rather than
        splitting it, which is the whole point: an untouched Vire is a locked door, a split one is
        two Blue Keese and the same locked door."""
        from .bot import B_BOOMERANG, b_item, select_b_item
        emu = self.emu
        if b_item(emu) != B_BOOMERANG:
            if not select_b_item(emu, emu.step, B_BOOMERANG, log=lambda *a: None):
                return False
        hearts0 = emu.state().hearts
        for _ in range(6):
            e = find_enemy(emu, slot)
            if e is None:
                return False
            s = emu.state()
            dx, dy = e[2] - s.x, e[3] - s.y
            face = ("Right" if dx > 24 else "Left" if dx < -24 else
                    "Down" if dy > 24 else "Up" if dy < -24 else None)
            if face is None:
                emu.step((), 8)                  # not lined up yet: shuffle and try again
                continue
            emu.step(face, 1)                    # the face press before B is load-bearing
            emu.step("B", 1)
            emu.step((), 30)                      # the boomerang has to actually travel
            if emu.state().hearts < hearts0:
                emu.note("MISTAKE: hit while trying to stun the Vire; abandoning it")
                return False
            e2 = find_enemy(emu, slot)
            if e2 is None:
                return False                     # dead rather than stunned: nothing to do next
            if e2[4] >> 4 >= 4:
                emu.note("VIRE: boomerang landed and it is stunned for 160 frames, unhurt")
                return True
        return False

    def _beam_ready(self, s: State) -> bool:
        """At full hearts the sword fires a beam: same damage, straight line, any range."""
        return s.hearts >= s.containers and s.containers > 0

    def _beam_shot(self, s: State, e) -> str | None:
        """Direction to fire a beam at e if aligned on a row/column and we're at full health."""
        if not self._beam_ready(s) or e[1] in self.BEAM_IMMUNE:
            return None
        dx, dy = e[2] - s.x, e[3] - s.y
        if e[1] in self.DARKNUTS:
            f = self._facing(e[0])           # a beam into its shield does nothing: only side/back
            if (f == 1 and dx < 0) or (f == 2 and dx > 0) or (f == 4 and dy < 0) or (f == 8 and dy > 0):
                return None
        if abs(dy) <= ALIGN and abs(dx) >= 24:
            return "Right" if dx > 0 else "Left"
        if abs(dx) <= ALIGN and abs(dy) >= 24:
            return "Down" if dy > 0 else "Up"
        return None
    PERP = {1: ("Up", "Down"), 2: ("Up", "Down"), 4: ("Left", "Right"), 8: ("Left", "Right")}

    def _facing(self, slot: int) -> int:
        return self.emu.byte(0x98 + slot)          # 1 R, 2 L, 4 D, 8 U

    def _in_front_of(self, e, s, facing: int, reach: int = 40) -> bool:
        """Is Link standing in the line this enemy faces along, within `reach`?"""
        dx, dy = s.x - e[2], s.y - e[3]
        if facing in (1, 2):
            return abs(dy) < 16 and 0 < (dx if facing == 1 else -dx) < reach
        return abs(dx) < 16 and 0 < (dy if facing == 4 else -dy) < reach

    def _sidestep(self, e, facing: int) -> State:
        """Leave a Darknut's line by moving perpendicular to its facing, away from room walls."""
        s = self.emu.state()
        a, b = self.PERP[facing]
        # pick the perpendicular direction that increases distance from the enemy's line
        if facing in (1, 2):
            d = "Up" if s.y <= e[3] else "Down"
        else:
            d = "Left" if s.x <= e[2] else "Right"
        return self.emu.step(d, 2)

    def attack_slot(self, slot: int, max_frames: int = 900) -> bool:
        """Kill the enemy in `slot`. Darknuts: approach from the side, strike at 90 degrees."""
        emu = self.emu
        e = find_enemy(emu, slot)
        if e is None:
            return True
        name = enemy_name(e[1])
        darknut = e[1] in self.DARKNUTS
        # A Vire must not be hit at all unless the hit finishes it. See the VIRE note above: the split
        # triggers on being hurt, so a white-sword swing on a 4 HP Vire trades one enemy for two Keese
        # and still leaves the door shut. The options are, in order: a weapon strong enough to one-shot
        # it, a bomb ($40, same as the magical sword), the boomerang to freeze it, or nothing.
        vire = e[1] == self.VIRE
        if vire and self.vire_splittable():
            # Nothing here can finish a 4 HP Vire without hurting it twice: the sword is worth 2 and a
            # wooden arrow 2, and both leave it alive and splitting. A bomb ($40) or a Silver Arrow
            # ($40) would one-shot it, and neither is wired into this routine yet - so the correct
            # move with what is in hand is to not swing at all. The boomerang is tried first only
            # because it is free: $00 damage and a $10 stun, so it cannot make the situation worse,
            # and a frozen Vire is at least a Vire that is not currently at you.
            emu.note(f"FIGHT: {name} at ({e[2]},{e[3]}), hp {enemy_hp(e)}: the sword is worth "
                     f"{self.sword_damage()} of 4 and a hurt Vire splits into two Keese")
            self.stun_with_boomerang(slot)
            emu.note(f"LEAVING the {name} alive - the door is shut either way, and a split one is worse")
            return False
        emu.note(f"FIGHT: {name} at ({e[2]},{e[3]}), hp {enemy_hp(e)}."
                 + (" Shielded in front: side hits only" if darknut else f" Need a gap of {REACH}px or less")
                 + (f" One-shot: {self.sword_damage()} of 4" if vire else ""))
        hearts0 = emu.state().hearts
        swings = hits = 0
        frames = 0
        while frames < max_frames:
            e = find_enemy(emu, slot)
            if e is None or enemy_hp(e) == 0:
                # DEAD, and the object table has not caught up. read_enemies filters on the TYPE
                # byte and nothing else, so a corpse keeps its slot - and its slot keeps its
                # position - until the game clears it, which for a Gel is a long time. Measured on
                # room $4A: the fighter threw six beam swings at one dead Gel from 103 to 142 px
                # away, 144 frames, because the slot was still there and hp still read 0. The other
                # half of that log is the Gel's state byte, $02: it is an effect object by then.
                #
                # Narrow on purpose. This is the Fighter's ordinary-room path; the bosses that
                # wake up at 0 HP (Gohma, Armos - the latter is in UNKILLABLE) are fought through
                # plan_fight with their own policies, so nothing here can decide a boss is over
                # before the boss says so.
                emu.note(f"The {name} is dead ({swings} swings, {hits} hits)"
                         + ("" if e is None else " - still in the object table at 0 HP"))
                return True
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died fighting")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): hit by the {name}, {s.hearts} hearts left")
                hearts0 = s.hearts
            ex, ey = e[2], e[3]
            dx, dy = ex - s.x, ey - s.y
            # A beam at a target the game will not let it hit is the same 24 wasted frames as a sword
            # swing at one, and the room-$4A instrument found six of them a side. Whether the beam
            # stops at a WALL is a separate question this project has not answered, and is left open
            # on purpose; whether the target is still in its burrow is not a question at all.
            beam = self._beam_shot(s, e) if hittable_now(emu, slot, e[1]) else None
            if beam:
                if swings == 0:
                    emu.note(f"Full hearts: firing sword beams at the {name} from range instead of closing in")
                hp0 = enemy_hp(e)
                aim, here = (e[2], e[3]), (s.x, s.y)      # where Link stood when he swung
                s = self.swing(beam)
                s = emu.step((), 10)                 # let the beam travel
                swings += 1; frames += 24
                e2 = find_enemy(emu, slot); hits += (e2 is None or enemy_hp(e2) < hp0)
                _judge_swing(self.floor, here, slot, hp0, aim[0], aim[1], s.room)
                continue
            facing = self._facing(slot) if darknut else 0
            # 1. never stand in a Darknut's line: sidestep out of it first
            if darknut:
                threat = None
                for o in read_enemies(emu):
                    if o[1] in self.DARKNUTS and self._in_front_of(o, s, self._facing(o[0])):
                        threat = o
                        break
                if threat is not None:
                    s = self._sidestep(threat, self._facing(threat[0]))
                    frames += 2
                    continue
            # 2. in position? swing (for Darknuts only from the side/back)
            #    ...and not into a wall. reach_clear is the other half of the same test: lined up and
            #    in range is not the same as able to reach, and swinging anyway is how the fighter
            #    spent sixty frames a Gibdo behind a block. Folded into the CONDITION rather than
            #    checked inside the branch, so a blocked reach falls through to the approach below -
            #    which steps, and so keeps the loop's frame budget honest. Skipping the swing without
            #    stepping would spin this loop on one frame of state until max_frames, forever.
            d = sword_reach(emu, s, e)
            if d and not (darknut and shield_side(facing, d, dx, dy)) \
                    and self.reach_clear(s, e, d) and hittable_now(emu, slot, e[1]):
                hp0 = enemy_hp(e)
                aim, here = (e[2], e[3]), (s.x, s.y)      # where Link stood when he swung
                s = self.swing(d)
                swings += 1; frames += 14
                e2 = find_enemy(emu, slot)
                if e2 is None or enemy_hp(e2) < hp0:
                    hits += 1
                _judge_swing(self.floor, here, slot, hp0, aim[0], aim[1], s.room)
                continue
            # 3. choose where to stand. Darknuts: beside them, relative to their facing.
            if darknut:
                off = 16 + REACH - 4
                if facing in (4, 8):      # faces up/down -> stand left or right of it
                    cands = [(ex - off, ey), (ex + off, ey)]
                else:                     # faces left/right -> stand above or below it
                    cands = [(ex, ey - off), (ex, ey + off)]
                tx, ty = min(cands, key=lambda c: abs(c[0] - s.x) + abs(c[1] - s.y))
                tx, ty = snap(max(16, min(224, tx)), max(69, min(205, ty)))
                ddx, ddy = tx - s.x, ty - s.y
                if ddx == 0 and ddy == 0:
                    s = emu.step((), 1); frames += 1
                    continue
                # move on the axis perpendicular to its facing first (stays out of its line)
                if facing in (4, 8):
                    d = ("Right" if ddx > 0 else "Left") if ddx else ("Down" if ddy > 0 else "Up")
                else:
                    d = ("Down" if ddy > 0 else "Up") if ddy else ("Right" if ddx > 0 else "Left")
            else:
                # The owner's Gleeok read, and it is worth encoding: that boss has a flawed hitbox on
                # the right, so Link can stand slightly off-centre to the right, connect, and still be
                # out of the line of fire. "Stand right of the thing and hit it" is a better default
                # than "walk at the thing" for anything that shoots back, and it costs nothing when
                # the target is harmless - so it is a tiebreak on the approach, not a rule.
                if e[1] in self.RIGHT_FLANK:
                    if abs(dy) > ALIGN:
                        s = self._move("Down" if dy > 0 else "Up", slot, toward=(ex, ey))
                        frames += 1
                        continue
                    if abs(dx) >= SWORD_ALONG:
                        s = self._move("Right", slot, toward=(ex, ey))
                        frames += 1
                        continue
                # Line up before closing, because a swing cannot reach across more than 12 or along
                # more than 16 (or the other way round, see sword_reach). A target 14 px off-line is
                # unreachable from any distance on its row, so walking along the row instead is the
                # oscillation the old ALIGN test existed to stop - and ALIGN = 4 was itself part of the
                # same wrong model, demanding a far tighter line-up than the game asks for.
                if abs(dy) >= SWORD_ALONG:
                    d = "Down" if dy > 0 else "Up"
                elif abs(dx) >= SWORD_ACROSS and dy:
                    d = "Down" if dy > 0 else "Up"
                else:
                    d = "Right" if dx > 0 else "Left" if dx else ("Down" if dy > 0 else "Up")
            # toward= is what makes a detour round a wall a route round rather than a drift: the
            # sideways step is ordered by which way closes on the target, so Link slides along the
            # obstacle towards the enemy instead of away from him.
            s = self._move(d, slot, toward=(ex, ey))
            frames += 1
        emu.note(f"Couldn't finish the {name} in {max_frames} frames ({swings} swings, {hits} hits)")
        wasted_report(emu)      # a no-op unless ZELDA_WASTED=1; this is where the instrument is read
        return False


    # ---------------------------------------------------------------- Darknut hunting
    def _step8(self, d: str, target_slot: int | None = None, frames: int = 8) -> State:
        """A committed 8 px step: hold one direction until Link has moved a grid step (or stalls)."""
        emu = self.emu
        s0 = emu.state()
        s = s0
        for _ in range(frames):
            s = self._move(d, target_slot)
            if abs(s.x - s0.x) >= 8 or abs(s.y - s0.y) >= 8 or s.hearts < s0.hearts:
                break
        return s

    DKV = {1: (1, 0), 2: (-1, 0), 4: (0, 1), 8: (0, -1)}   # Darknut velocity per facing (~1 px/frame)

    def _predicted_contact(self, s, e, facing: int, horizon: int, margin: int = 4) -> bool:
        """Will this Darknut's box come within `margin` px of Link's box within `horizon` frames,
        assuming it keeps walking its line? (It can't turn before the next tile centre.)"""
        vx, vy = self.DKV.get(facing, (0, 0))
        for t in range(0, horizon + 1, 2):
            ex, ey = e[2] + vx * t, e[3] + vy * t
            if abs(ex - s.x) < 16 + margin and abs(ey - s.y) < 16 + margin:
                return True
        return False

    def _escape(self, s, e, facing: int) -> str:
        """Direction that leaves this Darknut's path: perpendicular to its movement, away from it.
        If that side is a wall (Link at a room edge), use the other perpendicular; if both are
        blocked, retreat along its line."""
        from .overworld import read_cells, legal
        cells = read_cells(self.emu)
        kb = self.nav.kb
        kb.use(s.level)
        if facing in (1, 2):
            prefs = ["Up", "Down"] if s.y <= e[3] else ["Down", "Up"]
            prefs.append("Right" if facing == 1 else "Left")
        else:
            prefs = ["Left", "Right"] if s.x <= e[2] else ["Right", "Left"]
            prefs.append("Down" if facing == 4 else "Up")
        for d in prefs:
            ddx, ddy = DIRS[d]
            if legal(cells, kb, s.x + ddx, s.y + ddy, optimistic=True):
                return d
        return prefs[0]

    def hunt_darknut(self, slot: int, max_frames: int = 1500) -> bool:
        """Darknuts: contact hurts from any side, so every step and every swing is checked
        against where each Darknut will be over the next frames. Strike only from side/behind
        when it is walking away or across, never when it is coming at us."""
        emu = self.emu
        e = find_enemy(emu, slot)
        if e is None:
            return True
        name = enemy_name(e[1])
        emu.note(f"HUNT: {name} at ({e[2]},{e[3]}), hp {enemy_hp(e)}. Predicting its path; side/back hits only")
        hearts0 = emu.state().hearts
        swings = hits = frames = 0
        hold = None          # (direction, frames left) to avoid dithering
        cool = 0             # frames to hold still after an escape
        while frames < max_frames:
            e = find_enemy(emu, slot)
            if e is None:
                emu.note(f"The {name} is dead ({swings} swings, {hits} hits)")
                return True
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died hunting")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): hit by the {name}, {s.hearts} hearts left")
                hearts0 = s.hearts
            dks = [(o, self._facing(o[0])) for o in read_enemies(emu) if o[1] in self.DARKNUTS]
            # 1. escape anything about to touch us: a committed step fully out of its lane, and no
            #    approaching again until it has passed (approach and escape must never fight)
            danger = [(o, f) for o, f in dks if self._predicted_contact(s, o, f, 20)]
            if danger:
                o, f = min(danger, key=lambda of: abs(of[0][2] - s.x) + abs(of[0][3] - s.y))
                d = self._escape(s, o, f)
                s = emu.step(d, 8); frames += 8
                hold = None
                cool = 12
                continue
            if cool:
                cool -= 1
                s = emu.step((), 1); frames += 1
                continue
            ex, ey = e[2], e[3]
            f = self._facing(slot)
            vx, vy = self.DKV.get(f, (0, 0))
            dx, dy = ex - s.x, ey - s.y
            # 2. strike if in reach from side/behind and nothing will touch us during the swing
            coming = (vx and (vx > 0) == (dx < 0) and abs(dy) < 16) or (vy and (vy > 0) == (dy < 0) and abs(dx) < 16)
            safe_swing = not any(self._predicted_contact(s, o, ff, 18, margin=2) for o, ff in dks)
            if not coming and safe_swing:
                # reach_clear in the condition, as in attack_slot: a blocked swing falls through to
                # the approach below, which steps, rather than spinning here on one frame of state.
                dh = reach_box_model(s, e)          # Darknuts keep the reach they were built on
                if dh and not shield_side(f, dh, dx, dy) \
                        and self.reach_clear(s, e, dh) and hittable_now(emu, slot, e[1]):
                    hp0 = enemy_hp(e)
                    s = self.swing(dh)
                    swings += 1; frames += 14
                    e2 = find_enemy(emu, slot); hits += (e2 is None or enemy_hp(e2) < hp0)
                    continue
            # 3. approach a spot behind it (or beside it if it is standing still)
            back = 16 + REACH - 4
            if vx or vy:
                tx, ty = ex - vx * back, ey - vy * back
            else:
                tx, ty = (ex - back, ey) if s.x <= ex else (ex + back, ey)
            tx, ty = snap(max(16, min(224, tx)), max(69, min(205, ty)))
            ddx, ddy = tx - s.x, ty - s.y
            if abs(ddx) < 3 and abs(ddy) < 3:
                s = emu.step((), 1); frames += 1
                continue
            if hold and hold[1] > 0:
                d = hold[0]; hold = (d, hold[1] - 1)
            else:
                # cross-lane offset first so we never walk down its line toward it
                if vx:
                    d = ("Down" if ddy > 0 else "Up") if abs(ddy) >= 3 else ("Right" if ddx > 0 else "Left")
                else:
                    d = ("Right" if ddx > 0 else "Left") if abs(ddx) >= 3 else ("Down" if ddy > 0 else "Up")
                hold = (d, 3)
            # the step itself must not end inside any Darknut's near-future path
            ndx, ndy = DIRS[d]
            nxt = type("S", (), {"x": s.x + ndx, "y": s.y + ndy})
            if any(self._predicted_contact(nxt, o, ff, 8) for o, ff in dks):
                s = emu.step((), 1); frames += 1; hold = None
                continue
            s = self._move(d, slot, toward=(ex, ey)); frames += 1
        emu.note(f"Couldn't finish the {name} in {max_frames} frames ({swings} swings, {hits} hits)")
        return False


    def darknut_ambush(self, max_frames: int = 3600, post=None, rng=None) -> bool:
        """Crowded Darknut rooms (walkthrough technique): take a post beside a block so they can only
        come from limited directions, stand still, strike each one as it walks past (side/back only),
        and step out of any predicted contact. Kills everything that is a Darknut."""
        from .overworld import read_cells, box_cells
        emu = self.emu
        self.nav.kb.use(emu.state().level, emu.state().mode)
        cells = read_cells(emu)
        blocks = {(r // 2, k // 2) for r in range(4, 18) for k in range(4, 28) if cells[r][k] in (0xB0, 0xB1, 0xB2, 0xB3)}
        # candidate posts: floor tiles with a block directly left or right and open space on the other side
        cands = []
        for (br, bc) in blocks:
            for side in (-1, 1):
                pr, pc = br, bc + side
                if (pr, pc) in blocks or not (2 <= pc <= 13 and 1 <= pr <= 9):
                    continue
                x, y = pc * 16, 64 + pr * 16 - 3
                if all(self.nav.kb.is_walkable(cells[cy][cx], False) for cy, cx in box_cells(x, y)):
                    cands.append((x, y))
        if not cands:
            return self.clear_room()
        if post is None:
            s = emu.state()
            dks0 = [o for o in read_enemies(emu) if o[1] in self.DARKNUTS]
            def safety(c):   # far from every Darknut, but not absurdly far from us
                return min((max(abs(o[2] - c[0]), abs(o[3] - c[1])) for o in dks0), default=999) - 0.1 * (abs(c[0] - s.x) + abs(c[1] - s.y))
            cands.sort(key=safety, reverse=True)
            post = cands[rng.randrange(min(3, len(cands)))] if rng else cands[0]
        emu.note(f"DARKNUT AMBUSH: taking a post beside a block at {post}, the spot farthest from them; striking as they pass")
        self.nav.no_kill = True
        try:
            self.nav.go(lambda x, y: x == post[0] and y == post[1], "the ambush post", max_replans=80)
        except Exception as e:
            emu.note(f"couldn't reach the post: {str(e)[:50]}")
        finally:
            self.nav.no_kill = False
        hearts0 = emu.state().hearts
        swings = hits = frames = 0
        while frames < max_frames:
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died in ambush")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): Darknut got me at the post, {s.hearts} hearts left")
                hearts0 = s.hearts
            dks = [(o, self._facing(o[0])) for o in read_enemies(emu) if o[1] in self.DARKNUTS]
            if not dks:
                emu.note(f"All Darknuts dead from the post ({swings} swings, {hits} hits)")
                self.collect_drop()
                return True
            danger = [(o, f) for o, f in dks if self._predicted_contact(s, o, f, 12)]
            if danger:
                o, f = min(danger, key=lambda of: abs(of[0][2] - s.x) + abs(of[0][3] - s.y))
                s = emu.step(self._escape(s, o, f), 2); frames += 2
                continue
            struck = False
            for o, f in dks:
                vx, vy = self.DKV.get(f, (0, 0))
                dx, dy = o[2] - s.x, o[3] - s.y
                coming = (vx and (vx > 0) == (dx < 0) and abs(dy) < 16) or (vy and (vy > 0) == (dy < 0) and abs(dx) < 16)
                if coming:
                    continue
                # The post is chosen to be floor with a block beside it, so a wall in the way here
                # is a Darknut that has come round the block - the same swing into a wall the
                # instrument was built to count, and here it is a wasted 14 frames per pass.
                do = reach_box_model(s, o)         # as hunt_darknut: see reach_box_model
                if do and not shield_side(f, do, dx, dy) \
                        and self.reach_clear(s, o, do) and hittable_now(emu, o[0], o[1]):
                    hp0 = enemy_hp(o); s = self.swing(do); swings += 1; frames += 14
                    o2 = find_enemy(emu, o[0]); hits += (o2 is None or enemy_hp(o2) < hp0); struck = True; break
            if struck:
                continue
            # drift back to the post if we were pushed off it; otherwise hold
            if abs(s.x - post[0]) > 4 or abs(s.y - post[1]) > 4:
                d = ("Right" if post[0] > s.x else "Left") if abs(post[0] - s.x) > abs(post[1] - s.y) else ("Down" if post[1] > s.y else "Up")
                s = self._move(d); frames += 1
            else:
                s = emu.step((), 1); frames += 1
        emu.note(f"Ambush timed out with Darknuts alive ({swings} swings, {hits} hits)")
        return False


    def bomb_darknuts(self, keep: int = 2, max_frames: int = 3000, rng=None) -> bool:
        """Crowded Darknut rooms with bombs to spare: when one walks toward Link along his row or
        column from far enough away, drop a bomb in its lane and step out of the line. The fuse
        (~76 frames) meets it as it arrives. Sword-finish whatever survives."""
        emu = self.emu
        self.nav.kb.use(emu.state().level, emu.state().mode)
        emu.note(f"BOMBING DARKNUTS: {emu.state().bombs} bombs, keeping {keep}. Drop in their lane, sidestep, let the fuse work")
        hearts0 = emu.state().hearts
        frames = last_bomb = 0
        min_dist = rng.choice([48, 56, 64, 72]) if rng else 60
        while frames < max_frames:
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died bombing")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): hit while bombing, {s.hearts} hearts left")
                hearts0 = s.hearts
            dks = [(o, self._facing(o[0])) for o in read_enemies(emu) if o[1] in self.DARKNUTS]
            if not dks:
                emu.note("Darknuts gone")
                self.collect_drop()
                return True
            if s.bombs <= keep:
                emu.note(f"Down to {s.bombs} bombs (keeping {keep}); finishing with the sword")
                return self.clear_room_sword()
            danger = [(o, f) for o, f in dks if self._predicted_contact(s, o, f, 12)]
            if danger:
                o, f = min(danger, key=lambda of: abs(of[0][2] - s.x) + abs(of[0][3] - s.y))
                s = emu.step(self._escape(s, o, f), 2); frames += 2
                continue
            # a Darknut coming straight at us along our row/column from far enough: bomb its lane
            placed = False
            if frames - last_bomb > 90:
                for o, f in dks:
                    vx, vy = self.DKV.get(f, (0, 0))
                    dx, dy = o[2] - s.x, o[3] - s.y
                    if vx and abs(dy) <= 6 and (vx > 0) == (dx < 0) and min_dist <= abs(dx) <= 120:
                        face = "Left" if dx < 0 else "Right"
                    elif vy and abs(dx) <= 6 and (vy > 0) == (dy < 0) and min_dist <= abs(dy) <= 120:
                        face = "Up" if dy < 0 else "Down"
                    else:
                        continue
                    emu.step(face, 1); emu.step("B", 2); frames += 3
                    last_bomb = frames
                    emu.note(f"Bomb dropped in the lane of a Darknut {abs(dx) if vx else abs(dy)} px away; stepping out of its line")
                    s = emu.step(self._escape(s, o, f), 8); frames += 8
                    placed = True
                    break
            if placed:
                continue
            # otherwise line up on a lane: move so that some Darknut's row or column passes through us at a distance
            o, f = min(dks, key=lambda of: abs(of[0][2] - s.x) + abs(of[0][3] - s.y))
            vx, vy = self.DKV.get(f, (0, 0))
            if vx:
                d = "Down" if o[3] > s.y + 6 else "Up" if o[3] < s.y - 6 else None
            elif vy:
                d = "Right" if o[2] > s.x + 6 else "Left" if o[2] < s.x - 6 else None
            else:
                d = None
            if d:
                s = self._move(d, o[0]); frames += 1
            else:
                s = emu.step((), 2); frames += 2
        emu.note("Bombing timed out")
        return False

    def clear_room_sword(self, max_enemies: int = 12) -> bool:
        """Kill everything with the sword only (no bomb/ambush dispatch)."""
        emu = self.emu
        for _ in range(max_enemies * 3):
            s = emu.state()
            ens = [e for e in read_enemies(emu) if e[1] != 0x49 and e[1] < 0x50 and enemy_hp(e) > 0]
            if not ens:
                self.collect_drop(); return True
            walkers = [e for e in ens if e[1] not in self.FLIERS]
            if walkers:
                walkers.sort(key=lambda e: abs(e[2] - s.x) + abs(e[3] - s.y))
                (self.hunt_darknut if walkers[0][1] in self.DARKNUTS else self.attack_slot)(walkers[0][0])
            elif not self.ambush():
                break
            self.collect_drop()
        left = [e for e in read_enemies(emu) if killable(e) and enemy_hp(e) > 0]
        if left:
            wasted_report(emu)
        return not left

    FLIERS = {0x1B, 0x1C, 0x1D, 0x1A, 0x22}   # Keese, Peahat, flying Ghini: don't chase, ambush

    def sword_immune(self, e) -> bool:
        """Is this object one the game will parry a sword swing against?

        ObjInvincibilityMask ($4B2) is a per-slot bitmask of the damage TYPES a target refuses. The
        game tests `ObjInvincibilityMask, X / AND $09 / BNE parry` before it subtracts anything, and
        the harness had never read that byte - so it was swinging at things that cannot be hit, and
        (worse) considering them killable.

        The case that motivates it: every Gleeok neck segment is $FE, "invincible to everything but
        the sword", which reads as sword-proof at a glance and is the exact opposite. A Darknut's
        shield is a facing test rather than a mask, so it is not caught here - but Zol, Gel and the
        Vire's split children all do use it, and a target we cannot damage is a wall, not a kill.
        """
        return immune_to(self.emu, e[0], DMG_SWORD)

    def bomb_immune(self, e) -> bool:
        """Same question for a bomb. Separate because the two differ in practice: Gleeok's neck is
        $FE (sword yes, bomb no) and that asymmetry is the whole reason a bomb cannot finish one."""
        return immune_to(self.emu, e[0], DMG_BOMB)

    def killable_by(self, e, weapon: int) -> bool:
        """Can this weapon hurt this thing at all?"""
        return killable(e) and not immune_to(self.emu, e[0], weapon)

    def ghost_report(self) -> list[tuple[int, int, int, int, int]]:
        """Boss parts that are not monsters in the object table - Gleeok's neck, currently.

        Read-only knowledge, and it is worth having for the unglamorous reason first: the planner was
        walking through a body it could not see, because the segments have a real position and HP in
        slots 1..6 and a type of 0, which read_enemies drops. Six 10 HP sword-only segments standing in
        a room, invisible. Now they are at least furniture the fighter knows is there."""
        return read_ghost_objects(self.emu)

    def _hittable(self, s: State, e):
        """Direction to swing if the enemy is in reach right now, else None.

        The wall gate is here too, and it costs a flier ambush the most of anything in this file:
        Keese and Octoroks come in over the furniture, so the interesting moments are the ones
        where something is 20 px away on the far side of a block.
        """
        if immune_to(self.emu, e[0], DMG_SWORD):
            return None
        if not hittable_now(self.emu, e[0], e[1]):
            return None              # a Peahat still in its hole cannot be cut, whatever the geometry
        d = sword_reach(self.emu, s, e)
        return d if d and self.reach_clear(s, e, d) else None

    def ambush(self, max_frames: int = 1800) -> bool:
        """Stand mostly still and swing at whatever flies into reach. Small steps to line up
        when one hovers nearby. Returns True when no fliers remain."""
        emu = self.emu
        emu.note("AMBUSH: fliers are too erratic to chase. Holding position and swinging when one comes close")
        hearts0 = emu.state().hearts
        swings = hits = 0
        frames = 0
        while frames < max_frames:
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died in ambush")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): clipped by a flier, {s.hearts} hearts left")
                hearts0 = s.hearts
            ens = [e for e in read_enemies(emu) if e[1] in self.FLIERS and enemy_hp(e) > 0]
            if not ens:
                emu.note(f"No fliers left ({swings} swings, {hits} hits)")
                return True
            target = None
            for e in ens:
                d = self._hittable(s, e) or self._beam_shot(s, e)
                if d:
                    target = (e, d)
                    break
            if target:
                e, d = target
                hp0 = enemy_hp(e)
                self.swing(d)
                swings += 1; frames += 14
                e2 = find_enemy(emu, e[0])
                if e2 is None or enemy_hp(e2) < hp0:
                    hits += 1
                continue
            # nudge toward alignment with the nearest one if it's hovering close; otherwise wait
            e = min(ens, key=lambda e: abs(e[2] - s.x) + abs(e[3] - s.y))
            dx, dy = e[2] - s.x, e[3] - s.y
            if max(abs(dx), abs(dy)) <= 40:
                if abs(dy) < abs(dx) and abs(dy) > ALIGN:
                    emu.step("Down" if dy > 0 else "Up", 1)
                elif abs(dx) <= abs(dy) and abs(dx) > ALIGN:
                    emu.step("Right" if dx > 0 else "Left", 1)
                else:
                    emu.step((), 1)
            else:
                emu.step((), 2)
                frames += 1
            frames += 1
        emu.note(f"Ambush timed out ({swings} swings, {hits} hits)")
        return False

    # item ids that enemies drop (the drop uses the room-item slot $AB/$83/$97/$BF)
    DROPS = {0x00: "bombs", 0x0F: "5 rupees", 0x18: "rupee", 0x19: "key", 0x21: "clock", 0x22: "heart", 0x23: "fairy"}

    # A dead monster's object slot turns into the pickup while its drop lies on the floor.
    DROP_TYPE = 0x60

    def visible_drops(self):
        """Every item lying in the room: the room item AND each monster's drop, as (id, x, y, slot).

        For most of this project the harness looked only at the room item (object slot 0x13), which is
        where keys and dungeon treasure live. A monster's drop lives somewhere else entirely: the game
        converts the dead monster's OWN slot into the pickup - object type $60, item id at $AC+slot
        (disassembly Z_07 UpdateMetaObjectEnd, Z_04 SetUpDroppedItem). So every rupee, heart and bomb
        a fight produced was invisible, and Link only collected the ones he happened to walk over. The
        finished run's farms ran at 600-900 frames per rupee, which is what blindness looks like."""
        emu = self.emu
        out = []
        item = read_room_item(emu)
        if item is not None and item[0] in self.DROPS:
            out.append((item[0], item[1], item[2], None))
        blk = emu.ram(0x70, 0x2EB)          # x $70, y $84, item id $AC, type $34F in one read
        for i in range(1, 12):
            kind = blk[0xAC - 0x70 + i]
            if blk[0x34F - 0x70 + i] == self.DROP_TYPE and kind in self.DROPS:
                out.append((kind, blk[i], blk[0x84 - 0x70 + i], i))
        return out

    def _worth(self, t, s) -> bool:
        """Is this drop worth walking for right now? Only what Link can actually use."""
        if t in (0x22, 0x23):                  # heart, fairy: only while hurt
            return s.hearts < s.containers
        if t == 0x00:                          # bombs: only below capacity (MaxBombs, $67C)
            return s.bombs < max(8, self.emu.byte(0x67C))
        if t == 0x21:                          # clock: always worth it, see _clock_held
            return not self._clock_held()
        return True                            # rupees, five rupees, keys

    def _clock_held(self) -> bool:
        """Is the dungeon clock in hand?

        This used to be dead code dressed as a decision. The drop was thrown away at two places on the
        stated grounds that "the clock is not worth a detour" - which is a remark about a game this is not.
        In THIS cartridge the clock is the best item a run can get, and the disassembly says so in twenty
        places: `InvClock` ($66C) is tested at the top of essentially every enemy update routine, and
        the pattern is "if we have the magic clock, then don't move" (Z_04 UpdateFlyingGhini and nineteen
        others). It is reset by ResetPlayerState, so it lasts exactly one screen.

        And it is not only a freeze. Z_01 CheckLinkCollision:

            ; If Link is invincible, or we have the magic clock,
            ; or Link is stunned, or the monster is stunned; then return no collision.
            LDA ObjInvincibilityTimer
            ORA InvClock

        So holding the clock makes Link immune to contact damage as well. For a harness that walks into
        rooms it may not survive - the White Sword screen, a shutter room of Lynels, Gleeok - that is the
        difference between a segment that cannot be solved and one that can be walked."""
        return bool(self.emu.byte(0x66C))

    def collect_drop(self, max_frames: int = 240, max_detour: int = 120) -> bool:
        """Pick up what the fight left behind, nearest first, as long as it is worth the walk.

        Several drops can land at once, so take up to four, but never chase one more than
        `max_detour` pixels away or spend more than `max_frames` frames in total.

        A drop that cannot be reached is SKIPPED, not treated as the end of the collection. Both of
        these used to `break`: one that was further than `max_detour`, and one the navigator raised
        NavError on. Either one abandoned every other drop on the floor, including a clock lying
        behind the unreachable one - and a clock is the one item where being second-best loses the
        segment. `skip` holds the ones already known to be unreachable so the loop makes progress.
        """
        from .overworld import snap, NavError
        emu, nav = self.emu, self.nav
        took = False
        f0 = emu.state().frame
        skip: set = set()
        for _ in range(4):
            s = emu.state()
            if s.frame - f0 > max_frames:
                break
            # `on_floor`, not `drops`: the module zelda.drops is imported at the top of this file and a
            # local named `drops` shadowed it, so `drops.CLOCK` below raised AttributeError - on the
            # one code path that only runs when a clock is actually on the floor.
            on_floor = [d for d in self.visible_drops() if self._worth(d[0], s) and d[0] not in skip]
            if not on_floor:
                break
            # The clock outranks distance. It is contact immunity for a whole screen and it expires,
            # so a clock four steps away is worth more than a rupee underfoot.
            t, ix, iy, slot = min(on_floor, key=lambda d: (d[0] != drops.CLOCK,
                                                           abs(d[1] - s.x) + abs(d[2] - s.y)))
            if abs(ix - s.x) + abs(iy - s.y) > max_detour:
                emu.note(f"A {self.DROPS[t]} at ({ix},{iy}) is too far to chase; leaving it")
                skip.add(t)
                continue
            name = self.DROPS[t]

            def gone():
                if slot is None:
                    return read_room_item(emu) is None
                return emu.ram(0x34F, 12)[slot] != self.DROP_TYPE

            emu.note(f"DROP: a {name} at ({ix},{iy}). Grabbing it")
            tx, ty = snap(ix, iy)
            try:
                nav.go(lambda x, y: abs(x - tx) <= 8 and abs(y - ty) <= 8, f"the {name}", max_replans=30)
                for _ in range(3):
                    if gone():
                        break
                    nav.go(lambda x, y: x == tx and y == ty, f"the {name} exactly", max_replans=10)
                    emu.step((), 4)
                # Close the last few pixels, then make contact. This is the step that was missing and
                # it is why a clock was never once picked up: `snap` quantises to Link's 16px grid, so
                # the navigator's "exactly" target can leave Link ~7px short of an item whose position
                # is not on the grid, and the 3x4 idle frames that followed were not enough contact.
                # Measured in L3 room 0x5B, where a clock lands on the floor 10 attempts out of 10 and
                # was collected 0: a clock at (149,141) snaps to (144,141), and only pressing into it
                # again took it ($66C 00 -> 01).
                for _ in range(8):
                    if gone():
                        break
                    if emu.state().frame - f0 > max_frames:
                        break
                    s2 = emu.state()
                    btn = ("Right" if ix > s2.x + 1 else "Left" if ix < s2.x - 1 else "")
                    btn2 = ("Down" if iy > s2.y + 1 else "Up" if iy < s2.y - 1 else "")
                    emu.step(btn, 2)
                    emu.step(btn2, 2)
            except NavError as e:
                emu.note(f"Couldn't reach the {name}: {str(e)[:50]}; trying something else")
                skip.add(t)
                continue
            if gone():
                s2 = emu.state()
                emu.note(f"Got the {name}: hearts {s2.hearts}, bombs {s2.bombs}, rupees {s2.rupees}")
                took = True
            else:
                emu.note(f"The {name} vanished before I got there")
                skip.add(t)
        return took

    def _clock_order(self, walkers, s: State):
        """Order this room's kills so one of them lands on a clock column of DropItemTable.

        Nearest-first is the fallback, and it is preserved inside every choice prefer_target makes -
        reordering the queue is safe, picking the far corner of the room over the Gibdo at your feet
        is not. Returns a new list, or the plain nearest-first sort when there is nothing to steer
        towards (clock already held, room too small, no enemy in a row that drops one, or no enemy
        outside those rows to advance the cycle with).
        """
        by_distance = sorted(walkers, key=lambda e: abs(e[2] - s.x) + abs(e[3] - s.y))
        if not (CLOCK_STEER[0] and len(walkers) >= CLOCK_MIN_ROOM) or self._clock_held():
            return by_distance
        order = drops.prefer_target(self.emu, walkers, drops.CLOCK)
        if order is None:
            return by_distance
        # Keep prefer_target's CHOICE as the next kill; sort only the rest back to nearest-first.
        # Sorting the whole list by distance - which is what this did first - silently undid the
        # entire feature: 3000 randomised rooms came back with zero reorders.
        near = {e[0]: i for i, e in enumerate(by_distance)}
        return [order[0]] + sorted(order[1:], key=lambda e: near[e[0]])

    def clear_room(self, max_enemies: int = 12) -> bool:
        """Kill everything in the room: walkers nearest first, fliers by ambush. Collect drops."""
        emu = self.emu
        emu.note("CLEARING THE ROOM: every enemy must die before the doors open")
        s = emu.state()
        self.nav.kb.use(s.level, s.mode)
        self._ambushed = False
        if s.level and (s.x <= 16 or s.x >= 224 or s.y >= 205 or s.y <= 69):
            d = "Right" if s.x <= 16 else "Left" if s.x >= 224 else "Up" if s.y >= 205 else "Down"
            emu.step(d, 20)     # never fight from a doorway (attacks are disabled there)
        for _ in range(max_enemies * 3):
            s = emu.state()
            # hp > 0 as well as killable: a dead slot keeps its type and its position until the
            # game clears it, and read_enemies filters on type alone. See attack_slot's note - one
            # dead Gel cost 144 frames of beam swings before this.
            ens = [e for e in read_enemies(emu) if killable(e) and enemy_hp(e) > 0]
            if not ens:
                self.collect_drop()
                emu.note("Room clear")
                return True
            walkers = [e for e in ens if e[1] not in self.FLIERS]
            if sum(1 for e in walkers if e[1] in self.DARKNUTS) >= 3 and not getattr(self, "_ambushed", False):
                self._ambushed = True
                rng = self.jitter[0] if self.jitter else None
                if getattr(self, "use_bombs", False) and s.bombs >= 3:
                    if self.bomb_darknuts(rng=rng):
                        continue
            traps = [e for e in read_enemies(emu) if e[1] == 0x49]
            def in_trap_line(e):
                return any(abs(t[2] - e[2]) < 12 or abs(t[3] - e[3]) < 12 for t in traps)
            if walkers:
                # prefer targets that are not sitting in a blade trap's line; wait a little for others to leave it
                safe = [e for e in walkers if not in_trap_line(e)]
                if not safe:
                    waited = 0
                    while waited < 120 and not safe:
                        emu.step((), 4); waited += 4
                        walkers = [e for e in read_enemies(emu)
                                   if e[1] not in self.FLIERS and killable(e) and enemy_hp(e) > 0]
                        safe = [e for e in walkers if not in_trap_line(e)]
                    if not safe:
                        if walkers:
                            emu.note("Target is parked in a trap line; attacking anyway with care")
                        safe = walkers
                    if not safe:
                        continue
                walkers = safe
                # Nearest-first, unless a clock is winnable by reordering: _clock_order falls back to
                # exactly this sort whenever it declines to steer, so this line is the only ordering
                # decision in the room.
                walkers = self._clock_order(walkers, s)
                if walkers[0][1] in self.DARKNUTS:
                    self.hunt_darknut(walkers[0][0])
                else:
                    self.attack_slot(walkers[0][0])
            else:
                if not self.ambush():
                    break
            self.collect_drop()
        return not [e for e in read_enemies(emu) if killable(e) and enemy_hp(e) > 0]

    def grab_key_by_dodging(self, item_type: int = 0x19) -> State | None:
        """Fetch the room's item using avoidance navigation, not combat."""
        emu, nav = self.emu, self.nav
        item = read_room_item(emu)
        if item is None:
            emu.note("No item on the floor to grab")
            return None
        t, ix, iy = item
        emu.note(f"Grabbing the item (type {t:02X}) at ({ix},{iy}) by dodging the enemies, not fighting")
        tx, ty = snap(ix, iy)
        s = nav.go(lambda x, y: abs(x - tx) <= 8 and abs(y - ty) <= 8, "the item", max_replans=120)
        for _ in range(4):
            if read_room_item(emu) is None:
                emu.note(f"Got it. Keys now {emu.state().keys}")
                return emu.state()
            s = nav.go(lambda x, y: x == tx and y == ty, "the item exactly", max_replans=40)
        return emu.state()
