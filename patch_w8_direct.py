"""Ride to Level 8 straight from the screen below the pond: the six screens east along row 6 were only ever
walked because the whirlwind idea landed mid-walk in the second run."""
import ast, pathlib
p = pathlib.Path("fullgame.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
a = t.index('    # The whirlwind is no help here: its cycle now holds only the doors of Levels 5, 6 and 7, and')
b = t.index('    # --- THE WHIRLWIND, NOT THE WALK (switched mid-run at 0x67).')
cut = t[a:b]
assert '"w8_62"' in cut and 'w8_{room:02x}' in cut
t = t[:a] + '''    # (Step off the pond screen first - there the recorder drains the water instead of calling the wind -
    # and ride from 0x52. The second run walked six screens east before riding only because the idea
    # arrived mid-walk.)
''' + t[b:]
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
import fullgame
names = [s[0] for s in fullgame.segments()]
i = names.index("warp_L7")
print(len(names), names[i:i + 8])
