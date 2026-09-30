"""Short-horizon lookahead: at each decision, try every macro on an in-memory copy of the state,
look a few frames ahead, score the outcome, keep the best. This is the optimizer's core move.

Macros are 8-frame holds in each direction, a sword swing in each direction, and a short wait.
Scoring (fight mode): dying is catastrophic, losing hearts is very bad, enemy hp lost is good,
kills are great, and time costs a little. A cheap rollout after each macro (hold still a few
frames) catches "you'll be hit right after this".
"""
from __future__ import annotations

import os
import random

from .emulator import BizHawk, State
from .overworld import (read_enemies, read_room_item, immune_to, DMG_SWORD, DMG_BOMB,
                        DMG_BOOMERANG, DMG_ARROW, DMG_FIRE, read_ghost_objects)
from . import drops as _drops

DIRS4 = ("Up", "Down", "Left", "Right")
OPPOSITE = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}

# Set by the runner for segments whose damage is about to be refilled (a boss: the Triforce piece
# behind it restores every heart), or None to price damage from Link's own health.
CAUTION_OVERRIDE = [None]
WALK_INTERP = [False]         # True: interpolate walking distance between lattice points (see Lattice.walk)
SPOT_FACING = [True]          # the strike-spot field leaves out a Darknut's shield side (A/B: r8_3f 1,751 -> 1,479)
ROW2 = _drops.ROWS[2]             # the only monsters with bombs in their drop row; zelda.drops owns it
BOMB_TARGET = [6]             # plan_fight works the ten-kill forced drop for bombs while Link holds fewer than this
BEAMS = [True]                # full hearts: roll swings out far enough to see the sword beam land
OLD_PLANNER = [False]          # True restores Manhattan shaping and flat damage prices (A/B probes)
DMG_SCALE = [1.0]             # multiplies what a lost half heart costs the planners (boldness; set per attempt)
BEAM_PREMIUM = [1.0]          # at full hearts the first hit is priced at damage_weight x this (it also costs the beam)
TIME_SCALE = [1.0]            # multiplies what a frame costs the fight planner
COMPOUND = [True]             # fight planner also tries "step(s), THEN swing": finds the hit one move ahead
LAZY_HOLD = [True]            # a hold that barely moves Link (grid snap against a wall) is priced as wasted
COMPOUND_STEPS = [(8, 16)]    # how far ahead the walk-then-swing candidates look
IFRAME_SHAPING = [False]      # steer toward monsters that will be hittable on arrival, not ones still flashing
# Staged fights (runner.SPLIT_FIGHTS): plan_fight stops as soon as this many killable enemies are left, so the
# search can pick the best line for each kill instead of one line for the whole room. It reports the count it
# uses as emu.stage_count, so the stage's success test counts exactly what the planner counts.
KILL_STAGE = [None]
DECISION_LOG = [None]         # a list: plan_fight appends every decision (frame, link, enemies, field, branches, choice)


def caution(s) -> float:
    """How much a lost half heart is worth right now, as a multiplier on the planners' damage prices."""
    if OLD_PLANNER[0]:
        return 1.0
    h, c = s.hearts, max(1, s.containers)
    if CAUTION_OVERRIDE[0] is not None:
        # A refill is coming, and it is a FULL one - the Triforce piece restores every heart. So damage
        # is worth nothing at ANY health, including none, and this must not be gated on having health
        # left to spend.
        #
        # It used to be, with the comment "a refill is coming - but only while there is health to
        # spend", and that is exactly backwards. "There is health to spend" is the wrong condition to
        # look at when what is behind the boss makes the health come back regardless. The effect was
        # that the override switched itself off at 3.5 hearts and the planner became MORE careful the
        # lower it got - inside a fight where a lost heart costs nothing - which is the one thing the
        # boss segment exists to stop. The owner, watching a Gleeok attempt finish at 2.5 hearts:
        # "this is another where they can just tank it and we get all our health back in the next
        # room. Confirm that is in the logic." It was in the logic, and it did the reverse.
        return CAUTION_OVERRIDE[0]
    if h <= 2.0:
        return 1.5
    if h <= 3.5:
        return 1.0
    if h >= 8 or (h >= 5 and h / c >= 0.75):
        return 0.3
    return 0.55


class Lattice:
    """Where Link can stand in this room on the 8 px grid, and walking distances over it.

    Built once per planning call from the tile map (walls, blocks, water the ladder cannot span), so
    "how far is that spot" means how far Link has to WALK, not how far it is through a wall."""

    def __init__(self, emu: BizHawk):
        from .overworld import (TileKB, read_cells, legal, water_bridges, WATER_IDS, OW_WATER_IDS,
                                LADDER_FLAG, BLOCK_IDS)
        s = emu.state()
        kb = TileKB()
        kb.use(s.level, s.mode)
        cells = read_cells(emu)
        ok = water_bridges(cells, WATER_IDS if s.level else OW_WATER_IDS) if emu.byte(LADDER_FLAG) else None
        both = (ok[0] | ok[1]) if ok else None
        self.free = set()
        for x in range(0, 241, 8):
            for y in range(61, 206, 8):
                if s.level:
                    inside = 32 <= x <= 208 and 93 <= y <= 189
                    lane = (x == 120 and (y < 93 or y > 189)) or (y == 141 and (x < 32 or x > 208))
                    if not (inside or lane):
                        continue
                # (blocks are left to the tile knowledge base: Link's head may overlap a block's lower half,
                # which is what lets him through a diagonal line of them)
                if legal(cells, kb, x, y, True, None, both):
                    self.free.add((x, y))

    @staticmethod
    def snap(x: int, y: int) -> tuple:
        return (x + 4) // 8 * 8, (y - 5 + 4) // 8 * 8 + 5

    def nearest_free(self, x: int, y: int, radius: int = 24):
        p = self.snap(x, y)
        if p in self.free:
            return p
        best = None
        for q in self.free:
            d = abs(q[0] - x) + abs(q[1] - y)
            if d <= radius and (best is None or d < best[0]):
                best = (d, q)
        return best[1] if best else None

    def field(self, sources) -> dict:
        """Steps (8 px each) from every reachable lattice point to the nearest source."""
        from collections import deque
        dist = {}
        dq = deque()
        for sx, sy in sources:
            q = self.nearest_free(sx, sy)
            if q is not None and q not in dist:
                dist[q] = 0
                dq.append(q)
        free = self.free
        while dq:
            cx, cy = dq.popleft()
            d = dist[(cx, cy)] + 1
            for n in ((cx + 8, cy), (cx - 8, cy), (cx, cy + 8), (cx, cy - 8)):
                if n in free and n not in dist:
                    dist[n] = d
                    dq.append(n)
        return dist

    def walk(self, field: dict, x: int, y: int, fallback: float) -> float:
        """Walking distance in pixels from (x, y) according to `field`, or `fallback` if off the lattice."""
        if WALK_INTERP[0]:
            x0, y0 = x // 8 * 8, (y - 5) // 8 * 8 + 5
            best = None
            for qx in (x0, x0 + 8):
                for qy in (y0, y0 + 8):
                    f = field.get((qx, qy))
                    if f is not None:
                        d = 8.0 * f + abs(qx - x) + abs(qy - y)
                        if best is None or d < best:
                            best = d
            if best is not None:
                return best
        q = self.snap(x, y)
        if q in field:
            return 8.0 * field[q] + abs(q[0] - x) + abs(q[1] - y)
        q = self.nearest_free(x, y, 12)
        if q is not None and q in field:
            return 8.0 * field[q] + abs(q[0] - x) + abs(q[1] - y)
        return fallback

