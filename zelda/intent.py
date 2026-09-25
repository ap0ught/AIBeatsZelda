"""What the bot is trying to do in each room, and why - the text the video's panel shows.

The owner's note after watching the first run: "id like to see the reasoning behind each room, and
what you're trying to accomplish... theres many times where you just make interesting choices that a
player wouldnt make, which is great and funny, but the 'why' would just be neat to see."

So each segment gets a HEAD (where we are) and a WHY (what we are doing here and the reason). Keyed
by segment name, because the segment tuples are built by ~200 `S.append((name,) + cross(...))` sites
and adding a fifth field would mean touching every one of them.

Most rooms are crossings and get their reason from the family rules in `for_segment` below; rooms
where the bot does something a person would find odd get their own entry, because those are the ones
worth explaining.
"""
from __future__ import annotations

import re

# name -> (head, why)
INTENT: dict[str, tuple[str, str]] = {
    # -- the opening -------------------------------------------------------
    "start": ("POWER ON", "Register a file and walk into the first cave. The old man's sword is the "
                          "only weapon in the game you are given rather than having to earn."),
    "enter_L3": ("LEVEL 3 - THE MANJI", "Third dungeon first: it holds the raft, and without the raft "
                                        "two later dungeons cannot be reached at all."),
    "cellar": ("LEVEL 3 - CELLAR", "The raft. This is why we came here first."),
    "manhandla": ("BOSS: MANHANDLA", "Four heads, and the sword only reaches one at a time. "
                                     "One bomb catches all four."),
    "L3_done": ("TRIFORCE 1 of 8", "The Triforce piece ends the dungeon and warps us out."),

    # -- level 1 -----------------------------------------------------------
    "enter_L1": ("LEVEL 1 - THE EAGLE", "Six locked doors and no bombs yet, so every key has to be "
                                        "found the hard way."),
    "l1_bow": ("LEVEL 1 - CELLAR: THE BOW", "Gohma in Level 6 cannot be hurt by anything else. "
                                            "Buying arrows later is pointless without this."),
    "aquamentus": ("BOSS: AQUAMENTUS", "He fires three fireballs in a spread. At full health the "
                                       "sword throws beams, so we fight him from across the room."),

    # -- white sword, level 4 ---------------------------------------------
    "white_sword": ("THE WHITE SWORD", "Double damage, and the cave only opens with five heart "
                                       "containers. This is what makes Gleeok survivable."),
    "l4_sail": ("THE RAFT", "The island dungeon has no bridge. This is the only way across."),
    "enter_L4": ("LEVEL 4 - THE SNAKE", "The stepladder is in here, and without it half the "
                                        "overworld's secrets are behind water we cannot cross."),
    "l4_ladder": ("LEVEL 4 - CELLAR: THE STEPLADDER", "Crosses one-tile water. Several rupee caves "
                                                      "and Level 8's approach need it."),
    "l4_12": ("LEVEL 4 - BLADE TRAPS", "Six traps that cannot be killed, only baited. We walk the "
                                       "lane between them instead of fighting."),
    "gleeok": ("BOSS: GLEEOK", "Two heads on long necks; each has to be killed separately, and the "
                               "loose head keeps flying and spitting after the neck is gone."),

    # -- level 2, 5 --------------------------------------------------------
    "enter_L2": ("LEVEL 2 - THE MOON", "Short dungeon, and it holds the magic boomerang."),
    "enter_L5": ("LEVEL 5 - THE LIZARD", "The recorder is in here - Level 7's door is under a pond "
                                         "that only the recorder drains."),
    "l5_recorder": ("LEVEL 5 - THE RECORDER", "Drains the pond over Level 7, splits Digdogger, and "
                                              "warps between finished dungeons."),

    # -- money and shops ---------------------------------------------------
    "cave_6b": ("A HUNDRED RUPEES UNDER A TREE", "Burning the right tree pays better than an hour of "
                                                 "killing things. Measured, not read in a guide."),
    "cave_67": ("IT'S A SECRET TO EVERYBODY", "One bomb, thirty rupees, under a rock Link was walking "
                                              "past anyway. Farming the same money costs about twenty "
                                              "times as long - and the last run spent ten minutes doing "
                                              "exactly that."),
    "farm68": ("EARNING THE REST", "Still short for the arrows. The cave covered most of it, so this "
                                   "is a top-up, not the ten-minute grind it used to be."),
    "farm80": ("EIGHTY RUPEES: ARROWS", "Gohma in Level 6 can only be killed with an arrow, and arrows "
                                        "are sold, never found."),
    "buy_food": ("BUYING MONSTER BAIT", "Sixty rupees for a piece of meat, because one Goriya in "
                                        "Level 7 cannot be killed - only fed."),
    "buy_arrows": ("BUYING ARROWS", "Gohma takes arrows and nothing else. They are sold, not found - "
                                    "and the secret caves already paid for them."),
    "shop_leave": ("OUT OF THE ARROWS SHOP", "The bait is one screen further north, so buy that on the "
                                             "same trip."),
    "food_leave": ("OUT OF THE GRAVEYARD", "Both purchases done - one detour instead of two expeditions."),
    "l7_62": ("TOWARD THE LOST WOODS", "Level 6 sits on the far side of the only maze into the west."),
    "l7_61": ("THE EDGE OF THE LOST WOODS", "From here the forest has to be walked north, west, south, "
                                            "west - anything else loops."),
    "wl8_3c": ("RIDING THE WHIRLWIND TO LEVEL 2", "Level 8's door is a long walk along the bottom of the "
                                              "map, and four screens from Level 2's door. The wind is faster."),
    "n9_6c": ("OFF THE STAIRCASE", "The whirlwind will not pick Link up while he stands on a dungeon's "
                                   "stairs."),
    "hc_w37": ("RIDING THE WHIRLWIND TO LEVEL 1", "Three screens from a tree that hides a heart "
                                                  "container. The Magical Sword's old man wants twelve; "
                                                  "Link has eleven."),
    "hc_47_heart": ("HEART CONTAINER NUMBER TWELVE", "Burn the tree. Inside: a potion on the left, a "
                                                     "container on the right. Take the container."),
    "ms_w22": ("RIDING TO LEVEL 6'S DOOR", "The Magical Sword is under a gravestone three screens away."),
    "dm9_w0b": ("RIDING TO THE FOOT OF DEATH MOUNTAIN", "Level 5's door. Level 9 is a bombable rock at the "
                                                       "top of the mountain."),
    "enter_L9": ("LEVEL 9 - DEATH MOUNTAIN", "Entered once. The first run went in three times: for a "
                                             "sword, for bombs, and for real."),
    "m9_16_bombs": ("A PILE OF BOMBS", "Level 9 is bombable walls from here to Ganon. Take the pile "
                                       "instead of buying them."),
    "r6_18": ("INTO THE GLEEOK'S ROOM", "The shutters close behind Link, so the search sends him in with "
                                        "as many hearts as it can find."),

    # -- level 6, 7, 8 -----------------------------------------------------
    "enter_L6": ("LEVEL 6 - THE DRAGON", "Wizzrobes that shoot through walls, and Gohma at the top."),
    "l6_mini": ("A GLEEOK IN THE CORRIDOR", "Not the boss - just standing in the way. Point blank "
                                            "with the sword, because there is no room to retreat."),
    "gohma": ("BOSS: GOHMA", "The eye only opens for a moment and only an arrow hurts it. Sword, "
                             "bombs and boomerang all do nothing."),
    "l7_drain": ("PLAYING THE RECORDER AT THE POND", "Level 7's entrance is under the water. The "
                                                     "recorder drains it."),
    "l7_feed": ("THE HUNGRY GORIYA", "He cannot be killed by anything. He moves aside for meat, "
                                     "which is what the sixty rupees bought."),
    "l7_candle": ("THE RED CANDLE", "Burns as often as we like. Every 'burn the bush' secret on the "
                                    "map opens up from here."),
    "l7_38": ("BOSS: DIGDOGGER", "The sword bounces off. The recorder splits it into three small "
                                 "ones that can be cut down."),
    "enter_L8": ("LEVEL 8 - THE LION", "The magical key and the book. Every guide says burn a bush "
                                       "to get in; the tile is drawn as mountain."),
    "l8_4b": ("EIGHT POLS VOICE", "They ignore the sword and kill Link in melee. One arrow each."),
    "l8_gleeok": ("BOSS: GLEEOK, FOUR HEADS", "Twice the heads of the Level 4 one."),
    "dodongo": ("BOSS: DODONGO", "It eats bombs. That is the whole fight: feed it one, then cut it "
                                 "down while it is stunned."),
    "digdogger": ("BOSS: DIGDOGGER", "Armoured against the sword. The recorder's note shatters it "
                                     "into three small ones."),
    "s9_patra": ("BOSS: PATRA", "The core cannot be touched until all eight orbiting eyes are dead, "
                                "and only the sword hurts any of it - bombs, arrows and the boomerang "
                                "were all measured at zero."),
    "g9_52_patra": ("A SECOND PATRA", "The room directly beneath Ganon."),
    "l4_heart": ("A HEART CONTAINER", "Every container is one more mistake Link can survive later."),
    "l6_heart": ("A HEART CONTAINER", "Nine now. Twelve is what the Magical Sword's old man wants."),
    "l1_44_boom": ("THE MAGIC BOOMERANG", "Stuns almost everything, and reaches items across gaps "
                                          "Link cannot walk over."),

    # -- the finale --------------------------------------------------------
    "ms_sword": ("THE MAGICAL SWORD", "Four times the wooden sword. Ganon takes four hits from it "
                                      "instead of fifteen, and the old man only hands it over with "
                                      "twelve heart containers."),
    "s9_silver": ("THE SILVER ARROW", "The only thing in the game that can kill Ganon."),
    "g9_04_bomb": ("OUT OF BOMBS AT A BOMBABLE WALL", "The drop table only gives bombs from one "
                                                      "monster group, and only on certain kills - so "
                                                      "kill a Red Wizzrobe FIRST and take what drops."),
    "g9_ganon": ("GANON", "He is invisible: the sword only lands while he cannot be seen. Four hits "
                          "stun him, and then one Silver Arrow, fired before he recovers."),
    "g9_power": ("THE TRIFORCE OF POWER", "It sets no inventory byte at all - the game just plays a "
                                          "fanfare. Taking it means walking onto it."),
    "g9_zelda": ("ZELDA", "Four guard fires, then stand on the one square that starts the ending."),
    "g9_credits": ("THE END", "Beaten from power-on: no cheats, no memory writes, no save states."),
}

