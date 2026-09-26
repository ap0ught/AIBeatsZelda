"""Captions for route 4's new segments and for the reused ones whose purpose changed with the new errand order."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pprint
import pathlib

from zelda.captions import CAPTIONS

NEW = {
    "warp_L3": ("OUTSIDE LEVEL 3", "New order: north-east first. A heart container, a hundred rupees, a candle and the White Sword - before Level 1."),
    "ow1_73": ("NORTH-EAST: THE LONG WALK", "Fifteen screens to a rock face with a heart container behind it. It is on the road to the White Sword."),
    "ow1_38": ("PAST LEVEL 1'S DOOR", "Level 1 is one screen west. Not yet: the White Sword first, so Level 1 is fought with twice the damage."),
    "h2c_heart": ("HEART ROCK", "One bomb opens this rock face. Heart container five - exactly what the White Sword's old man asks for."),
    "h2c_2d": ("EAST, TO A HIDDEN ROAD", "Two screens on, a wall that is drawn as rock and is not: the game's own secret road to a hundred rupees."),
    "cave_0f": ("A HUNDRED RUPEES", "\"It's a secret to everybody.\" Sixty of it buys a candle four screens from here; the rest goes toward arrows."),
    "cdl_0d": ("TO THE CANDLE SHOP", "West along the top of the map. The shop is an open cave one screen east of Level 5's door."),
    "cdl_0c": ("TO THE CANDLE SHOP", "The planner weighed three candle shops; this one is on the way to the White Sword."),
    "buy_candle": ("THE BLUE CANDLE - 60 RUPEES", "Level 8's door is a bush, and Level 7's red candle costs forty seconds of cellar. Walk into the right-hand ware ONLY."),
    "candle_leave": ("BACK OUTSIDE", "Candle in hand: trees that hide things can burn now - a heart container and a hundred rupees lie on roads ahead."),
    "cdl_1c": ("SOUTH, THEN WEST", "Down to the Lost Hills' row and west along it to the waterfall screen where the White Sword waits."),
    "ws_19": ("STRAIGHT WEST", "The third run doubled back through the Lost Hills here. The route planner pins the lane: one screen, not three."),
    "ow1_37": ("LEVEL 1'S SCREEN", "Back past Lynel country to Level 1 - with the White Sword this time."),
    "enter_L1": ("INTO LEVEL 1 WITH THE WHITE SWORD", "The third run fought this dungeon with the wooden sword. Everything in it now dies in half the hits."),
    "h47_heart": ("THE HEART TREE", "Burn the tree, take the heart container. It was a separate whirlwind trip last time; now it is on the road to Level 4."),
    "l4_21": ("LEVEL 4 - EAST, ONTO THE RING", "A moat room. Its island cannot reach the north wall - two squares of water, and the ladder spans one. The ring outside can."),
    "l4_11": ("LEVEL 4 - BOMB NORTH FROM THE RING", "Round the moat to the north wall and blow it. This skips three rooms, a fight, an old man's speech and a locked door."),
    "l4_12r": ("LEVEL 4 - BOMB EAST IN THE DARK", "Second bomb: the dark room's east wall opens next to Gleeok's door."),
    "r6b_68": ("TO THE SECOND HUNDRED", "South and east to a tree that hides a hundred rupees. It pays for the arrows and the bait."),
    "r6b_69": ("TO THE SECOND HUNDRED", "East along the forest's edge."),
    "r6b_6a": ("TO THE SECOND HUNDRED", "One more screen east."),
    "r6b_6b": ("TO THE SECOND HUNDRED", "The tree is in the middle of this screen - and Level 8's door is two screens further on."),
    "cave_6b": ("A HUNDRED RUPEES UNDER A TREE", "Burn it, take the money. Arrows are 80 and bait 60: with what is left of the first hundred, that is covered."),
    "l8a_5b": ("TO LEVEL 8", "North, then east: Level 8 straight after Level 4, because its door is here and the candle is already bought."),
    "enter_L8": ("BURN THE BUSH: LEVEL 8", "The blue candle gives one flame a screen. One is enough."),
    "l8a_5c": ("TO LEVEL 8", "East on the TOP lane: this screen's bottom lane is a dead end, and an unpinned crossing walked straight into it."),
    "l8a_5d": ("TO LEVEL 8", "One more screen east, then south onto Level 8's screen."),
    "l8a_6d": ("LEVEL 8'S SCREEN", "Down the right-hand lane, to the east side of the bush that hides the stairs."),
    "l2b_5d": ("TO LEVEL 2", "The warp sets Link down WEST of Level 8's stairs; going east means walking back in. North by the left lane."),
    "l2b_4d": ("TO LEVEL 2", "North again. Level 2's door is two screens away."),
    "l2b_4c": ("TO LEVEL 2", "West one screen."),
    "l2b_3c": ("LEVEL 2'S SCREEN", "North onto Level 2's screen - the fifth dungeon of nine, at about eighteen minutes."),
    "p7b_44": ("TO LEVEL 7", "Arrows and bait bought. South past the arrows shop, then west to the pond."),
    "p7b_54": ("TO LEVEL 7", "South one more screen."),
    "p7b_53": ("TO LEVEL 7", "West along the row south of the pond."),
    "p7b_52": ("TO LEVEL 7", "Into the split canyon on its TOP row - the only part of it that leads north to the pond."),
    "p7b_42": ("THE POND", "North onto the pond screen. The recorder drains it."),
    "ms_b31": ("SOUTH FROM THE GRAVEYARD", "The Magical Sword in hand, three screens to Level 6's door - which is why it was fetched now."),
    "ms_sword": ("THE MAGICAL SWORD", "Twelve hearts: seven dungeons, a rock and a tree. Four times the wooden sword, in time for Levels 6 and 9."),
    "enter_L6": ("INTO LEVEL 6 WITH THE MAGICAL SWORD", "Wizzrobe rooms were the slowest fights of the last run. They take half the hits now."),
}
for n, (h, w) in NEW.items():
    assert len(h) <= 40, (n, len(h))
    assert len(w) <= 150, (n, len(w))
CAPTIONS.update(NEW)
p = pathlib.Path("zelda/captions.py")
head = p.read_text(encoding="utf-8").split("CAPTIONS: dict[str, tuple[str, str]] = ", 1)[0]
p.write_text(head + "CAPTIONS: dict[str, tuple[str, str]] = " + pprint.pformat(CAPTIONS, width=118, sort_dicts=False) + "\n",
             encoding="utf-8")
print(f"{len(NEW)} captions added/updated; {len(CAPTIONS)} total")
