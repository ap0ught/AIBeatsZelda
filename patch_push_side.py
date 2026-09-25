"""push_any_block: try the REMEMBERED push direction first. Level 7's 0D block can be pushed from either
side; the stairs it uncovers are outside the ring of blocks (top-right corner), so pushing it Right from
inside the ring leaves Link walled in and walking all the way round, while pushing it Left from the
corridor leaves him 48 px below the stairs (the owner's suggestion, and the probe agrees: both work)."""
import json
import pathlib

p = pathlib.Path("zelda/overworld.py")
t = p.read_text(encoding="utf-8")
old = """        sides = (("Up", 0, 21), ("Down", 0, -19), ("Right", -19, 3), ("Left", 21, 3))
        for br, bc in blocks:"""
new = """        sides = (("Up", 0, 21), ("Down", 0, -19), ("Right", -19, 3), ("Left", 21, 3))
        if known and len(known) >= 3:
            sides = tuple(sorted(sides, key=lambda sd: sd[0] != known[2]))      # the side that worked before first
        for br, bc in blocks:"""
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8")

b = pathlib.Path("knowledge/blocks.json")
d = json.loads(b.read_text(encoding="utf-8"))
print("was", d.get("L7_0d"))
d["L7_0d"] = [5, 12, "Left"]
b.write_text(json.dumps(d, indent=1), encoding="utf-8")
print("now", d["L7_0d"])
