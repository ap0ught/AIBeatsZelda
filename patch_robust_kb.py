import ast, pathlib
def load(p):
    raw = pathlib.Path(p).read_bytes(); return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw
def save(p, t, crlf):
    ast.parse(t); pathlib.Path(p).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
def sub(t, old, new, what):
    assert t.count(old) == 1, (what, t.count(old)); print("  applied:", what); return t.replace(old, new)
t, crlf = load("zelda/overworld.py")
t = sub(t, '''        if path.exists():
            d = json.loads(path.read_text())
            if "walkable" in d:''', '''        if path.exists():
            d = _read_json(path)
            if "walkable" in d:''', "TileKB reads under the lock")
t = sub(t, '''import threading as _threading
_KB_LOCK = _threading.Lock()
''', '''import threading as _threading
_KB_LOCK = _threading.RLock()


def _read_json(path, default=None):
    """Read a knowledge file under the lock, retrying briefly: on Windows a reader that has the file open makes
    another thread's os.replace fail with 'Access is denied', which killed a scout's thread mid-search."""
    import time as _t
    for _ in range(5):
        with _KB_LOCK:
            try:
                return json.loads(path.read_text())
            except (OSError, ValueError):
                pass
        _t.sleep(0.02)
    return {} if default is None else default


def _write_json(path, obj) -> None:
    import os
    import time as _t
    with _KB_LOCK:
        tmp = path.with_suffix(".tmp%d_%d" % (os.getpid(), _threading.get_ident()))
        try:
            tmp.write_text(json.dumps(obj, indent=1))
            for _ in range(5):
                try:
                    os.replace(tmp, path)
                    return
                except OSError:
                    _t.sleep(0.03)
        except OSError:
            pass
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
''', "locked read / retried write helpers")
t = sub(t, '''            try:
                disk = json.loads(self.path.read_text())
            except (OSError, ValueError):
                disk = {}
            for c, v in disk.items():''', '''            disk = _read_json(self.path)
            for c, v in disk.items():''', "TileKB.save reads via helper")
t = sub(t, '''            tmp = self.path.with_suffix(".tmp%d" % os.getpid())
            tmp.write_text(json.dumps({c: {"walkable": sorted(v["walkable"]), "solid": sorted(v["solid"]),
                                           "evidence": v["evidence"]} for c, v in self.ctx.items()}, indent=1))
            os.replace(tmp, self.path)''', '''            _write_json(self.path, {c: {"walkable": sorted(v["walkable"]), "solid": sorted(v["solid"]),
                                        "evidence": v["evidence"]} for c, v in self.ctx.items()})''', "TileKB.save writes via helper")
t = sub(t, '''        try:
            return json.loads(self.BLOCKS_PATH.read_text()).get(f"L{level}_{room:02x}")
        except Exception:
            return None''', '''        return _read_json(self.BLOCKS_PATH).get(f"L{level}_{room:02x}")''', "known_block via helper")
t = sub(t, '''        d = {}
        try:
            d = json.loads(self.BLOCKS_PATH.read_text())
        except Exception:
            pass
        d[f"L{level}_{room:02x}"] = [br, bc, push]
        import os
        with _KB_LOCK:
            tmp = self.BLOCKS_PATH.with_suffix(".tmp%d" % os.getpid())
            tmp.write_text(json.dumps(d, indent=1))
            os.replace(tmp, self.BLOCKS_PATH)''', '''        with _KB_LOCK:
            d = _read_json(self.BLOCKS_PATH)
            if d.get(f"L{level}_{room:02x}") == [br, bc, push]:
                return                       # already known: do not rewrite the file for nothing
            d[f"L{level}_{room:02x}"] = [br, bc, push]
            _write_json(self.BLOCKS_PATH, d)''', "remember_block robust")
save("zelda/overworld.py", t, crlf)

t, crlf = load("zelda/search.py")
t = sub(t, '''            try:
                outcome = policy(emu, rec, rng, max_frames)
            except LinkDied:
                outcome = "died"
            except TimeoutError as e:
                outcome = "timeout: " + str(e)[:40]
            s = emu.state()
            try:
                ok = outcome != "died" and success(emu, s)''', '''            try:
                outcome = policy(emu, rec, rng, max_frames)
            except LinkDied:
                outcome = "died"
            except TimeoutError as e:
                outcome = "timeout: " + str(e)[:40]
            except (OSError, ValueError, KeyError, IndexError) as e:
                outcome = f"error: {type(e).__name__}: {str(e)[:40]}"     # one bad attempt, not a dead scout
            s = emu.state()
            try:
                ok = outcome != "died" and not str(outcome).startswith("error:") and success(emu, s)''', "a policy error is a failed attempt, not a dead thread")
# more variety between attempts: identical attempts cannot dodge a hit that one of them takes
t = sub(t, '''        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25] if OLD_AVOIDANCE[0] else [0.0, 0.03, 0.08]))''',
        '''        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25] if OLD_AVOIDANCE[0] else [0.0, 0.0, 0.04, 0.10, 0.18]))''', "cross jitter variety")
t = sub(t, '''            rec.step((), rng.randint(0, 40) if OLD_AVOIDANCE[0] else rng.randint(0, 6))''',
        '''            rec.step((), rng.randint(0, 40) if OLD_AVOIDANCE[0] else rng.choice([0, 1, 2, 3, 4, 6, 9, 13, 18, 24]))''', "cross lead-in variety")
save("zelda/search.py", t, crlf)
print("robust knowledge files; more varied attempts")
