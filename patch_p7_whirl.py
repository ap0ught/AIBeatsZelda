"""Level 6 -> the pond by WHIRLWIND to Level 3's door (0x74), five screens from it, instead of ten screens on
foot - two of them Lynel country. Screen 0x32 is a one-tile-wide staircase with Lynels at the bottom of it: the
third run lost four hearts and 1,212 frames there with the careful planner dithering up and down the steps.
Probe (probe_chain.py p7_whirl): 1,904 and 2,017 frames door to pond, half a heart, against 3,420 and four.
The recorder ends up in B, which the pond wants anyway, and the wind's counter ends a note nearer Level 2."""
import pathlib
import pprint

p = pathlib.Path("fullgame.py")
t = p.read_text(encoding="utf-8")
start = t.index("    for d, room in zip([\"Down\", \"Left\", \"Down\", \"Left\", \"Down\", \"Down\", \"Right\", \"Right\", \"Up\", \"Up\"],")
end = t.index("    S.append((\"l7_drain\", pond_policy,")
new = '''    # BY WHIRLWIND. On foot the pond is ten screens from Level 6's door, and the second of them (0x32) is a
    # one-tile staircase with Lynels at the foot of it: four hearts and 1,212 frames in the third run. Level 3's
    # door (0x74) is five quiet screens from the pond - west, north, west, north, north - and the wind's counter
    # sits on Level 4 after the shop trip, so it is ONE note facing Left. The recorder stays in B for the pond.
    S.append(("p7_w74", lambda nav: whirl_to_policy(nav, 0x74),
              lambda emu, s: s.room == 0x74 and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Left", "Up", "Left", "Up", "Up"], [0x73, 0x63, 0x62, 0x52, 0x42]):
        S.append((f"p7_{room:02x}",) + cross(d, room, 40))
'''
t = t[:start] + new + t[end:]
p.write_text(t, encoding="utf-8")

from zelda.captions import CAPTIONS
NEW = {
    "warp_L6": ("OUTSIDE LEVEL 6'S DOOR",
                "Level 7 hides under a pond ten screens away on foot - through Lynel country. The whirlwind knows a "
                "shorter way."),
    "p7_w74": ("ONE NOTE TO LEVEL 3'S DOOR",
               "Level 3's door is five quiet screens from the pond. The wind's counter sits on Level 4: face left, one "
               "note, one ride."),
    "p7_73": ("TO LEVEL 7: THE POND", "West from Level 3's door. Moblins and Octoroks from here on - nothing that hits hard."),
    "p7_63": ("TO LEVEL 7: THE POND", "North, into the forest south of the pond."),
    "p7_62": ("TO LEVEL 7: THE POND", "West again. From the next screen the road turns north toward the pond."),
    "p7_52": ("TO LEVEL 7: THE POND",
              "This canyon splits into two lanes that never meet. Link is in the western one, which leads north."),
    "p7_42": ("TO LEVEL 7: THE POND", "North onto the pond screen. The recorder is already in hand."),
}
for n, (h, w) in NEW.items():
    assert len(h) <= 40, (n, len(h))
    assert len(w) <= 150, (n, len(w))
CAPTIONS.update(NEW)
for dead in ("p7_32", "p7_31", "p7_41", "p7_40", "p7_50", "p7_60", "p7_61"):
    CAPTIONS.pop(dead, None)
c = pathlib.Path("zelda/captions.py")
head = c.read_text(encoding="utf-8").split("CAPTIONS: dict[str, tuple[str, str]] = ", 1)[0]
c.write_text(head + "CAPTIONS: dict[str, tuple[str, str]] = " + pprint.pformat(CAPTIONS, width=118, sort_dicts=False) + "\n",
             encoding="utf-8")
print("route patched;", len(CAPTIONS), "captions")
