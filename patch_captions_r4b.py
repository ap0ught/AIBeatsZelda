"""Route 4: captions of REUSED segments whose purpose changed with the new errand order."""
import pprint
import pathlib

from zelda.captions import CAPTIONS

NEW = {
    "ws_28": ("NORTH-EAST: TO THE HEART ROCK", "North, then four screens east along the mountain's foot to a rock face with a heart container in it."),
    "ws_29": ("NORTH-EAST: TO THE HEART ROCK", "East along the foot of Death Mountain."),
    "ws_2a": ("NORTH-EAST: TO THE HEART ROCK", "East again. Lynels and Tektites: cut down only what stands in the lane."),
    "ws_2b": ("NORTH-EAST: TO THE HEART ROCK", "One more screen east."),
    "ws_2c": ("THE HEART ROCK'S SCREEN", "The rock face in the middle of this screen is hollow. One bomb."),
    "ws_1b": ("TO THE WHITE SWORD CAVE", "West into the Lost Hills' screen - its west exit is always open."),
    "ws_1a": ("TO THE WHITE SWORD CAVE", "West again, to the screen below the waterfall."),
    "ws_0a": ("TO THE WHITE SWORD CAVE", "North to the top row of the map. The cave is in the far corner."),
    "white_sword": ("THE WHITE SWORD", "Double damage, and the old man only hands it over at five hearts: three, Level 3's, and the heart rock's."),
    "l4w00_1a": ("DOWN TO LEVEL 1", "White Sword in hand BEFORE the first fighting dungeon. Eight screens south-west to Level 1."),
    "l4w04_18": ("DOWN TO LEVEL 1", "West along the mountain. Blue Lynels here hit for two hearts: the path prices that in."),
    "l4w05_17": ("DOWN TO LEVEL 1", "West once more, then the road turns south."),
    "l4w06_27": ("DOWN TO LEVEL 1", "South off the mountain."),
    "l4w07_28": ("DOWN TO LEVEL 1", "East one screen."),
    "l4w08_38": ("DOWN TO LEVEL 1", "South onto the screen beside Level 1's door."),
    "warp_L1": ("WARP OUT OF LEVEL 1", "Six hearts. Next: a heart container under a tree two screens away - the candle is already bought - then Level 4."),
    "ws_38": ("TO THE HEART TREE AND LEVEL 4", "East, south, west: the tree that hides a heart container is on the road to Level 4's raft."),
    "l4w09_48": ("TO THE HEART TREE AND LEVEL 4", "South. The tree is one screen west of here."),
    "l4w10_47": ("THE HEART TREE'S SCREEN", "One tree on this screen burns. The third run came back for it with the whirlwind; now it is simply on the way."),
    "warp_L4": ("LEVEL 4 DONE - BACK ON THE ISLAND", "Ladder in hand. Next: a hundred rupees under a tree, then Level 8 - its door is near and the candle is bought."),
    "l2_sail": ("RAFT OFF THE ISLAND", "Back to the dock on the shore, then east and south to the money tree."),
    "l2w00_56": ("EAST FROM THE DOCK", "Three screens east along this row, then south."),
    "l2w01_57": ("EAST FROM THE DOCK", "East again."),
    "l2w02_58": ("EAST FROM THE DOCK", "One more, then the road turns south toward the forest."),
    "warp_L8": ("LEVEL 8 DONE - FOURTH TRIFORCE", "Level 8 before Level 2: the order follows the map, not the numbers. Level 2 is four screens north-west."),
    "warp_L2": ("LEVEL 2 DONE - NEXT, LEVEL 5", "Ten hearts. Level 5 holds the recorder, and the recorder is the whirlwind: every long walk after it is a ride."),
    "warp_L5": ("OUT OF LEVEL 5", "The recorder. First ride: Level 4's island, four screens from the arrows and the bait."),
    "warp_L7": ("LEVEL 7 DONE - TWELVE HEARTS", "Seven dungeons, a rock and a tree: twelve heart containers. The Magical Sword's old man is past the Lost Woods."),
    "w8_52": ("TO THE MAGICAL SWORD", "South off the pond, then west through the Lost Woods to the graveyard."),
    "l7_62": ("TO THE MAGICAL SWORD", "South to the forest's edge."),
    "l7w20_50": ("PAST THE LOST WOODS", "Out of the maze. North up the far west edge of Hyrule to the graveyard."),
    "l7w21_40": ("PAST THE LOST WOODS", "North again."),
    "l7w22_41": ("PAST THE LOST WOODS", "East one screen."),
    "l7w23_31": ("PAST THE LOST WOODS", "North. The graveyard is the next screen up; Level 6's door is two screens east of it."),
    "l7w24_32": ("TO LEVEL 6", "East onto the staircase screen below Level 6's door."),
    "warp_L6": ("EIGHT TRIFORCES", "All eight pieces. One ride to Level 5's door, then west along the mountain to Spectacle Rock: Level 9."),
}
for n, (h, w) in NEW.items():
    assert n in CAPTIONS, n
    assert len(h) <= 40, (n, len(h))
    assert len(w) <= 150, (n, len(w))
CAPTIONS.update(NEW)
p = pathlib.Path("zelda/captions.py")
head = p.read_text(encoding="utf-8").split("CAPTIONS: dict[str, tuple[str, str]] = ", 1)[0]
p.write_text(head + "CAPTIONS: dict[str, tuple[str, str]] = " + pprint.pformat(CAPTIONS, width=118, sort_dicts=False) + "\n",
             encoding="utf-8")
print(f"{len(NEW)} captions updated; {len(CAPTIONS)} total")