# Dungeon interiors whose segment names are just room numbers ("7c_left", "49_key", "4a_bombs").
# They all belong to Level 3, the first dungeon the run plays.
ROOM_NAME = re.compile(r"^[0-9a-f]{2}_")

# family rules: (prefix, head, why) - first match wins, so put specific prefixes first
FAMILIES: list[tuple[str, str, str]] = [
    ("ws_", "WALKING TO THE WHITE SWORD", "The second sword sits in a cave on the mountain, and the "
                                          "old man will not hand it over under five heart containers."),
    ("hills_", "THE LOST HILLS", "Walk the wrong way here and the screen simply repeats. The way "
                                 "through is a fixed sequence, the same every time."),
    ("bwoods_", "THE LOST WOODS, GOING BACK", "The same trick in reverse."),
    ("woods_", "THE LOST WOODS", "Four screens that all look identical. Take a wrong turn and the "
                                 "forest puts Link back where he started."),
    ("back", "WALKING BACK", "The shop is one way; the dungeon is the other."),
    ("bw", "WALKING BACK", "Retracing the way out to the next thing that matters."),
    ("heal", "A FAIRY POND", "Free hearts, and cheaper than dying in the next dungeon."),
    ("p7", "TOWARD LEVEL 7", "The dungeon under the pond."),
    ("sh7", "UP TO THE ARROWS SHOP", "It is two screens off the road west. Buying here, on the way, is "
                                     "what lets Level 6 be climbed once instead of twice."),
    ("bait_", "THE GRAVEYARD SHOP", "Monster bait is sold under a gravestone, one screen north of the "
                                    "arrows."),
    ("fw7", "BACK ON THE ROAD WEST", "Arrows and bait bought. Next: the Lost Woods, and Level 6 behind "
                                     "them."),
    ("m7", "CROSSING TO THE SHOPS", "Hyrule's shops are caves scattered across the map."),
    ("b7", "BACK TO LEVEL 7", "With the meat that the Goriya wants."),
    ("w7", "LEAVING LEVEL 7", "On to the next dungeon."),
    ("w8", "TOWARD LEVEL 8", "Along the bottom of the map, where the lion's door is hidden."),
    ("n8", "TOWARD LEVEL 8", "Working east across the desert."),
    ("o8", "TOWARD LEVEL 8", "Down the east edge."),
    ("m8", "AROUND LEVEL 8", "Walking between the dungeon door and what the route still needs."),
    ("s8", "TOWARD LEVEL 8", "The last stretch to the lion."),
    ("dm9", "UP DEATH MOUNTAIN", "Magical Sword, twelve hearts, arrows and bombs: Level 9 gets entered "
                                "once, with everything it needs."),
    ("wl8", "TOWARD LEVEL 8", "Four screens from Level 2's door to the lion's. Walking there along the "
                              "bottom of the map is far longer."),
    ("n9", "TOWARD DEATH MOUNTAIN", "Level 9's door is at the top of the map, and the road there is "
                                    "the most dangerous walk in the game."),
    ("h9", "TOWARD DEATH MOUNTAIN", "The mountain road."),
    ("x9", "OUT OF LEVEL 9", "Leaving to fetch something the last dungeon needs."),
    ("r9", "BACK INTO LEVEL 9", "Returning with what was missing."),
    ("rb", "THE SUPPLY RUN", "Sailing back across the lake for bombs."),
    ("ms_", "TOWARD THE MAGICAL SWORD", "Twelve heart containers buys the best sword in the game."),
    ("m9", "LEVEL 9", "Death Mountain."),
    ("l7w", "CROSSING HYRULE", "Walking to the next dungeon."),
    ("l5w", "CROSSING HYRULE", "Walking to the next dungeon."),
    ("l4w", "CROSSING HYRULE", "Walking to the next dungeon."),
    ("l2w", "CROSSING HYRULE", "Walking to the next dungeon."),
    ("l3w", "CROSSING HYRULE", "Walking to the next dungeon."),
    ("warp_", "RECORDER WARP", "The recorder drops Link at a finished dungeon's door. Free travel, "
                               "paid for by having beaten the place."),
    ("whirl", "RIDING THE WHIRLWIND", "The note sends a whirlwind that carries Link across Hyrule. "
                                      "Which way he faces decides which dungeon it drops him at."),
    ("enter_", "GOING IN", "The dungeon door."),
    ("hc_", "A HEART CONTAINER IN A CAVE", "Hidden behind a rock or a tree. More hearts is more "
                                           "mistakes Link can afford later."),
    ("farm", "EARNING RUPEES THE SLOW WAY", "Killing the same rooms over and over because the shop "
                                            "will not take promises."),
    ("fd", "EARNING RUPEES THE SLOW WAY", "Dungeon rooms refill with monsters every time Link walks "
                                          "back in. It is tedious and it is money."),
    ("shop", "WALKING TO THE SHOP", "Hyrule's shops are caves, and they are a long way apart."),
    ("l9_", "LEVEL 9 - DEATH MOUNTAIN", "The last dungeon. Everything in here hits hard."),
    ("s9_", "LEVEL 9", "Working toward the Silver Arrow."),
    ("g9_", "LEVEL 9", "The last rooms before Ganon."),
    ("l", "CROSSING", "Getting to the next room that matters."),
    ("ow", "CROSSING HYRULE", "Walking the overworld to the next dungeon."),
]