# How much more expensive a frame becomes over the course of one planning run. 0 reproduces the
# old behaviour (time almost free), which is what made Link stand around; set by ZELDA_URGENCY so
# the two can be measured against each other.
URGENCY = float(os.environ.get("ZELDA_URGENCY", "7"))
_FIGHT_DEBUG = bool(os.environ.get("ZELDA_FIGHT_DEBUG"))


# B throws whatever is in the B slot - the project has been bitten by this (see the Dodongo notes in
# boss.py). So a move called "bomb" is really "press B", and what it costs depends on the slot:
# the Blue Candle does DMG_FIRE, a bomb DMG_BOMB, the wand another fireball, the bow DMG_ARROW.
# Pricing all of them as DMG_BOMB means the planner scores the better weapon as the worse one and
# never picks it - which is what happened: Link cleared a room of Vires with the candle on a crossing
# segment and nothing in the code had any idea that was available.
_B_ITEM_DMG = {0: DMG_BOOMERANG, 1: DMG_BOMB, 2: DMG_ARROW, 4: DMG_FIRE, 8: DMG_FIRE}


def b_damage_type(emu) -> int:
    """What a B press will actually do, given what is in the slot. 0 if it is not a weapon."""
    return _B_ITEM_DMG.get(emu.byte(0x656), 0)


def macros_for(kind: str, bombs: bool = False, bow: bool = False, emu=None):
    m = [("hold", d, 8) for d in DIRS4] + [("wait", None, 6)]
    if kind == "fight":
        m += [("swing", d, 0) for d in DIRS4]
        # A B press is offered when the SLOT holds something that damages, not merely when bombs > 0.
        have_weapon = b_damage_type(emu) != 0 if emu is not None else bombs
        if have_weapon:
            m += [("bomb", d, 0) for d in DIRS4]
        if bow:
            m += [("shoot", d, 0) for d in DIRS4]
    return m


FACE_FIRST = [True]           # turn until Link really faces the way he is about to strike (see face())
_DIRCODE = {"Right": 1, "Left": 2, "Down": 4, "Up": 8}


def face(step, d: str):
    """Turn Link to face d. One frame of d is only enough when he already stands on the 8 px grid line for that
    axis: off it, the game first SLIDES him along his old axis to the nearest line - facing left or right the whole
    time - and turns him afterwards. Every perpendicular swing, bomb and arrow issued off the grid (about half of
    them: a 12 px stride lands on a line every other stride) went out sideways and hit nothing, which is a large
    part of why Link circled things instead of cutting them down. Up to four more frames fixes it."""
    s = step(d, 1)
    if FACE_FIRST[0]:
        n = 1
        while s.dir != _DIRCODE[d] and n < 6 and s.mode in (5, 9):
            s = step(d, 1)
            n += 1
    return s


def run_macro(emu: BizHawk, macro, rec=None) -> State:
    step = rec.step if rec else emu.step
    kind, d, n = macro
    if kind == "hold":
        return step(d, n)
    if kind == "wait":
        return step((), n)
    if kind == "swing":
        face(step, d)
        step("A", 2)
        return step((), 11)
    if kind == "bomb":
        face(step, d)
        step("B", 2)
        return step((), 4)
    if kind == "shoot":
        face(step, d)
        step("B", 2)
        return step((), 12)
    if kind == "go_swing":               # d = (walk direction, swing direction), n = frames walked first
        step(d[0], n)
        face(step, d[1])
        step("A", 2)
        return step((), 11)
    raise ValueError(macro)


# Things that cannot be killed and so never count toward "clear the room":
# 0x49 blade traps, 0x2B-0x2D Bubbles.
# 0x40 is the fire that flanks an old man, and 0x4B/0x4C are old men themselves. They sit in the
# object table looking exactly like enemies, they cannot be hurt, and a room "clear" check that
# counts them never finishes - which is how Level 9's very first room, where the old man opens the
# way for anyone carrying all eight Triforce pieces, stopped the run dead.
UNKILLABLE = {0x49, 0x2B, 0x2C, 0x2D, 0x40, 0x4B, 0x4C}

# Killable in principle, but never worth chasing: Zoras submerge in water where Link cannot follow,
# and Peahats are invulnerable while airborne. Walk around them instead.
# Lynels (0x01/0x02) hit for two hearts and take many hits; the guides say avoid, not fight.
NEVER_CHASE = UNKILLABLE | {0x11, 0x1A, 0x01, 0x02}

# The owner's standing rule, and it is a rule about STATE rather than about a segment: "anytime he
# has a full health and the white sword he must kill the lynol."
#
# That is better than putting "revenge" in a NEED_FULL_HEARTS set, because the condition switches
# itself on. The route walks PAST the Blue Lynel on the way in - correctly, it is in NEVER_CHASE and
# the sword is not worth a fight yet - and then the Triforce piece behind Gleeok refills the bar and
# the White Sword is already in hand, so on the way back the same enemy becomes the objective with no
# route edit at all. The story writes itself: get by the guard, take the head, come back and kill him.
#
# "must kill" is deliberate wording. The Lynel is not merely allowed to be a target here, he is the
# objective, so a segment that is fighting at full health with the White Sword should be searching for
# his death and not for a way past him.
def must_kill(t: int, s) -> bool:
    """Is this enemy the objective right now, rather than something to walk around?"""
    return t in (0x01, 0x02) and s.sword >= 2 and s.hearts >= s.containers

