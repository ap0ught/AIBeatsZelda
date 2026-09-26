"""Bomb walls from wherever there is floor: rooms full of blocks (Level 6's 0x28, Level 4's 0x10) put a block on
the standard spot a tile and a half from the wall. Candidates now run up to the wall itself and to the tiles
beside the doorway (facing along the wall, the bomb lands on the same square)."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast, pathlib
def load(p):
    raw = pathlib.Path(p).read_bytes(); return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw
def save(p, t, crlf):
    ast.parse(t); pathlib.Path(p).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
t, crlf = load("zelda/bot.py")
old = '''def bomb_door(nav, direction: str, log=print):'''
new = '''BOMB_CANDIDATES = {   # (stand x, stand y, face): nearest the measured spot first
    "Right": [(184, 141, "Right"), (192, 141, "Right"), (200, 141, "Right"), (208, 141, "Right"),
              (208, 125, "Down"), (208, 157, "Up")],
    "Left":  [(56, 141, "Left"), (48, 141, "Left"), (40, 141, "Left"), (32, 141, "Left"),
              (32, 125, "Down"), (32, 157, "Up")],
    "Up":    [(120, 93, "Up"), (104, 93, "Right"), (136, 93, "Left")],
    "Down":  [(120, 181, "Down"), (120, 189, "Down"), (104, 189, "Right"), (136, 189, "Left")],
}


def bomb_spot(emu, direction: str):
    """The first bombing candidate that is floor and reachable from where Link stands, or the standard one."""
    from .lookahead import Lattice
    lat = Lattice(emu)
    s = emu.state()
    field = lat.field([(s.x, s.y)])
    for x, y, face in BOMB_CANDIDATES[direction]:
        if (x, y) in lat.free and (x, y) in field:
            return x, y, face
    x, y = BOMB_SPOTS[direction]
    return x, y, direction


def bomb_door(nav, direction: str, log=print):'''
assert t.count(old) == 1
t = t.replace(old, new)
old = '''    tx, ty = BOMB_SPOTS[direction]
    emu.note(f"Bombable wall on the {direction} side: standing at ({tx},{ty}) and placing a bomb")
    s = nav.go(lambda x, y: x == tx and y == ty, f"the bombing spot for the {direction} wall")
    doors0 = emu.byte(0xEE)
    emu.step(direction, 1)'''
new = '''    tx, ty, face = bomb_spot(emu, direction)
    emu.note(f"Bombable wall on the {direction} side: standing at ({tx},{ty}) facing {face} and placing a bomb")
    s = nav.go(lambda x, y: x == tx and y == ty, f"the bombing spot for the {direction} wall")
    doors0 = emu.byte(0xEE)
    emu.step(face, 1)'''
assert t.count(old) == 1
t = t.replace(old, new)
save("zelda/bot.py", t, crlf)

t, crlf = load("fullgame.py")
old = '''            tx, ty = bot.BOMB_SPOTS[direction]
            doors0 = emu.byte(0xEE)
            for _ in range(3):'''
new = '''            tx, ty, face = bot.bomb_spot(emu, direction)
            doors0 = emu.byte(0xEE)
            for _ in range(3):'''
assert t.count(old) == 1
t = t.replace(old, new)
old = '''                rec.step(direction, 1)
                rec.step("B", 2)
                emu.step = orig
                plan_reach(emu, rec, Goal(tx, ty, -1), max_frames=72, rng=rng)     # dodge while it burns'''
new = '''                rec.step(face, 1)
                rec.step("B", 2)
                emu.step = orig
                plan_reach(emu, rec, Goal(tx, ty, -1), max_frames=72, rng=rng)     # dodge while it burns'''
assert t.count(old) == 1
t = t.replace(old, new)
save("fullgame.py", t, crlf)

t, crlf = load("zelda/lookahead.py")
old = '''                from .overworld import box_cells
                if any(cells[cy][cx] in BLOCK_IDS for cy, cx in box_cells(x, y) if 0 <= cy < 22 and 0 <= cx < 32):
                    continue
                if legal(cells, kb, x, y, True, None, both):'''
new = '''                # (blocks are left to the tile knowledge base: Link's head may overlap a block's lower half,
                # which is what lets him through a diagonal line of them)
                if legal(cells, kb, x, y, True, None, both):'''
assert t.count(old) == 1
t = t.replace(old, new)
save("zelda/lookahead.py", t, crlf)

q = pathlib.Path("probe_chain.py"); s = q.read_text(encoding="utf-8")
s = s.replace('''    ("bomb E 28->29", lambda nav: fg.bomb_policy(nav, "Right", 0x29), lambda s: s.room == 0x29),''',
              '''    ("dash-bomb E 28->29", lambda nav: fg.dash_bomb_policy(nav, "Right", 0x29), lambda s: s.room == 0x29),''')
s = s.replace('''    ("bomb E 10->11", lambda nav: fg.bomb_policy(nav, "Right", 0x11), lambda s: s.room == 0x11),
    ("bomb E 11->12", lambda nav: fg.bomb_policy(nav, "Right", 0x12), lambda s: s.room == 0x12),''',
              '''    ("dash-bomb E 10->11", lambda nav: fg.dash_bomb_policy(nav, "Right", 0x11), lambda s: s.room == 0x11),
    ("dash-bomb E 11->12", lambda nav: fg.dash_bomb_policy(nav, "Right", 0x12), lambda s: s.room == 0x12),''')
s = s.replace('''    ("bomb W 66->65", lambda nav: fg.bomb_policy(nav, "Left", 0x65), lambda s: s.room == 0x65),
    ("bomb W 65->64", lambda nav: fg.bomb_policy(nav, "Left", 0x64), lambda s: s.room == 0x64)]),''',
              '''    ("dash-bomb W 66->65", lambda nav: fg.dash_bomb_policy(nav, "Left", 0x65), lambda s: s.room == 0x65),
    ("dash-bomb W 65->64", lambda nav: fg.dash_bomb_policy(nav, "Left", 0x64), lambda s: s.room == 0x64)]),''')
q.write_text(s, encoding="utf-8")
print("bomb spots adaptive")
