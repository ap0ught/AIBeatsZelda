"""Search a little deeper where it pays. With the OverBudget cut an extra attempt costs at most the best one's
length, and the third run showed how much the best-of-N matters on long rooms (the same Level 6 fight: 1,486
frames in run 2's search, 1,886 in run 3's). Long segments get 1.6x the patience; short ones are unchanged."""
import pathlib

p = pathlib.Path("zelda/search.py")
t = p.read_text(encoding="utf-8")
old = """                if best is not None and st["since"] >= limit:
                    if not st["stop"]:"""
new = """                if best is not None and best.frames >= 700 and limit < tries:
                    limit = min(tries, int(limit * 1.6))      # long rooms vary most between attempts
                if best is not None and st["since"] >= limit:
                    if not st["stop"]:"""
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched: deeper search on long segments")