# "I want to be at FULL health for this one."
#
# The owner asked for two separate things and they are two separate mechanisms. This is the first:
# a declared desire, in the same shape as BOMB_TARGET and HEARTS_FREE, so any segment can ask for it
# rather than one boss policy hardcoding a private refill. The second is in fight_score below.
#
# Why it exists at all: the sword beam fires only at `hearts >= containers` (Fighter._beam_ready,
# combat.py), so a fight that wants the beam is not a fight about damage dealt - it is a fight about
# damage NOT taken, because one lost half-heart removes the weapon. Gleeok already does this with a
# hand-rolled pre-fight refill; this makes it a property of a segment instead.
#
# FICTION, CLEARLY LABELLED: the run's story is that Link carries the dragon's head home and leaves it
# in the cave the White Sword came from. The game has no such mechanic and no head item - nothing here
# pretends otherwise. The cave is the finish because the owner said it is, not because the ROM does
# anything with a head.
NEED_FULL_HEARTS = [False]


def hearts_full(s) -> bool:
    return s.hearts >= s.containers



def killable(e) -> bool:
    return e[1] not in UNKILLABLE and e[1] < 0x50


def enemy_hp_total(emu: BizHawk, types=None, ignore=()) -> tuple[int, int]:
    ens = [e for e in read_enemies(emu) if killable(e) and e[0] not in ignore and (types is None or e[1] in types)]
    return sum(e[4] >> 4 for e in ens), len(ens)


def fireballs_near(emu: BizHawk, s, radius: int = 56) -> bool:
    ts = emu.ram(0x34F, 20)
    xs = emu.ram(0x70, 20)
    ys = emu.ram(0x84, 20)
    return any(0x50 <= ts[i] < 0x60 and max(abs(xs[i] - s.x), abs(ys[i] - s.y)) <= radius
               and not parried_now(emu, s, i) for i in range(20))


# ---------------------------------------------------------------- the shield, for free
#
# Z_01.asm CheckLinkCollision (5598-5705). A monster's shot does NOT harm Link when, in order:
#   1. it is not $56 (Fireball2) or $5A - those always harm, magic shield or not;
#   2. Link's own ObjState high nybble is $00 - he is IDLE, not walking and not swinging;
#   3. Link and the shot face OPPOSITE directions.
# Then a shot below $55 (flying rock) or at/above $5B (boomerang) is parried outright, while $55-$5A
# need InvMagicShield ($676) - bought in the Level 5 shop for 130 rupees, so not before then.
#
# The owner had this as "Link starts with a shield that blocks if he is not moving or using his sword",
# which is exactly rule 2. He was right and the harness was wrong to assume otherwise: there was no
# shield code here at all, only dodging.
#
# WHAT THIS DELIBERATELY DOES NOT DO: it never suggests standing still. It only declines to charge
# for a hit that the game is not going to land, so the fighter stops paying frames to sidestep a rock
# it is already blocking. A parry that rewarded idling would stop Link closing on Gleeok, and Gleeok
# is immune to the whole idea anyway - UpdateGleeok shoots $56 (Z_04.asm:8639-8640), one of the two
# types rule 1 excludes outright, so no dragon frame can be won or lost by anything in this section.
SHOT_ALWAYS_HARMS = {0x56, 0x5A}
LINK_STATE = 0xAC          # ObjState; the bridge's FIELDS table calls this "anim", which is wrong
LINK_DIR = 0x98            # ObjDir
# ON by default: the owner watched it helping and asked to keep it ("2. keep the parry I was seeing
# it helping"). It was gated off purely as caution on a cold change, and that caution has now been
# overruled by an observation I did not make. ZELDA_PARRY=0 turns it off without a code edit, which
# is how to A/B it - the free parry only ever saves the damage, never presses a button.
PARRY = [bool(int(os.environ.get("ZELDA_PARRY", "1")))]


def parried_now(emu: BizHawk, s, i: int) -> bool:
    """Is shot `i` bouncing off Link's shield right now, needing no item and no button?"""
    if not PARRY[0]:
        return False
    ts = emu.ram(0x34F, 20)
    dirs = emu.ram(0x98, 20)
    t = ts[i]
    if t in SHOT_ALWAYS_HARMS or not (0x50 <= t < 0x60):
        return False
    if not (t < 0x55 or t >= 0x5B):         # $55-$5A are the fireballs, and they need the shield item
        return False
    if emu.byte(LINK_STATE) & 0xF0:         # rule 2: Link must be idle, not mid-step or mid-swing
        return False
    d = dirs[0] | dirs[i]                   # rule 3: opposite facings, either axis
    return (d & 0x0C) == 0x0C or (d & 0x03) == 0x03


def fight_score(before: State, after: State, hp0: int, n0: int, hp1: int, n1: int, frames: int,
                near_penalty: float = 0.0, damage_weight: float = 400.0, hp_weight: float = 60.0,
                time_weight: float = 0.5) -> float:
    if after.hearts <= 0 or after.mode == 0x11 or after.mode == 0x08:
        return -100000
    if after.room != before.room or after.mode not in (5, 9):
        return -50000            # leaving the room (or a scroll) is not clearing it
    sc = 0.0
    sc -= damage_weight * (before.hearts - after.hearts) * 2       # per half heart
    if NEED_FULL_HEARTS[0]:
        # The second half of "I want to be at full health for this one", and the half that actually
        # changes behaviour. damage_weight prices a lost heart in frames; for a beam fight a lost
        # heart is not a cost, it is the LOSS OF THE WEAPON, so it has to dominate every other term
        # here or the planner will happily trade the beam for two swings. Being short when the fight
        # is over is worse than being slow, and being full at the end is worth a lot.
        lost = max(0.0, after.containers - after.hearts)
        sc -= 9000.0 * lost
        if after.hearts >= after.containers:
            sc += 3000.0
    # bosses can swap in a fresh head, which raises the tracked health; never punish that
    sc += hp_weight * max(0, hp0 - hp1)
    sc += 150 * (n0 - n1)
    sc -= time_weight * frames
    sc -= near_penalty
    return sc


def static_slots(emu: BizHawk) -> set:
    """Slots that never move and have no health: pickups, not enemies (rupee caches)."""
    before = {e[0]: (e[2], e[3], e[4]) for e in read_enemies(emu)}
    root = emu.msave()
    emu.cmd("step 10 -")
    after = {e[0]: (e[2], e[3], e[4]) for e in read_enemies(emu)}
    emu.mload(root)
    emu.mfree(root)
    return {s for s, v in before.items() if s in after and after[s] == v and v[2] == 0}


