import ast, pathlib
def load(p):
    raw = pathlib.Path(p).read_bytes(); return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw
def save(p, t, crlf):
    ast.parse(t); pathlib.Path(p).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
t, crlf = load("zelda/search.py")
old = '''def parallel_search(scouts, navs, state_name: str, factory, success, *, tries: int = 60, max_frames: int = 900,
                    setup=None, log=print, label: str = "", patience: int = 8):'''
new = '''def parallel_search(scouts, navs, state_name: str, factory, success, *, tries: int = 60, max_frames: int = 900,
                    setup=None, log=print, label: str = "", patience: int = 14):'''
assert t.count(old) == 1; t = t.replace(old, new)
old = '''                elif best.hearts >= min(c, st["h0"]):
                    limit = max(4, patience - 2)     # unhurt: little left to find'''
new = '''                elif best.hearts >= min(c, st["h0"]):
                    limit = patience                 # unhurt: search on a while for a faster line'''
assert t.count(old) == 1; t = t.replace(old, new)
save("zelda/search.py", t, crlf)
t, crlf = load("zelda/runner.py")
old = '''        best = parallel_search(self.scouts, self.snavs, start, factory, success, tries=tries,'''
new = '''        # Four scouts make attempts cheap, and fights vary by a factor of two between attempts: look longer.
        best = parallel_search(self.scouts, self.snavs, start, factory, success, tries=max(tries, 60),'''
assert t.count(old) == 1; t = t.replace(old, new)
save("zelda/runner.py", t, crlf)
print("patience 14, tries >= 60")
