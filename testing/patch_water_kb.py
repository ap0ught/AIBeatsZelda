"""Water is never floor. The tile knowledge base had learned dungeon water (F4) and overworld river tiles as
"walkable" because Link stepped on them - on the stepladder. After that the planner routed straight across
four-tile-wide water in every ladder room and burned its attempts on BLOCKED moves (Level 4's dark Keese
room: 0 of 6 crossings). Water is passable only where water_bridges() says the ladder spans it."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast, json, pathlib
p = pathlib.Path("zelda/overworld.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
def sub(old, new, what):
    global t
    assert t.count(old) == 1, (what, t.count(old))
    t = t.replace(old, new); print("  applied:", what)
sub('''    def is_walkable(self, tid: int, optimistic: bool) -> bool:
        if tid in self.solid:
            return False''', '''    def is_water(self, tid: int) -> bool:
        return tid == 0xF4 if self.current == "dg" else (0x90 <= tid < 0xA0 if self.current == "ow" else False)

    def is_walkable(self, tid: int, optimistic: bool) -> bool:
        if self.is_water(tid):
            return False           # only ever crossed on the stepladder (legal()'s cells_ok)
        if tid in self.solid:
            return False''', "water is never walkable")
sub('''    def learn(self, tid: int, walkable: bool, why: str) -> None:
        (self.walkable if walkable else self.solid).add(tid)''', '''    def learn(self, tid: int, walkable: bool, why: str) -> None:
        if self.is_water(tid):
            return                 # stepping on water means the ladder was under him; learn nothing
        (self.walkable if walkable else self.solid).add(tid)''', "never learn water")
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
kb = pathlib.Path("knowledge/tiles.json"); d = json.loads(kb.read_text())
for c, test in (("dg", lambda x: x == 0xF4), ("ow", lambda x: 0x90 <= x < 0xA0)):
    before = len(d[c]["walkable"])
    d[c]["walkable"] = [x for x in d[c]["walkable"] if not test(x)]
    print(f"  {c}: removed {before - len(d[c]['walkable'])} water ids from walkable")
kb.write_text(json.dumps(d, indent=1))
