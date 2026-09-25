"""push_any_block returned the moment the tile map changed - which is when the block STARTS to slide. The
staircase (or the door) only appears when it arrives, 16-odd frames later, so the caller looked, saw no
stairs and gave up (Level 7's 0D: 40 of 60 attempts). Let the block finish before reporting."""
import pathlib

p = pathlib.Path("zelda/overworld.py")
t = p.read_text(encoding="utf-8")
old = """                now = read_cells(emu)
                if any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):
                    emu.note(f"That block moved when pushed {push}")
                    self.remember_block(s0.level, s0.room, br, bc, push)
                    return True
        emu.note("No block would move")"""
new = """                now = read_cells(emu)
                if any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):
                    # the map changed when the block LEFT its tile; what it uncovers (stairs, a door) only
                    # appears when it arrives. Wait for the map to change again, or for it to settle.
                    moving = [row[:] for row in now]
                    for _ in range(40):
                        emu.step((), 1)
                        now = read_cells(emu)
                        if any(now[r][c] != moving[r][c] for r in range(22) for c in range(32)):
                            emu.step((), 2)
                            break
                    emu.note(f"That block moved when pushed {push}")
                    self.remember_block(s0.level, s0.room, br, bc, push)
                    return True
        emu.note("No block would move")"""
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched push_any_block")
