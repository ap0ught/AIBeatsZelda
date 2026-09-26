"""Captions for the segments the third route changed (the rest of zelda/captions.py still describes what Link does)."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pprint
import pathlib

from zelda.captions import CAPTIONS

NEW = {
    "l1_43": ("LEVEL 1 - BOMB THE NORTH WALL",
              "One bomb through 53's north wall skips a three-room loop and a locked door - and the key detour that paid for it."),
    "l1_45": ("LEVEL 1 - THE BOOMERANG ROOM",
              "The boomerang is in here. The last run fought for it and never threw it once, so walk straight through."),
    "l1_53_key": ("LEVEL 1 - FIVE STALFOS, ONE KEY",
                  "The key only appears once all five Stalfos are dead. Take it, then blast north."),
    "l4_40_key": ("LEVEL 4 - DARK ROOM, KEY ON THE FLOOR",
                  "The key is just lying here. Dodge the five Zols, take it, go north - no need to kill anything in the dark."),
    "l4_02": ("LEVEL 4 - DARK KEESE ROOM, FLOOR KEY",
              "Two one-tile water gaps: the stepladder crosses each. Take the key on the floor - Level 5 starts with it - then east."),
    "l5_66": ("LEVEL 5 - NORTH FROM THE ENTRANCE", "One room north: a key on the floor and a wall to bomb."),
    "l5_66_key": ("LEVEL 5 - FLOOR KEY AMONG GIBDOS",
                  "The key lies on the floor: dodge the three Gibdos (two hearts a touch) and take it. The first lock is far ahead."),
    "l5_65": ("LEVEL 5 - BOMB THE WEST WALL",
              "No door leads west, so blow one open - dashing in and dodging while the fuse burns, not standing in the Gibdos."),
    "l5_64": ("LEVEL 5 - BOMB THE NEXT WALL WEST",
              "One more wall, same trick. Behind it: five Blue Darknuts and a ring of blocks around the staircase."),
    "l6_78": ("LEVEL 6 - UNLOCK WEST, THEN NORTH",
              "A key from Level 5 opens the entrance's west door. The old route went east for a key first."),
    "l6_48": ("LEVEL 6 - EIGHT BLUE KEESE, ONE KEY",
              "A shutter room: all eight Keese must die before north opens - and the key they leave is needed at Gohma's door."),
    "l6_29": ("LEVEL 6 - BOMB EAST, SKIP THE DRAGON",
              "This wall is also 29's wall. One bomb skips a Gleeok, a locked door and a dead-end tour of six rooms."),
    "l6_39": ("LEVEL 6 - FLOOR KEY AMONG WIZZROBES",
              "The key is on the floor: take it and leave south. Five Wizzrobes - the boomerang passes through them, so don't linger."),
    "l6_1d": ("LEVEL 6 - THE BOSS WING", "The south door is open: walk past the Zols and Like Likes, cutting down only what blocks the way."),
    "l6_2c": ("LEVEL 6 - LAST LOCKED DOOR",
              "Locked, not a shutter - nothing here has to die. Dash to the north door past the blade traps and Wizzrobes."),
    "l7_49": ("LEVEL 7 - SIX GORIYAS", "The north door is open. Go through them, cutting down whatever stands in the way."),
    "l7_38": ("LEVEL 7 - WEST TO THE LOCKED DOOR",
              "Straight on west. The old route bombed east for a key Link did not need - and coming back spawned a Digdogger here."),
    "l7_28": ("LEVEL 7 - LOCKED DOOR TO THE GORIYA", "A key, not a cleared room, opens this door. The hungry Goriya is in the room beyond."),
    "l7_19": ("LEVEL 7 - PAST THE HUNGRY GORIYA",
              "The east door is locked, so nothing in here has to die: cross and unlock. Clearing it cost 44 seconds last time."),
    "l7_1c": ("LEVEL 7 - SIX GORIYAS, LOCKED DOOR", "Locked, not a shutter: through the Goriyas to the east door and unlock it."),
    "l8_6e": ("LEVEL 8 - NORTH FROM THE ENTRANCE", "The entrance room is empty, so straight north."),
    "l8_7f_key": ("LEVEL 8 - FLOOR KEY",
                  "The key is lying on the floor: grab it and go back west. Level 9 has three locked doors and few keys."),
    "l8_5e_key": ("LEVEL 8 - FIVE BLUE DARKNUTS",
                  "Both ways on are shutters, so all five Darknuts must die. Their key comes too. Then one step west."),
    "l8_5d_key": ("LEVEL 8 - IN AND OUT FOR A FLOOR KEY",
                  "A key on the floor, one room off the route. Take it, dodge the Pols Voice and Gibdos, and step back east."),
    "l8_4e": ("LEVEL 8 - NORTH THROUGH THE SHUTTER",
              "5E's north shutter opens onto 4E. The old route looped west through three rooms and a locked door to get here."),
    "l8_3e": ("LEVEL 8 - UNLOCK NORTH", "Fight only what blocks the way. The north door takes a key, not a cleared room."),
    "l8_3c": ("LEVEL 8 - BOMB NORTH INTO THE BOSS ROOM",
              "Eight Pols Voices - and the boss is behind this room's north wall. Dash, bomb, dodge the fuse, go. None of them has to die."),
    "m9_16": ("LEVEL 9 - THREE BLUE WIZZROBES", "The east door is open: go through, into the room that holds a pile of four bombs."),
    "wl8_3c": ("THE WHIRLWIND TO LEVEL 2",
               "The game keeps a destination counter in RAM ($523). Read it, face the right way, one note, one ride."),
    "hc_w37": ("THE WHIRLWIND TO LEVEL 1",
               "One note back. Three screens from a tree that hides a heart container; the Magical Sword wants twelve."),
    "ms_w22": ("THREE NOTES, ONE RIDE",
               "Each note moves the counter one level and freezes the game, the wind too. Play three before it arrives: Level 6."),
    "dm9_w0b": ("THE WHIRLWIND TO DEATH MOUNTAIN", "One note back to Level 5's door. Level 9 is a bombable rock at the top."),
    "5b_bombs": ("LEVEL 3 - THREE DARKNUTS FOR BOMBS",
                 "Clearing this room pays four bombs, and bombs open Manhandla's wall and kill Manhandla. Then north."),
}
for n, (h, w) in NEW.items():
    assert len(h) <= 40, (n, len(h))
    assert len(w) <= 150, (n, len(w))
CAPTIONS.update(NEW)
p = pathlib.Path("zelda/captions.py")
head = p.read_text(encoding="utf-8").split("CAPTIONS: dict[str, tuple[str, str]] = ", 1)[0]
p.write_text(head + "CAPTIONS: dict[str, tuple[str, str]] = " + pprint.pformat(CAPTIONS, width=118, sort_dicts=False) + "\n",
             encoding="utf-8")
print(f"{len(NEW)} captions updated; {len(CAPTIONS)} total")
