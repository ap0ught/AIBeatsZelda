"""Run 5 caption audit: facts that were true of an older route or an older run (owner: "they seem to be based on
previous runs"). Counts are now read live from the game (intent.fill: {tri1} {containers} {bombs} ...)."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pprint
import pathlib

from zelda.captions import CAPTIONS

LONG = "NORTH-EAST: THE LONG WALK"
NEW = {
    # the walk after Level 3 goes PAST Level 1 to the heart rock - the headings said "TO LEVEL 1" for eight screens
    "ow1_63": (LONG, "North, back up to the row the route came along."),
    "ow1_64": (LONG, "Turn east. The heart rock is far to the north-east; Level 1's door is on the way and gets walked past."),
    "ow1_65": (LONG, "East along the same row the walk to Level 3 came in on."),
    "ow1_66": (LONG, "Still east, fighting only what gets in the way."),
    "ow1_67": (LONG, "East again. A rock here hides thirty rupees - not worth the stop: two hundred-rupee caves pay for everything."),
    "ow1_68": (LONG, "One more screen east, then the road turns north."),
    "ow1_58": (LONG, "Turn north. Level 1's door is three screens up and one west - and the route walks past it."),
    "ow1_48": (LONG, "North again."),
    "l1_63": ("LEVEL 1 - ENTRANCE", "Key in hand: spend it on the entrance's locked north door."),
    "l1_b33": ("LEVEL 1 - RETRACING SOUTH", "Back down through the Goriya room, heading for the boomerang room's locked west door."),
    "aquamentus": ("BOSS: AQUAMENTUS", "Three fireballs in a spread. At full hearts the sword throws beams and he dies from across the room; "
                                       "otherwise the planner goes in close."),
    "L1_done": ("LEVEL 1 - TRIFORCE PIECE {tri1} OF 8", "Aquamentus is dead and his heart container taken. East into the next room for the Triforce piece."),
    "warp_L1": ("WARP OUT OF LEVEL 1", "{containers:C} hearts. Next: a heart container under a tree two screens away - the candle is already bought - "
                                       "then Level 4."),
    "l4_32": ("LEVEL 4 - FIVE VIRES ON THE WALKWAYS", "All five Vires must die to open the east shutter. The lookahead fighter plays each move forward "
                                                      "before it commits."),
    "l4_02": ("LEVEL 4 - DARK KEESE ROOM, FLOOR KEY", "Two one-tile water gaps: the stepladder crosses each. Take the key on the floor - the next "
                                                      "dungeon starts with it - then east."),
    "L4_done": ("LEVEL 4 - TRIFORCE PIECE {tri1} OF 8", "Gleeok is dead and its heart is taken. North to the Triforce piece; taking it ends Level 4 "
                                                        "and warps Link out."),
    "r8_3f_bombs": ("LEVEL 8 - A PILE OF BOMBS", "{bombs:C} bombs in hand, and walls ahead that each want one. Clear the room and take the four it "
                                                 "gives before moving on."),
    "r8_3f_st": ("LEVEL 8 - STAIRS TO THE GLEEOK'S WING", "The staircase stands in the open. It is the join to the pocket with the Gleeok and the "
                                                          "Triforce piece, which no door reaches."),
    "l8_heart": ("LEVEL 8 - HEART CONTAINER", "Take the Gleeok's heart container, number {containers1}. The Magical Sword's old man wants twelve."),
    "L8_done": ("LEVEL 8 - TRIFORCE PIECE {tri1} OF 8", "North to the Triforce piece. Taking it ends Level 8 and warps Link back outside."),
    "warp_L8": ("LEVEL 8 DONE - {tri:W} TRIFORCES", "Level 8 before Level 2: the order follows the map, not the numbers. Level 2 is four screens "
                                                    "north-west."),
    "l2_3f": ("LEVEL 2 - MOLDORM, DETOUR EAST", "Dodongo only dies to bombs and Link has {bombs}; Level 7's walls want five more. The room to the "
                                               "east gives four."),
    "L2_done": ("LEVEL 2 - TRIFORCE PIECE {tri1} OF 8", "Take Dodongo's heart container, then west to the Triforce piece. Taking it ends Level 2 "
                                                        "and warps Link out."),
    "warp_L2": ("LEVEL 2 DONE - NEXT, LEVEL 5", "{containers:C} hearts. Level 5 holds the recorder, and the recorder is the whirlwind: every long "
                                                "walk after it is a ride."),
    "l5w03_2d": ("TO LEVEL 5: THE LOST HILLS", "North to 2D, then west. The hundred-rupee cave north-east of here was emptied on the way to the "
                                               "White Sword."),
    "l5w04_2c": ("TO LEVEL 5: THE LOST HILLS", "West to 2C, then north and west to the foot of the Lost Hills."),
    "l5_heart": ("LEVEL 5 - DIGDOGGER'S ROOM", "{containers1:C} heart containers now. Pick up anything still on the floor before going north for the "
                                               "Triforce."),
    "L5_done": ("LEVEL 5 - TRIFORCE PIECE {tri1} OF 8", "North of Digdogger's room. The piece ends Level 5 and warps Link out to its door; eight of "
                                                        "them open Death Mountain."),
    "l7d_1b": ("LEVEL 7 - EAST ALONG THE TOP", "Bomb this room's east wall and keep following the top corridor to the far staircase."),
    "l7_aqua": ("LEVEL 7 BOSS - AQUAMENTUS AGAIN", "The same boss Level 1 had, with the same White Sword - and twice the hearts behind it."),
    "L7_done": ("LEVEL 7 - TRIFORCE PIECE {tri1} OF 8", "Out the east door to the Triforce piece. Taking it ends Level 7 and warps Link back outside."),
    "l6_78": ("LEVEL 6 - UNLOCK WEST, THEN NORTH", "A key carried in from an earlier dungeon opens the entrance's west door. The old route went east "
                                                   "for a key first."),
    "l6_heart": ("A HEART CONTAINER", "{containers1:C} now - the last heart container of the run."),
    "L6_done": ("LEVEL 6 - TRIFORCE PIECE {tri1} OF 8", "The Triforce room is directly north of Gohma's. Touch the piece and the game carries Link "
                                                        "outside."),
    "dm9_19": ("TO LEVEL 9: SPECTACLE ROCK", "Still west. No bombs are bought for Level 9: Link carries {bombs:w}, and a pile of four inside tops "
                                             "him up."),
    "g9_04_bomb": ("BOMBS IN HAND AT A BOMBABLE WALL", "The drop table only gives bombs from one monster group, and only on certain kills. With "
                                                       "{bombs:w} in hand, the Red Wizzrobe hunt is skipped."),
    "g9_52_patra": ("ANOTHER PATRA", "The room directly beneath Ganon."),
}
for n, (h, w) in NEW.items():
    assert n in CAPTIONS, n
    assert len(h) <= 40, (n, len(h), h)
    assert len(w) <= 150, (n, len(w))
CAPTIONS.update(NEW)
p = pathlib.Path("zelda/captions.py")
head = p.read_text(encoding="utf-8").split("CAPTIONS: dict[str, tuple[str, str]] = ", 1)[0]
p.write_text(head + "CAPTIONS: dict[str, tuple[str, str]] = " + pprint.pformat(CAPTIONS, width=118, sort_dicts=False) + "\n",
             encoding="utf-8")
print(f"{len(NEW)} captions updated; {len(CAPTIONS)} total")