def for_segment(name: str, narration: dict | None = None) -> tuple[str, str]:
    """(head, why) for a segment.

    Order: a hand-written entry, then the old one-line NARRATION, then the structural rules, then a
    generic crossing. Never returns the raw segment name - a panel reading "l7w03_52" tells a viewer
    nothing, and 244 of the run's segments fell through to exactly that before these rules existed.
    """
    try:                                 # the fact-checked per-room captions, when they exist
        from .captions import CAPTIONS
        if name in CAPTIONS:
            return CAPTIONS[name]
    except ImportError:
        pass
    if name in INTENT:
        return INTENT[name]
    if narration and name in narration:
        return narration[name], ""
    if name.endswith("_done"):
        return ("A TRIFORCE PIECE", "Eight of these open Death Mountain. Taking one ends the dungeon "
                                    "and puts Link back outside.")
    if name.endswith("_key"):
        return ("A KEY", "Locked doors outnumber keys in here, so every one has to be earned - "
                         "usually by clearing the room it is in.")
    if ROOM_NAME.match(name):
        return ("LEVEL 3 - THE MANJI", "The first dungeon the run plays, because the raft is in it "
                                       "and two later dungeons cannot be reached without one.")
    for prefix, head, why in FAMILIES:
        if name.startswith(prefix):
            return head, why
    return ("CROSSING", "Getting to the next room that matters.")