def plan_fight(emu: BizHawk, rec, *, max_frames: int = 3000, rollout: int = 14, rng: random.Random | None = None,
               types=None, log=None, targets=None, done=None, damage_weight: float = 400.0,
               hp_weight: float = 60.0, approach_range: int = 0, use_bombs: str = "sparing",
               use_bow: bool = False, miss_penalty: float = 1.0) -> str:
    """Clear the room's killable enemies with lookahead. Returns 'clear', 'died' or 'timeout'.
    `rec` is a Recorder whose step() advances the real (kept) trajectory."""
    frames = 0
    ignore = static_slots(emu)
    FUSE = 86            # a bomb's blast lands well after a normal rollout, so give it its own
    BEAM_ROLL = 48       # ...and the sword beam crosses the room at ~3 px a frame
    ARROW = 44           # ...and so does an arrow: it needs this long to cross most of a room
    last_dir = None      # for the anti-dithering penalty
    streak_fuse_until = -1
    # A/B from full-health states: a Vire room 1,444 -> 1,138 with the beam rollout, a Keese room 799 -> 921.
    # So it is a per-attempt choice and the search keeps whichever came out ahead.
    beam_attempt = BEAMS[0] and (rng is None or rng.random() < 0.6)
    # decisions spent holding the tenth kill back for a bomb before giving up on it. It varies by attempt (some do
    # not try at all) so the search, which now counts bombs in its ranking, decides whether it was worth it
    streak_patience = rng.choice([0, 0, 8, 16]) if rng else 16
    lattice = None if OLD_PLANNER[0] else Lattice(emu)

    def measure():
        """(total hp, count) of what we are trying to kill.

        The ghosts count, and it matters more than it looks. For Gleeok the explicit tracker sees one
        head, so the measure was 10 HP while the fight was 70, and the cutoff fired the moment the
        head died - at which point gleeok_dead, which checks $034D and every slot from 1 to 7, was
        still False. The planner declared the room finished inside its own budget and the segment
        scored it a failure. A budget measured against a tenth of the boss is a budget that ends
        early, and an attempt that ends early looks exactly like one that ran out of room.
        """
        if targets is None:
            total, n = enemy_hp_total(emu, types, ignore)
        else:
            ts = targets(emu)
            total, n = sum(t[4] >> 4 for t in ts), len(ts)
        for g in read_ghost_objects(emu):
            if not immune_to(emu, g[0], DMG_SWORD):
                total += g[3] >> 4
                n += 1
        return total, n

    def finished():
        if done is not None:
            return done(emu)
        if measure()[1] == 0:
            return True
        # The game keeps its own room-cleared flag and it is the authority. Counting objects has
        # fooled this planner more than once - sword-beam splashes, fireballs and death animations
        # all sit in the same table - and the symptom is Link swinging at an empty room long after
        # he won. If the cartridge says the room is clear, the room is clear.
        return bool(emu.state().level) and emu.byte(0x34D) != 0

    while frames < max_frames:
        s0 = emu.state()
        if s0.hearts <= 0:
            return "died"
        if frames == 0:
            room0 = s0.room
        if s0.room != room0:
            return "left the room"
        hp0, n0 = measure()
        emu.stage_count = n0
        if finished():
            emu.stage_count = 0
            return "clear"
        if KILL_STAGE[0] is not None and n0 <= KILL_STAGE[0]:
            return "stage"
        # bombs are only worth branching on when something is close enough for the blast to reach:
        # each bomb branch costs a full fuse of emulation, so they are not free to consider
        tlist = targets(emu) if targets is not None else [
            e for e in read_enemies(emu) if killable(e) and e[0] not in ignore]
        # Gleeok's neck, added whichever way tlist was built. This was originally only in the
        # read_enemies branch, which meant it silently did nothing for the one fight it was written
        # for: gleeok_policy passes targets=gleeok_head_tracker(emu), so tlist came from the tracker
        # and the six segments - 60 of the boss's 70 hit points - were never in the room. A 490-frame
        # attempt came out of the other three fixes, and it still could not finish the fight, and the
        # neck being unreachable is the most likely reason why.
        #
        # The tracker locks onto one head deliberately (its own docstring: re-picking every frame
        # makes the target flicker and the planner loses its sense of progress). That reasoning is
        # about the HEAD, and it still holds - so the head stays the lock-on target and the neck is
        # added as what it is: something to walk through on the way, and something the sword can
        # reach. Segments already dead are excluded, so the count falls as the fight goes on.
        ghosts = [g for g in read_ghost_objects(emu) if not immune_to(emu, g[0], DMG_SWORD)]
        ghost_targets = [(g[0], 0x43, g[1], g[2], g[3]) for g in ghosts]
        # A target the game will parry a swing at is not a target. ObjInvincibilityMask ($4B2) says
        # which damage TYPES a slot refuses, and the game checks it before subtracting anything, so
        # counting one of these as "HP to remove" has the planner trying to grind a number down that
        # can never move. Price it as furniture instead: still something to walk round, but not
        # something to keep hitting.
        # ...and the other half, which is the half that matters for a dragon. Gleeok's six neck
        # segments have real positions and real HP in slots 1..6 with an object type of 0, so they are
        # absent from read_enemies and the planner has been swinging at a 10 HP head in a room holding
        # sixty more hit points of boss. The mask on those segments is $FE - hurt by the sword and
        # nothing else - so the sword IS the key to them, which makes them targets, not furniture.
        # The owner's read: "step straight up to the remaining necks and mash your attack button."
        #
        # Added after the immunity filter, not before: a ghost that happens to be sword-immune is still
        # a wall, and putting it in the list first would just have the filter throw it away again.
        tlist = [t for t in tlist if not immune_to(emu, t[0], DMG_SWORD)] + ghost_targets
        near_target = any(max(abs(t[2] - s0.x), abs(t[3] - s0.y)) <= 48 for t in tlist)
        help_n = emu.byte(_drops.STREAK)              # kills in a row since Link was last hit
        want_bombs = (not OLD_PLANNER[0]) and 1 <= s0.bombs < BOMB_TARGET[0] and use_bombs != "never"
        streak_bomb = want_bombs and help_n == 9 and streak_patience > 0
        # Same arithmetic the clock uses, from the one table: bombs are row 2 columns 1, 6 and 8, so
        # the pre-kill $52A has to be 0, 5 or 7. prefer_target also encodes the "there must be a
        # monster to burn the cycle on" half that used to be spelled `not all(ROW2 ...)`.
        #
        # order[0] being a ROW2 monster is what makes this mean "the NEXT kill is the bomb column".
        # prefer_target also returns an order when the next column is not wanted - it puts a filler
        # first to advance the cycle - and reading that as a "yes" here would have paid the +120
        # reward for killing the wrong monster.
        _order = _drops.prefer_target(emu, tlist, _drops.BOMBS) if want_bombs else None
        row2_next = bool(_order) and _order[0][1] in ROW2
        if streak_bomb and len(rec.inputs) >= streak_fuse_until:
            streak_patience -= 1                  # not for ever: after a while the sword may have the tenth kill
        # Branching costs a lot of emulation. When everything is far away and nothing is incoming,
        # just walk toward the target: there is nothing to weigh up yet.
        if approach_range and tlist and not fireballs_near(emu, s0):
            t = min(tlist, key=lambda t: abs(t[2] - s0.x) + abs(t[3] - s0.y))
            dx, dy = t[2] - s0.x, t[3] - s0.y
            if max(abs(dx), abs(dy)) > approach_range:
                d = ("Right" if dx > 0 else "Left") if abs(dx) > abs(dy) else ("Down" if dy > 0 else "Up")
                run_macro(emu, ("hold", d, 8), rec)
                frames += 8
                continue
        # Coarse mode: far from the target, only the four walking moves matter and a short rollout
        # is enough. Full branching (swings, bombs, waits, long rollout) is reserved for close
        # quarters. This is what makes a long boss fight searchable in reasonable time.
        # Coarse mode ("too far to bother attacking, just walk closer") is wrong with a bow:
        # range is the whole point, and walking closer to Gohma is how Link dies.
        far = (bool(tlist) and not use_bow
               and min(max(abs(t[2] - s0.x), abs(t[3] - s0.y)) for t in tlist) > 40)
        beam = beam_attempt and not OLD_PLANNER[0] and s0.hearts >= s0.containers and s0.sword >= 1
        if far:
            macros = [("hold", d, 8) for d in DIRS4]
            this_rollout = 8
            if beam and tlist:
                # a target in line, however far: the beam reaches it
                for t_ in tlist:
                    dx, dy = t_[2] - s0.x, t_[3] - s0.y
                    if abs(dy) <= 10 and abs(dx) > 16:
                        macros.append(("swing", "Right" if dx > 0 else "Left", 0))
                    if abs(dx) <= 10 and abs(dy) > 16:
                        macros.append(("swing", "Down" if dy > 0 else "Up", 0))
                macros = list(dict.fromkeys(macros))
        else:
            # Bombs are a resource, not a weapon of convenience: a skeleton dies to the sword for
            # free, and the bombs are needed for Dodongo and for blasting walls. Only offer them
            # when they are the point (a boss that ignores the sword) or when one blast can take a
            # whole cluster, and even then they carry a cost in the scoring below.
            cluster = 0
            # A cluster only counts if a bomb could ACTUALLY hit it. That qualification was not here
            # until ghosts entered tlist, and it is not a detail: Gleeok's six neck segments are
            # stacked 5 px apart (GleeokSegmentYs: $6F,$74,$79,$7E,$83,$88), so counting all targets
            # makes the neck look like a six-body cluster - and its mask is $FE, sword-only. The gate
            # opened, the planner started throwing bombs at a body that cannot be hurt, and those bombs
            # are what Level 8's door and Level 5's two walls are going to need later.
            #
            # The owner caught it by watching: "I see bomb useage." Count only what the bomb reaches.
            # Count only what the B slot's weapon reaches. It is DMG_BOMB when bombs are selected and
            # DMG_FIRE when the candle is, so asking about DMG_BOMB with a candle in hand credited the
            # planner for hits it cannot land.
            _bd = b_damage_type(emu) or DMG_BOMB
            bombable = [t for t in tlist if not immune_to(emu, t[0], _bd)]
            for t in bombable:
                near_t = sum(1 for u in bombable if max(abs(u[2] - t[2]), abs(u[3] - t[3])) <= 24)
                cluster = max(cluster, near_t)
            # Level 9 is entered once now, with no shop trip in the middle, and its route needs a bomb
            # for every one of five walls. A bomb thrown at a cluster there is a wall that cannot be
            # opened later (the first run reached 0x30 with none), so in Level 9 the sword does it.
            # ...and never the last two: the route bombs walls (Level 1's 53, the 0x67 cave, Level 5's two)
            # and a fight that spends the bomb a wall needed stops the whole run at that wall.
            offer_bombs = s0.bombs > (0 if use_bombs == "free" else 2) and near_target and s0.level != 9 and (
                use_bombs == "free" or (use_bombs == "sparing" and cluster >= 3))
            if streak_bomb and near_target:
                offer_bombs = True               # the tenth kill, made with a bomb, pays four bombs back
            macros = macros_for("fight", bombs=offer_bombs, bow=use_bow and s0.rupees > 0, emu=emu)
            this_rollout = rollout
            if streak_bomb and len(rec.inputs) < streak_fuse_until:
                # a bomb laid for the tenth kill is ticking: keep the sword out of it, or the sword takes the kill
                macros = [m for m in macros if m[0] in ("hold", "wait")]
        # One move ahead. The plain macros only see a hit that is available THIS instant, and everything
        # else is steered by a static guess at where to stand - so against anything that keeps moving
        # (a Darknut showing its side for half a second) Link circled for a hundred frames between hits.
        # "Walk 8 or 16 frames, then swing" is tried for every direction whose swing would face something
        # in reach once he gets there; the walk is simulated once per direction and shared by its swings.
        compounds = []
        if COMPOUND[0] and not far and not OLD_PLANNER[0] and tlist and not (
                streak_bomb and len(rec.inputs) < streak_fuse_until):
            croot = emu.msave()
            slots = [t_[0] for t_ in tlist]
            for d in DIRS4:
                emu.mload(croot)
                for k in COMPOUND_STEPS[0]:
                    sk = emu.step(d, 8)
                    if sk.hearts < s0.hearts or sk.mode not in (5, 9) or (k == 8 and (sk.x, sk.y) == (s0.x, s0.y)):
                        break
                    xs_, ys_, ts_ = emu.ram(0x70, 12), emu.ram(0x84, 12), emu.ram(0x4F0, 12)
                    for d2 in DIRS4:
                        ddx, ddy = {"Right": (1, 0), "Left": (-1, 0), "Down": (0, 1), "Up": (0, -1)}[d2]
                        for sl in slots:
                            if ts_[sl] * 2 > 8:
                                continue                 # still flashing from the last hit when the blade lands
                            ex_, ey_ = xs_[sl] - sk.x, ys_[sl] - sk.y
                            if (ddx and abs(ey_) < 14 and 0 < ex_ * ddx <= 34) or (ddy and abs(ex_) < 14 and 0 < ey_ * ddy <= 34):
                                compounds.append(("go_swing", (d, d2), k))
                                break
            emu.mload(croot)
            emu.mfree(croot)
        # Impatience. A half heart is worth 400 points and a frame only 0.5, so early on the
        # planner will happily burn hundreds of frames to dodge one hit - which on screen looks
        # like Link standing about doing nothing. Time gets steadily more expensive instead.
        urgency = 1.0 + URGENCY * (frames / max_frames)
        dmg_w = damage_weight * caution(s0) * DMG_SCALE[0]
        if beam:
            dmg_w = max(dmg_w, damage_weight * BEAM_PREMIUM[0])   # the first hit costs the beam as well as the half heart
        if want_bombs and 5 <= help_n < 10:
            dmg_w *= 1.5                          # a hit resets the streak
        if emu.byte(0x66C):
            # Holding the dungeon clock. Z_01 CheckLinkCollision ORs InvClock into the same test as
            # Link's invincibility timer, so contact does nothing at all while it is held, and every
            # enemy update routine bails out at the top. Damage is not "less bad" here, it is zero:
            # the planner is free to walk the shortest line through the room instead of paying frames
            # to go round. Not zero-cost, though - the clock dies with the screen, so anything the
            # fighter does has to be finished before Link leaves this room.
            dmg_w = 0.0
        # true walking distance to the nearest strike spot, from where the enemies are NOW
        spot_field = None
        if lattice is not None and tlist:
            srcs = []
            inv = emu.ram(0x4F0, 12) if IFRAME_SHAPING[0] else None
            ready = [e for e in tlist if inv is None or e[0] >= 12 or inv[e[0]] * 2 <= 12
                     + 0.6 * (abs(e[2] - s0.x) + abs(e[3] - s0.y))]
            for e in (ready or tlist):
                f = emu.byte(0x98 + e[0]) if (SPOT_FACING[0] and e[1] in (0x0B, 0x0C)) else 0
                fx, fy = {1: (1, 0), 2: (-1, 0), 4: (0, 1), 8: (0, -1)}.get(f, (0, 0))
                if fx:                        # a Darknut: its sides and its back, never its shield
                    srcs += [(e[2] - fx * 24, e[3]), (e[2], e[3] - 24), (e[2], e[3] + 24)]
                elif fy:
                    srcs += [(e[2], e[3] - fy * 24), (e[2] - 24, e[3]), (e[2] + 24, e[3])]
                else:
                    srcs += [(e[2] - 24, e[3]), (e[2] + 24, e[3]), (e[2], e[3] - 24), (e[2], e[3] + 24)]
            spot_field = lattice.field(srcs)
        root = emu.msave()
        results = []
        order = list(macros) + compounds
        if rng:
            rng.shuffle(order)
        for m in order:
            emu.mload(root)
            s1 = run_macro(emu, m)                       # branch: not recorded
            s2 = emu.step((), FUSE if m[0] == "bomb" else ARROW if (m[0] == "shoot" and lattice is not None)
                          else BEAM_ROLL if (m[0] == "swing" and beam) else this_rollout)
            hp1, n1 = measure()
            used = {"hold": 8, "wait": 6, "bomb": FUSE, "shoot": 14}.get(m[0], 14)
            if m[0] == "go_swing":
                used = m[2] + 14
            # shaping: pull toward a strike spot (side/back of the nearest killable enemy at sword range),
            # and only penalize standing in FRONT of a Darknut (its shield side / walking line)
            ens = targets(emu) if targets is not None else [
                e for e in read_enemies(emu) if killable(e) and e[0] not in ignore and (types is None or e[1] in types)]
            shaping = 0.0
            if ens:
                spots = []
                front_pen = 0.0
                for e in ens:
                    f = emu.byte(0x98 + e[0]) if e[1] in (0x0B, 0x0C) else 0
                    fx, fy = {1: (1, 0), 2: (-1, 0), 4: (0, 1), 8: (0, -1)}.get(f, (0, 0))
                    ex, ey = e[2], e[3]
                    if fx:
                        spots += [(ex - fx * 24, ey), (ex, ey - 24), (ex, ey + 24)]
                    elif fy:
                        spots += [(ex, ey - fy * 24), (ex - 24, ey), (ex + 24, ey)]
                    else:
                        spots += [(ex - 24, ey), (ex + 24, ey), (ex, ey - 24), (ex, ey + 24)]
                    # in front of it within 40 px on its line: bad
                    dx, dy = s2.x - ex, s2.y - ey
                    if (fx and abs(dy) < 16 and 0 < dx * fx < 40) or (fy and abs(dx) < 16 and 0 < dy * fy < 40):
                        front_pen += 60
                dist = min(abs(s2.x - px) + abs(s2.y - py) for px, py in spots)
                if spot_field:
                    dist = lattice.walk(spot_field, s2.x, s2.y, dist)
                shaping = -0.6 * dist - front_pen
            # A swing that connects is already rewarded through the health terms. A swing that
            # hits nothing is Link flailing at the air: it costs 14 frames, telegraphs nothing and
            # looks terrible, so make it clearly worse than walking.
            penalty = 0.0
            # an arrow that misses costs a rupee as well as the frames, so it is worse
            # than a wasted sword swing
            if m[0] == "shoot" and hp1 >= hp0 and n1 >= n0:
                penalty += miss_penalty * 220
            if m[0] == "go_swing" and hp1 >= hp0 and n1 >= n0:
                continue
            if m[0] == "swing" and hp1 >= hp0 and n1 >= n0:
                dx, dy = {"Right": (1, 0), "Left": (-1, 0), "Down": (0, 1), "Up": (0, -1)}[m[1]]
                in_reach = any((dx and abs(t[3] - s0.y) < 16 and 0 < (t[2] - s0.x) * dx <= 28) or
                               (dy and abs(t[2] - s0.x) < 16 and 0 < (t[3] - s0.y) * dy <= 28)
                               for t in tlist)
                penalty += miss_penalty * (150 if in_reach else 400)
            # Something is lying on the floor - a heart, a fairy, a dropped item. Go and get it,
            # and want it much more when Link is hurt. Walking past a heart is never right.
            # That means the room item AND every monster drop. For most of the project this read
            # only the room item (slot 0x13), but a monster's drop lives in the dead monster's own
            # object slot as type $60 - so the planner walked straight past rupees, hearts and bombs
            # in every fight. One RAM read covers x ($70), y ($84), item ids ($AC) and object types
            # ($34F): this runs on every scored branch, and four separate reads would slow every search.
            blk = emu.ram(0x70, 0x2EB)
            drops = []
            item = read_room_item(emu)
            if item is not None:
                drops.append((item[0], item[1], item[2]))
            for i in range(1, 12):
                if blk[0x34F - 0x70 + i] == 0x60:
                    drops.append((blk[0xAC - 0x70 + i], blk[i], blk[0x84 - 0x70 + i]))
            best = None
            for kind, ix, iy in drops:
                if kind in (0x22, 0x23) and s0.hearts >= s0.containers:
                    continue                                   # a heart is worthless at full health
                if kind == 0x00 and s0.bombs >= max(8, emu.byte(0x67C)):
                    continue                                   # at MaxBombs it cannot be picked up
                if kind == 0x21 and emu.byte(0x66C):
                    continue                                   # already holding the clock; nothing to gain
                # A clock is the best drop in the game for a harness that walks into rooms it cannot
                # survive, and this line used to skip it. See combat.Fighter._clock_held for the
                # disassembly: InvClock gates every enemy update routine, and ORA InvClock in
                # CheckLinkCollision makes Link immune to contact damage for as long as it is held.
                want = 1.2 + 1.6 * max(0.0, (s0.containers - s0.hearts)) / max(1.0, s0.containers)
                if kind == 0x21:
                    # Grab it BEFORE the fight, not after: it freezes the room it is picked up in, and
                    # the pickup happens mid-fight when the kill that made it possible.
                    want += 6.0
                # Bombs are always worth the walk, and far more so when Link is short: Level 9
                # stranded this run with zero bombs (the owner's rule: prioritise dropped bombs).
                if kind == 0x00:
                    want += 1.5 + (2.5 if s0.bombs < 4 else 0.0)
                cost = want * (abs(s2.x - ix) + abs(s2.y - iy))
                best = cost if best is None else min(best, cost)
            if best is not None:
                shaping -= best

            sc = fight_score(s0, s2, hp0, n0, hp1, n1, used,
                             damage_weight=dmg_w, hp_weight=hp_weight,
                             time_weight=0.5 * urgency * TIME_SCALE[0]) + shaping - penalty
            # A key spent on a door nobody asked for is a locked door later with no key: Level 4's Vire room
            # has a locked north door the route never uses, Link brushed it mid-fight, and three rooms on the
            # run stopped dead at the door the key was for.
            if s2.keys < s0.keys:
                sc -= 6000
            # spending a bomb has to pay for itself: the score already gives 150 a kill, so this
            # is worth it for three at once or for something the sword cannot hurt, not otherwise
            if m[0] == "bomb" and use_bombs != "free":
                sc -= 320
            if row2_next and n1 < n0:
                alive = {e[0] for e in ens}
                dead = [t_ for t_ in tlist if t_[0] not in alive]
                if dead:
                    sc += 120 if any(t_[1] in ROW2 for t_ in dead) else -80
            if streak_bomb and n1 < n0:
                if m[0] == "bomb" and emu.byte(0x51):
                    sc += 1200                    # the tenth kill was the bomb's: four bombs are on the floor
                elif m[0] != "bomb":
                    sc -= 500                     # the tenth kill wasted on five rupees
            # standing still is a move of last resort, and it gets worse the longer this drags on
            if m[0] == "wait":
                sc -= 25 * urgency
            # a hold that does not move Link is him walking into a wall: never let that look
            # like a free way to pass time
            if m[0] == "hold" and (s1.x, s1.y) == (s0.x, s0.y):
                sc -= 120
            elif (LAZY_HOLD[0] and m[0] == "hold" and s1.hearts >= s0.hearts
                  and abs(s1.x - s0.x) + abs(s1.y - s0.y) < 6):
                sc -= 60                  # eight frames for a three-pixel grid snap against a wall
            # doubling back on the last direction is the dithering that reads as erratic on screen
            if m[0] == "hold" and last_dir and m[1] == OPPOSITE[last_dir]:
                sc -= 30
            results.append((sc, m))
        emu.mload(root)
        emu.mfree(root)
        results.sort(key=lambda t: t[0], reverse=True)
        best_sc, best = results[0]
        if streak_bomb and os.environ.get("ZELDA_STREAK_DEBUG"):
            print(f"    streak 9: bombs {s0.bombs} near {near_target} far {far} fuse_wait {len(rec.inputs) < streak_fuse_until} "
                  f"-> {best} {best_sc:.0f} | " + " ".join(f"{m[0][:2]}{(m[1] or '')[:1]}:{sc:.0f}" for sc, m in results[:6]), flush=True)
        if DECISION_LOG[0] is not None:
            DECISION_LOG[0].append({
                "frame": len(rec.inputs), "link": [s0.x, s0.y, s0.dir], "hearts": s0.hearts, "far": bool(far), "beam": bool(beam),
                "enemies": [[t_[0], t_[1], t_[2], t_[3], t_[4] >> 4, emu.byte(0x98 + t_[0])] for t_ in tlist],
                "field": [[q[0], q[1], v] for q, v in spot_field.items()] if spot_field else [],
                "branches": [{"macro": m[0], "dir": (m[1] if isinstance(m[1], str) else list(m[1])) if m[1] else None,
                              "n": m[2], "score": round(sc, 1)} for sc, m in results],
                "choice": [best[0], (best[1] if isinstance(best[1], str) else list(best[1])) if best[1] else None, best[2]]})
        if _FIGHT_DEBUG:
            print(f"    f{frames:4d} link ({s0.x},{s0.y}) h{s0.hearts} far={int(far)} beam={int(bool(beam))} "
                  + " ".join(f"{t_[1]:02X}@({t_[2]},{t_[3]})f{emu.byte(0x98 + t_[0])}h{t_[4] >> 4}" for t_ in tlist)
                  + f" -> {best[0]} {best[1]} {best_sc:.0f} | "
                  + " ".join(f"{m[0][:2]}{(m[1] if isinstance(m[1], str) else '>'.join(x[0] for x in m[1]) if m[1] else '')[:3]}:{sc:.0f}" for sc, m in results[1:]), flush=True)
        if best[0] == "go_swing":
            best = ("hold", best[1][0], 8)
        s = run_macro(emu, best, rec)
        last_dir = best[1] if best[0] == "hold" else last_dir
        if best[0] == "bomb" and streak_bomb:
            streak_fuse_until = len(rec.inputs) + FUSE + 10
        frames += {"hold": 8, "wait": 6, "bomb": FUSE, "shoot": 14}.get(best[0], 14)
        if log and best[0] in ("swing", "bomb"):
            hpn, nn = measure()
            if hpn < hp0 or nn < n0:
                emu.note(f"Lookahead: {best[0]} {best[1]} connected (target hp {hp0}->{hpn}, {n0}->{nn} left)")
    return "timeout"


def plan_reach(emu: BizHawk, rec, goal, *, max_frames: int = 3000, rollout: int = 12,
               rng: random.Random | None = None, exit_ok: bool = False,
               transit: bool = False) -> str:
    """Reach goal(x, y) with lookahead: score = progress toward the goal, minus damage/death.
    Used for dashes through rooms we don't want to fight (e.g. the eight-Darknut stairs room).
    If exit_ok, a room change or mode change counts as success (walking into stairs/doors).

    transit=True means "just run". It removes the swing from the macro list outright and stops
    pricing a lost half heart, so the planner takes the shortest line and eats whatever is in the way.
    That is a deliberate trade, not a better planner: on a leg whose only job is to be somewhere else,
    half a heart is worth a few hundred frames at most and the frames are the thing being scored. The
    owner, watching Level 4's ladder cellar, put it as "while he is leaving the room he is still
    fighting, he should just be running" - and the reason it was fighting is right here: `all_macros`
    offers ("swing", d) whenever anything killable is within 36 px, and a swing that connects reads as
    progress, so a room the bot is only passing through turns into a fight it did not need. Damage is
    priced at 800 per half heart, which is right for a fight and wrong for a corridor.

    Do not use transit where the room must be CLEARED - a shutter door needs every enemy dead, and
    "walk past" does not open one."""
    frames = 0
    walk_macros = [("hold", d, 8) for d in DIRS4] + [("wait", None, 4)]
    all_macros = walk_macros + [("swing", d, 0) for d in DIRS4]
    s0 = emu.state()
    room0 = s0.room
    last_dir = None
    tries_fa = 0
    lattice = goal_field = None
    if not OLD_PLANNER[0] and getattr(goal, "target", None) is not None:
        lattice = Lattice(emu)
        goal_field = lattice.field([goal.target])
    while frames < max_frames:
        s0 = emu.state()
        if s0.hearts <= 0:
            return "died"
        if s0.mode not in (5, 9) or s0.room != room0:
            return "arrived" if exit_ok else "left the room"
        if goal(s0.x, s0.y):
            return "arrived"
        tgt = getattr(goal, "target", None)
        if tgt is not None and not OLD_PLANNER[0]:
            tries_fa += 1
            if abs(s0.x - tgt[0]) + abs(s0.y - tgt[1]) <= 28 and tries_fa % 3 == 1:
                done = False
                for x_first in (True, False):
                    seq = []
                    root = emu.msave()
                    st = s0
                    stall, last = 0, None
                    for _ in range(48):
                        if goal(st.x, st.y):
                            break
                        dx, dy = tgt[0] - st.x, tgt[1] - st.y
                        if x_first:
                            d = ("Right" if dx > 0 else "Left") if dx else ("Down" if dy > 0 else "Up")
                        else:
                            d = ("Down" if dy > 0 else "Up") if dy else ("Right" if dx > 0 else "Left")
                        st = emu.step(d, 1)
                        seq.append(d)
                        stall = stall + 1 if (st.x, st.y) == last else 0
                        last = (st.x, st.y)
                        if stall >= 6 or st.mode not in (5, 9) or st.room != room0:
                            break
                    ok = goal(st.x, st.y) and st.hearts >= s0.hearts and st.mode in (5, 9) and st.room == room0
                    emu.mload(root)
                    emu.mfree(root)
                    if ok:
                        for d in seq:
                            rec.step(d, 1)
                        done = True
                        break
                if done:
                    return "arrived"
        # a swing is only worth considering with something killable in reach; offered always, it is
        # what Link does when a wall piece blocks every hold - stand there and cut the air
        if transit:
            macros = walk_macros           # just run: never offer the swing
        elif OLD_PLANNER[0]:
            macros = all_macros
        else:
            close = any(killable(e) and max(abs(e[2] - s0.x), abs(e[3] - s0.y)) <= 36 for e in read_enemies(emu))
            macros = all_macros if close else walk_macros
        dmg_scale = 0.0 if transit else caution(s0)
        root = emu.msave()
        n_before = len([e for e in read_enemies(emu) if e[1] != 0x49 and e[1] < 0x50])
        results = []
        order = list(macros)
        if rng:
            rng.shuffle(order)
        urgency = 1.0 + URGENCY * (frames / max_frames)
        for m in order:
            emu.mload(root)
            s1 = run_macro(emu, m)
            if s1.mode not in (5, 9) or s1.room != room0:
                sc = 5000 if exit_ok else -50000
            else:
                s2 = emu.step((), rollout)
                if s2.hearts <= 0:
                    sc = -100000
                elif s2.mode not in (5, 9) or s2.room != room0:
                    sc = 5000 if exit_ok else -50000
                else:
                    sc = -800 * dmg_scale * DMG_SCALE[0] * (s0.hearts - s2.hearts) * 2
                    if s2.keys < s0.keys:
                        sc -= 6000              # a dash never unlocks a door on the way
                    sc += 10 if goal(s2.x, s2.y) else 0
                    ens = [e for e in read_enemies(emu) if killable(e)]
                    from .overworld import harm_halfhearts
                    near = sum(max(0, (28 if harm_halfhearts(e[1]) < 3 else 44) - max(abs(e[2] - s2.x), abs(e[3] - s2.y)))
                               * max(1.0, harm_halfhearts(e[1]) / 2.0) for e in ens)
                    # impatience: keeping away from enemies matters less the longer this takes,
                    # otherwise a camping enemy (a Lynel on the White Sword screen) stalls Link
                    # forever at a safe distance and the attempt just runs out of frames
                    sc -= 1.5 * max(0.2, 1.0 - frames / max_frames) * near
                    sc += 40 * (n_before - len(ens))          # a kill on the way is worth a little
                    sc -= 0.4 * urgency * (8 if m[0] == "hold" else 14 if m[0] == "swing" else 4)
                    if m[0] == "wait":
                        sc -= 25 * urgency          # never idle as a way of staying safe
                    if m[0] == "hold" and (s1.x, s1.y) == (s0.x, s0.y):
                        sc -= 120                   # this hold is Link walking into a wall
                    if m[0] == "hold" and last_dir and m[1] == OPPOSITE[last_dir]:
                        sc -= 30                    # stop the back-and-forth dithering
                    results.append((sc, m, s1))
                    continue
            results.append((sc, m, s1))
        emu.mload(root)
        emu.mfree(root)
        # progress term needs the goal distance: compute from the branch end state
        scored = []
        for sc, m, s1 in results:
            d = goal_distance(goal, s1)
            if goal_field:
                d = lattice.walk(goal_field, s1.x, s1.y, d)
            scored.append((sc - 0.8 * (1.0 + 2.0 * frames / max_frames) * d, m))
        scored.sort(key=lambda t: t[0], reverse=True)
        best = scored[0][1]
        run_macro(emu, best, rec)
        last_dir = best[1] if best[0] == "hold" else last_dir
        frames += 8 if best[0] == "hold" else 14 if best[0] == "swing" else 4
    return "timeout"


def goal_distance(goal, s) -> float:
    """Manhattan distance to the goal's target if it exposes .target, else 0 when satisfied."""
    t = getattr(goal, "target", None)
    if t is None:
        return 0.0 if goal(s.x, s.y) else 100.0
    return abs(s.x - t[0]) + abs(s.y - t[1])


class Goal:
    def __init__(self, tx, ty, tol=8):
        self.target = (tx, ty); self.tol = tol
    def __call__(self, x, y):
        return abs(x - self.target[0]) <= self.tol and abs(y - self.target[1]) <= self.tol