# ---- live numbers ---------------------------------------------------------------------------------------------
# The owner, after the fourth run: "sometimes the descriptions of what you are doing are incorrect. they seem to be
# based on previous runs". They were: a caption that says "TRIFORCE 8 OF 8" or "down to three bombs" is a fact about
# the run it was written for, and the route has changed twice since. Counts are now read from the game at the moment
# the caption goes up: write {tri1:w} OF 8, {containers:w} heart containers, {bombs} bombs.
_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
          "thirteen", "fourteen", "fifteen", "sixteen"]
_ORD = ["zeroth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
        "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth"]


class _N(int):
    """An int that can spell itself: {x} -> 8, {x:w} -> eight, {x:W} -> EIGHT, {x:o} -> eighth, {x:O} -> EIGHTH."""
    def __format__(self, spec):
        v = int(self)
        if spec in ("w", "W", "C", "o", "O") and 0 <= v < len(_WORDS):
            s = (_WORDS if spec in "wWC" else _ORD)[v]
            return s.upper() if spec in "WO" else s.capitalize() if spec == "C" else s
        return format(v, spec if spec not in ("w", "W", "C", "o", "O") else "")


class _Keep(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def facts_from(state) -> dict:
    """The numbers a caption may quote, from an emulator State."""
    tri = bin(getattr(state, "triforce", 0) & 0xFF).count("1")
    hearts = getattr(state, "hearts", 0)
    return {"tri": _N(tri), "tri1": _N(tri + 1), "containers": _N(int(getattr(state, "containers", 0))),
            "containers1": _N(int(getattr(state, "containers", 0)) + 1),
            "hearts": (int(hearts) if float(hearts).is_integer() else hearts),
            "bombs": _N(getattr(state, "bombs", 0)), "keys": _N(getattr(state, "keys", 0)),
            "rupees": _N(getattr(state, "rupees", 0))}


def fill(text: str, facts: dict | None) -> str:
    if not facts or "{" not in text:
        return text
    try:
        return text.format_map(_Keep(facts))
    except (ValueError, IndexError, KeyError):
        return text

